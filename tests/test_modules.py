"""Pruebas unitarias de cada módulo por separado (simulación MyHDL).

Metodología del anteproyecto: cada módulo se verifica de forma independiente
antes de integrarlo en el nivel superior.
"""

import os
import random

from myhdl import (Signal, StopSimulation, always, block, delay, instance,
                   instances, intbv)

from candado.datapath import code_comparator, code_register, digit_buffer
from candado.display import display_driver
from candado.glyphs import (G_BLANK, GLYPH_DEFS, GLYPH_ROM, table_text,
                            word_to_indices)
from candado.inputs import debouncer
from candado.params import HW, SIM
from candado.states import STATE_NAMES, STATE_RGB, STATE_WORDS
from candado.status import status_outputs
from candado.testing import decode_uart
from candado.timebase import tick_timer
from candado.uart import event_logger, uart_tx

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


@block
def _clock(clk):
    @always(delay(5))
    def gen():
        clk.next = not clk

    return gen


def _run(bench):
    bench().run_sim(quiet=1)


# --------------------------------------------------------------------------
def test_debouncer_un_pulso_por_pulsacion_y_filtra_rebotes():
    D = 8
    log = {"pulses": 0, "level_trace": []}

    @block
    def bench():
        clk, din = Signal(False), Signal(False)
        level, pulse = Signal(False), Signal(False)
        dut = debouncer(clk, din, level, pulse, D)
        ck = _clock(clk)

        def hold(v, n):
            din.next = v
            for _ in range(n):
                yield clk.posedge
                yield delay(1)
                log["pulses"] += int(pulse)
                log["level_trace"].append(int(level))

        @instance
        def stim():
            yield from hold(0, 10)
            # glitch de 3 ciclos (< D): ni nivel ni pulso
            yield from hold(1, 3)
            yield from hold(0, 20)
            assert log["pulses"] == 0 and max(log["level_trace"]) == 0
            # pulsación con rebotes al subir
            for v, n in ((1, 2), (0, 2), (1, 3), (0, 1)):
                yield from hold(v, n)
            yield from hold(1, 40)
            assert log["pulses"] == 1 and log["level_trace"][-1] == 1
            # rebotes al soltar: sigue en alto hasta estabilizar abajo
            for v, n in ((0, 2), (1, 1), (0, 2), (1, 2)):
                yield from hold(v, n)
            assert log["level_trace"][-1] == 1
            yield from hold(0, 40)
            assert log["level_trace"][-1] == 0 and log["pulses"] == 1
            # segunda pulsación: segundo pulso
            yield from hold(1, 30)
            yield from hold(0, 30)
            assert log["pulses"] == 2
            raise StopSimulation()

        return instances()

    _run(bench)


def test_debouncer_retardo_igual_al_tiempo_de_antirrebote():
    D = 8
    seen = {}

    @block
    def bench():
        clk, din = Signal(False), Signal(False)
        level, pulse = Signal(False), Signal(False)
        dut = debouncer(clk, din, level, pulse, D)
        ck = _clock(clk)

        @instance
        def stim():
            yield clk.posedge
            yield delay(1)
            din.next = 1
            n = 0
            while not level:
                yield clk.posedge
                yield delay(1)
                n += 1
                assert n < 100
            seen["delay"] = n
            raise StopSimulation()

        return instances()

    _run(bench)
    # 2 FF de sincronización + D ciclos de estabilidad (+1 de registro del nivel)
    assert D <= seen["delay"] <= D + 4


def test_tick_timer_periodo_y_clear():
    N = 10
    ticks = []

    @block
    def bench():
        clk, clear, tick = Signal(False), Signal(False), Signal(False)
        dut = tick_timer(clk, clear, tick, N)
        ck = _clock(clk)

        @instance
        def stim():
            for cyc in range(100):
                yield clk.posedge
                yield delay(1)
                if tick:
                    ticks.append(cyc)
            # clear reinicia la fase
            clear.next = 1
            yield clk.posedge
            yield delay(1)
            clear.next = 0
            n = 0
            while not tick:
                yield clk.posedge
                yield delay(1)
                n += 1
            ticks.append(("tras_clear", n))
            raise StopSimulation()

        return instances()

    _run(bench)
    periodic = [t for t in ticks if isinstance(t, int)]
    assert [b - a for a, b in zip(periodic, periodic[1:])] == [N] * (len(periodic) - 1)
    assert ticks[-1] == ("tras_clear", N)


def test_digit_buffer_push_delete_clear_y_orden():
    @block
    def bench():
        clk, rst, clear = Signal(False), Signal(False), Signal(False)
        push, delete = Signal(False), Signal(False)
        digit = Signal(intbv(0)[4:])
        count = Signal(intbv(0, min=0, max=5))
        seq = Signal(intbv(0)[16:])
        dut = digit_buffer(clk, rst, clear, push, delete, digit, count, seq)
        ck = _clock(clk)

        def pulse(sig, d=None):
            if d is not None:
                digit.next = d
            sig.next = 1
            yield clk.posedge
            yield delay(1)
            sig.next = 0
            yield clk.posedge
            yield delay(1)

        @instance
        def stim():
            yield clk.posedge
            for d in (0x1, 0x2, 0x3):
                yield from pulse(push, d)
            assert count == 3 and int(seq) >> 4 == 0x123
            yield from pulse(delete)
            assert count == 2
            yield from pulse(push, 0x9)            # reescribe la 3ª posición
            yield from pulse(push, 0x4)
            assert count == 4 and seq == 0x1294
            yield from pulse(push, 0xF)            # lleno: se ignora
            assert count == 4 and seq == 0x1294
            yield from pulse(clear)
            assert count == 0 and seq == 0
            yield from pulse(delete)               # vacío: no baja de 0
            assert count == 0
            yield from pulse(push, 0xA)
            rst.next = 1
            yield clk.posedge
            yield delay(1)
            assert count == 0 and seq == 0
            raise StopSimulation()

        return instances()

    _run(bench)


def test_code_register_valor_de_fabrica_escritura_y_reset_duro():
    @block
    def bench():
        clk, rst, we = Signal(False), Signal(True), Signal(False)
        new = Signal(intbv(0)[16:])
        code = Signal(intbv(0x1234)[16:])
        dut = code_register(clk, rst, we, new, code, 0x1234)
        ck = _clock(clk)

        @instance
        def stim():
            yield clk.posedge
            yield delay(1)
            assert code == 0x1234
            rst.next = 0
            new.next = 0xBEEF
            yield clk.posedge
            yield delay(1)
            assert code == 0x1234                  # sin we no cambia
            we.next = 1
            yield clk.posedge
            yield delay(1)
            we.next = 0
            assert code == 0xBEEF
            rst.next = 1
            yield clk.posedge
            yield delay(1)
            assert code == 0x1234                  # el reset duro restaura
            raise StopSimulation()

        return instances()

    _run(bench)


def test_comparador():
    rnd = random.Random(7)

    @block
    def bench():
        seq, code = Signal(intbv(0)[16:]), Signal(intbv(0)[16:])
        match = Signal(False)
        dut = code_comparator(seq, code, match)

        @instance
        def stim():
            for _ in range(300):
                a = rnd.randrange(65536)
                b = a if rnd.random() < 0.4 else (a ^ (1 << rnd.randrange(16)))
                seq.next, code.next = a, b
                yield delay(1)
                assert bool(match) == (a == b)
            raise StopSimulation()

        return instances()

    _run(bench)


# --------------------------------------------------------------------------
def _expected_display(state, left):
    word = STATE_WORDS[state].ljust(4, "_")
    pats = {}
    for i, g in enumerate(word_to_indices(word)):
        pats[7 - i] = GLYPH_ROM[g]
    pats[3] = pats[2] = pats[1] = GLYPH_ROM[G_BLANK]
    pats[0] = GLYPH_ROM[1 + left]            # glifos 1..4 = dígitos 0..3
    return pats


def test_display_driver_muestra_estado_e_intentos_restantes():
    p = SIM
    frame = 8 << p.scan_bits

    @block
    def bench():
        clk = Signal(False)
        state = Signal(intbv(0)[3:])
        left = Signal(intbv(0, min=0, max=4))
        seg, an = Signal(intbv(0)[7:]), Signal(intbv(0)[8:])
        dut = display_driver(clk, state, left, seg, an, p.scan_bits)
        ck = _clock(clk)

        @instance
        def stim():
            for s in range(len(STATE_NAMES)):
                for l in range(4):
                    state.next, left.next = s, l
                    shown = {}
                    for _ in range(3 * frame):
                        yield clk.posedge
                        yield delay(1)
                        one_hot = int(an)
                        if bin(one_hot).count("1") == 1 and _ > 4:
                            shown[one_hot.bit_length() - 1] = int(seg)
                    assert shown == _expected_display(s, l), (STATE_NAMES[s], l)
            raise StopSimulation()

        return instances()

    _run(bench)


def test_status_leds_termometro_banderas_y_rgb():
    p = SIM

    @block
    def bench():
        clk = Signal(False)
        state = Signal(intbv(0)[3:])
        count = Signal(intbv(0, min=0, max=5))
        led, rgb = Signal(intbv(0)[16:]), Signal(intbv(0)[3:])
        dut = status_outputs(clk, state, count, led, rgb, p.pwm_bits)
        ck = _clock(clk)

        @instance
        def stim():
            colores = set()
            for s in range(len(STATE_NAMES)):
                for c in range(5):
                    state.next, count.next = s, c
                    seen_rgb = set()
                    for _ in range(2 << p.pwm_bits):
                        yield clk.posedge
                        yield delay(1)
                        seen_rgb.add(int(rgb))
                    therm = (1 << c) - 1
                    flags = {5: 1 << 15, 4: 1 << 14, 3: 1 << 13, 6: 1 << 12}.get(s, 0)
                    assert int(led) == flags | therm, (STATE_NAMES[s], c)
                    assert seen_rgb == {0, STATE_RGB[s]}      # PWM: apagado o color
                colores.add(STATE_RGB[s])
            assert len(colores) == len(STATE_NAMES)           # un color por estado
            raise StopSimulation()

        return instances()

    _run(bench)


# --------------------------------------------------------------------------
def test_uart_tx_8n1():
    B = 8
    payload = [0x00, 0x55, 0xFF, ord("A"), 0x0A]
    samples = []

    @block
    def bench():
        clk, rst = Signal(False), Signal(False)
        data = Signal(intbv(0)[8:])
        start, busy, txd = Signal(False), Signal(False), Signal(True)
        dut = uart_tx(clk, rst, data, start, busy, txd, B)
        ck = _clock(clk)

        @always(clk.posedge)
        def sampler():
            samples.append(int(txd))

        @instance
        def stim():
            yield clk.posedge
            for b in payload:
                data.next = b
                start.next = 1
                yield clk.posedge
                start.next = 0
                n = 0
                yield delay(1)
                while busy:
                    yield clk.posedge
                    yield delay(1)
                    n += 1
                assert abs(n - 10 * B) <= 2                 # 10 bits por byte
            for _ in range(20):
                yield clk.posedge
            raise StopSimulation()

        return instances()

    _run(bench)
    assert list(decode_uart(samples, B)) == payload


def test_event_logger_texto_y_ranura_pendiente():
    B = 8
    samples = []

    @block
    def bench():
        clk, rst = Signal(False), Signal(False)
        state = Signal(intbv(0)[3:])
        fail = Signal(intbv(0, min=0, max=4))
        txd = Signal(True)
        dut = event_logger(clk, rst, state, fail, txd, B)
        ck = _clock(clk)

        @always(clk.posedge)
        def sampler():
            samples.append(int(txd))

        @instance
        def stim():
            def goto(s, f=0, wait=0):
                state.next, fail.next = s, f
                yield clk.posedge
                for _ in range(wait):
                    yield clk.posedge

            # Una línea de 12 bytes dura 12 * 10 * B = 960 ciclos.
            yield clk.posedge
            yield from goto(1, 0, 1100)           # INPUT: se envía completo
            yield from goto(2, 0, 1)              # VALIDATE: no se registra
            yield from goto(4, 1, 1100)           # ERROR con 1 fallo
            yield from goto(5, 3, 100)            # ALARM: empieza a enviarse ...
            yield from goto(1, 0, 50)             # ... INPUT llega durante el envío ...
            yield from goto(0, 0, 1900)           # ... e IDLE lo reemplaza (ranura única)
            raise StopSimulation()

        return instances()

    _run(bench)
    text = decode_uart(samples, B).decode()
    assert text == ("INPUT    0\r\n"
                    "ERROR    1\r\n"
                    "ALARM    3\r\n"
                    "IDLE     0\r\n")     # INPUT se descartó: sólo se guarda el último


# --------------------------------------------------------------------------
def test_tabla_de_glifos_coincide_con_el_archivo_del_repositorio():
    path = os.path.join(ROOT, "tables", "glyphs_abcdefg.txt")
    assert open(path, encoding="utf-8").read() == table_text()
    for _, pat, _ in GLYPH_DEFS:
        assert len(pat) == 7 and set(pat) <= {"0", "1"}


def test_digitos_de_la_tabla_son_los_estandar():
    # 0..3 en abcdefg
    patrones = {k: p for k, p, _ in GLYPH_DEFS}
    assert patrones["0"] == "1111110" and patrones["1"] == "0110000"
    assert patrones["2"] == "1101101" and patrones["3"] == "1111001"


def test_parametros_de_hardware_equivalen_a_tiempos_reales():
    f = 100e6
    assert HW.debounce_cycles / f == 0.015
    assert HW.tick_cycles / f == 0.1
    assert HW.error_ticks * HW.tick_cycles / f == 1.0
    assert HW.unlocked_ticks * HW.tick_cycles / f == 10.0
    assert HW.alarm_ticks * HW.tick_cycles / f == 30.0
    assert abs(f / HW.baud_cycles - 115200) / 115200 < 0.01
    assert 0.010 <= HW.debounce_cycles / f <= 0.020      # rango del anteproyecto (10-20 ms)
    refresco = f / (8 << HW.scan_bits)
    assert 60 <= refresco <= 1000        # refresco de los 8 dígitos (Hz): sin parpadeo visible
    assert 0.5e-3 <= (1 << HW.scan_bits) / f <= 4e-3        # 0,5-4 ms encendido por dígito

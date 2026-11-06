"""Pruebas unitarias de cada módulo por separado (simulación MyHDL).

Metodología del anteproyecto: cada módulo se verifica de forma independiente
antes de integrarlo en el nivel superior.
"""

import os
import random

from myhdl import (Signal, StopSimulation, always, block, delay, instance,
                   instances, intbv)

from candado.datapath import code_comparator, code_register, digit_buffer
from candado.alarm import alarm_outputs
from candado.display import display_driver
from candado.glyphs import (G_DASH, G_UNDER, GLYPH_DEFS, GLYPH_INDEX, GLYPH_ROM,
                            table_text)
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
def _expected_display(state, left, count, seq):
    """Texto esperado, construido carácter a carácter desde STATE_WORDS."""
    digits = [(seq >> (12 - 4 * k)) & 0xF for k in range(4)]
    pats = {}
    for i, ch in enumerate(STATE_WORDS[state]):
        if ch == "#":
            g = left
        elif ch in "0123":
            k = int(ch)
            if k < count:
                g = digits[k] if STATE_NAMES[state] == "CONFIG" else G_DASH
            else:
                g = G_UNDER
        else:
            g = GLYPH_INDEX[ch]
        pats[7 - i] = GLYPH_ROM[g]
    return pats


def test_display_driver_muestra_texto_intentos_y_casillas():
    p = SIM
    frame = 8 << p.scan_bits
    casos = []
    for s in range(len(STATE_NAMES)):
        for l in (0, 3, p.max_attempts):
            casos.append((s, l, 0, 0))
        for c in range(5):
            casos.append((s, 2, c, 0xA5C3))

    @block
    def bench():
        clk = Signal(False)
        state = Signal(intbv(0)[3:])
        left = Signal(intbv(0, min=0, max=p.max_attempts + 1))
        count = Signal(intbv(0, min=0, max=5))
        seq = Signal(intbv(0)[16:])
        blink = Signal(True)
        seg, an = Signal(intbv(0)[7:]), Signal(intbv(0)[8:])
        dut = display_driver(clk, state, left, count, seq, blink, seg, an,
                             p.scan_bits)
        ck = _clock(clk)

        @instance
        def stim():
            for s, l, c, q in casos:
                state.next, left.next, count.next, seq.next = s, l, c, q
                shown = {}
                for n in range(3 * frame):
                    yield clk.posedge
                    yield delay(1)
                    one_hot = int(an)
                    if bin(one_hot).count("1") == 1 and n > 4:
                        shown[one_hot.bit_length() - 1] = int(seg)
                assert shown == _expected_display(s, l, c, q), (STATE_NAMES[s], l, c)
            # En ALARM con blink = 0 el display queda apagado.
            state.next, blink.next = STATE_NAMES.index("ALARM"), False
            for n in range(2 * frame):
                yield clk.posedge
                yield delay(1)
                if n > 4:
                    assert int(seg) == 0
            raise StopSimulation()

        return instances()

    _run(bench)


def test_status_leds_termometro_intentos_banderas_y_rgb():
    p = SIM

    @block
    def bench():
        clk = Signal(False)
        state = Signal(intbv(0)[3:])
        count = Signal(intbv(0, min=0, max=5))
        left = Signal(intbv(0, min=0, max=p.max_attempts + 1))
        blink = Signal(True)
        led, rgb = Signal(intbv(0)[16:]), Signal(intbv(0)[3:])
        dut = status_outputs(clk, state, count, left, blink, led, rgb, p.pwm_bits)
        ck = _clock(clk)

        @instance
        def stim():
            colores = set()
            for s in range(len(STATE_NAMES)):
                for c in range(5):
                    for l in range(p.max_attempts + 1):
                        state.next, count.next, left.next = s, c, l
                        seen_rgb = set()
                        for _ in range(2 << p.pwm_bits):
                            yield clk.posedge
                            yield delay(1)
                            seen_rgb.add(int(rgb))
                        name = STATE_NAMES[s]
                        if name == "ALARM":
                            expected = 0xFFFF               # blink = 1: todos encendidos
                        else:
                            flags = {"ERROR": 1 << 14, "UNLOCKED": 1 << 13,
                                     "CONFIG": 1 << 12}.get(name, 0)
                            if name not in ("UNLOCKED", "CONFIG"):
                                flags |= 1 << 11            # candado cerrado
                            expected = flags | (((1 << l) - 1) << 4) | ((1 << c) - 1)
                        assert int(led) == expected, (name, c, l)
                        assert seen_rgb == {0, STATE_RGB[s]}      # PWM: apagado o color
                colores.add(STATE_RGB[s])
            assert len(colores) == len(STATE_NAMES)           # un color por estado
            # ALARM con blink = 0: LEDs y RGB apagados
            state.next, blink.next = STATE_NAMES.index("ALARM"), False
            for _ in range(2 << p.pwm_bits):
                yield clk.posedge
                yield delay(1)
                assert int(led) == 0 and int(rgb) == 0
            raise StopSimulation()

        return instances()

    _run(bench)


def test_alarm_outputs_sirena_y_parpadeo():
    p = SIM
    log = {"blink": [], "tone": [], "sd": []}

    @block
    def bench():
        clk = Signal(False)
        state = Signal(intbv(0)[3:])
        blink, tone, sd = Signal(False), Signal(False), Signal(False)
        dut = alarm_outputs(clk, state, blink, tone, sd, p.blink_bits,
                            p.tone_hi_cycles, p.tone_lo_cycles)
        ck = _clock(clk)

        @instance
        def stim():
            for s in range(len(STATE_NAMES)):
                state.next = s
                for _ in range(2 << p.blink_bits):
                    yield clk.posedge
                    yield delay(1)
                    log["blink"].append(int(blink))
                    log["tone"].append((STATE_NAMES[s], int(blink), int(tone)))
                    log["sd"].append((STATE_NAMES[s], int(sd)))
            raise StopSimulation()

        return instances()

    _run(bench)
    # parpadeo: onda cuadrada de periodo 2^BLINK_BITS
    b = log["blink"]
    flancos = [k for k in range(1, len(b)) if b[k] != b[k - 1]]
    assert {y - x for x, y in zip(flancos, flancos[1:])} == {1 << (p.blink_bits - 1)}
    # sirena y amplificador sólo en ALARM
    assert all(v == (n == "ALARM") for n, v in log["sd"])
    assert all(v == 0 for n, _, v in log["tone"] if n != "ALARM")
    # dos tonos: medio periodo TONE_HI con blink = 1 y TONE_LO con blink = 0
    for fase, half in ((1, p.tone_hi_cycles), (0, p.tone_lo_cycles)):
        w = [v for n, bl, v in log["tone"] if n == "ALARM" and bl == fase]
        runs, n = [], 1
        for x, y in zip(w, w[1:]):
            if x == y:
                n += 1
            else:
                runs.append(n)
                n = 1
        assert half in runs and max(runs[1:]) == half, (fase, runs)


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
        fail = Signal(intbv(0, min=0, max=6))
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
            yield from goto(5, 5, 100)            # ALARM: empieza a enviarse ...
            yield from goto(1, 0, 50)             # ... INPUT llega durante el envío ...
            yield from goto(0, 0, 1900)           # ... y LOCKED lo reemplaza (ranura única)
            raise StopSimulation()

        return instances()

    _run(bench)
    text = decode_uart(samples, B).decode()
    assert text == ("INPUT    0\r\n"
                    "ERROR    1\r\n"
                    "ALARM    5\r\n"
                    "LOCKED   0\r\n")     # INPUT se descartó: sólo se guarda el último


# --------------------------------------------------------------------------
def test_tabla_de_glifos_coincide_con_el_archivo_del_repositorio():
    path = os.path.join(ROOT, "tables", "glyphs_abcdefg.txt")
    assert open(path, encoding="utf-8").read() == table_text()
    for _, pat, _ in GLYPH_DEFS:
        assert len(pat) == 7 and set(pat) <= {"0", "1"}


def test_digitos_de_la_tabla_son_los_estandar():
    # 0..F en abcdefg, consecutivos desde el índice 0
    estandar = ("1111110", "0110000", "1101101", "1111001", "0110011", "1011011",
                "1011111", "1110000", "1111111", "1111011", "1110111", "0011111",
                "1001110", "0111101", "1001111", "1000111")
    assert tuple(p for _, p, _ in GLYPH_DEFS[:16]) == estandar
    assert len({p for _, p, _ in GLYPH_DEFS}) == len(GLYPH_DEFS)   # sin glifos repetidos


def test_todos_los_textos_de_estado_tienen_8_caracteres_representables():
    for name, word in zip(STATE_NAMES, STATE_WORDS):
        assert len(word) == 8, name
        assert set(word) <= set(GLYPH_INDEX) | set("#0123"), name


def test_parametros_de_hardware_equivalen_a_tiempos_reales():
    f = 100e6
    assert HW.debounce_cycles / f == 0.015
    assert HW.tick_cycles / f == 0.1
    assert HW.error_ticks * HW.tick_cycles / f == 1.0
    assert HW.unlocked_ticks * HW.tick_cycles / f == 10.0
    assert HW.alarm_ticks * HW.tick_cycles / f == 30.0
    assert HW.max_attempts == 5
    assert abs(f / (2 * HW.tone_hi_cycles) - 1000) < 1      # sirena: 1 kHz ...
    assert abs(f / (2 * HW.tone_lo_cycles) - 660) < 1       # ... y 660 Hz
    assert 1 <= f / (1 << HW.blink_bits) <= 5               # parpadeo visible (Hz)
    assert abs(f / HW.baud_cycles - 115200) / 115200 < 0.01
    assert 0.010 <= HW.debounce_cycles / f <= 0.020      # rango del anteproyecto (10-20 ms)
    refresco = f / (8 << HW.scan_bits)
    assert 60 <= refresco <= 1000        # refresco de los 8 dígitos (Hz): sin parpadeo visible
    assert 0.5e-3 <= (1 << HW.scan_bits) / f <= 4e-3        # 0,5-4 ms encendido por dígito

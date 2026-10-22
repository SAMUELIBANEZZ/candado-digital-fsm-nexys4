"""Pruebas del nivel superior a nivel de pines de la Nexys4 DDR."""

import pytest

from candado.glyphs import GLYPH_ROM, G_BLANK, word_to_indices
from candado.params import SIM
from candado.scenarios import CODE, WRONG, ex09_secuencia_completa_uart
from candado.states import STATE_RGB, STATE_WORDS
from candado.testing import Stimulus, decode_display, decode_uart, run_top

SCAN_FRAME = 8 << SIM.scan_bits


def expected_display(state, left):
    word = STATE_WORDS[state].ljust(4, "_")
    pats = {7 - i: GLYPH_ROM[g] for i, g in enumerate(word_to_indices(word))}
    pats.update({3: GLYPH_ROM[G_BLANK], 2: GLYPH_ROM[G_BLANK], 1: GLYPH_ROM[G_BLANK]})
    pats[0] = GLYPH_ROM[1 + left]
    return pats


def window(trace, k, before=24, after=24):
    return k - before, k + after


def seen_rgb(t, a, b):
    return {t.rgb[i] for i in range(a, b)}


@pytest.fixture(scope="module")
def estados():
    """Un solo escenario que visita todos los estados y marca cada uno."""
    s = Stimulus(SIM)
    s.reset_hard()
    s.wait(60)
    s.mark("idle")
    s.digit(1)
    s.digit(2)
    s.wait(10)
    s.mark("input")                      # 2 dígitos
    s.digit(3)
    s.digit(4)
    s.settle(2)
    s.mark("unlocked")
    s.digit(9, mode=True)
    s.wait(8)
    s.mark("config")
    s.press("BTNR")
    s.settle(8)
    s.code(WRONG)
    s.settle(2)
    s.mark("error")                      # fallo 1
    s.wait(SIM.error_ticks * SIM.tick_cycles)
    s.press("BTNR")
    s.settle(8)
    for v in (0x1111, 0x2222, 0x3333):
        s.code(v)
        s.settle(4)
        s.wait_ticks(SIM.error_ticks + 1)
    s.wait(10)
    s.mark("alarm")
    s.wait(40)                           # cola para las ventanas de observación
    return s, run_top(s, SIM)


def test_leds_por_estado(estados):
    s, t = estados
    m = s.marks
    assert t.led[m["idle"]] == 0
    assert t.led[m["input"]] == 0b0011                      # 2 dígitos en termómetro
    assert t.led[m["unlocked"]] == 1 << 13                  # LD13
    assert t.led[m["config"]] & (1 << 12)                   # LD12
    assert t.led[m["error"]] == 1 << 14                     # LD14
    assert t.led[m["alarm"]] == 1 << 15                     # LD15


def test_display_por_estado_e_intentos_restantes(estados):
    s, t = estados
    m = s.marks
    casos = {"idle": (0, 3), "input": (1, 3), "unlocked": (3, 3),
             "config": (6, 3), "error": (4, 2), "alarm": (5, 0)}
    for nombre, (estado, restantes) in casos.items():
        a, b = window(t, m[nombre], 20, 20)
        assert decode_display(t, a, b) == expected_display(estado, restantes), nombre


def test_rgb_distinto_por_estado(estados):
    s, t = estados
    m = s.marks
    casos = {"idle": 0, "input": 1, "unlocked": 3, "config": 6, "error": 4, "alarm": 5}
    colores = set()
    for nombre, estado in casos.items():
        a, b = window(t, m[nombre], 20, 20)
        vistos = seen_rgb(t, a, b) - {0}
        assert vistos == {STATE_RGB[estado]}, nombre
        colores.add(STATE_RGB[estado])
    assert len(colores) == len(casos)


def test_polaridad_de_la_placa(estados):
    s, t = estados
    # anodos y catodos activos en bajo, punto decimal apagado (1)
    assert set(t.dp[5:]) == {1}
    activos = [bin(~a & 0xFF).count("1") for a in t.an[20:]]
    assert set(activos) == {1}                              # un solo ánodo a la vez
    # con IDLE y reloj corriendo, un dígito apagado se ve como segmentos = 1111111
    assert 0x7F in t.seg[20:]


def test_registro_uart_de_eventos():
    s = ex09_secuencia_completa_uart(SIM)
    t = run_top(s, SIM)
    texto = decode_uart(t.uart, SIM.baud_cycles).decode()
    esperado = (
        "INPUT    0\r\n"      # primer dígito
        "IDLE     0\r\n"      # BTNL borra el único dígito
        "INPUT    0\r\n"
        "ERROR    1\r\n"      # VALIDATE no se registra
        "INPUT    1\r\n"
        "IDLE     0\r\n"      # BTNR
        "INPUT    0\r\n"
        "UNLOCKED 0\r\n"
        "CONFIG   0\r\n"
        "IDLE     0\r\n"
    )
    assert texto == esperado


def test_sin_uart_la_linea_queda_en_reposo():
    s = ex09_secuencia_completa_uart(SIM)
    t = run_top(s, SIM, enable_uart=False)
    assert set(t.uart[5:]) == {1}


def test_el_top_se_comporta_igual_que_el_nucleo(traces):
    """Estado visible en los pines (LEDs) coherente con el estado del núcleo."""
    from candado.scenarios import tc04_tres_incorrectas_consecutivas
    s = tc04_tres_incorrectas_consecutivas(SIM)
    t = run_top(s, SIM)
    core = traces["tc04_tres_incorrectas_consecutivas"]
    for nombre in ("e1", "e2", "e3"):
        assert t.led[s.marks[nombre] + 3] & (1 << 14)
    assert t.led[s.marks["alarma"]] & (1 << 15)
    assert core.at("alarma")[0] == "ALARM"

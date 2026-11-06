"""Pruebas del nivel superior a nivel de pines de la Nexys4 DDR."""

import pytest

from candado.glyphs import G_DASH, G_UNDER, GLYPH_INDEX, GLYPH_ROM
from candado.params import SIM
from candado.scenarios import WRONG, WRONGS, ex09_secuencia_completa_uart
from candado.states import STATE_NAMES, STATE_RGB, STATE_WORDS
from candado.testing import Stimulus, decode_display, decode_uart, run_top

MAXA = SIM.max_attempts


def expected_display(state, left, digits=()):
    """{posición: patrón} que debe verse para ``state`` (índice de STATE_NAMES)."""
    pats = {}
    for i, ch in enumerate(STATE_WORDS[state]):
        if ch == "#":
            g = left
        elif ch in "0123":
            k = int(ch)
            if k < len(digits):
                g = digits[k] if STATE_NAMES[state] == "CONFIG" else G_DASH
            else:
                g = G_UNDER
        else:
            g = GLYPH_INDEX[ch]
        pats[7 - i] = GLYPH_ROM[g]
    return pats


def window(k, before=20, after=20):
    return k - before, k + after


def seen_rgb(t, a, b):
    return {t.rgb[i] for i in range(a, b)}


def S(name):
    return STATE_NAMES.index(name)


@pytest.fixture(scope="module")
def estados():
    """Un solo escenario que visita todos los estados y marca cada uno."""
    s = Stimulus(SIM)
    s.reset_hard()
    s.wait(60)
    s.mark("locked")
    s.digit(1)
    s.digit(2)
    s.wait(10)
    s.mark("input")                      # 2 dígitos
    s.digit(3)
    s.digit(4)
    s.settle(2)
    s.mark("unlocked")
    s.press("BTNU")
    s.digit(9)
    s.digit(0xC)
    s.wait(8)
    s.mark("config")                     # código nuevo: 9, C, _, _
    s.press("BTNR")
    s.settle(8)
    s.code(WRONG)
    s.settle(2)
    s.mark("error")                      # fallo 1
    s.wait(SIM.error_ticks * SIM.tick_cycles)
    s.reset_hard()
    for v in WRONGS:
        s.code(v)
        s.settle(4)
        s.wait_ticks(SIM.error_ticks + 1)
    s.wait(10)
    s.mark("alarm")
    s.wait(200)                          # cola para las ventanas de observación
    return s, run_top(s, SIM)


def test_leds_por_estado(estados):
    s, t = estados
    m = s.marks
    bar = (1 << MAXA) - 1                                   # LD8..LD4: intentos restantes
    assert t.led[m["locked"]] == (1 << 11) | (bar << 4)     # LD11 cerrado
    assert t.led[m["input"]] == (1 << 11) | (bar << 4) | 0b0011
    assert t.led[m["unlocked"]] == (1 << 13) | (bar << 4)   # LD13 abierto, LD11 apagado
    assert t.led[m["config"]] == (1 << 12) | (bar << 4) | 0b0011
    assert t.led[m["error"]] == (1 << 14) | (1 << 11) | ((bar >> 1) << 4)


def test_en_alarma_todos_los_leds_parpadean(estados):
    s, t = estados
    a, b = window(s.marks["alarm"], 0, 3 << SIM.blink_bits)
    assert {t.led[i] for i in range(a, b)} == {0x0000, 0xFFFF}


def test_display_por_estado(estados):
    s, t = estados
    m = s.marks
    casos = {"locked": (S("LOCKED"), MAXA, ()),
             "input": (S("INPUT"), MAXA, (1, 2)),
             "unlocked": (S("UNLOCKED"), MAXA, ()),
             "config": (S("CONFIG"), MAXA, (9, 0xC)),
             "error": (S("ERROR"), MAXA - 1, ())}
    for nombre, (estado, restantes, digitos) in casos.items():
        a, b = window(m[nombre])
        assert decode_display(t, a, b) == expected_display(estado, restantes, digitos), nombre


def test_textos_legibles():
    # LOCKED muestra los intentos restantes; INPUT nunca muestra los dígitos.
    assert STATE_WORDS[S("LOCKED")].startswith("LOCKEd")
    assert STATE_WORDS[S("UNLOCKED")] == "UnLOCKEd"
    assert expected_display(S("INPUT"), MAXA, (7, 7))[3] == GLYPH_ROM[G_DASH]
    assert expected_display(S("LOCKED"), 3)[0] == GLYPH_ROM[3]


def test_display_parpadea_en_alarma(estados):
    s, t = estados
    a, b = window(s.marks["alarm"], 0, 3 << SIM.blink_bits)
    texto = expected_display(S("ALARM"), 0)
    vistos = {p: set() for p in range(8)}
    for k in range(a, b):
        en = [i for i in range(8) if not (t.an[k] >> i) & 1]
        if len(en) == 1:
            vistos[en[0]].add(t.seg[k] ^ 0x7F)
    for pos in range(8):
        assert vistos[pos] == {0, texto[pos]}, pos         # texto y apagado


def test_rgb_distinto_por_estado(estados):
    s, t = estados
    m = s.marks
    casos = {"locked": 0, "input": 1, "unlocked": 3, "config": 6, "error": 4, "alarm": 5}
    colores = set()
    for nombre, estado in casos.items():
        a, b = window(m[nombre], 20, 20 if nombre != "alarm" else 3 << SIM.blink_bits)
        vistos = seen_rgb(t, a, b) - {0}
        assert vistos == {STATE_RGB[estado]}, nombre
        colores.add(STATE_RGB[estado])
    assert len(colores) == len(casos)


def test_sirena_solo_en_alarma(estados):
    s, t = estados
    k = s.marks["alarm"]
    # Fuera de ALARM: audio apagado y amplificador deshabilitado.
    assert set(t.aud_pwm[:s.marks["error"] + 20]) == {0}
    assert set(t.aud_sd[:s.marks["error"] + 20]) == {0}
    # En ALARM: amplificador encendido y onda cuadrada en AUD_PWM y JA1 (BUZZER).
    a, b = window(k, 0, 3 << SIM.blink_bits)
    assert set(t.aud_sd[a:b]) == {1}
    assert set(t.aud_pwm[a:b]) == {0, 1}
    assert t.aud_pwm[a:b] == t.buzzer[a:b]


def test_sirena_de_dos_tonos(estados):
    s, t = estados
    a, b = window(s.marks["alarm"], 0, 3 << SIM.blink_bits)
    w = t.aud_pwm[a:b]
    # longitudes de los tramos constantes de la onda cuadrada (sin los extremos)
    runs, n = [], 1
    for x, y in zip(w, w[1:]):
        if x == y:
            n += 1
        else:
            runs.append(n)
            n = 1
    assert {SIM.tone_hi_cycles, SIM.tone_lo_cycles} <= set(runs[1:])


def test_polaridad_de_la_placa(estados):
    s, t = estados
    # ánodos y cátodos activos en bajo, punto decimal apagado (1)
    assert set(t.dp[5:]) == {1}
    activos = [bin(~a & 0xFF).count("1") for a in t.an[20:]]
    assert set(activos) == {1}                              # un solo ánodo a la vez
    # con el reloj corriendo, un dígito apagado se ve como segmentos = 1111111
    assert 0x7F in t.seg[20:]


def test_registro_uart_de_eventos():
    s = ex09_secuencia_completa_uart(SIM)
    t = run_top(s, SIM)
    texto = decode_uart(t.uart, SIM.baud_cycles).decode()
    esperado = (
        "INPUT    0\r\n"      # primer dígito
        "LOCKED   0\r\n"      # BTNL borra el único dígito
        "INPUT    0\r\n"
        "ERROR    1\r\n"      # VALIDATE no se registra
        "LOCKED   1\r\n"
        "INPUT    1\r\n"
        "UNLOCKED 0\r\n"
        "CONFIG   0\r\n"
        "LOCKED   0\r\n"      # BTNR
    )
    assert texto == esperado


def test_sin_uart_la_linea_queda_en_reposo():
    s = ex09_secuencia_completa_uart(SIM)
    t = run_top(s, SIM, enable_uart=False)
    assert set(t.uart[5:]) == {1}


def test_el_top_se_comporta_igual_que_el_nucleo(traces):
    """Estado visible en los pines (LEDs) coherente con el estado del núcleo."""
    from candado.scenarios import tc04_cinco_incorrectas_consecutivas
    s = tc04_cinco_incorrectas_consecutivas(SIM)
    t = run_top(s, SIM)
    core = traces["tc04_cinco_incorrectas_consecutivas"]
    for i in range(1, MAXA + 1):
        assert t.led[s.marks[f"e{i}"] + 3] & (1 << 14)
    assert core.at("alarma")[0] == "ALARM"
    a = s.marks["alarma"]
    assert set(t.aud_sd[a:a + 10]) == {1}

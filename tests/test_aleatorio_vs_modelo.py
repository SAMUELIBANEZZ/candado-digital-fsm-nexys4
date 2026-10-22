"""RTL (MyHDL) contra el modelo de referencia independiente, con estímulos
pseudoaleatorios: pulsaciones con rebotes, pulsos espurios, resets, esperas y
vencimientos de temporizadores."""

import pytest

from candado.params import SIM
from candado.randomized import random_stimulus
from candado.reference import LockModel
from candado.testing import run_core


@pytest.mark.parametrize("seed", list(range(1, 11)))
def test_rtl_coincide_con_el_modelo_de_referencia(seed):
    stim, checks = random_stimulus(SIM, seed=seed, events=60)
    trace = run_core(stim, SIM)
    for name, (estado, digitos, fallos, codigo) in checks:
        got = trace.at(name)
        assert (got[0], got[1], got[2], got[4]) == (estado, digitos, fallos, codigo), (
            f"semilla {seed}, evento {name}: modelo={estado,digitos,fallos,hex(codigo)} "
            f"RTL={got[0], got[1], got[2], hex(got[4])}")
        assert got[3] == SIM.max_attempts - fallos       # intentos restantes coherentes


def test_los_aleatorios_visitan_todos_los_estados_y_transiciones():
    vistos, trans = set(), set()
    for seed in range(1, 11):
        stim, _ = random_stimulus(SIM, seed=seed, events=60)
        t = run_core(stim, SIM)
        p = t.path()
        vistos |= set(p)
        trans |= set(zip(p, p[1:]))
    assert vistos == {"IDLE", "INPUT", "VALIDATE", "UNLOCKED", "ERROR", "ALARM", "CONFIG"}
    for par in [("IDLE", "INPUT"), ("INPUT", "VALIDATE"), ("VALIDATE", "UNLOCKED"),
                ("VALIDATE", "ERROR"), ("ERROR", "INPUT"), ("ERROR", "ALARM"),
                ("UNLOCKED", "IDLE"), ("ALARM", "IDLE"), ("UNLOCKED", "CONFIG"),
                ("CONFIG", "UNLOCKED"), ("CONFIG", "IDLE"), ("INPUT", "IDLE")]:
        assert par in trans, f"transición sin cubrir en aleatorios: {par}"


def test_el_modelo_de_referencia_cumple_la_tabla_iii_por_si_solo():
    """Sanidad del propio modelo: reproduce los casos básicos de la especificación."""
    p = SIM
    m = LockModel(p)

    def code(value):
        for sh in (12, 8, 4, 0):
            m.press({"BTNC"}, (value >> sh) & 0xF)

    code(0x1234)
    assert m.snapshot()[0] == "UNLOCKED"
    m.advance(p.unlocked_ticks * p.tick_cycles)
    assert m.state == "IDLE"
    for i in range(3):
        code(0x1111)
        assert m.state == "ERROR" and m.fail == i + 1
        m.advance(p.error_ticks * p.tick_cycles)
    assert m.state == "ALARM"
    m.press({"BTNC"}, 1)
    assert m.state == "ALARM" and m.count == 0
    m.press({"BTNR"})
    assert m.snapshot() == ("IDLE", 0, 0, p.default_code)

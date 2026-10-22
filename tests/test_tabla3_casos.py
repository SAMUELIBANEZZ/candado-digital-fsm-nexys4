"""Casos de la Tabla III del anteproyecto (TC01..TC10) sobre el núcleo.

Cada prueba simula el escenario correspondiente con tiempos reducidos (SIM) y
comprueba estado, dígitos ingresados, intentos fallidos y código vigente.
"""

from candado.params import SIM
from candado.scenarios import CODE

TICK = SIM.tick_cycles
# Un estado temporizado de L ticks dura L*TICK + 2 ciclos (latencia del tick y del timeout).
TOL = 3


def dur(ticks):
    return ticks * TICK + 2


def test_tc01_reset_en_cualquier_estado(traces):
    t = traces["tc01_reset_en_cualquier_estado"]
    # (a) desde INPUT con 2 dígitos y 1 fallo previo
    assert t.at("a_antes")[:3] == ("INPUT", 2, 1)
    assert t.at("a_despues") == ("IDLE", 0, 0, 3, CODE)
    # (b) desde UNLOCKED
    assert t.at("b_antes")[0] == "UNLOCKED"
    assert t.at("b_despues")[:3] == ("IDLE", 0, 0)
    # (c) desde ERROR (el fallo se borra)
    assert t.at("c_antes")[:3] == ("ERROR", 0, 1)
    assert t.at("c_despues")[:3] == ("IDLE", 0, 0)
    # (d) desde ALARM
    assert t.at("d_antes")[:3] == ("ALARM", 0, 3)
    assert t.at("d_despues")[:3] == ("IDLE", 0, 0)
    # (e) desde CONFIG (no se guarda nada)
    assert t.at("e_antes")[0] == "CONFIG"
    assert t.at("e_despues") == ("IDLE", 0, 0, 3, CODE)
    # (f) reset duro (CPU_RESET) con dígitos y fallo pendientes
    assert t.at("f_antes")[:3] == ("INPUT", 1, 1)
    assert t.at("f_despues") == ("IDLE", 0, 0, 3, CODE)


def test_tc02_secuencia_correcta_desbloquea(traces):
    t = traces["tc02_secuencia_correcta"]
    assert t.path() == ["IDLE", "INPUT", "VALIDATE", "UNLOCKED"]
    assert t.at("fin") == ("UNLOCKED", 0, 0, 3, CODE)
    assert "ERROR" not in t.path()


def test_tc03_incorrecta_bajo_el_maximo(traces):
    t = traces["tc03_incorrecta_bajo_el_maximo"]
    assert t.path()[:5] == ["IDLE", "INPUT", "VALIDATE", "ERROR", "INPUT"]
    assert t.at("en_error")[:4] == ("ERROR", 0, 1, 2)
    assert t.at("despues_error")[:4] == ("INPUT", 0, 1, 2)
    # un acceso correcto reinicia el contador de intentos
    assert t.at("desbloqueado")[:4] == ("UNLOCKED", 0, 0, 3)
    assert abs(t.run_length("ERROR") - dur(SIM.error_ticks)) <= TOL


def test_tc04_tres_incorrectas_llevan_a_alarm(traces):
    t = traces["tc04_tres_incorrectas_consecutivas"]
    assert t.at("e1")[:3] == ("ERROR", 0, 1)
    assert t.at("i1")[:3] == ("INPUT", 0, 1)
    assert t.at("e2")[:3] == ("ERROR", 0, 2)
    assert t.at("i2")[:3] == ("INPUT", 0, 2)
    assert t.at("e3")[:4] == ("ERROR", 0, 3, 0)
    assert t.at("alarma")[0] == "ALARM"
    # el tercer ERROR va directo a ALARM (no regresa a INPUT)
    assert t.path()[-2:] == ["ERROR", "ALARM"]
    assert t.path().count("ERROR") == 3


def test_tc05_alarm_ignora_entradas(traces):
    t = traces["tc05_alarma_ignora_entradas"]
    k0, k1 = t.marks["inicio_alarma"], t.marks["fin_entradas"]
    assert set(t.names()[k0:k1 + 1]) == {"ALARM"}
    assert set(t.count[k0:k1 + 1]) == {0}
    assert "UNLOCKED" not in t.path()
    assert t.path().count("VALIDATE") == 3     # ni el código correcto se validó


def test_tc06_alarm_sale_por_reset_o_timeout(traces):
    t = traces["tc06_alarma_reset_o_timeout"]
    assert t.at("a_alarma")[0] == "ALARM"
    assert t.at("a_idle")[:3] == ("IDLE", 0, 0)
    assert t.at("b_alarma")[0] == "ALARM"
    assert t.at("b_idle")[:3] == ("IDLE", 0, 0)
    assert t.at("b_desbloqueado")[:3] == ("UNLOCKED", 0, 0)
    # duración del bloqueo por temporizador: ALARM_TICKS ticks desde su entrada
    segunda = t.first("ALARM", t.marks["a_idle"])
    assert abs(t.run_length("ALARM", segunda) - dur(SIM.alarm_ticks)) <= TOL


def test_tc07_rebotes_y_pulsos_cortos(traces):
    t = traces["tc07_rebotes_y_pulsos_cortos"]
    assert t.at("tras_glitch")[:2] == ("IDLE", 0)           # pulso < antirrebote: nada
    assert t.at("tras_pulsacion")[:2] == ("INPUT", 1)       # con rebotes: un solo dígito
    assert t.at("tras_glitches")[:2] == ("INPUT", 1)        # más glitches: nada
    assert t.at("tras_larga")[:2] == ("INPUT", 2)           # pulsación larga: un dígito


def test_tc08_secuencia_incompleta(traces):
    t = traces["tc08_secuencia_incompleta"]
    assert t.at("tres")[:2] == ("INPUT", 3)
    assert t.at("espera")[:2] == ("INPUT", 3)
    assert "VALIDATE" not in t.path()


def test_tc09_error_en_cada_posicion(traces):
    t = traces["tc09_error_en_cada_posicion"]
    for pos in range(4):
        assert t.at(f"error_pos{pos}")[:3] == ("ERROR", 0, 1), f"posición {pos}"
    assert t.path().count("ERROR") == 4
    assert "UNLOCKED" not in t.path()


def test_tc10_unlocked_vence_y_vuelve_a_idle(traces):
    t = traces["tc10_unlocked_vence"]
    assert t.at("abierto")[0] == "UNLOCKED"
    assert t.at("cerrado")[0] == "IDLE"
    assert t.path() == ["IDLE", "INPUT", "VALIDATE", "UNLOCKED", "IDLE"]
    assert abs(t.run_length("UNLOCKED") - dur(SIM.unlocked_ticks)) <= TOL

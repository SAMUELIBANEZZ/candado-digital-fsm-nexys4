"""Casos adicionales: huecos de especificación cerrados durante el diseño."""

from candado.params import SIM
from candado.scenarios import CODE

TICK = SIM.tick_cycles
MAXA = SIM.max_attempts


def test_ex01_borrar_digitos(traces):
    t = traces["ex01_borrar_digitos"]
    assert t.at("tres")[:2] == ("INPUT", 3)
    assert t.at("borrado")[:2] == ("INPUT", 2)               # BTNL borra el último
    assert t.at("desbloqueado")[0] == "UNLOCKED"            # 1,2,(9 borrado),3,4
    assert t.at("uno")[:2] == ("INPUT", 1)
    assert t.at("vuelve_locked")[:2] == ("LOCKED", 0)       # borrar el único dígito
    assert t.at("borrar_en_locked")[:2] == ("LOCKED", 0)    # sin efecto en LOCKED


def test_ex02_configurar_codigo_desde_unlocked(traces):
    t = traces["ex02_configurar_codigo"]
    assert t.at("btnu_en_locked")[:2] == ("LOCKED", 0)      # BTNU cerrado: nada
    assert t.at("unlocked_btnc")[:2] == ("UNLOCKED", 0)     # BTNC abierto: se ignora
    assert t.at("config_abierto")[:2] == ("CONFIG", 0)      # BTNU no consume dígito
    assert t.at("config_uno")[:2] == ("CONFIG", 1)
    assert t.at("config_guardado") == ("UNLOCKED", 0, 0, MAXA, 0xA5C3)
    assert t.at("cerrado")[:2] == ("LOCKED", 0)             # BTND cierra
    assert t.at("viejo_falla")[:3] == ("LOCKED", 0, 1)      # el código viejo ya no sirve
    assert t.at("nuevo_abre")[0] == "UNLOCKED"              # el nuevo sí
    # el código sólo cambia al completar 4 dígitos en CONFIG
    k = t.marks["config_uno"]
    assert set(t.code[:k + 1]) == {CODE}


def test_ex03_config_vence_sin_guardar(traces):
    t = traces["ex03_config_vence_sin_guardar"]
    assert t.at("en_config")[:2] == ("CONFIG", 2)
    assert t.at("cerrado") == ("LOCKED", 0, 0, MAXA, CODE)
    assert t.at("sigue_valido")[0] == "UNLOCKED"
    assert set(t.code) == {CODE}


def test_ex04_reset_duro_restaura_codigo(traces):
    t = traces["ex04_reset_duro_restaura_codigo"]
    assert t.at("cambiado")[:2] == ("UNLOCKED", 0)
    assert t.at("cambiado")[4] == 0x0F0F
    assert t.at("tras_btnr") == ("LOCKED", 0, 0, MAXA, 0x0F0F)  # BTNR conserva el código
    assert t.at("tras_reset_duro")[4] == CODE               # CPU_RESET lo restaura
    assert t.at("fabrica_abre")[0] == "UNLOCKED"


def test_ex05_pulsaciones_simultaneas(traces):
    t = traces["ex05_pulsaciones_simultaneas"]
    assert t.at("dos")[:2] == ("INPUT", 2)
    assert t.at("delete_gana")[:2] == ("INPUT", 1)          # BTNL > BTNC
    assert t.at("reset_gana")[:2] == ("LOCKED", 0)          # BTNR > BTNC


def test_ex06_error_incrementa_una_sola_vez(traces):
    t = traces["ex06_error_cuenta_una_vez"]
    assert set(t.fail) == {0, 1}                            # nunca 2, aunque ERROR dure cientos de ciclos
    assert t.at("fin")[:3] == ("LOCKED", 0, 1)


def test_ex07_entradas_en_error_se_ignoran(traces):
    t = traces["ex07_entradas_en_error_se_ignoran"]
    assert t.at("durante_error")[0] == "ERROR"
    assert t.at("vuelve_locked")[:3] == ("LOCKED", 0, 1)    # el dígito pulsado en ERROR no cuenta


def test_ex08_btnu_btnd_sin_efecto_con_el_candado_cerrado(traces):
    t = traces["ex08_botones_sin_funcion"]
    assert t.at("locked_sin_efecto")[:2] == ("LOCKED", 0)
    assert t.at("input_sin_efecto")[:2] == ("INPUT", 1)


def test_ex10_cierre_manual_con_btnd(traces):
    t = traces["ex10_cierre_manual"]
    assert t.at("abierto")[0] == "UNLOCKED"
    assert t.at("cerrado")[:2] == ("LOCKED", 0)
    assert t.at("btnd_gana")[0] == "LOCKED"                 # BTND > BTNU
    assert "CONFIG" not in t.path()
    # BTND cierra mucho antes de que venza UNLOCKED
    k = t.first("UNLOCKED")
    assert t.run_length("UNLOCKED", k) < SIM.unlocked_ticks * TICK


def test_ex11_btnr_no_devuelve_intentos(traces):
    t = traces["ex11_btnr_no_borra_intentos"]
    assert t.at("antes_ultimo")[:4] == ("LOCKED", 0, MAXA - 1, 1)
    assert t.at("alarma")[0] == "ALARM"


def test_el_estado_validate_dura_un_solo_ciclo(traces):
    for name, t in traces.items():
        k = t.first("VALIDATE")
        while k is not None:
            assert t.state[k + 1] != t.state[k], f"{name}: VALIDATE dura más de un ciclo"
            k = t.first("VALIDATE", k + 1)


def test_nunca_hay_mas_de_4_digitos_ni_mas_fallos_que_el_maximo(traces):
    for name, t in traces.items():
        assert max(t.count) <= 4, name
        assert max(t.fail) <= MAXA, name
        assert min(t.left) >= 0, name


def test_las_transiciones_observadas_son_las_del_diagrama(traces):
    """Toda transición observada debe existir en el diagrama de estados."""
    permitidas = {
        ("LOCKED", "INPUT"), ("INPUT", "LOCKED"), ("INPUT", "VALIDATE"),
        ("VALIDATE", "UNLOCKED"), ("VALIDATE", "ERROR"),
        ("ERROR", "LOCKED"), ("ERROR", "ALARM"),
        ("UNLOCKED", "LOCKED"), ("UNLOCKED", "CONFIG"),
        ("CONFIG", "UNLOCKED"), ("CONFIG", "LOCKED"),
        ("ALARM", "LOCKED"),
    }
    vistas = set()
    for name, t in traces.items():
        p = t.path()
        for a, b in zip(p, p[1:]):
            assert (a, b) in permitidas, f"{name}: transición no prevista {a}->{b}"
            vistas.add((a, b))
    # cobertura: cada flecha del diagrama se ejercitó al menos una vez
    assert permitidas == vistas, f"transiciones sin cubrir: {permitidas - vistas}"

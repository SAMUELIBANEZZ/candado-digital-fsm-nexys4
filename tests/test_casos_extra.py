"""Casos adicionales: huecos de especificación cerrados durante el diseño."""

from candado.params import SIM
from candado.scenarios import CODE

TICK = SIM.tick_cycles


def test_ex01_borrar_digitos(traces):
    t = traces["ex01_borrar_digitos"]
    assert t.at("tres")[:2] == ("INPUT", 3)
    assert t.at("borrado")[:2] == ("INPUT", 2)               # BTNL borra el último
    assert t.at("desbloqueado")[0] == "UNLOCKED"            # 1,2,(9 borrado),3,4
    assert t.at("uno")[:2] == ("INPUT", 1)
    assert t.at("vuelve_idle")[:2] == ("IDLE", 0)           # borrar el único dígito
    assert t.at("borrar_en_idle")[:2] == ("IDLE", 0)        # sin efecto en IDLE


def test_ex02_configurar_codigo_desde_unlocked(traces):
    t = traces["ex02_configurar_codigo"]
    assert t.at("sw15_en_idle")[:2] == ("INPUT", 1)         # SW15 en IDLE: dígito normal
    assert t.at("unlocked_sin_sw15")[:2] == ("UNLOCKED", 0)  # BTNC sin SW15: se ignora
    assert t.at("config_abierto")[:2] == ("CONFIG", 1)
    assert t.at("config_guardado") == ("UNLOCKED", 0, 0, 3, 0xA5C3)
    assert t.at("viejo_falla")[:3] == ("INPUT", 0, 1)        # el código viejo ya no sirve
    assert t.at("nuevo_abre")[0] == "UNLOCKED"              # el nuevo sí
    assert "CONFIG" in t.path()
    # el código sólo cambia al completar 4 dígitos en CONFIG
    k = t.marks["config_abierto"]
    assert set(t.code[:k + 1]) == {CODE}


def test_ex03_config_vence_sin_guardar(traces):
    t = traces["ex03_config_vence_sin_guardar"]
    assert t.at("en_config")[:2] == ("CONFIG", 2)
    assert t.at("cerrado") == ("IDLE", 0, 0, 3, CODE)
    assert t.at("sigue_valido")[0] == "UNLOCKED"
    assert set(t.code) == {CODE}


def test_ex04_reset_duro_restaura_codigo(traces):
    t = traces["ex04_reset_duro_restaura_codigo"]
    assert t.at("cambiado")[4] == 0x0F0F
    assert t.at("tras_btnr") == ("IDLE", 0, 0, 3, 0x0F0F)   # BTNR conserva el código
    assert t.at("tras_reset_duro")[4] == CODE               # CPU_RESET lo restaura
    assert t.at("fabrica_abre")[0] == "UNLOCKED"


def test_ex05_pulsaciones_simultaneas(traces):
    t = traces["ex05_pulsaciones_simultaneas"]
    assert t.at("dos")[:2] == ("INPUT", 2)
    assert t.at("delete_gana")[:2] == ("INPUT", 1)          # BTNL > BTNC
    assert t.at("reset_gana")[:2] == ("IDLE", 0)            # BTNR > BTNC


def test_ex06_error_incrementa_una_sola_vez(traces):
    t = traces["ex06_error_cuenta_una_vez"]
    assert set(t.fail) == {0, 1}                            # nunca 2, aunque ERROR dure 122 ciclos
    assert t.at("fin")[:3] == ("INPUT", 0, 1)


def test_ex07_entradas_en_error_se_ignoran(traces):
    t = traces["ex07_entradas_en_error_se_ignoran"]
    assert t.at("durante_error")[0] == "ERROR"
    assert t.at("vuelve_input")[:3] == ("INPUT", 0, 1)      # el dígito pulsado en ERROR no cuenta


def test_ex08_botones_no_usados(traces):
    t = traces["ex08_botones_no_usados"]
    assert t.at("idle_sin_efecto")[:2] == ("IDLE", 0)
    assert t.at("input_sin_efecto")[:2] == ("INPUT", 1)


def test_el_estado_validate_dura_un_solo_ciclo(traces):
    for name, t in traces.items():
        k = t.first("VALIDATE")
        while k is not None:
            assert t.state[k + 1] != t.state[k], f"{name}: VALIDATE dura más de un ciclo"
            k = t.first("VALIDATE", k + 1)


def test_nunca_hay_mas_de_4_digitos_ni_mas_de_3_fallos(traces):
    for name, t in traces.items():
        assert max(t.count) <= 4, name
        assert max(t.fail) <= SIM.max_attempts, name
        assert min(t.left) >= 0, name


def test_las_transiciones_observadas_son_las_del_diagrama(traces):
    """Toda transición observada debe existir en el diagrama de estados."""
    permitidas = {
        ("IDLE", "INPUT"), ("INPUT", "IDLE"), ("INPUT", "VALIDATE"),
        ("VALIDATE", "UNLOCKED"), ("VALIDATE", "ERROR"),
        ("ERROR", "INPUT"), ("ERROR", "ALARM"),
        ("UNLOCKED", "IDLE"), ("UNLOCKED", "CONFIG"),
        ("CONFIG", "UNLOCKED"), ("CONFIG", "IDLE"),
        ("ALARM", "IDLE"),
        # BTNR / CPU_RESET llevan a IDLE desde cualquier estado
        ("INPUT", "IDLE"), ("VALIDATE", "IDLE"), ("ERROR", "IDLE"),
    }
    vistas = set()
    for name, t in traces.items():
        p = t.path()
        for a, b in zip(p, p[1:]):
            assert (a, b) in permitidas, f"{name}: transición no prevista {a}->{b}"
            vistas.add((a, b))
    # cobertura: cada flecha de la Fig. 2 (+CONFIG) se ejercitó al menos una vez
    esperadas = {
        ("IDLE", "INPUT"), ("INPUT", "VALIDATE"), ("VALIDATE", "UNLOCKED"),
        ("VALIDATE", "ERROR"), ("ERROR", "INPUT"), ("ERROR", "ALARM"),
        ("UNLOCKED", "IDLE"), ("ALARM", "IDLE"), ("UNLOCKED", "CONFIG"),
        ("CONFIG", "UNLOCKED"), ("CONFIG", "IDLE"), ("INPUT", "IDLE"),
    }
    assert esperadas <= vistas, f"transiciones sin cubrir: {esperadas - vistas}"

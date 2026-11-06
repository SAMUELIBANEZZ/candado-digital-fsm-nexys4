"""Escenarios de verificación.

``TC01..TC10`` reproducen los 10 casos de la Tabla III del anteproyecto.
``EX01..EX11`` cubren los huecos de especificación cerrados durante el diseño
(borrado de dígitos, modo configuración, reset duro, pulsaciones simultáneas,
cierre manual, BTNR no borra los intentos...).

Cada escenario devuelve un :class:`~candado.testing.Stimulus` con *marcas*
(``mark``) que las pruebas consultan para comprobar el estado en puntos
concretos. Los mismos escenarios generan los vectores del testbench VHDL.
"""

from .params import SIM, Params
from .testing import Stimulus

CODE = 0x1234          # código de fábrica
WRONG = 0x1111         # secuencia incorrecta (difiere del código)
WRONGS = (0x1111, 0x2222, 0x3333, 0x4444, 0x5555)   # 5 fallos -> ALARM


def _wait_error_end(s: Stimulus):
    """Espera a que termine el estado ERROR (vuelve a LOCKED o pasa a ALARM)."""
    s.settle(4)
    s.wait_ticks(s.p.error_ticks + 1)


def _to_alarm(s: Stimulus):
    """MAX_ATTEMPTS intentos fallidos consecutivos; termina ya dentro de ALARM."""
    for value in WRONGS[:s.p.max_attempts]:
        s.code(value)
        _wait_error_end(s)


def _start(p: Params) -> Stimulus:
    s = Stimulus(p)
    s.reset_hard()
    return s


# --------------------------------------------------------------------------
# Tabla III del anteproyecto
# --------------------------------------------------------------------------
def tc01_reset_en_cualquier_estado(p=SIM):
    s = _start(p)
    # (a) INPUT con un intento fallido previo y 2 dígitos ya ingresados
    s.code(WRONG)
    _wait_error_end(s)
    s.digit(1)
    s.digit(2)
    s.mark("a_antes")
    s.press("BTNR")
    s.settle(6)
    s.mark("a_despues")              # LOCKED, sin dígitos; el fallo se conserva
    # (b) UNLOCKED
    s.code(CODE)
    s.settle(4)
    s.mark("b_antes")
    s.press("BTNR")
    s.settle(6)
    s.mark("b_despues")
    # (c) ERROR
    s.code(WRONG)
    s.settle(2)
    s.mark("c_antes")
    s.press("BTNR")
    s.settle(6)
    s.mark("c_despues")
    # (d) ALARM: BTNR no la cancela; CPU_RESET sí
    s.reset_hard()                   # parte de 0 fallos
    _to_alarm(s)
    s.mark("d_antes")
    s.press("BTNR")
    s.settle(6)
    s.mark("d_btnr")
    s.reset_hard()
    s.mark("d_despues")
    # (e) CONFIG
    s.code(CODE)
    s.settle(4)
    s.press("BTNU")
    s.digit(7)
    s.mark("e_antes")
    s.press("BTNR")
    s.settle(6)
    s.mark("e_despues")
    # (f) reset duro (CPU_RESET) con el sistema en INPUT y 1 fallo
    s.code(WRONG)
    _wait_error_end(s)
    s.digit(3)
    s.mark("f_antes")
    s.reset_hard()
    s.mark("f_despues")
    return s


def tc02_secuencia_correcta(p=SIM):
    s = _start(p)
    s.mark("inicio")
    s.code(CODE)
    s.settle(4)
    s.mark("fin")
    return s


def tc03_incorrecta_bajo_el_maximo(p=SIM):
    s = _start(p)
    s.code(WRONG)
    s.settle(2)
    s.mark("en_error")
    _wait_error_end(s)
    s.mark("despues_error")
    # un acceso correcto reinicia el contador de intentos
    s.code(CODE)
    s.settle(4)
    s.mark("desbloqueado")
    return s


def tc04_cinco_incorrectas_consecutivas(p=SIM):
    s = _start(p)
    for i, value in enumerate(WRONGS[:p.max_attempts]):
        s.code(value)
        s.settle(2)
        s.mark(f"e{i + 1}")
        _wait_error_end(s)
        s.mark(f"l{i + 1}")
    s.mark("alarma")
    return s


def tc05_alarma_ignora_entradas(p=SIM):
    s = _start(p)
    _to_alarm(s)
    s.mark("inicio_alarma")
    s.code(CODE)                 # incluso el código correcto se ignora
    s.press("BTNL")
    s.press("BTNR")              # BTNR tampoco la cancela
    s.press("BTNU")
    s.press("BTND")
    s.mark("fin_entradas")
    return s


def tc06_alarma_reset_o_timeout(p=SIM):
    s = _start(p)
    # (a) salida por reset duro (CPU_RESET)
    _to_alarm(s)
    s.mark("a_alarma")
    s.reset_hard()
    s.mark("a_locked")
    # (b) salida por vencimiento del temporizador
    _to_alarm(s)
    s.mark("b_alarma")
    s.wait_ticks(p.alarm_ticks + 1)
    s.mark("b_locked")
    # tras salir, el contador de intentos quedó en cero: el código vale
    s.code(CODE)
    s.settle(4)
    s.mark("b_desbloqueado")
    return s


def tc07_rebotes_y_pulsos_cortos(p=SIM):
    s = _start(p)
    s.glitch("BTNC")
    s.mark("tras_glitch")
    s.set_sw(5)
    s.settle(4)
    s.press("BTNC", bounce=True)
    s.mark("tras_pulsacion")
    s.glitch("BTNC")
    s.glitch("BTNC", length=3)
    s.mark("tras_glitches")
    s.press("BTNC", hold=100)    # pulsación larga: un solo dígito
    s.mark("tras_larga")
    return s


def tc08_secuencia_incompleta(p=SIM):
    s = _start(p)
    s.digit(1)
    s.digit(2)
    s.digit(3)
    s.mark("tres")
    s.wait_ticks(20)
    s.mark("espera")
    return s


def tc09_error_en_cada_posicion(p=SIM):
    s = _start(p)
    for pos in range(4):
        bad = CODE ^ (0x1 << (4 * (3 - pos)))   # cambia un solo dígito
        s.code(bad)
        s.settle(2)
        s.mark(f"error_pos{pos}")
        _wait_error_end(s)
    return s


def tc10_unlocked_vence(p=SIM):
    s = _start(p)
    s.code(CODE)
    s.settle(4)
    s.mark("abierto")
    s.wait_ticks(p.unlocked_ticks + 1)
    s.mark("cerrado")
    return s


# --------------------------------------------------------------------------
# Casos adicionales
# --------------------------------------------------------------------------
def ex01_borrar_digitos(p=SIM):
    s = _start(p)
    s.digit(1)
    s.digit(2)
    s.digit(9)
    s.mark("tres")
    s.press("BTNL")
    s.mark("borrado")              # count == 2
    s.digit(3)
    s.digit(4)
    s.settle(4)
    s.mark("desbloqueado")         # 1,2,3,4 -> UNLOCKED
    s.press("BTNR")
    s.settle(6)
    s.digit(8)
    s.mark("uno")
    s.press("BTNL")
    s.mark("vuelve_locked")        # borrar el único dígito -> LOCKED
    s.press("BTNL")
    s.mark("borrar_en_locked")     # sin efecto
    return s


def ex02_configurar_codigo(p=SIM):
    new = 0xA5C3
    s = _start(p)
    # BTNU con el candado cerrado no abre CONFIG
    s.press("BTNU")
    s.mark("btnu_en_locked")
    # desbloquear y entrar a CONFIG
    s.code(CODE)
    s.settle(4)
    s.digit(7)                      # BTNC en UNLOCKED se ignora
    s.mark("unlocked_btnc")
    s.press("BTNU")
    s.mark("config_abierto")        # CONFIG sin dígitos
    s.digit(new >> 12)
    s.mark("config_uno")
    for shift in (8, 4, 0):
        s.digit((new >> shift) & 0xF)
    s.settle(4)
    s.mark("config_guardado")
    s.press("BTND")                 # cerrar
    s.settle(6)
    s.mark("cerrado")
    # el código anterior ya no sirve
    s.code(CODE)
    _wait_error_end(s)
    s.mark("viejo_falla")
    # el nuevo sí
    s.code(new)
    s.settle(4)
    s.mark("nuevo_abre")
    return s


def ex03_config_vence_sin_guardar(p=SIM):
    s = _start(p)
    s.code(CODE)
    s.settle(4)
    s.press("BTNU")
    s.digit(0xF)
    s.digit(0xE)
    s.mark("en_config")
    s.wait_ticks(p.config_ticks + 1)
    s.mark("cerrado")
    s.code(CODE)                    # el código original sigue vigente
    s.settle(4)
    s.mark("sigue_valido")
    return s


def ex04_reset_duro_restaura_codigo(p=SIM):
    new = 0x0F0F
    s = _start(p)
    s.code(CODE)
    s.settle(4)
    s.press("BTNU")
    s.code(new)
    s.settle(4)
    s.mark("cambiado")
    s.press("BTNR")                 # BTNR: conserva el nuevo código
    s.settle(6)
    s.mark("tras_btnr")
    s.reset_hard()                  # reset duro: vuelve al código de fábrica
    s.mark("tras_reset_duro")
    s.code(CODE)
    s.settle(4)
    s.mark("fabrica_abre")
    return s


def ex05_pulsaciones_simultaneas(p=SIM):
    s = _start(p)
    s.digit(1)
    s.digit(2)
    s.mark("dos")
    s.set_sw(9)
    s.settle(4)
    s.press_together(["BTNC", "BTNL"])
    s.mark("delete_gana")           # count == 1
    s.press_together(["BTNC", "BTNR"])
    s.mark("reset_gana")            # LOCKED
    return s


def ex06_error_cuenta_una_vez(p=SIM):
    s = _start(p)
    s.code(WRONG)
    s.settle(2)
    s.mark("error")
    _wait_error_end(s)
    s.mark("fin")
    return s


def ex07_entradas_en_error_se_ignoran(p=SIM):
    s = _start(p)
    s.code(WRONG)
    s.settle(2)
    s.digit(5)                      # durante ERROR: debe ignorarse
    s.mark("durante_error")
    _wait_error_end(s)
    s.mark("vuelve_locked")         # LOCKED con 0 dígitos
    return s


def ex08_botones_sin_funcion(p=SIM):
    s = _start(p)
    s.press("BTNU")
    s.press("BTND")
    s.mark("locked_sin_efecto")
    s.digit(1)
    s.press("BTNU")
    s.press("BTND")
    s.mark("input_sin_efecto")
    return s


def ex09_secuencia_completa_uart(p=SIM):
    """Recorre varios estados espaciados para verificar el registro UART."""
    s = _start(p)
    s.wait(100)
    s.digit(1)
    s.wait(300)
    s.press("BTNL")                 # INPUT -> LOCKED
    s.wait(300)
    s.code(WRONG)
    _wait_error_end(s)              # ERROR -> LOCKED
    s.wait(300)
    s.code(CODE)
    s.wait(100)
    s.press("BTNU")                 # UNLOCKED -> CONFIG
    s.wait(300)
    s.press("BTNR")
    s.wait(700)                     # deja terminar la última línea UART
    return s


def ex10_cierre_manual(p=SIM):
    s = _start(p)
    s.code(CODE)
    s.settle(4)
    s.mark("abierto")
    s.press("BTND")                 # cierra sin esperar el temporizador
    s.mark("cerrado")
    s.code(CODE)
    s.settle(4)
    s.press_together(["BTNU", "BTND"])
    s.mark("btnd_gana")             # BTND > BTNU: cierra
    return s


def ex11_btnr_no_borra_intentos(p=SIM):
    s = _start(p)
    for value in WRONGS[:p.max_attempts - 1]:
        s.code(value)
        _wait_error_end(s)
        s.press("BTNR")             # cancelar no devuelve los intentos
        s.settle(6)
    s.mark("antes_ultimo")
    s.code(WRONGS[p.max_attempts - 1])
    _wait_error_end(s)
    s.mark("alarma")
    return s


SCENARIOS = {
    "tc01_reset_en_cualquier_estado": tc01_reset_en_cualquier_estado,
    "tc02_secuencia_correcta": tc02_secuencia_correcta,
    "tc03_incorrecta_bajo_el_maximo": tc03_incorrecta_bajo_el_maximo,
    "tc04_cinco_incorrectas_consecutivas": tc04_cinco_incorrectas_consecutivas,
    "tc05_alarma_ignora_entradas": tc05_alarma_ignora_entradas,
    "tc06_alarma_reset_o_timeout": tc06_alarma_reset_o_timeout,
    "tc07_rebotes_y_pulsos_cortos": tc07_rebotes_y_pulsos_cortos,
    "tc08_secuencia_incompleta": tc08_secuencia_incompleta,
    "tc09_error_en_cada_posicion": tc09_error_en_cada_posicion,
    "tc10_unlocked_vence": tc10_unlocked_vence,
    "ex01_borrar_digitos": ex01_borrar_digitos,
    "ex02_configurar_codigo": ex02_configurar_codigo,
    "ex03_config_vence_sin_guardar": ex03_config_vence_sin_guardar,
    "ex04_reset_duro_restaura_codigo": ex04_reset_duro_restaura_codigo,
    "ex05_pulsaciones_simultaneas": ex05_pulsaciones_simultaneas,
    "ex06_error_cuenta_una_vez": ex06_error_cuenta_una_vez,
    "ex07_entradas_en_error_se_ignoran": ex07_entradas_en_error_se_ignoran,
    "ex08_botones_sin_funcion": ex08_botones_sin_funcion,
    "ex09_secuencia_completa_uart": ex09_secuencia_completa_uart,
    "ex10_cierre_manual": ex10_cierre_manual,
    "ex11_btnr_no_borra_intentos": ex11_btnr_no_borra_intentos,
}

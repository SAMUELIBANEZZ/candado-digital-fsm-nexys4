"""Parámetros de diseño del candado digital.

Los mismos módulos se instancian con dos juegos de parámetros:

* ``HW``  : valores reales para la placa (reloj de 100 MHz).
* ``SIM`` : valores reducidos para que la simulación termine en miles de
            ciclos y no en miles de millones (30 s a 100 MHz = 3x10^9 ciclos).

Todos los tiempos de la FSM se expresan en *ticks* de ``tick_cycles`` ciclos de
reloj (100 ms en hardware), de modo que existe un único dominio de reloj y no
hay relojes divididos.
"""

from dataclasses import dataclass


def bits(n: int) -> int:
    """Número mínimo de bits para representar el entero ``n`` (mínimo 1)."""
    return max(1, int(n).bit_length())


@dataclass(frozen=True)
class Params:
    debounce_cycles: int   # ciclos de estabilidad exigidos al antirrebote
    tick_cycles: int       # ciclos de reloj por tick de la base de tiempo
    error_ticks: int       # permanencia en ERROR
    unlocked_ticks: int    # permanencia en UNLOCKED antes de re-bloquear
    alarm_ticks: int       # permanencia en ALARM
    config_ticks: int      # tiempo máximo en CONFIG
    scan_bits: int         # bits del prescaler por dígito del display
    pwm_bits: int          # bits del contador PWM del LED RGB (encendido 1/16)
    baud_cycles: int       # ciclos de reloj por bit UART
    max_attempts: int = 3  # intentos fallidos antes de ALARM
    default_code: int = 0x1234  # código de fábrica (4 dígitos hexadecimales)

    @property
    def tick_max(self) -> int:
        return max(self.error_ticks, self.unlocked_ticks,
                   self.alarm_ticks, self.config_ticks)


# Hardware real: reloj de 100 MHz de la Nexys4 DDR / Nexys A7-100T.
HW = Params(
    debounce_cycles=1_500_000,   # 15 ms
    tick_cycles=10_000_000,      # 100 ms
    error_ticks=10,              # 1 s
    unlocked_ticks=100,          # 10 s
    alarm_ticks=300,             # 30 s
    config_ticks=300,            # 30 s
    scan_bits=17,                # 1,3 ms por dígito -> ~95 Hz para los 8 dígitos
    pwm_bits=8,                  # LED RGB atenuado a 1/16
    baud_cycles=868,             # 115 200 baudios
)

# Simulación: los mismos módulos con tiempos reducidos.
SIM = Params(
    debounce_cycles=8,
    tick_cycles=40,
    error_ticks=8,
    unlocked_ticks=10,
    alarm_ticks=15,
    config_ticks=15,
    scan_bits=2,
    pwm_bits=4,
    baud_cycles=2,
)

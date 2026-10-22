"""Códigos de estado y texto asociado (display de 7 segmentos y registro UART).

El FSM usa internamente un ``enum`` de MyHDL (se convierte a un tipo
enumerado de VHDL y Vivado elige la codificación). Fuera del FSM los demás
módulos reciben ``state_code`` (3 bits) con estos valores.
"""

S_IDLE = 0
S_INPUT = 1
S_VALIDATE = 2
S_UNLOCKED = 3
S_ERROR = 4
S_ALARM = 5
S_CONFIG = 6

STATE_NAMES = ("IDLE", "INPUT", "VALIDATE", "UNLOCKED", "ERROR", "ALARM", "CONFIG")

# Palabra de 4 caracteres que se muestra en AN7..AN4 (ver glyphs.py).
STATE_WORDS = ("IdLE", "InPt", "CHEc", "OPEn", "Err_", "ALAr", "COnF")

# Color del LED RGB (bit2=R, bit1=G, bit0=B), todos distintos.
STATE_RGB = (
    0b001,  # IDLE      azul
    0b011,  # INPUT     cian
    0b111,  # VALIDATE  blanco (dura un ciclo)
    0b010,  # UNLOCKED  verde
    0b100,  # ERROR     rojo
    0b101,  # ALARM     magenta
    0b110,  # CONFIG    amarillo
)

# Texto del registro UART: nombre del estado relleno a 8 caracteres.
UART_NAME_ROM = tuple(ord(c) for name in STATE_NAMES for c in name.ljust(8))

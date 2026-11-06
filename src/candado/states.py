"""Códigos de estado y texto asociado (display de 7 segmentos y registro UART).

El FSM usa internamente un ``enum`` de MyHDL (se convierte a un tipo
enumerado de VHDL y Vivado elige la codificación). Fuera del FSM los demás
módulos reciben ``state_code`` (3 bits) con estos valores.
"""

S_LOCKED = 0
S_INPUT = 1
S_VALIDATE = 2
S_UNLOCKED = 3
S_ERROR = 4
S_ALARM = 5
S_CONFIG = 6

STATE_NAMES = ("LOCKED", "INPUT", "VALIDATE", "UNLOCKED", "ERROR", "ALARM", "CONFIG")

# Texto de 8 caracteres que se muestra en AN7..AN0 (AN7 = primer carácter).
# Caracteres especiales (ver glyphs.py):
#   '#'          intentos restantes (0..5)
#   '0'..'3'     casilla del dígito ingresado k: en INPUT se ve '-' (oculto) si ya
#                se ingresó y '_' si falta; en CONFIG se ve el dígito real (hex).
# Las 'K' y 'm' no existen en 7 segmentos: K se aproxima y "ALArnn" = "ALARM".
STATE_WORDS = (
    "LOCKEd #",   # LOCKED    candado cerrado, intentos restantes a la derecha
    "CodE0123",   # INPUT     "CodE" + casillas de los 4 dígitos
    "CHECK   ",   # VALIDATE  (dura un ciclo, no se alcanza a ver)
    "UnLOCKEd",   # UNLOCKED  candado abierto
    "Error  #",   # ERROR     intento fallido, intentos restantes a la derecha
    "ALArnn  ",   # ALARM     parpadea junto con LEDs y sirena
    "SEt 0123",   # CONFIG    "SEt" + el código nuevo que se va escribiendo
)

# Color del LED RGB (bit2=R, bit1=G, bit0=B), todos distintos.
STATE_RGB = (
    0b100,  # LOCKED    rojo      (cerrado)
    0b011,  # INPUT     cian      (escribiendo)
    0b001,  # VALIDATE  azul      (dura un ciclo)
    0b010,  # UNLOCKED  verde     (abierto)
    0b110,  # ERROR     amarillo
    0b101,  # ALARM     magenta   (parpadea)
    0b111,  # CONFIG    blanco
)

# Texto del registro UART: nombre del estado relleno a 8 caracteres.
UART_NAME_ROM = tuple(ord(c) for name in STATE_NAMES for c in name.ljust(8))

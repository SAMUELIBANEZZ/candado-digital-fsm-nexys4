"""Tabla de glifos del display de 7 segmentos (formato del taller).

Cada patrón son 7 bits en el orden ``abcdefg`` (a = bit más significativo)
con 1 = segmento encendido (lógica positiva). La placa usa lógica negativa:
la inversión se hace en el módulo de nivel superior.

         aaa
        f   b
        f   b
         ggg
        e   c
        e   c
         ddd

Los glifos 0..15 son los dígitos hexadecimales 0..F (intentos restantes y
dígitos del código nuevo); el resto son las letras necesarias para escribir el
texto de cada estado.
"""

# (clave, patrón abcdefg, descripción)
GLYPH_DEFS = (
    ("0", "1111110", "dígito 0 / letra O"),
    ("1", "0110000", "dígito 1"),
    ("2", "1101101", "dígito 2"),
    ("3", "1111001", "dígito 3"),
    ("4", "0110011", "dígito 4"),
    ("5", "1011011", "dígito 5 / letra S"),
    ("6", "1011111", "dígito 6"),
    ("7", "1110000", "dígito 7"),
    ("8", "1111111", "dígito 8"),
    ("9", "1111011", "dígito 9"),
    ("A", "1110111", "dígito A"),
    ("b", "0011111", "dígito b"),
    ("C", "1001110", "dígito C"),
    ("d", "0111101", "dígito d"),
    ("E", "1001111", "dígito E"),
    ("F", "1000111", "dígito F"),
    (" ", "0000000", "apagado"),
    ("L", "0001110", "L"),
    ("K", "1010111", "K (aproximada)"),
    ("U", "0111110", "U"),
    ("n", "0010101", "n"),
    ("o", "0011101", "o"),
    ("r", "0000101", "r"),
    ("t", "0001111", "t"),
    ("H", "0110111", "H"),
    ("-", "0000001", "guion (dígito ingresado, oculto)"),
    ("_", "0001000", "guion bajo (dígito pendiente)"),
)

GLYPH_INDEX = {key: i for i, (key, _, _) in enumerate(GLYPH_DEFS)}
# Letras que comparten glifo con un dígito.
GLYPH_INDEX["O"] = GLYPH_INDEX["0"]
GLYPH_INDEX["S"] = GLYPH_INDEX["5"]

# ROM de 32 entradas (índice de 5 bits); las no usadas quedan apagadas.
GLYPH_ROM = tuple(
    [int(pat, 2) for _, pat, _ in GLYPH_DEFS]
    + [0] * (32 - len(GLYPH_DEFS))
)

G_HEX0 = GLYPH_INDEX["0"]     # los dígitos 0..F son consecutivos desde aquí
G_BLANK = GLYPH_INDEX[" "]
G_DASH = GLYPH_INDEX["-"]
G_UNDER = GLYPH_INDEX["_"]

# Códigos especiales del texto de cada estado (no son glifos: el display los
# reemplaza por un valor en tiempo real).
C_ATTEMPTS = 27               # '#'      -> intentos restantes
C_SLOT0 = 28                  # '0'..'3' -> casilla del dígito k (28 + k)
assert len(GLYPH_DEFS) <= C_ATTEMPTS

WORD_CHARS = dict(GLYPH_INDEX)
WORD_CHARS.update({"#": C_ATTEMPTS, "0": C_SLOT0, "1": C_SLOT0 + 1,
                   "2": C_SLOT0 + 2, "3": C_SLOT0 + 3})


def word_to_indices(word: str):
    """Texto de un estado -> códigos de la ROM de texto (glifo o especial)."""
    return tuple(WORD_CHARS[ch] for ch in word)


def table_text() -> str:
    """Contenido de ``tables/glyphs_abcdefg.txt``: una línea por glifo."""
    return "".join(f"{pat}\n" for _, pat, _ in GLYPH_DEFS)

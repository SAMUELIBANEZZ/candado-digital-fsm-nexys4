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

Los glifos 1..4 son los dígitos 0..3 (intentos restantes); el resto son las
letras necesarias para escribir el nombre de cada estado.
"""

# (clave, patrón abcdefg, descripción)
GLYPH_DEFS = (
    ("_", "0000000", "apagado"),
    ("0", "1111110", "dígito 0"),
    ("1", "0110000", "dígito 1"),
    ("2", "1101101", "dígito 2"),
    ("3", "1111001", "dígito 3"),
    ("I", "0000110", "I (segmentos e,f)"),
    ("d", "0111101", "d"),
    ("L", "0001110", "L"),
    ("E", "1001111", "E"),
    ("n", "0010101", "n"),
    ("P", "1100111", "P"),
    ("t", "0001111", "t"),
    ("C", "1001110", "C"),
    ("H", "0110111", "H"),
    ("c", "0001101", "c"),
    ("O", "1111110", "O"),
    ("F", "1000111", "F"),
    ("r", "0000101", "r"),
    ("A", "1110111", "A"),
)

GLYPH_INDEX = {key: i for i, (key, _, _) in enumerate(GLYPH_DEFS)}

# ROM de 32 entradas (índice de 5 bits); las no usadas quedan apagadas.
GLYPH_ROM = tuple(
    [int(pat, 2) for _, pat, _ in GLYPH_DEFS]
    + [0] * (32 - len(GLYPH_DEFS))
)

G_BLANK = GLYPH_INDEX["_"]
G_DIGIT0 = GLYPH_INDEX["0"]  # los dígitos 0..3 son consecutivos


def word_to_indices(word: str):
    return tuple(GLYPH_INDEX[ch] for ch in word)


def table_text() -> str:
    """Contenido de ``tables/glyphs_abcdefg.txt``: una línea por glifo."""
    return "".join(f"{pat}\n" for _, pat, _ in GLYPH_DEFS)

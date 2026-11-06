"""Display de 7 segmentos multiplexado (8 dígitos).

Cada estado tiene un texto de 8 caracteres (``STATE_WORDS``) que ocupa todo el
display, AN7 = primer carácter:

    LOCKED    "LOCKEd 5"   (a la derecha, intentos restantes)
    INPUT     "CodE--__"   (un '-' por dígito ingresado; el valor no se muestra)
    UNLOCKED  "UnLOCKEd"
    ERROR     "Error  4"   (intentos restantes)
    ALARM     "ALArnn"     (parpadea)
    CONFIG    "SEt 12__"   (el código nuevo sí se muestra para poder revisarlo)

La salida ``seg`` (abcdefg) y ``an`` (un bit por dígito) son de lógica
POSITIVA (1 = encendido); la inversión para la placa se hace en el top.
"""

from myhdl import (Signal, always, always_comb, block, concat, instances,
                   intbv, modbv)

from .glyphs import (C_ATTEMPTS, C_SLOT0, G_DASH, G_HEX0, G_UNDER, GLYPH_ROM,
                     word_to_indices)
from .states import S_ALARM, S_CONFIG, STATE_WORDS

# ROM de texto: dirección = {state_code, carácter 0..7}; 8 entradas por estado
# (el código de estado 7 no se usa y queda apagado).
WORD_ROM = tuple(
    i for word in STATE_WORDS + (" " * 8,) for i in word_to_indices(word.ljust(8))
)


@block
def display_driver(clk, state_code, attempts_left, count, seq, blink, seg, an,
                   SCAN_BITS):
    W = SCAN_BITS + 3
    cnt = Signal(modbv(0)[W:])
    pos = Signal(intbv(0)[3:])
    cidx = Signal(intbv(0)[3:])
    waddr = Signal(intbv(0)[6:])
    wchar = Signal(intbv(0)[5:])
    slot = Signal(intbv(0)[2:])
    nibble = Signal(intbv(0)[4:])
    gidx = Signal(intbv(0)[5:])
    gpat = Signal(intbv(0)[7:])
    an_sel = Signal(intbv(0)[8:])

    @always(clk.posedge)
    def scan():
        cnt.next = cnt + 1

    @always_comb
    def pos_logic():
        pos.next = cnt[W:W - 3]

    # pos = 7 es el dígito de la izquierda (AN7) = carácter 0 del texto.
    @always_comb
    def char_index():
        cidx.next = 7 - pos

    # Dirección de la ROM = {state_code, carácter}. Se arma con concat() y no
    # con state_code*8 + k: en VHDL (numeric_std) el producto unsigned*natural
    # conserva el ancho del operando izquierdo y se truncaría.
    @always_comb
    def addr_logic():
        waddr.next = concat(state_code, cidx)

    @always_comb
    def word_rom_logic():
        wchar.next = WORD_ROM[waddr]

    # Casilla k (0..3) de los códigos especiales C_SLOT0 + k y su dígito.
    @always_comb
    def slot_logic():
        slot.next = wchar[2:0]

    @always_comb
    def nibble_logic():
        if slot == 0:
            nibble.next = seq[16:12]
        elif slot == 1:
            nibble.next = seq[12:8]
        elif slot == 2:
            nibble.next = seq[8:4]
        else:
            nibble.next = seq[4:0]

    @always_comb
    def glyph_select():
        if wchar == C_ATTEMPTS:
            gidx.next = G_HEX0 + attempts_left
        elif wchar >= C_SLOT0:
            if count > slot:
                if state_code == S_CONFIG:
                    gidx.next = G_HEX0 + nibble
                else:
                    gidx.next = G_DASH
            else:
                gidx.next = G_UNDER
        else:
            gidx.next = wchar

    @always_comb
    def glyph_rom_logic():
        gpat.next = GLYPH_ROM[gidx]

    @always_comb
    def an_decode():
        if pos == 0:
            an_sel.next = 0b00000001
        elif pos == 1:
            an_sel.next = 0b00000010
        elif pos == 2:
            an_sel.next = 0b00000100
        elif pos == 3:
            an_sel.next = 0b00001000
        elif pos == 4:
            an_sel.next = 0b00010000
        elif pos == 5:
            an_sel.next = 0b00100000
        elif pos == 6:
            an_sel.next = 0b01000000
        else:
            an_sel.next = 0b10000000

    @always(clk.posedge)
    def out_reg():
        # En ALARM el texto parpadea (segmentos apagados en la fase baja).
        if state_code == S_ALARM and not blink:
            seg.next = 0
        else:
            seg.next = gpat
        an.next = an_sel

    return instances()

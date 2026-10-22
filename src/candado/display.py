"""Display de 7 segmentos multiplexado (8 dígitos).

AN7..AN4 muestran la palabra del estado ("IdLE", "InPt", "OPEn", "Err",
"ALAr", "COnF"...) y AN0 muestra los intentos restantes (0..3).

La salida ``seg`` (abcdefg) y ``an`` (un bit por dígito) son de lógica
POSITIVA (1 = encendido); la inversión para la placa se hace en el top.
"""

from myhdl import (Signal, always, always_comb, block, concat, instances,
                   intbv, modbv)

from .glyphs import G_BLANK, G_DIGIT0, GLYPH_ROM, word_to_indices
from .states import STATE_WORDS

WORD_ROM = tuple(i for word in STATE_WORDS for i in word_to_indices(word.ljust(4, "_")))


@block
def display_driver(clk, state_code, attempts_left, seg, an, SCAN_BITS):
    W = SCAN_BITS + 3
    cnt = Signal(modbv(0)[W:])
    pos = Signal(intbv(0)[3:])
    waddr = Signal(intbv(0)[5:])
    wchar = Signal(intbv(0)[5:])
    gidx = Signal(intbv(0)[5:])
    gpat = Signal(intbv(0)[7:])
    an_sel = Signal(intbv(0)[8:])

    @always(clk.posedge)
    def scan():
        cnt.next = cnt + 1

    @always_comb
    def pos_logic():
        pos.next = cnt[W:W - 3]

    # Dirección de la ROM = {state_code, posición del carácter}. Se arma con
    # concat() y no con state_code*4 + k: en VHDL (numeric_std) el producto
    # unsigned*natural conserva el ancho del operando izquierdo y se truncaría.
    @always_comb
    def addr_logic():
        if pos == 7:
            waddr.next = concat(state_code, intbv(0)[2:])
        elif pos == 6:
            waddr.next = concat(state_code, intbv(1)[2:])
        elif pos == 5:
            waddr.next = concat(state_code, intbv(2)[2:])
        else:
            waddr.next = concat(state_code, intbv(3)[2:])

    @always_comb
    def word_rom_logic():
        wchar.next = WORD_ROM[waddr]

    @always_comb
    def glyph_select():
        if pos >= 4:
            gidx.next = wchar
        elif pos == 0:
            gidx.next = G_DIGIT0 + attempts_left
        else:
            gidx.next = G_BLANK

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
        seg.next = gpat
        an.next = an_sel

    return instances()

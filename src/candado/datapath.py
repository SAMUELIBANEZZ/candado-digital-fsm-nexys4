"""Ruta de datos: registro de secuencia, código almacenado y comparador."""

from myhdl import Signal, always, always_comb, block, concat, instances, intbv


@block
def digit_buffer(clk, rst, clear, push, delete, digit, count, seq):
    """Registro de secuencia ingresada (hasta 4 dígitos de 4 bits).

    * ``push``   : guarda ``digit`` en la siguiente posición y suma 1 a ``count``.
    * ``delete`` : borra el último dígito (resta 1 a ``count``).
    * ``clear``  : borra todo (``count`` = 0).
    * ``seq``    : los 4 dígitos concatenados; el primero ingresado queda en el
                   nibble más significativo (código 0x1234 = se digita 1,2,3,4).
    """
    d0 = Signal(intbv(0)[4:])
    d1 = Signal(intbv(0)[4:])
    d2 = Signal(intbv(0)[4:])
    d3 = Signal(intbv(0)[4:])
    cnt = Signal(intbv(0, min=0, max=5))

    @always(clk.posedge)
    def regs():
        if rst or clear:
            cnt.next = 0
            d0.next = 0
            d1.next = 0
            d2.next = 0
            d3.next = 0
        elif push and cnt < 4:
            if cnt == 0:
                d0.next = digit
            elif cnt == 1:
                d1.next = digit
            elif cnt == 2:
                d2.next = digit
            else:
                d3.next = digit
            cnt.next = cnt + 1
        elif delete and cnt > 0:
            cnt.next = cnt - 1

    @always_comb
    def outs():
        count.next = cnt
        seq.next = concat(d0, d1, d2, d3)

    return instances()


@block
def code_register(clk, rst_hard, we, new_code, code, DEFAULT_CODE):
    """Código de acceso almacenado (16 bits).

    Vuelve al valor de fábrica con el reset duro (CPU_RESET) y al configurar la
    FPGA; el reset de usuario (BTNR) NO lo modifica. No hay memoria no volátil.
    """

    @always(clk.posedge)
    def seq():
        if rst_hard:
            code.next = DEFAULT_CODE
        elif we:
            code.next = new_code

    return seq


@block
def code_comparator(seq, code, match):
    """Comparador combinacional: ``match`` = secuencia ingresada == código."""

    @always_comb
    def logic():
        match.next = seq == code

    return logic

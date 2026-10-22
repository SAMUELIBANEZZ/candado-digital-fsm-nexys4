"""Acondicionamiento de entradas: sincronizador de 2 FF y antirrebote."""

from myhdl import Signal, always, always_comb, block, instances, intbv


@block
def synchronizer(clk, din, dout):
    """Sincronizador de dos flip-flops para una entrada asíncrona de 1 bit.

    Reduce la probabilidad de metaestabilidad al llevar la señal externa
    (pulsador o switch) al dominio del reloj de 100 MHz.
    """
    s1 = Signal(False)

    @always(clk.posedge)
    def seq():
        s1.next = din
        dout.next = s1

    return seq


@block
def debouncer(clk, din, level, pulse, DEBOUNCE_CYCLES):
    """Antirrebote digital con detector de flanco de subida.

    * ``din``   : entrada cruda del pulsador (asíncrona, con rebotes).
    * ``level`` : nivel filtrado; sólo cambia cuando ``din`` (ya sincronizada)
                  permaneció distinta del nivel actual durante
                  ``DEBOUNCE_CYCLES`` ciclos consecutivos.
    * ``pulse`` : un solo ciclo en alto cuando ``level`` sube. Un rebote más
                  corto que ``DEBOUNCE_CYCLES`` reinicia la cuenta y no genera
                  ningún evento.
    """
    s2 = Signal(False)
    sync = synchronizer(clk, din, s2)

    stable = Signal(False)
    prev = Signal(False)
    cnt = Signal(intbv(0, min=0, max=DEBOUNCE_CYCLES))

    @always(clk.posedge)
    def seq():
        if s2 == stable:
            cnt.next = 0
        elif cnt == DEBOUNCE_CYCLES - 1:
            cnt.next = 0
            stable.next = s2
        else:
            cnt.next = cnt + 1
        prev.next = stable

    @always_comb
    def outs():
        level.next = stable
        pulse.next = stable and not prev

    return instances()

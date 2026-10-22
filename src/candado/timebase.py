"""Base de tiempo: habilitación de reloj (clock enable), no reloj dividido."""

from myhdl import Signal, always, block, intbv


@block
def tick_timer(clk, clear, tick, TICK_CYCLES):
    """Genera ``tick`` (1 ciclo en alto) cada ``TICK_CYCLES`` ciclos de reloj.

    ``clear`` reinicia la fase del prescaler. La FSM lo activa en cada cambio
    de estado, de modo que el tiempo de permanencia en ERROR, UNLOCKED, ALARM
    y CONFIG se mide con exactitud desde la entrada al estado.

    Todo el diseño usa un único reloj (100 MHz); ``tick`` sólo habilita la
    cuenta de segundos y no es un reloj.
    """
    cnt = Signal(intbv(0, min=0, max=TICK_CYCLES))

    @always(clk.posedge)
    def seq():
        if clear:
            cnt.next = 0
            tick.next = False
        elif cnt == TICK_CYCLES - 1:
            cnt.next = 0
            tick.next = True
        else:
            cnt.next = cnt + 1
            tick.next = False

    return seq

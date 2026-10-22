"""Registro de eventos por UART (extensión opcional, usa el puente USB-UART
de la propia placa; 115200 8N1, sólo transmisión).

Cada cambio de estado estable envía una línea de 12 bytes:

    "UNLOCKED 0\\r\\n"  ->  8 caracteres de nombre + espacio + intentos fallidos + CR LF

VALIDATE no se registra (dura un ciclo). Si ocurre un nuevo cambio mientras se
transmite, se guarda el último y se envía al terminar (una ranura pendiente).
"""

from myhdl import Signal, always, always_comb, block, concat, instances, intbv

from .states import S_VALIDATE, UART_NAME_ROM


@block
def uart_tx(clk, rst, data, start, busy, txd, BAUD_CYCLES):
    """Transmisor UART 8N1. ``start`` (1 ciclo) con ``busy`` = 0 inicia el envío."""
    baud = Signal(intbv(0, min=0, max=BAUD_CYCLES))
    nbit = Signal(intbv(0)[4:])
    shreg = Signal(intbv(0x3FF)[10:])
    busy_r = Signal(False)

    @always(clk.posedge)
    def seq():
        if rst:
            busy_r.next = False
            txd.next = True
            baud.next = 0
            nbit.next = 0
        elif not busy_r:
            txd.next = True
            if start:
                shreg.next = concat(True, data, False)  # stop, dato, start
                busy_r.next = True
                txd.next = False                         # bit de start
                baud.next = 0
                nbit.next = 0
        else:
            if baud == BAUD_CYCLES - 1:
                baud.next = 0
                if nbit == 9:
                    busy_r.next = False
                    txd.next = True
                else:
                    nbit.next = nbit + 1
                    txd.next = shreg[1]
                    shreg.next = concat(True, shreg[10:1])
            else:
                baud.next = baud + 1

    @always_comb
    def busy_out():
        busy.next = busy_r

    return instances()


@block
def event_logger(clk, rst, state_code, fail, txd, BAUD_CYCLES):
    tdata = Signal(intbv(0)[8:])
    tstart = Signal(False)
    tbusy = Signal(False)
    tx = uart_tx(clk, rst, tdata, tstart, tbusy, txd, BAUD_CYCLES)

    prev = Signal(intbv(0)[3:])
    pending = Signal(False)
    pend_state = Signal(intbv(0)[3:])
    msg_state = Signal(intbv(0)[3:])
    msg_fail = Signal(intbv(0)[2:])
    idx = Signal(intbv(0)[4:])
    phase = Signal(intbv(0)[2:])
    raddr = Signal(intbv(0)[6:])
    rchar = Signal(intbv(0)[8:])

    # Dirección = {estado, índice de carácter}; concat() en vez de msg_state*8 + idx
    # porque en VHDL el producto unsigned*natural se trunca al ancho de msg_state.
    @always_comb
    def addr_logic():
        if idx < 8:
            raddr.next = concat(msg_state, idx[3:])
        else:
            raddr.next = 0

    @always_comb
    def rom_logic():
        rchar.next = UART_NAME_ROM[raddr]

    @always_comb
    def data_logic():
        if idx < 8:
            tdata.next = rchar
        elif idx == 8:
            tdata.next = 32
        elif idx == 9:
            tdata.next = 48 + msg_fail
        elif idx == 10:
            tdata.next = 13
        else:
            tdata.next = 10

    @always(clk.posedge)
    def seq():
        prev.next = state_code
        tstart.next = False
        if rst:
            phase.next = 0
            pending.next = False
            idx.next = 0
        else:
            if phase == 0:
                if pending:
                    msg_state.next = pend_state
                    msg_fail.next = fail
                    idx.next = 0
                    pending.next = False
                    phase.next = 1
            elif phase == 1:
                if not tbusy:
                    tstart.next = True
                    phase.next = 2
            elif phase == 2:
                phase.next = 3
            else:
                if not tbusy:
                    if idx == 11:
                        phase.next = 0
                    else:
                        idx.next = idx + 1
                        phase.next = 1
            # La detección va al final para que gane sobre el consumo de 'pending'.
            if state_code != prev and state_code != S_VALIDATE:
                pending.next = True
                pend_state.next = state_code

    return instances()

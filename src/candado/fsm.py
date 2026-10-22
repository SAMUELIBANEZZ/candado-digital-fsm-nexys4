"""Unidad de control: FSM de Moore (FSMD) del candado digital.

Estados (los 6 del anteproyecto + CONFIG para cambiar el código):

    IDLE      reposo, sin dígitos.
    INPUT     captura de los 4 dígitos.
    VALIDATE  compara la secuencia con el código (dura un ciclo).
    UNLOCKED  acceso concedido durante UNLOCKED_TICKS.
    ERROR     intento fallido registrado, visible durante ERROR_TICKS.
    ALARM     bloqueo tras MAX_ATTEMPTS fallos; sólo sale por BTNR o timeout.
    CONFIG    captura de un código nuevo (sólo se entra desde UNLOCKED con SW15).

Estilo de tres procesos: registro de estado, lógica de siguiente estado /
habilitaciones del datapath y decodificación de ``state_code``.
Prioridad de entradas simultáneas: BTNR > BTNL > BTNC.
"""

from myhdl import Signal, always, always_comb, block, enum, instances, intbv

from .states import (S_ALARM, S_CONFIG, S_ERROR, S_IDLE, S_INPUT, S_UNLOCKED,
                     S_VALIDATE)

t_state = enum("IDLE", "INPUT", "VALIDATE", "UNLOCKED", "ERROR", "ALARM", "CONFIG")


@block
def fsm_control(clk, rst, btn_c, btn_l, btn_r, sw_mode, count, match, tick,
                state_code, clear_timer, push_en, del_en, clear_buf, code_we,
                fail,
                ERROR_TICKS, UNLOCKED_TICKS, ALARM_TICKS, CONFIG_TICKS,
                MAX_ATTEMPTS, TICK_MAX):
    state = Signal(t_state.IDLE)
    next_state = Signal(t_state.IDLE)
    tcount = Signal(intbv(0, min=0, max=TICK_MAX + 1))
    fail_r = Signal(intbv(0, min=0, max=MAX_ATTEMPTS + 1))
    timeout = Signal(False)

    # --- Proceso 1: registros (estado, contador de ticks, intentos fallidos)
    @always(clk.posedge)
    def seq():
        if rst:
            state.next = t_state.IDLE
            tcount.next = 0
            fail_r.next = 0
        else:
            state.next = next_state
            if next_state != state:
                tcount.next = 0
            elif tick and tcount < TICK_MAX:
                tcount.next = tcount + 1

            if btn_r:
                fail_r.next = 0
            elif state == t_state.VALIDATE:
                if match:
                    fail_r.next = 0
                elif fail_r < MAX_ATTEMPTS:
                    fail_r.next = fail_r + 1
            elif state == t_state.ALARM and next_state == t_state.IDLE:
                fail_r.next = 0

    # --- Vencimiento del temporizador del estado actual
    @always_comb
    def timeout_logic():
        timeout.next = False
        if state == t_state.ERROR:
            if tcount >= ERROR_TICKS:
                timeout.next = True
        elif state == t_state.UNLOCKED:
            if tcount >= UNLOCKED_TICKS:
                timeout.next = True
        elif state == t_state.ALARM:
            if tcount >= ALARM_TICKS:
                timeout.next = True
        elif state == t_state.CONFIG:
            if tcount >= CONFIG_TICKS:
                timeout.next = True

    # --- Proceso 2: siguiente estado y habilitaciones del datapath
    @always_comb
    def comb():
        next_state.next = state
        push_en.next = False
        del_en.next = False
        clear_buf.next = False
        code_we.next = False

        if btn_r:
            # Reset de usuario: vuelve a IDLE desde cualquier estado.
            next_state.next = t_state.IDLE
            clear_buf.next = True
        elif state == t_state.IDLE:
            if btn_c and not btn_l:
                push_en.next = True
                next_state.next = t_state.INPUT
        elif state == t_state.INPUT:
            if count == 4:
                next_state.next = t_state.VALIDATE
            elif btn_l:
                if count > 0:
                    del_en.next = True
                if count == 1:
                    next_state.next = t_state.IDLE
            elif btn_c:
                push_en.next = True
        elif state == t_state.VALIDATE:
            clear_buf.next = True
            if match:
                next_state.next = t_state.UNLOCKED
            else:
                next_state.next = t_state.ERROR
        elif state == t_state.UNLOCKED:
            if timeout:
                next_state.next = t_state.IDLE
            elif btn_c and sw_mode and not btn_l:
                push_en.next = True
                next_state.next = t_state.CONFIG
        elif state == t_state.ERROR:
            if timeout:
                if fail_r >= MAX_ATTEMPTS:
                    next_state.next = t_state.ALARM
                else:
                    next_state.next = t_state.INPUT
        elif state == t_state.ALARM:
            if timeout:
                next_state.next = t_state.IDLE
        elif state == t_state.CONFIG:
            if timeout:
                next_state.next = t_state.IDLE
                clear_buf.next = True
            elif count == 4:
                code_we.next = True
                clear_buf.next = True
                next_state.next = t_state.UNLOCKED
            elif btn_l:
                if count > 0:
                    del_en.next = True
            elif btn_c:
                push_en.next = True

    @always_comb
    def timer_clear():
        clear_timer.next = next_state != state

    # --- Proceso 3: decodificación de salidas (Moore)
    @always_comb
    def outputs():
        if state == t_state.IDLE:
            state_code.next = S_IDLE
        elif state == t_state.INPUT:
            state_code.next = S_INPUT
        elif state == t_state.VALIDATE:
            state_code.next = S_VALIDATE
        elif state == t_state.UNLOCKED:
            state_code.next = S_UNLOCKED
        elif state == t_state.ERROR:
            state_code.next = S_ERROR
        elif state == t_state.ALARM:
            state_code.next = S_ALARM
        else:
            state_code.next = S_CONFIG

    @always_comb
    def fail_out():
        fail.next = fail_r

    return instances()

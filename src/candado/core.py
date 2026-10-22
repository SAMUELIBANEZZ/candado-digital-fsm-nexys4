"""Núcleo del candado: entradas acondicionadas + ruta de datos + FSM."""

from myhdl import Signal, always, always_comb, block, concat, instances, intbv

from .datapath import code_comparator, code_register, digit_buffer
from .fsm import fsm_control
from .inputs import debouncer
from .timebase import tick_timer


@block
def candado_core(clk, rst, btnc, btnl, btnr, sw_digit, sw_mode,
                 state_code, count, fail, attempts_left, code,
                 DEBOUNCE_CYCLES, TICK_CYCLES, ERROR_TICKS, UNLOCKED_TICKS,
                 ALARM_TICKS, CONFIG_TICKS, MAX_ATTEMPTS, TICK_MAX,
                 DEFAULT_CODE):
    """Núcleo funcional.

    Entradas  : ``rst`` (reset duro ya sincronizado, activo en alto), botones
                crudos ``btnc/btnl/btnr``, ``sw_digit`` (SW3..SW0) y
                ``sw_mode`` (SW15).
    Salidas   : ``state_code``, ``count`` (dígitos ingresados), ``fail``
                (intentos fallidos), ``attempts_left`` y ``code`` (código
                vigente; sólo para observación y pruebas).
    """
    # Botones: sincronizador + antirrebote + flanco.
    c_level = Signal(False)
    c_pulse = Signal(False)
    l_level = Signal(False)
    l_pulse = Signal(False)
    r_level = Signal(False)
    r_pulse = Signal(False)
    deb_c = debouncer(clk, btnc, c_level, c_pulse, DEBOUNCE_CYCLES)
    deb_l = debouncer(clk, btnl, l_level, l_pulse, DEBOUNCE_CYCLES)
    deb_r = debouncer(clk, btnr, r_level, r_pulse, DEBOUNCE_CYCLES)

    # Switches: sólo sincronización (se muestrean al confirmar con BTNC).
    sw_s1 = Signal(intbv(0)[5:])
    sw_s2 = Signal(intbv(0)[5:])
    digit = Signal(intbv(0)[4:])
    mode = Signal(False)

    @always(clk.posedge)
    def sw_sync():
        sw_s1.next = concat(sw_mode, sw_digit)
        sw_s2.next = sw_s1

    @always_comb
    def sw_split():
        digit.next = sw_s2[4:0]
        mode.next = sw_s2[4]

    # Señales internas del datapath y de control.
    tick = Signal(False)
    clear_timer = Signal(False)
    push_en = Signal(False)
    del_en = Signal(False)
    clear_buf = Signal(False)
    code_we = Signal(False)
    seq = Signal(intbv(0)[16:])
    match = Signal(False)

    timer = tick_timer(clk, clear_timer, tick, TICK_CYCLES)
    buf = digit_buffer(clk, rst, clear_buf, push_en, del_en, digit, count, seq)
    store = code_register(clk, rst, code_we, seq, code, DEFAULT_CODE)
    cmp_ = code_comparator(seq, code, match)
    ctrl = fsm_control(clk, rst, c_pulse, l_pulse, r_pulse, mode, count, match,
                       tick, state_code, clear_timer, push_en, del_en,
                       clear_buf, code_we, fail,
                       ERROR_TICKS, UNLOCKED_TICKS, ALARM_TICKS, CONFIG_TICKS,
                       MAX_ATTEMPTS, TICK_MAX)

    @always_comb
    def attempts():
        attempts_left.next = MAX_ATTEMPTS - fail

    return instances()

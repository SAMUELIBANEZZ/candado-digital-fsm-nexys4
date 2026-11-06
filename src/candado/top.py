"""Nivel superior: pines de la Nexys4 DDR / Nexys A7-100T.

Los nombres de los puertos coinciden con los del XDC maestro de Digilent
(CLK100MHZ, CPU_RESETN, SW, BTNx, LED, AN, UART_RXD_OUT, LED16_x, AUD_PWM,
AUD_SD). Los segmentos CA..CG se agrupan en el bus SEG[6:0] con SEG[6]=CA ...
SEG[0]=CG (mismo orden "abcdefg" del taller). ``BUZZER`` va al pin JA[1] del
conector Pmod JA (zumbador piezoeléctrico pasivo opcional).

Lógica de la placa: cátodos y ánodos son ACTIVOS EN BAJO; el reset
CPU_RESETN (botón rojo) también es activo en bajo.
"""

from myhdl import Signal, always, always_comb, block, instances, intbv

from .core import candado_core
from .display import display_driver
from .alarm import alarm_outputs
from .params import HW
from .status import status_outputs
from .uart import event_logger


@block
def candado_top(CLK100MHZ, CPU_RESETN, SW, BTNC, BTNU, BTND, BTNL, BTNR,
                LED, SEG, DP, AN, LED16_R, LED16_G, LED16_B, UART_RXD_OUT,
                AUD_PWM, AUD_SD, BUZZER, p=HW, enable_uart=True):
    DEB = p.debounce_cycles
    TICK = p.tick_cycles
    ERR = p.error_ticks
    UNL = p.unlocked_ticks
    ALM = p.alarm_ticks
    CFG = p.config_ticks
    MAXA = p.max_attempts
    TMAX = p.tick_max
    DEF = p.default_code
    SCAN = p.scan_bits
    BAUD = p.baud_cycles
    PWM = p.pwm_bits
    BLINK = p.blink_bits
    TONE_HI = p.tone_hi_cycles
    TONE_LO = p.tone_lo_cycles

    # Reset duro: CPU_RESETN (activo en bajo) -> sincronizado, activo en alto.
    # Arranca en 1 para mantener el diseño en reset los primeros ciclos.
    rst_s1 = Signal(True)
    rst = Signal(True)

    @always(CLK100MHZ.posedge)
    def rst_sync():
        rst_s1.next = not CPU_RESETN
        rst.next = rst_s1

    # Sólo SW3..SW0 tienen función (dígito a ingresar).
    sw_digit = Signal(intbv(0)[4:])

    @always_comb
    def sw_split():
        sw_digit.next = SW[4:0]

    state_code = Signal(intbv(0)[3:])
    count = Signal(intbv(0, min=0, max=5))
    fail = Signal(intbv(0, min=0, max=MAXA + 1))
    attempts_left = Signal(intbv(0, min=0, max=MAXA + 1))
    code = Signal(intbv(DEF)[16:])
    seq = Signal(intbv(0)[16:])

    core = candado_core(CLK100MHZ, rst, BTNC, BTNL, BTNR, BTNU, BTND, sw_digit,
                        state_code, count, fail, attempts_left, code, seq,
                        DEB, TICK, ERR, UNL, ALM, CFG, MAXA, TMAX, DEF)

    # Alarma: base de parpadeo y sirena.
    blink = Signal(False)
    tone = Signal(False)
    amp_on = Signal(False)
    siren = alarm_outputs(CLK100MHZ, state_code, blink, tone, amp_on,
                          BLINK, TONE_HI, TONE_LO)

    @always_comb
    def pins_audio():
        AUD_PWM.next = tone
        AUD_SD.next = amp_on
        BUZZER.next = tone

    # Display: el driver entrega lógica positiva; aquí se invierte para la placa.
    seg_raw = Signal(intbv(0)[7:])
    an_raw = Signal(intbv(0)[8:])
    disp = display_driver(CLK100MHZ, state_code, attempts_left, count, seq,
                          blink, seg_raw, an_raw, SCAN)

    @always_comb
    def pins_display():
        SEG.next = seg_raw ^ 0x7F
        AN.next = an_raw ^ 0xFF

    @always(CLK100MHZ.posedge)
    def dp_off():
        # Punto decimal apagado (lógica negativa: 1 = apagado).
        DP.next = True

    # LEDs y LED RGB.
    rgb = Signal(intbv(0)[3:])
    status = status_outputs(CLK100MHZ, state_code, count, attempts_left, blink,
                            LED, rgb, PWM)

    @always_comb
    def pins_rgb():
        LED16_R.next = rgb[2]
        LED16_G.next = rgb[1]
        LED16_B.next = rgb[0]

    # Registro UART (opcional).
    if enable_uart:
        logger = event_logger(CLK100MHZ, rst, state_code, fail, UART_RXD_OUT, BAUD)
    else:
        @always(CLK100MHZ.posedge)
        def uart_idle():
            # Sin registro UART: la línea queda en reposo (1).
            UART_RXD_OUT.next = True

    return instances()

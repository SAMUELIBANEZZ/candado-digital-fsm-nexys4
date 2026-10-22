"""Indicadores: LEDs LD15..LD0 y LED RGB LD16.

* LD3..LD0 : dígitos ingresados en código termómetro (0000, 0001, 0011, 0111, 1111).
* LD12     : CONFIG          LD13 : UNLOCKED
* LD14     : ERROR           LD15 : ALARM
* LD16 RGB : un color distinto por estado, atenuado por PWM (encendido 1/16 del tiempo) porque el
             LED RGB de la placa es muy brillante.
"""

from myhdl import Signal, always, always_comb, block, concat, instances, intbv, modbv

from .states import S_ALARM, S_CONFIG, S_ERROR, S_UNLOCKED, STATE_RGB


@block
def status_outputs(clk, state_code, count, led, rgb, PWM_BITS):
    pwm_cnt = Signal(modbv(0)[PWM_BITS:])
    rgb_raw = Signal(intbv(0)[3:])
    therm = Signal(intbv(0)[4:])
    f_config = Signal(False)
    f_unlocked = Signal(False)
    f_error = Signal(False)
    f_alarm = Signal(False)

    @always(clk.posedge)
    def pwm():
        pwm_cnt.next = pwm_cnt + 1

    @always_comb
    def rgb_rom():
        rgb_raw.next = STATE_RGB[state_code]

    @always(clk.posedge)
    def rgb_out():
        if pwm_cnt[PWM_BITS:PWM_BITS - 4] == 0:
            rgb.next = rgb_raw
        else:
            rgb.next = 0

    @always_comb
    def thermometer():
        if count == 0:
            therm.next = 0b0000
        elif count == 1:
            therm.next = 0b0001
        elif count == 2:
            therm.next = 0b0011
        elif count == 3:
            therm.next = 0b0111
        else:
            therm.next = 0b1111

    @always_comb
    def flags():
        f_config.next = state_code == S_CONFIG
        f_unlocked.next = state_code == S_UNLOCKED
        f_error.next = state_code == S_ERROR
        f_alarm.next = state_code == S_ALARM

    @always_comb
    def led_logic():
        led.next = concat(f_alarm, f_error, f_unlocked, f_config,
                          intbv(0)[8:], therm)

    return instances()

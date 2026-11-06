"""Indicadores: LEDs LD15..LD0 y LED RGB LD16.

* LD3..LD0  : dígitos ingresados en código termómetro (0000, 0001, 0011, 0111, 1111).
* LD8..LD4  : intentos restantes en código termómetro (5 LEDs = 5 intentos).
* LD11      : candado cerrado (cualquier estado salvo UNLOCKED y CONFIG).
* LD12      : CONFIG          LD13 : UNLOCKED
* LD14      : ERROR           LD15 : ALARM
* En ALARM todos los LEDs parpadean.
* LD16 RGB  : un color distinto por estado, atenuado por PWM (encendido 1/16 del
              tiempo) porque el LED RGB de la placa es muy brillante. En ALARM
              parpadea.
"""

from myhdl import Signal, always, always_comb, block, concat, instances, intbv, modbv

from .states import S_ALARM, S_CONFIG, S_ERROR, S_UNLOCKED, STATE_RGB


@block
def status_outputs(clk, state_code, count, attempts_left, blink, led, rgb,
                   PWM_BITS):
    pwm_cnt = Signal(modbv(0)[PWM_BITS:])
    rgb_raw = Signal(intbv(0)[3:])
    therm = Signal(intbv(0)[4:])
    tries = Signal(intbv(0)[5:])
    f_locked = Signal(False)
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
        if pwm_cnt[PWM_BITS:PWM_BITS - 4] == 0 and (blink or not f_alarm):
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
    def attempts_bar():
        if attempts_left == 0:
            tries.next = 0b00000
        elif attempts_left == 1:
            tries.next = 0b00001
        elif attempts_left == 2:
            tries.next = 0b00011
        elif attempts_left == 3:
            tries.next = 0b00111
        elif attempts_left == 4:
            tries.next = 0b01111
        else:
            tries.next = 0b11111

    @always_comb
    def flags():
        f_config.next = state_code == S_CONFIG
        f_unlocked.next = state_code == S_UNLOCKED
        f_error.next = state_code == S_ERROR
        f_alarm.next = state_code == S_ALARM
        f_locked.next = state_code != S_UNLOCKED and state_code != S_CONFIG

    @always_comb
    def led_logic():
        if f_alarm:
            if blink:
                led.next = 0xFFFF
            else:
                led.next = 0
        else:
            led.next = concat(f_alarm, f_error, f_unlocked, f_config, f_locked,
                              intbv(0)[2:], tries, therm)

    return instances()

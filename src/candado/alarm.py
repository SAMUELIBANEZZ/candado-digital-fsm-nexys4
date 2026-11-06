"""Alarma sonora y base de parpadeo.

La Nexys4 DDR NO trae parlante ni zumbador: trae una salida de audio mono
(conector jack de 3,5 mm, filtro pasabajos + amplificador) gobernada por
``AUD_PWM`` (pin A11) y ``AUD_SD`` (pin D12, 1 = amplificador encendido).
En ALARM se genera una sirena de dos tonos (onda cuadrada que alterna entre
``TONE_HI`` y ``TONE_LO`` en cada fase de parpadeo) por:

* ``AUD_PWM``  -> audífonos o parlante con amplificador en el jack de audio.
* ``JA[1]``    -> zumbador piezoeléctrico PASIVO opcional entre JA1 y GND (Pmod JA).

Además, LEDs, LED RGB y display parpadean (status.py, display.py), de modo que
la alarma es visible aunque no haya nada conectado al audio.
"""

from myhdl import Signal, always, always_comb, block, instances, intbv, modbv

from .states import S_ALARM


@block
def alarm_outputs(clk, state_code, blink, tone, aud_sd, BLINK_BITS,
                  TONE_HI, TONE_LO):
    """``blink``: onda cuadrada lenta (MSB de un contador libre de BLINK_BITS).
    ``tone``  : sirena (sólo en ALARM; 0 en los demás estados).
    ``aud_sd``: habilita el amplificador de audio de la placa sólo en ALARM.
    """
    bcnt = Signal(modbv(0)[BLINK_BITS:])
    half = max(TONE_HI, TONE_LO)
    tcnt = Signal(intbv(0, min=0, max=half))
    sq = Signal(False)
    in_alarm = Signal(False)

    @always(clk.posedge)
    def blink_counter():
        bcnt.next = bcnt + 1

    @always_comb
    def blink_out():
        blink.next = bcnt[BLINK_BITS - 1]
        in_alarm.next = state_code == S_ALARM

    # Generador de onda cuadrada: invierte ``sq`` cada medio periodo; el medio
    # periodo depende de la fase de parpadeo (tono agudo / tono grave).
    @always(clk.posedge)
    def tone_gen():
        if not in_alarm:
            tcnt.next = 0
            sq.next = False
        elif (blink and tcnt >= TONE_HI - 1) or (not blink and tcnt >= TONE_LO - 1):
            tcnt.next = 0
            sq.next = not sq
        else:
            tcnt.next = tcnt + 1

    @always_comb
    def outs():
        tone.next = sq
        aud_sd.next = in_alarm

    return instances()

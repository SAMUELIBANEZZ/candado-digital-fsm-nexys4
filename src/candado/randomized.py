"""Estímulos pseudoaleatorios acoplados al modelo de referencia.

``random_stimulus`` construye una secuencia ciclo a ciclo (pulsaciones con
rebotes, pulsos espurios, esperas largas, resets...) y, en paralelo, avanza el
modelo de referencia. Devuelve el estímulo y una lista de comprobaciones
``(marca, (estado, dígitos, fallos, código))`` para comparar con el RTL.

Regla de margen: ninguna pulsación ni muestra se coloca a menos de ``MARGIN``
ciclos de un vencimiento de temporizador; así el resultado no depende de la
latencia exacta (+/- unos pocos ciclos) entre el modelo y el hardware.
"""

import random

from .params import Params
from .reference import LockModel
from .testing import Stimulus

MARGIN = 14


def press_geometry(p: Params, simultaneous: bool, bounce: bool):
    """(instante en que surte efecto, duración total) de una pulsación de ``Stimulus``."""
    d = p.debounce_cycles
    short = max(1, d // 4)
    hold = gap = d + 8
    if simultaneous or not bounce:
        return d + 5, hold + gap
    prefix = 3 * short + 2
    suffix = 3 * short + 1
    return prefix + d + 5, prefix + hold + suffix + gap


def random_stimulus(p: Params, seed: int, events: int = 60):
    rng = random.Random(seed)
    model = LockModel(p)
    s = Stimulus(p)
    checks = []
    d = p.debounce_cycles

    def wait(n):
        s.wait(n)
        model.advance(n)

    def clear_of_timeout(effect, duration):
        """Espera hasta que efecto y muestra queden lejos de un vencimiento."""
        while True:
            rem = model.remaining()
            if rem is None:
                return
            if abs(rem - effect) < MARGIN or abs(rem - duration) < MARGIN \
                    or effect < rem < duration:
                wait(rem + MARGIN + 2)
                continue
            return

    def press(buttons, digit=None, mode=False, bounce=True):
        if digit is not None:
            s.set_sw((digit & 0xF) | (0x8000 if mode else 0))
            wait(4)
        simultaneous = len(buttons) > 1
        effect, duration = press_geometry(p, simultaneous, bounce)
        clear_of_timeout(effect, duration)
        if simultaneous:
            s.press_together(sorted(buttons))
        else:
            s.press(next(iter(buttons)), bounce=bounce)
        model.advance(effect)
        model.press(buttons, digit or 0, mode)
        model.advance(duration - effect)

    s.reset_hard()
    model.hard_reset()
    model.advance(5 + d + 2)
    s.mark("ev_inicio")
    checks.append(("ev_inicio", model.snapshot()))

    for n in range(events):
        r = rng.random()
        bounce = rng.random() < 0.7
        mode = rng.random() < 0.25
        if r < 0.38:                                   # un dígito
            press({"BTNC"}, rng.randrange(16), mode, bounce)
        elif r < 0.50:                                 # código completo (correcto o con 1 error)
            digits = [(model.code >> sh) & 0xF for sh in (12, 8, 4, 0)]
            if rng.random() < 0.4:
                digits[rng.randrange(4)] ^= 1 << rng.randrange(4)
            for dgt in digits:
                press({"BTNC"}, dgt, False, rng.random() < 0.7)
            if rng.random() < 0.4:                     # si abrió, intenta entrar a CONFIG (SW15)
                press({"BTNC"}, rng.randrange(16), True, bounce)
        elif r < 0.60:                                 # borrar
            press({"BTNL"}, bounce=bounce)
        elif r < 0.65:                                 # BTNR
            press({"BTNR"}, bounce=bounce)
        elif r < 0.67:                                 # reset duro
            clear_of_timeout(0, 5 + d + 2 + MARGIN)
            s.reset_hard()
            model.hard_reset()
            model.advance(5 + d + 2)
        elif r < 0.72:                                 # simultáneas
            combo = rng.choice([{"BTNC", "BTNL"}, {"BTNC", "BTNR"}, {"BTNL", "BTNR"}])
            press(combo, rng.randrange(16), mode, False)
        elif r < 0.76:                                 # botones sin función
            press({rng.choice(["BTNU", "BTND"])}, bounce=bounce)
        elif r < 0.82:                                 # pulso espurio (< antirrebote)
            btn = rng.choice(["BTNC", "BTNL", "BTNR"])
            length = rng.randrange(1, max(2, d // 2 + 1))
            dur = length + d + 8
            clear_of_timeout(dur, dur)
            s.glitch(btn, length=length)
            model.advance(dur)
        else:                                          # espera (corta o hasta cerca de un vencimiento)
            if rng.random() < 0.6 or model.remaining() is None:
                n_wait = rng.randrange(1, p.tick_cycles * 3)
            else:
                n_wait = max(1, model.remaining() + rng.choice([-3 * MARGIN, 3 * MARGIN]))
            clear_of_timeout(n_wait, n_wait)
            wait(n_wait)
        wait(2)
        rem = model.remaining()
        if rem is not None and rem < MARGIN:           # la muestra no puede caer junto a un vencimiento
            wait(rem + MARGIN + 2)
        name = f"ev{n}"
        s.mark(name)
        checks.append((name, model.snapshot()))
    return s, checks

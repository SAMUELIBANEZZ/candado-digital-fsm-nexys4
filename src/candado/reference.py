"""Modelo de referencia independiente del candado (sin reloj, por eventos).

Escrito a partir de la especificación (anteproyecto + reglas de diseño), NO a
partir del RTL: sirve para detectar discrepancias entre lo que se especificó y
lo que se implementó. Trabaja con *eventos* (pulsaciones ya antirrebotadas) y
con el paso del tiempo en ciclos de reloj.
"""

from .params import Params

TIMED = ("ERROR", "UNLOCKED", "ALARM", "CONFIG")


class LockModel:
    def __init__(self, p: Params):
        self.p = p
        self.code = p.default_code
        self.soft_reset()

    # -- resets ----------------------------------------------------------------
    def soft_reset(self):
        """BTNR: vuelve a IDLE, borra dígitos e intentos; conserva el código."""
        self.state = "IDLE"
        self.digits = []
        self.fail = 0
        self.t = 0

    def hard_reset(self):
        """CPU_RESET: además restaura el código de fábrica."""
        self.code = self.p.default_code
        self.soft_reset()

    # -- tiempo ------------------------------------------------------------------
    def limit(self, state=None):
        state = state or self.state
        ticks = {"ERROR": self.p.error_ticks, "UNLOCKED": self.p.unlocked_ticks,
                 "ALARM": self.p.alarm_ticks, "CONFIG": self.p.config_ticks}[state]
        return ticks * self.p.tick_cycles

    def remaining(self):
        """Ciclos hasta el vencimiento del estado actual (None si no tiene)."""
        if self.state not in TIMED:
            return None
        return self.limit() - self.t

    def _enter(self, state):
        self.state = state
        self.t = 0

    def advance(self, cycles):
        self.t += cycles
        while self.state in TIMED and self.t >= self.limit():
            carry = self.t - self.limit()
            self._timeout()
            self.t = carry

    def _timeout(self):
        if self.state == "ERROR":
            if self.fail >= self.p.max_attempts:
                self._enter("ALARM")
            else:
                self._enter("INPUT")
        elif self.state == "UNLOCKED":
            self._enter("IDLE")
        elif self.state == "ALARM":
            self.fail = 0
            self._enter("IDLE")
        elif self.state == "CONFIG":
            self.digits = []
            self._enter("IDLE")

    # -- eventos -----------------------------------------------------------------
    def _validate(self):
        value = 0
        for d in self.digits:
            value = (value << 4) | d
        self.digits = []
        if value == self.code:
            self.fail = 0
            self._enter("UNLOCKED")
        else:
            self.fail = min(self.fail + 1, self.p.max_attempts)
            self._enter("ERROR")

    def press(self, buttons, digit=0, mode=False):
        """Pulsación de uno o más botones (``buttons``: conjunto de nombres)."""
        c, l, r = "BTNC" in buttons, "BTNL" in buttons, "BTNR" in buttons
        if r:                                  # BTNR > BTNL > BTNC
            self.soft_reset()
            return
        s = self.state
        if s == "IDLE":
            if c and not l:
                self.digits = [digit]
                self._enter("INPUT")
        elif s == "INPUT":
            if l:
                if self.digits:               # sin dígitos (tras ERROR) BTNL no hace nada
                    self.digits.pop()
                    if not self.digits:
                        self._enter("IDLE")
            elif c:
                self.digits.append(digit)
                if len(self.digits) == 4:
                    self._validate()
        elif s == "UNLOCKED":
            if c and mode and not l:
                self.digits = [digit]
                self._enter("CONFIG")
        elif s == "CONFIG":
            if l:
                if self.digits:
                    self.digits.pop()
            elif c:
                self.digits.append(digit)
                if len(self.digits) == 4:
                    value = 0
                    for d in self.digits:
                        value = (value << 4) | d
                    self.code = value
                    self.digits = []
                    self._enter("UNLOCKED")
        # ERROR y ALARM ignoran los botones (salvo BTNR)

    # -- observación ---------------------------------------------------------------
    @property
    def count(self):
        return len(self.digits)

    def snapshot(self):
        return (self.state, self.count, self.fail, self.code)

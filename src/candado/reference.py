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
        self.hard_reset()

    # -- resets ----------------------------------------------------------------
    def cancel(self):
        """BTNR: vuelve a LOCKED y borra los dígitos; conserva código e intentos."""
        self.state = "LOCKED"
        self.digits = []
        self.t = 0

    def hard_reset(self):
        """CPU_RESET: LOCKED, sin intentos fallidos y con el código de fábrica."""
        self.code = self.p.default_code
        self.fail = 0
        self.cancel()

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
                self._enter("LOCKED")
        elif self.state == "UNLOCKED":
            self._enter("LOCKED")
        elif self.state == "ALARM":
            self.fail = 0
            self._enter("LOCKED")
        elif self.state == "CONFIG":
            self.digits = []
            self._enter("LOCKED")

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

    def press(self, buttons, digit=0):
        """Pulsación de uno o más botones (``buttons``: conjunto de nombres)."""
        c, l, r = "BTNC" in buttons, "BTNL" in buttons, "BTNR" in buttons
        u, d = "BTNU" in buttons, "BTND" in buttons
        s = self.state
        if s == "ALARM":                       # la alarma ignora todos los botones
            return
        if r:                                  # BTNR > BTNL > BTNC
            self.cancel()
            return
        if s == "LOCKED":
            if c and not l:
                self.digits = [digit]
                self._enter("INPUT")
        elif s == "INPUT":
            if l:
                self.digits.pop()
                if not self.digits:
                    self._enter("LOCKED")
            elif c:
                self.digits.append(digit)
                if len(self.digits) == 4:
                    self._validate()
        elif s == "UNLOCKED":
            if d:                              # BTND > BTNU
                self._enter("LOCKED")
            elif u:
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
        # ERROR ignora los botones (salvo BTNR)

    # -- observación ---------------------------------------------------------------
    @property
    def count(self):
        return len(self.digits)

    def snapshot(self):
        return (self.state, self.count, self.fail, self.code)

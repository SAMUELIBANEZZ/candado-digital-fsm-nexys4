"""Arnés de verificación: estímulos, bancos de simulación MyHDL y decodificadores.

El mismo constructor de estímulos (:class:`Stimulus`) alimenta:

* las pruebas ``pytest`` (simulación en Python con MyHDL), y
* la generación de vectores para el testbench VHDL (``tools/generate_vectors.py``),

de modo que el VHDL convertido se compara ciclo a ciclo con el modelo Python.

Temporización de un ciclo ``k`` (periodo 10, flancos de subida en 5+10k):
las entradas se aplican en t = 10k y las salidas se muestrean en t = 10k+9,
es decir, justo después del flanco que capturó las entradas del ciclo ``k``.
"""

from dataclasses import dataclass, field

from myhdl import (Signal, StopSimulation, always, block, delay, instance,
                   instances, intbv)

from .core import candado_core
from .glyphs import GLYPH_ROM
from .params import SIM, Params
from .states import STATE_NAMES
from .top import candado_top

BUTTONS = ("BTNC", "BTNU", "BTND", "BTNL", "BTNR")

# Bits de la palabra de entrada / salida usada en los vectores VHDL.
IN_WIDTH = 22    # [21]=CPU_RESETN [20]=BTNC [19]=BTNU [18]=BTND [17]=BTNL [16]=BTNR [15:0]=SW
OUT_WIDTH = 36   # [35:20]=LED [19:13]=SEG [12]=DP [11:4]=AN [3]=LED16_R [2]=LED16_G [1]=LED16_B [0]=UART


# --------------------------------------------------------------------------
# Estímulos
# --------------------------------------------------------------------------
@dataclass
class Vec:
    rstn: int = 1
    btnc: int = 0
    btnu: int = 0
    btnd: int = 0
    btnl: int = 0
    btnr: int = 0
    sw: int = 0

    def word(self) -> int:
        return ((self.rstn << 21) | (self.btnc << 20) | (self.btnu << 19)
                | (self.btnd << 18) | (self.btnl << 17) | (self.btnr << 16)
                | (self.sw & 0xFFFF))


class Stimulus:
    """Constructor de secuencias de entrada ciclo a ciclo."""

    def __init__(self, p: Params = SIM):
        self.p = p
        self.vecs = []
        self.marks = {}
        self.sw = 0
        self.rstn = 1
        self.level = {b: 0 for b in BUTTONS}

    # -- primitivas ---------------------------------------------------------
    def _emit(self, n=1):
        v = Vec(self.rstn, self.level["BTNC"], self.level["BTNU"],
                self.level["BTND"], self.level["BTNL"], self.level["BTNR"],
                self.sw)
        self.vecs.extend([Vec(**v.__dict__) for _ in range(n)])
        return self

    def mark(self, name):
        """Marca el último ciclo emitido: la muestra de salida en ese índice es
        lo que el sistema muestra una vez aplicado todo lo anterior."""
        self.marks[name] = max(0, len(self.vecs) - 1)
        return self

    def wait(self, cycles):
        return self._emit(cycles)

    def wait_ticks(self, ticks):
        return self._emit(ticks * self.p.tick_cycles)

    def set_sw(self, value):
        self.sw = value
        return self

    def reset_hard(self, cycles=5):
        """Botón CPU_RESET (activo en bajo) mantenido ``cycles`` ciclos."""
        self.rstn = 0
        self._emit(cycles)
        self.rstn = 1
        return self._emit(self.p.debounce_cycles + 2)

    # -- botones ------------------------------------------------------------
    def _drive(self, btn, value, n):
        self.level[btn] = value
        return self._emit(n)

    def press(self, btn, hold=None, bounce=True, gap=None):
        """Pulsación con rebotes (más cortos que el antirrebote) al subir y bajar."""
        d = self.p.debounce_cycles
        hold = d + 8 if hold is None else hold
        gap = d + 8 if gap is None else gap
        if bounce:
            short = max(1, d // 4)
            for v, n in ((1, short), (0, short), (1, short + 1), (0, 1)):
                self._drive(btn, v, n)
        self._drive(btn, 1, hold)
        if bounce:
            short = max(1, d // 4)
            for v, n in ((0, short), (1, 1), (0, short), (1, short)):
                self._drive(btn, v, n)
        self._drive(btn, 0, gap)
        return self

    def glitch(self, btn, length=None):
        """Pulso espurio MÁS CORTO que el antirrebote: no debe generar evento."""
        length = max(1, self.p.debounce_cycles // 2) if length is None else length
        self._drive(btn, 1, length)
        self._drive(btn, 0, self.p.debounce_cycles + 8)
        return self

    def press_together(self, btns, hold=None, gap=None):
        """Pulsación simultánea de varios botones (sin rebotes)."""
        d = self.p.debounce_cycles
        hold = d + 8 if hold is None else hold
        gap = d + 8 if gap is None else gap
        for b in btns:
            self.level[b] = 1
        self._emit(hold)
        for b in btns:
            self.level[b] = 0
        return self._emit(gap)

    # -- operaciones de alto nivel -------------------------------------------
    def digit(self, d, mode=False):
        """Fija SW3..SW0 (y SW15 si ``mode``) y confirma con BTNC."""
        self.set_sw((d & 0xF) | (0x8000 if mode else 0))
        self._emit(4)
        return self.press("BTNC")

    def code(self, value, mode=False):
        """Ingresa un código de 4 dígitos hexadecimales (MSB primero)."""
        for shift in (12, 8, 4, 0):
            self.digit((value >> shift) & 0xF, mode=mode)
        return self

    def settle(self, cycles=4):
        return self._emit(cycles)


# --------------------------------------------------------------------------
# Trazas
# --------------------------------------------------------------------------
@dataclass
class CoreTrace:
    state: list = field(default_factory=list)
    count: list = field(default_factory=list)
    fail: list = field(default_factory=list)
    left: list = field(default_factory=list)
    code: list = field(default_factory=list)
    marks: dict = field(default_factory=dict)

    def name(self, k):
        return STATE_NAMES[self.state[k]]

    def names(self):
        return [STATE_NAMES[s] for s in self.state]

    def path(self, start=0, stop=None):
        """Secuencia de estados sin repeticiones consecutivas."""
        out = []
        for s in self.state[start:stop]:
            n = STATE_NAMES[s]
            if not out or out[-1] != n:
                out.append(n)
        return out

    def first(self, name, start=0):
        code = STATE_NAMES.index(name)
        for k in range(start, len(self.state)):
            if self.state[k] == code:
                return k
        return None

    def at(self, mark):
        """(estado, dígitos, fallos, intentos restantes, código) en una marca."""
        k = self.marks[mark]
        return (STATE_NAMES[self.state[k]], self.count[k], self.fail[k],
                self.left[k], self.code[k])

    def run_length(self, name, start=0):
        """Ciclos consecutivos en ``name`` desde su primera aparición."""
        k = self.first(name, start)
        if k is None:
            return 0
        code = STATE_NAMES.index(name)
        n = 0
        while k + n < len(self.state) and self.state[k + n] == code:
            n += 1
        return n


@dataclass
class TopTrace:
    led: list = field(default_factory=list)
    seg: list = field(default_factory=list)
    dp: list = field(default_factory=list)
    an: list = field(default_factory=list)
    rgb: list = field(default_factory=list)
    uart: list = field(default_factory=list)

    def out_words(self):
        words = []
        for k in range(len(self.led)):
            words.append((self.led[k] << 20) | (self.seg[k] << 13)
                         | (self.dp[k] << 12) | (self.an[k] << 4)
                         | (self.rgb[k] << 1) | self.uart[k])
        return words


# --------------------------------------------------------------------------
# Bancos de simulación MyHDL
# --------------------------------------------------------------------------
@block
def _clock_and_driver(clk, stim, apply_vec, sample):
    @always(delay(5))
    def clkgen():
        clk.next = not clk

    @instance
    def driver():
        for vec in stim.vecs:
            apply_vec(vec)
            yield delay(9)
            sample()
            yield delay(1)
        raise StopSimulation()

    return instances()


@block
def _core_bench(stim, p, trace):
    clk = Signal(False)
    rst = Signal(False)
    btnc = Signal(False)
    btnl = Signal(False)
    btnr = Signal(False)
    sw_digit = Signal(intbv(0)[4:])
    sw_mode = Signal(False)
    state_code = Signal(intbv(0)[3:])
    count = Signal(intbv(0, min=0, max=5))
    fail = Signal(intbv(0, min=0, max=p.max_attempts + 1))
    left = Signal(intbv(0, min=0, max=p.max_attempts + 1))
    code = Signal(intbv(p.default_code)[16:])

    dut = candado_core(clk, rst, btnc, btnl, btnr, sw_digit, sw_mode,
                       state_code, count, fail, left, code,
                       p.debounce_cycles, p.tick_cycles, p.error_ticks,
                       p.unlocked_ticks, p.alarm_ticks, p.config_ticks,
                       p.max_attempts, p.tick_max, p.default_code)

    def apply_vec(v):
        rst.next = not v.rstn
        btnc.next = v.btnc
        btnl.next = v.btnl
        btnr.next = v.btnr
        sw_digit.next = v.sw & 0xF
        sw_mode.next = bool(v.sw & 0x8000)

    def sample():
        trace.state.append(int(state_code))
        trace.count.append(int(count))
        trace.fail.append(int(fail))
        trace.left.append(int(left))
        trace.code.append(int(code))

    drv = _clock_and_driver(clk, stim, apply_vec, sample)
    return instances()


def run_core(stim: Stimulus, p: Params = SIM) -> CoreTrace:
    """Simula ``candado_core`` (FSM + datapath + antirrebote) con el estímulo."""
    trace = CoreTrace(marks=dict(stim.marks))
    _core_bench(stim, p, trace).run_sim(quiet=1)
    return trace


@block
def _top_bench(stim, p, enable_uart, trace):
    CLK100MHZ = Signal(False)
    CPU_RESETN = Signal(True)
    SW = Signal(intbv(0)[16:])
    BTNC = Signal(False)
    BTNU = Signal(False)
    BTND = Signal(False)
    BTNL = Signal(False)
    BTNR = Signal(False)
    LED = Signal(intbv(0)[16:])
    SEG = Signal(intbv(0)[7:])
    DP = Signal(False)
    AN = Signal(intbv(0)[8:])
    LED16_R = Signal(False)
    LED16_G = Signal(False)
    LED16_B = Signal(False)
    UART_RXD_OUT = Signal(True)

    dut = candado_top(CLK100MHZ, CPU_RESETN, SW, BTNC, BTNU, BTND, BTNL, BTNR,
                      LED, SEG, DP, AN, LED16_R, LED16_G, LED16_B,
                      UART_RXD_OUT, p=p, enable_uart=enable_uart)

    def apply_vec(v):
        CPU_RESETN.next = v.rstn
        SW.next = v.sw
        BTNC.next = v.btnc
        BTNU.next = v.btnu
        BTND.next = v.btnd
        BTNL.next = v.btnl
        BTNR.next = v.btnr

    def sample():
        trace.led.append(int(LED))
        trace.seg.append(int(SEG))
        trace.dp.append(int(DP))
        trace.an.append(int(AN))
        trace.rgb.append((int(LED16_R) << 2) | (int(LED16_G) << 1) | int(LED16_B))
        trace.uart.append(int(UART_RXD_OUT))

    drv = _clock_and_driver(CLK100MHZ, stim, apply_vec, sample)
    return instances()


def run_top(stim: Stimulus, p: Params = SIM, enable_uart=True) -> TopTrace:
    """Simula ``candado_top`` (todos los pines de la placa) con el estímulo."""
    trace = TopTrace()
    _top_bench(stim, p, enable_uart, trace).run_sim(quiet=1)
    return trace


# --------------------------------------------------------------------------
# Decodificadores de salidas de pines
# --------------------------------------------------------------------------
def decode_display(trace: TopTrace, start=0, stop=None):
    """Reconstruye lo que muestra el display multiplexado.

    Devuelve {posición 0..7: patrón abcdefg en lógica positiva}. Sólo cuenta
    las muestras con exactamente un ánodo activo (en bajo), como ve el ojo.
    """
    shown = {}
    for k in range(start, stop if stop is not None else len(trace.an)):
        an = trace.an[k]
        enabled = [i for i in range(8) if not (an >> i) & 1]
        if len(enabled) == 1:
            shown[enabled[0]] = trace.seg[k] ^ 0x7F
    return shown


def display_text_patterns(word_indices):
    """Patrones esperados para una lista de índices de glifo."""
    return tuple(GLYPH_ROM[i] for i in word_indices)


def decode_uart(samples, baud_cycles, start=0):
    """Decodifica una secuencia de muestras (1 por ciclo) de una línea UART 8N1."""
    out = bytearray()
    k = start
    n = len(samples)
    while k < n:
        if samples[k] == 0:  # bit de start
            mid = k + baud_cycles // 2
            if mid >= n:
                break
            if samples[mid] != 0:
                k += 1
                continue
            value = 0
            ok = True
            for bit in range(8):
                pos = k + baud_cycles * (1 + bit) + baud_cycles // 2
                if pos >= n:
                    ok = False
                    break
                value |= samples[pos] << bit
            stop = k + baud_cycles * 9 + baud_cycles // 2
            if not ok or stop >= n:
                break
            out.append(value)
            k += baud_cycles * 10
        else:
            k += 1
    return bytes(out)

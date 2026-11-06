#!/usr/bin/env python3
"""Genera las figuras del informe con matplotlib (dependencia opcional).

* ``docs/img/fig_fsm.png``      diagrama de estados de la FSM (Figura 1).
* ``docs/img/fig_bloques.png``  diagrama de bloques del sistema (Figura 2).

Uso: ``python tools/generate_figures.py``  (requiere ``pip install matplotlib``)
"""

import argparse
import math
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Rectangle  # noqa: E402
from matplotlib.path import Path  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
INK = "#1f3a5f"
FILL = "#edf2fa"
FSM_FILL = "#fbeedc"
FONT = "DejaVu Sans"


def arrow(ax, a, b, rad=0.0, label=None, lpos=None, dashed=False, size=9.5):
    """Flecha de ``a`` a ``b`` (parches o puntos) con etiqueta opcional en ``lpos``."""
    pa = a if isinstance(a, tuple) else a.center
    pb = b if isinstance(b, tuple) else b.center
    p = FancyArrowPatch(pa, pb, arrowstyle="-|>", mutation_scale=16, lw=1.3, color=INK,
                        connectionstyle=f"arc3,rad={rad}", linestyle="--" if dashed else "-",
                        patchA=None if isinstance(a, tuple) else a,
                        patchB=None if isinstance(b, tuple) else b,
                        shrinkA=0 if isinstance(a, tuple) else 2,
                        shrinkB=0 if isinstance(b, tuple) else 2)
    ax.add_patch(p)
    if label:
        ax.text(*lpos, label, ha="center", va="center", fontsize=size, family=FONT,
                color="black", bbox=dict(fc="white", ec="none", pad=1.0))
    return p


def curve(ax, a, ang_a, b, ang_b, c1, c2, label, lpos, size=9.5):
    """Flecha Bézier cúbica del borde del círculo ``a`` (ángulo ``ang_a``) al de ``b``."""
    def edge(node, ang):
        (x, y), r = node.center, node.radius + 0.05
        return (x + r * math.cos(math.radians(ang)), y + r * math.sin(math.radians(ang)))

    path = Path([edge(a, ang_a), c1, c2, edge(b, ang_b)],
                [Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4])
    ax.add_patch(FancyArrowPatch(path=path, arrowstyle="-|>", mutation_scale=16, lw=1.3,
                                 color=INK))
    ax.text(*lpos, label, ha="center", va="center", fontsize=size, family=FONT,
            bbox=dict(fc="white", ec="none", pad=1.0))


# ---------------------------------------------------------------------------
# Figura 1: diagrama de estados
# ---------------------------------------------------------------------------
class Node(Circle):
    @property
    def center(self):
        return Circle.get_center(self)


def fsm_figure(path):
    fig = plt.figure(figsize=(12.25, 5.675), dpi=200)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 24.5)
    ax.set_ylim(0, 11.35)
    ax.set_aspect("equal")
    ax.axis("off")

    pos = {
        "LOCKED": (2.4, 5.6), "INPUT": (8.0, 4.4), "VALIDATE": (12.8, 5.6),
        "UNLOCKED": (17.6, 8.4), "CONFIG": (22.4, 8.4), "ERROR": (17.6, 2.8),
        "ALARM": (22.4, 2.8),
    }
    disp = {
        "LOCKED": "LOCKEd 5", "INPUT": "CodE--__", "VALIDATE": "1 ciclo",
        "UNLOCKED": "UnLOCKEd", "CONFIG": "SEt 9C__", "ERROR": "Error  4",
        "ALARM": "ALArnn",
    }
    r = 1.15
    n = {}
    for name, (x, y) in pos.items():
        c = Node((x, y), r, fc=FSM_FILL if name == "ALARM" else FILL, ec=INK, lw=1.4)
        ax.add_patch(c)
        n[name] = c
        ax.text(x, y + 0.22, name, ha="center", va="center", fontsize=11.5,
                family=FONT, weight="bold")
        ax.text(x, y - 0.38, disp[name], ha="center", va="center", fontsize=8.5,
                family="DejaVu Sans Mono", color="#555555")
    # estado inicial
    arrow(ax, (0.2, 8.2), n["LOCKED"], rad=0.0)
    ax.text(0.25, 8.55, "encendido /\nCPU RESET", ha="left", va="bottom", fontsize=9, family=FONT)

    arrow(ax, n["LOCKED"], n["INPUT"], rad=-0.15, label="BTNC\n(1.er dígito)", lpos=(5.4, 6.0))
    arrow(ax, n["INPUT"], n["LOCKED"], rad=-0.25, label="BTNL sobre el\núnico dígito / BTNR",
          lpos=(6.0, 3.0))
    # bucle en INPUT
    x, y = pos["INPUT"]
    arrow(ax, (x - 0.5, y + 1.05), (x + 0.5, y + 1.05), rad=-1.6)
    ax.text(x, y + 2.55, "BTNC: añade dígito\nBTNL: borra", ha="center", va="center",
            fontsize=9.5, family=FONT)
    arrow(ax, n["INPUT"], n["VALIDATE"], rad=0.0, label="4.º dígito", lpos=(10.4, 5.4))
    arrow(ax, n["VALIDATE"], n["UNLOCKED"], rad=-0.1, label="correcto", lpos=(14.6, 7.6))
    arrow(ax, n["VALIDATE"], n["ERROR"], rad=0.1, label="incorrecto", lpos=(14.6, 3.6))
    arrow(ax, n["UNLOCKED"], n["CONFIG"], rad=-0.3, label="BTNU", lpos=(20.0, 9.55))
    arrow(ax, n["CONFIG"], n["UNLOCKED"], rad=-0.3, label="4.º dígito:\nguarda el código",
          lpos=(20.0, 6.95))
    arrow(ax, n["ERROR"], n["ALARM"], rad=0.0, label="1 s,\nfallos = 5", lpos=(20.0, 3.55))
    # retornos largos a LOCKED
    curve(ax, n["UNLOCKED"], 165, n["LOCKED"], 60, (13.0, 9.6), (5.0, 9.3),
          "10 s / BTND / BTNR", (10.0, 9.3))
    curve(ax, n["CONFIG"], 95, n["LOCKED"], 95, (21.5, 11.6), (2.4, 11.6),
          "30 s / BTNR (no guarda)", (12.0, 11.0))
    curve(ax, n["ERROR"], 195, n["LOCKED"], 285, (12.0, 1.0), (4.0, 1.0),
          "1 s, fallos < 5 / BTNR", (10.2, 1.45))
    curve(ax, n["ALARM"], 270, n["LOCKED"], 245, (21.0, -0.4), (1.4, -0.4),
          "30 s (ignora todos los botones; sirena y parpadeo)", (12.4, 0.35))

    fig.savefig(path, dpi=200, facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figura 2: diagrama de bloques
# ---------------------------------------------------------------------------
class Box(FancyBboxPatch):
    def __init__(self, ax, x, y, w, h, text, fill=FILL, size=10.5):
        super().__init__((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.02,rounding_size=0.35",
                         fc=fill, ec=INK, lw=1.3)
        ax.add_patch(self)
        ax.text(x, y, text, ha="center", va="center", fontsize=size, family=FONT)
        self.cx, self.cy, self.w, self.h = x, y, w, h

    @property
    def center(self):
        return (self.cx, self.cy)

    def side(self, where, off=0.0):
        x, y, w, h = self.cx, self.cy, self.w / 2 + 0.06, self.h / 2 + 0.06
        return {"l": (x - w, y + off), "r": (x + w, y + off),
                "t": (x + off, y + h), "b": (x + off, y - h)}[where]


def cluster(ax, x0, y0, x1, y1, title):
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="none", ec="#999999", lw=1.2))
    ax.text((x0 + x1) / 2, y1 - 0.45, title, ha="center", va="center", fontsize=13, family=FONT)


def blocks_figure(path):
    fig = plt.figure(figsize=(12.485, 6.015), dpi=200)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 25.0)
    ax.set_ylim(0, 12.04)
    ax.set_aspect("equal")
    ax.axis("off")

    cluster(ax, 0.3, 5.2, 3.9, 11.6, "Entrada")
    sw = Box(ax, 2.1, 9.9, 3.0, 1.0, "SW3..SW0")
    bt = Box(ax, 2.1, 8.1, 3.2, 1.3, "BTNC, BTNL, BTNR,\nBTNU, BTND")
    rs = Box(ax, 2.1, 6.3, 2.6, 1.0, "CPU_RESETN")

    s2 = Box(ax, 6.0, 9.9, 2.6, 1.0, "Sincronizador\n2 FF")
    db = Box(ax, 6.0, 8.1, 2.6, 1.3, "Antirrebote\n(15 ms) + flanco")
    sr = Box(ax, 6.0, 6.3, 2.6, 1.0, "Sincronizador\nde reset")
    arrow(ax, sw.side("r"), s2.side("l"))
    arrow(ax, bt.side("r"), db.side("l"))
    arrow(ax, rs.side("r"), sr.side("l"))

    cluster(ax, 8.3, 5.2, 24.7, 11.6, "Núcleo (candado_core)")
    fsm = Box(ax, 10.8, 7.6, 2.9, 1.5, "FSM de Moore\n(7 estados)", fill=FSM_FILL, size=11)
    buf = Box(ax, 15.4, 9.9, 2.6, 1.1, "Registro de\n4 dígitos")
    tim = Box(ax, 15.4, 6.95, 2.8, 1.1, "Base de tiempo\n(tick 100 ms)")
    reg = Box(ax, 19.6, 8.1, 2.6, 1.1, "Registro del\ncódigo")
    cmp_ = Box(ax, 23.0, 9.9, 2.4, 1.0, "Comparador")

    arrow(ax, s2.side("r"), buf.side("l", 0.2), label="dígito", lpos=(10.8, 10.35), size=9)
    arrow(ax, db.side("r"), fsm.side("l", 0.3), label="pulsos", lpos=(8.15, 8.25), size=9)
    arrow(ax, sr.side("r"), fsm.side("l", -0.45), label="reset", lpos=(8.15, 6.55), size=9)
    arrow(ax, fsm.side("t", 0.3), buf.side("l", -0.25), rad=-0.2, label="push/del/clear",
          lpos=(12.3, 9.55), size=9)
    arrow(ax, fsm.side("r", -0.25), tim.side("l", 0.4), label="clear", lpos=(13.15, 7.6), size=9)
    arrow(ax, tim.side("l", 0.05), fsm.side("r", -0.6), label="tick", lpos=(13.15, 6.72), size=9)
    arrow(ax, fsm.side("r", 0.45), reg.side("l", -0.05), dashed=True, label="we",
          lpos=(17.3, 8.3), size=9)
    arrow(ax, buf.side("b", 0.6), reg.side("l", 0.3), rad=0.2, dashed=True,
          label="código nuevo", lpos=(17.35, 9.0), size=9)
    arrow(ax, buf.side("r"), cmp_.side("l"), label="secuencia", lpos=(19.6, 10.15), size=9)
    arrow(ax, reg.side("r"), cmp_.side("b", -0.4), rad=0.25)
    # match: Comparador -> FSM por debajo de la base de tiempo
    ax.plot([23.0, 23.0, 11.6], [9.34, 5.6, 5.6], color=INK, lw=1.3)
    arrow(ax, (11.6, 5.6), fsm.side("b", 0.8))
    ax.text(18.0, 5.6, "match", ha="center", va="center", fontsize=9, family=FONT,
            bbox=dict(fc="white", ec="none", pad=1.0))

    cluster(ax, 8.3, 0.25, 24.7, 4.2, "Salida")
    leds = Box(ax, 10.3, 1.75, 3.0, 1.3, "LEDs + RGB\n(intentos, estado)")
    dsp = Box(ax, 14.3, 1.75, 3.0, 1.3, "Display 7 seg\n(texto de 8 car.)")
    alm = Box(ax, 18.75, 1.75, 3.9, 1.3, "Alarma: sirena (AUD_PWM,\nJA1) y parpadeo", size=10)
    uart = Box(ax, 22.85, 1.75, 2.9, 1.3, "Registro UART\n115200 8N1")
    # bus de salida: FSM -> indicadores
    bus_y = 4.75
    ax.plot([10.0, 10.0], [fsm.side("b")[1], bus_y], color=INK, lw=1.3)
    ax.plot([10.0, 22.85], [bus_y, bus_y], color=INK, lw=1.3)
    for b in (leds, dsp, alm, uart):
        if b.cx > 10.0:
            ax.plot([b.cx, b.cx], [bus_y, 3.0], color=INK, lw=1.3)
        arrow(ax, (b.cx, 3.0 if b.cx > 10.0 else bus_y), b.side("t"))
    ax.text(16.5, 5.0, "state_code, intentos restantes, dígitos", ha="center", va="center",
            fontsize=9, family=FONT, bbox=dict(fc="white", ec="none", pad=1.0))
    fig.savefig(path, dpi=200, facecolor="white")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--outdir", default=os.path.join(ROOT, "docs", "img"))
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)
    fsm_figure(os.path.join(args.outdir, "fig_fsm.png"))
    blocks_figure(os.path.join(args.outdir, "fig_bloques.png"))
    print(f"Figuras escritas en {args.outdir}")


if __name__ == "__main__":
    main()

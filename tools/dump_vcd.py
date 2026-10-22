#!/usr/bin/env python3
"""Escribe un VCD de la simulación Python (MyHDL) de un escenario.

El VCD se abre con GTKWave o en https://vc.drom.io/ (como pide el taller).

Uso: ``python tools/dump_vcd.py [escenario] [--top]``
  escenario  nombre de ``candado.scenarios.SCENARIOS`` (por omisión tc04_...)
  --top      simula candado_top completo (pines de la placa) en vez del núcleo
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from candado.params import SIM  # noqa: E402
from candado.scenarios import SCENARIOS  # noqa: E402
from candado.testing import (CoreTrace, TopTrace, _core_bench, _top_bench)  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("escenario", nargs="?", default="tc04_tres_incorrectas_consecutivas",
                    choices=sorted(SCENARIOS))
    ap.add_argument("--top", action="store_true")
    ap.add_argument("--dir", default="build")
    args = ap.parse_args()

    os.makedirs(args.dir, exist_ok=True)
    stim = SCENARIOS[args.escenario](SIM)
    if args.top:
        bench = _top_bench(stim, SIM, True, TopTrace())
        name = f"{args.escenario}_top"
    else:
        bench = _core_bench(stim, SIM, CoreTrace())
        name = f"{args.escenario}_core"
    bench.config_sim(trace=True, directory=args.dir, filename=name)
    bench.run_sim(quiet=1)
    print(f"{os.path.join(args.dir, name)}.vcd  ({len(stim.vecs)} ciclos de 10 ns)")


if __name__ == "__main__":
    main()

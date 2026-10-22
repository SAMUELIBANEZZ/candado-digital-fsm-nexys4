#!/usr/bin/env python3
"""Genera ``sim/tb_vectors_pkg.vhd`` a partir de la simulación en Python.

1. Concatena todos los escenarios (``candado.scenarios``) y el escenario
   pseudoaleatorio (``candado.randomized``), cada uno precedido de un reset duro.
2. Simula ``candado_top`` (parámetros SIM) con MyHDL y registra, ciclo a ciclo,
   las entradas aplicadas y las salidas de los pines.
3. Escribe ambos como un paquete VHDL (sólo cambios, para que sea compacto) que
   consume el testbench ``sim/tb_candado_top.vhd`` para comparar el VHDL
   convertido contra el modelo Python ciclo a ciclo.

Uso: ``python tools/generate_vectors.py [--out sim/tb_vectors_pkg.vhd]``
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from candado.params import SIM  # noqa: E402
from candado.randomized import random_stimulus  # noqa: E402
from candado.scenarios import SCENARIOS  # noqa: E402
from candado.testing import IN_WIDTH, OUT_WIDTH, Stimulus, run_top  # noqa: E402

NAME_LEN = 40
RANDOM_SEEDS = (1, 2, 3)


def build_suite():
    """Lista [(nombre, Stimulus)] con todo lo que se cruza contra el VHDL."""
    suite = [(name, build(SIM)) for name, build in SCENARIOS.items()]
    for seed in RANDOM_SEEDS:
        stim, _ = random_stimulus(SIM, seed=seed, events=60)
        suite.append((f"aleatorio_semilla_{seed}", stim))
    return suite


def concat(suite):
    big = Stimulus(SIM)
    starts = []
    for name, st in suite:
        starts.append((len(big.vecs), name))
        big.vecs.extend(st.vecs)
    return big, starts


def rle(words):
    """[(ciclo, valor)] sólo cuando el valor cambia."""
    out, last = [], None
    for k, w in enumerate(words):
        if w != last:
            out.append((k, w))
            last = w
    return out


def bits(value, width):
    return format(value, f"0{width}b")


def write_package(path, n_cycles, in_events, out_events, starts):
    lines = []
    w = lines.append
    w("-- Generado por tools/generate_vectors.py a partir del modelo Python (MyHDL).")
    w("-- NO EDITAR A MANO: regenerar con `make vectors`.")
    w("library ieee;")
    w("use ieee.std_logic_1164.all;")
    w("")
    w("package tb_vectors_pkg is")
    w(f"  constant N_CYCLES : natural := {n_cycles};")
    w(f"  constant N_IN     : natural := {len(in_events)};")
    w(f"  constant N_OUT    : natural := {len(out_events)};")
    w(f"  constant N_SCEN   : natural := {len(starts)};")
    w(f"  constant NAME_LEN : natural := {NAME_LEN};")
    w(f"  subtype in_word_t  is std_logic_vector({IN_WIDTH - 1} downto 0);")
    w(f"  subtype out_word_t is std_logic_vector({OUT_WIDTH - 1} downto 0);")
    w("  type in_event_t  is record cyc : natural; val : in_word_t;  end record;")
    w("  type out_event_t is record cyc : natural; val : out_word_t; end record;")
    w("  type scen_t      is record cyc : natural; name : string(1 to NAME_LEN); end record;")
    w("  type in_event_array_t  is array (natural range <>) of in_event_t;")
    w("  type out_event_array_t is array (natural range <>) of out_event_t;")
    w("  type scen_array_t      is array (natural range <>) of scen_t;")
    w("")
    w("  constant SCENARIOS : scen_array_t(0 to N_SCEN - 1) := (")
    body = [f'    ({c}, "{n.ljust(NAME_LEN)[:NAME_LEN]}")' for c, n in starts]
    w(",\n".join(body))
    w("  );")
    w("")
    w("  constant IN_EVENTS : in_event_array_t(0 to N_IN - 1) := (")
    body = [f'    ({c}, "{bits(v, IN_WIDTH)}")' for c, v in in_events]
    w(",\n".join(body))
    w("  );")
    w("")
    w("  constant OUT_EVENTS : out_event_array_t(0 to N_OUT - 1) := (")
    body = [f'    ({c}, "{bits(v, OUT_WIDTH)}")' for c, v in out_events]
    w(",\n".join(body))
    w("  );")
    w("end package tb_vectors_pkg;")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="sim/tb_vectors_pkg.vhd")
    args = ap.parse_args()

    suite = build_suite()
    big, starts = concat(suite)
    trace = run_top(big, SIM)
    in_words = [v.word() for v in big.vecs]
    out_words = trace.out_words()
    assert len(in_words) == len(out_words)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    write_package(args.out, len(in_words), rle(in_words), rle(out_words), starts)
    print(f"{args.out}: {len(in_words)} ciclos, {len(suite)} escenarios, "
          f"{len(rle(in_words))} cambios de entrada, {len(rle(out_words))} cambios de salida")


if __name__ == "__main__":
    main()

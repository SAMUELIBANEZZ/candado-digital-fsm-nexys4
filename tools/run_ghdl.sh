#!/usr/bin/env bash
# Simula con GHDL el VHDL convertido (candado_top_sim) contra los vectores del
# modelo Python. Sale con código 0 sólo si TODAS las salidas coinciden.
#
# Uso: tools/run_ghdl.sh [archivo.vcd]
#   Con un argumento escribe además las formas de onda (VCD) para abrirlas en
#   GTKWave o en https://vc.drom.io/
set -euo pipefail
cd "$(dirname "$0")/.."

STD=08
WORK=build/ghdl
mkdir -p "$WORK"

ghdl -a --std=$STD --workdir="$WORK" \
  hdl/pck_myhdl_011.vhd \
  hdl/candado_top_sim.vhd \
  sim/tb_vectors_pkg.vhd \
  sim/tb_candado_top.vhd
ghdl -e --std=$STD --workdir="$WORK" tb_candado_top

# --assert-level=warning: cualquier aviso de numeric_std (p. ej. "vector truncated")
# detiene la simulación con error, para no pasar por alto truncamientos.
if [ $# -ge 1 ]; then
  ghdl -r --std=$STD --workdir="$WORK" tb_candado_top --assert-level=warning --vcd="$1"
else
  ghdl -r --std=$STD --workdir="$WORK" tb_candado_top --assert-level=warning
fi

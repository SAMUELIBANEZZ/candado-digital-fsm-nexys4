# Candado digital FSM - Nexys4 DDR / Nexys A7-100T
#
#   make all        regenera todo y ejecuta todas las verificaciones
#   make test       pruebas Python (pytest + MyHDL)
#   make hdl        convierte Python -> VHDL (hdl/)
#   make xdc        regenera el archivo de pines (constraints/)
#   make vectors    simula en Python y genera los vectores del testbench VHDL
#   make ghdl       simula el VHDL convertido con GHDL y lo compara con Python
#   make vcd        como ghdl, pero escribe build/candado.vcd (GTKWave / vc.drom.io)
#   make pyvcd      VCD de la simulación Python de un escenario (SCEN=tc04_...)
#   make mutation   prueba de mutación (rompe el diseño y comprueba que las pruebas fallan)
#   make clean

PY ?= python3
SCEN ?= tc04_tres_incorrectas_consecutivas

.PHONY: all test hdl xdc vectors ghdl vcd pyvcd mutation clean

all: hdl xdc vectors test ghdl

test:
	$(PY) -m pytest tests -q

hdl:
	$(PY) tools/generate_hdl.py

xdc:
	$(PY) tools/generate_xdc.py

vectors: hdl
	$(PY) tools/generate_vectors.py

ghdl: hdl vectors
	bash tools/run_ghdl.sh

vcd: hdl vectors
	mkdir -p build
	bash tools/run_ghdl.sh build/candado.vcd

pyvcd:
	$(PY) tools/dump_vcd.py $(SCEN)

mutation:
	$(PY) tools/mutation_check.py

clean:
	rm -rf build vivado/proj vivado/reports .pytest_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +

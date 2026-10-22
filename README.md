# Candado digital de control de acceso (FSM de Moore) — Nexys4 DDR / Artix-7

Proyecto final de **Electrónica Digital 2026-2** — Universidad San Buenaventura, Bogotá.
Integrantes: Samuel Ibañez, Manuel Betancurt, David A. Cañón M.

Candado de 4 dígitos descrito como máquina de estados de Moore. Flujo de trabajo del curso:

```
Python (MyHDL)  ──►  pruebas + modelo de referencia  ──►  VHDL  ──►  GHDL / Vivado (simulación)  ──►  bitstream  ──►  Nexys4 DDR
```

El diseño sólo usa recursos de la placa: switches, pulsadores, LEDs, display de 7 segmentos,
LED RGB y el puente USB-UART (registro de eventos, opcional).

## Uso en la placa (resumen)

| Entrada | Función |
|---|---|
| `SW3..SW0` | dígito hexadecimal a ingresar (0..F) |
| `BTNC` | confirma el dígito seleccionado |
| `BTNL` | borra el último dígito |
| `BTNR` | reset de usuario: vuelve a IDLE (conserva el código) |
| `CPU RESET` (botón rojo) | reset duro: vuelve a IDLE y restaura el código de fábrica |
| `SW15` | con `SW15=1` y `BTNC` estando en UNLOCKED se entra a CONFIG (código nuevo) |

Código de fábrica: **1234** (hex). Tres intentos fallidos consecutivos → ALARM (30 s, sólo sale por `BTNR` o por tiempo).
Display: palabra del estado en AN7..AN4 (`IdLE`, `InPt`, `OPEn`, `Err_`, `ALAr`, `COnF`), intentos restantes en AN0.
LEDs: LD3..LD0 = dígitos ingresados; LD12 CONFIG, LD13 UNLOCKED, LD14 ERROR, LD15 ALARM; LED RGB con un color por estado.
UART (115200 8N1, sólo TX por el USB): una línea `UNLOCKED 0` por cada cambio de estado.

Guía completa y tablas de pines: `docs/Informe_Candado_Digital_APA7.docx`.

## Requisitos

* Python ≥ 3.10, `pip install -r requirements.txt` (MyHDL 0.11.52, pytest)
* GHDL ≥ 4 (opcional pero recomendado, para comprobar el VHDL sin Vivado)
* Vivado (WebPACK sirve) para sintetizar y programar la Nexys4 DDR

## Comandos

```bash
pip install -r requirements.txt
make all        # regenera VHDL/XDC/vectores, corre pytest y la simulación GHDL
make test       # sólo pruebas Python
make mutation   # prueba de mutación (el probador debe detectar 15/15 fallos inyectados)
make vcd        # build/candado.vcd para GTKWave o https://vc.drom.io
make pyvcd SCEN=tc10_unlocked_vence   # VCD de la simulación Python de un escenario
```

## Poner el diseño en la placa

```bash
vivado -mode batch -source vivado/build_bitstream.tcl   # síntesis + implementación + build/candado_top.bit
vivado -mode batch -source vivado/program_board.tcl     # programa la FPGA (placa por USB)
```

Los scripts Tcl **no se ejecutaron** en el entorno donde se desarrolló el repositorio (no había Vivado).
Si algo falla, el procedimiento manual equivalente está en el informe (sección de implementación):
crear proyecto `xc7a100tcsg324-1`, añadir `hdl/pck_myhdl_011.vhd` + `hdl/candado_top.vhd` y
`constraints/candado_nexys4ddr.xdc`, *top* = `candado_top`, generar bitstream y programar.

## Estructura

```
src/candado/      diseño en Python/MyHDL (fsm, datapath, inputs, display, status, uart, top) + modelo de referencia
tests/            pytest: Tabla III del anteproyecto, casos extra, módulos, pines, aleatorio vs modelo, XDC/HDL
tools/            conversión a VHDL, vectores, GHDL, mutación, XDC, VCD
hdl/              VHDL generado (candado_top.vhd = hardware, candado_top_sim.vhd = tiempos reducidos) y por módulo
sim/              testbench VHDL autoverificable + vectores generados desde Python
constraints/      candado_nexys4ddr.xdc (asignación de pines)
vivado/           scripts Tcl
docs/             informe APA 7
```

**No edite `hdl/` a mano:** se regenera con `make hdl`; el CI falla si el VHDL versionado no coincide con el Python.

## Cómo se verifica

1. Pruebas dirigidas: los 10 casos de la Tabla III del anteproyecto + 9 casos extra.
2. Modelo de referencia independiente (nivel de evento) contra el RTL con estímulo aleatorio y rebotes.
3. El VHDL convertido se simula en GHDL con un testbench autoverificable que compara las 36 salidas
   **en cada ciclo** (40 175 ciclos, 22 escenarios) contra la simulación Python.
4. Prueba de mutación: 15 fallos inyectados, los 15 detectados.
5. El XDC se contrasta con el XDC maestro oficial de Digilent.

## Limitaciones

Maqueta de control lógico, no dispositivo de seguridad: el código no está cifrado, se pierde al reprogramar
y el dígito en curso es visible en los switches. El registro UART es una extensión (el anteproyecto
excluía la comunicación con computador). Para una Nexys4 original (no DDR) los pines son otros.

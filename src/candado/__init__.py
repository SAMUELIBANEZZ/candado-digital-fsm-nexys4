"""Candado digital de control de acceso (FSM) para Nexys4 DDR / Nexys A7-100T.

Diseño en Python (MyHDL) -> simulación en Python -> conversión a VHDL ->
simulación del VHDL -> bitstream con Vivado.
"""

from .params import HW, SIM, Params

__all__ = ["HW", "SIM", "Params"]

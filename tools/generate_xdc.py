#!/usr/bin/env python3
"""Genera ``constraints/candado_nexys4ddr.xdc`` (asignación de pines).

Los pines salen de ``tools/pins_nexys_a7_100t.json``, extraído del XDC maestro
oficial de Digilent (Nexys-A7-100T-Master.xdc, que también vale para la
Nexys4 DDR). Aquí sólo se eligen los que usa ``candado_top`` y se renombran
los puertos del bus de segmentos (CA..CG -> SEG[6:0]).

Uso: ``python tools/generate_xdc.py``
"""

import argparse
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# (puerto del diseño, puerto en el XDC maestro, función en el candado)
def port_table():
    rows = []
    add = rows.append
    add(("CLK100MHZ", "CLK100MHZ", "Reloj de 100 MHz (sincronización, antirrebote y temporizadores)"))
    add(("CPU_RESETN", "CPU_RESETN", "Botón rojo CPU RESET (activo en bajo): reset duro, restaura el código de fábrica"))
    for i in range(4):
        add((f"SW[{i}]", f"SW[{i}]", f"SW{i}: bit {i} del dígito a ingresar (SW3..SW0)"))
    for i in range(4, 15):
        add((f"SW[{i}]", f"SW[{i}]", f"SW{i}: sin función (reservado)"))
    add(("SW[15]", "SW[15]", "SW15: selector de modo; en UNLOCKED permite configurar un código nuevo"))
    add(("BTNC", "BTNC", "BTNC: confirma el dígito seleccionado en SW3..SW0"))
    add(("BTNU", "BTNU", "BTNU: sin función (reservado)"))
    add(("BTND", "BTND", "BTND: sin función (reservado)"))
    add(("BTNL", "BTNL", "BTNL: borra el último dígito ingresado"))
    add(("BTNR", "BTNR", "BTNR: reset de usuario, vuelve a IDLE (conserva el código)"))
    for i in range(16):
        if i < 4:
            fn = f"LD{i}: dígitos ingresados (código termómetro)"
        elif i == 12:
            fn = "LD12: modo configuración (CONFIG)"
        elif i == 13:
            fn = "LD13: acceso concedido (UNLOCKED)"
        elif i == 14:
            fn = "LD14: intento fallido (ERROR)"
        elif i == 15:
            fn = "LD15: alarma activa (ALARM)"
        else:
            fn = f"LD{i}: sin función (apagado)"
        add((f"LED[{i}]", f"LED[{i}]", fn))
    add(("LED16_R", "LED16_R", "LED RGB LD16, canal rojo (color según estado)"))
    add(("LED16_G", "LED16_G", "LED RGB LD16, canal verde"))
    add(("LED16_B", "LED16_B", "LED RGB LD16, canal azul"))
    for i, seg in enumerate("ABCDEFG"):
        bit = 6 - i
        add((f"SEG[{bit}]", f"C{seg}", f"Segmento {seg.lower()} (cátodo C{seg}, activo en bajo) = SEG[{bit}]"))
    add(("DP", "DP", "Punto decimal (activo en bajo; siempre apagado)"))
    for i in range(8):
        fn = {7: "estado: 1.er carácter", 6: "estado: 2.º", 5: "estado: 3.º",
              4: "estado: 4.º", 0: "intentos restantes"}.get(i, "apagado")
        add((f"AN[{i}]", f"AN[{i}]", f"Ánodo del dígito {i} (activo en bajo): {fn}"))
    add(("UART_RXD_OUT", "UART_RXD_OUT", "UART: transmisión al PC por el USB de la placa (registro de eventos, 115200 8N1)"))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=os.path.join(ROOT, "constraints", "candado_nexys4ddr.xdc"))
    args = ap.parse_args()
    with open(os.path.join(ROOT, "tools", "pins_nexys_a7_100t.json"), encoding="utf-8") as f:
        master = json.load(f)["pines"]

    out = []
    w = out.append
    w("## Candado digital (FSM) - asignación de pines para Nexys4 DDR / Nexys A7-100T")
    w("## FPGA: Xilinx Artix-7 XC7A100T-1CSG324C")
    w("##")
    w("## Archivo generado por tools/generate_xdc.py a partir del XDC maestro oficial de")
    w("## Digilent (https://github.com/Digilent/digilent-xdc, Nexys-A7-100T-Master.xdc).")
    w("## Los nombres de puerto coinciden con la entidad candado_top (hdl/candado_top.vhd).")
    w("## Para una Nexys4 ORIGINAL (no DDR) los pines de botones, display y reloj de memoria")
    w("## son otros: usar el XDC maestro de esa placa.")
    w("")
    sections = [
        ("Reloj y reset", lambda n: n in ("CLK100MHZ", "CPU_RESETN")),
        ("Switches", lambda n: n.startswith("SW[")),
        ("Pulsadores", lambda n: n.startswith("BTN")),
        ("LEDs LD15..LD0", lambda n: n.startswith("LED[")),
        ("LED RGB LD16", lambda n: n.startswith("LED16_")),
        ("Display de 7 segmentos (cátodos CA..CG -> SEG[6:0], 'abcdefg')",
         lambda n: n.startswith("SEG[") or n == "DP"),
        ("Display de 7 segmentos (ánodos)", lambda n: n.startswith("AN[")),
        ("UART (puente USB-UART de la placa)", lambda n: n == "UART_RXD_OUT"),
    ]
    table = port_table()
    used = set()
    for title, pick in sections:
        w(f"## {title}")
        for port, master_name, fn in table:
            if not pick(port):
                continue
            pin = master[master_name]
            used.add(port)
            w(f"set_property -dict {{ PACKAGE_PIN {pin['pin']:<4} IOSTANDARD {pin['iostandard']} }} "
              f"[get_ports {{ {port} }}]; # {fn}")
            if port == "CLK100MHZ":
                w("create_clock -add -name sys_clk_pin -period 10.00 -waveform {0 5} [get_ports { CLK100MHZ }];")
        w("")
    assert used == {p for p, _, _ in table}

    w("## Opciones de configuración (bancos a 3,3 V)")
    w("set_property CFGBVS VCCO [current_design]")
    w("set_property CONFIG_VOLTAGE 3.3 [current_design]")

    path = args.out
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")
    print(f"{path}: {len(table)} puertos asignados")


if __name__ == "__main__":
    main()

"""El XDC cubre cada puerto del VHDL; el VHDL versionado es reproducible."""

import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def vhdl_ports(path):
    """{nombre: (dirección, ancho)} de la entidad candado_top."""
    text = open(path, encoding="utf-8").read()
    block = re.search(r"entity candado_top is\s+port \((.*?)\);\s*end entity", text, re.S).group(1)
    ports = {}
    for m in re.finditer(r"(\w+):\s*(in|out)\s+std_logic(?:_vector\((\d+) downto (\d+)\))?", block):
        name, direction, hi, lo = m.groups()
        ports[name] = (direction, 1 if hi is None else int(hi) - int(lo) + 1)
    return ports


def xdc_constraints(path):
    pat = re.compile(r"set_property -dict \{ PACKAGE_PIN (\w+)\s+IOSTANDARD (\w+) \} \[get_ports \{ ([^}\s]+) \}\]")
    return {m.group(3): (m.group(1), m.group(2))
            for m in pat.finditer(open(path, encoding="utf-8").read())}


def test_cada_puerto_del_top_tiene_un_pin_en_el_xdc():
    ports = vhdl_ports(os.path.join(ROOT, "hdl", "candado_top.vhd"))
    cons = xdc_constraints(os.path.join(ROOT, "constraints", "candado_nexys4ddr.xdc"))
    esperados = set()
    for name, (_, width) in ports.items():
        esperados |= {name} if width == 1 else {f"{name}[{i}]" for i in range(width)}
    assert esperados == set(cons), (
        f"sin pin: {sorted(esperados - set(cons))}; sobran: {sorted(set(cons) - esperados)}")


def test_pines_unicos_y_estandar_de_e_s():
    cons = xdc_constraints(os.path.join(ROOT, "constraints", "candado_nexys4ddr.xdc"))
    pines = [pin for pin, _ in cons.values()]
    assert len(pines) == len(set(pines)), "hay dos puertos en el mismo pin"
    # El XDC oficial pone SW[8] y SW[9] en el banco de 1,8 V (LVCMOS18); el resto a 3,3 V.
    en_18 = {port for port, (_, io) in cons.items() if io == "LVCMOS18"}
    assert en_18 <= {"SW[8]", "SW[9]"}
    assert {io for _, io in cons.values()} <= {"LVCMOS33", "LVCMOS18"}


def test_pines_clave_coinciden_con_el_xdc_oficial_de_digilent():
    oficial = json.load(open(os.path.join(ROOT, "tools", "pins_nexys_a7_100t.json"),
                             encoding="utf-8"))["pines"]
    cons = xdc_constraints(os.path.join(ROOT, "constraints", "candado_nexys4ddr.xdc"))
    equivalentes = {f"SEG[{6 - i}]": f"C{c}" for i, c in enumerate("ABCDEFG")}
    for port, (pin, _) in cons.items():
        ref = oficial[equivalentes.get(port, port)]["pin"]
        assert pin == ref, f"{port}: {pin} != {ref} (oficial)"
    # valores conocidos de la documentación de la placa
    assert cons["CLK100MHZ"][0] == "E3" and cons["CPU_RESETN"][0] == "C12"
    assert cons["BTNC"][0] == "N17" and cons["SW[15]"][0] == "V10"
    assert cons["UART_RXD_OUT"][0] == "D4"


def test_el_xdc_define_el_reloj_de_100_mhz():
    text = open(os.path.join(ROOT, "constraints", "candado_nexys4ddr.xdc"), encoding="utf-8").read()
    assert "create_clock -add -name sys_clk_pin -period 10.00" in text


def test_el_xdc_versionado_esta_al_dia():
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "x.xdc")
        subprocess.run([sys.executable, "-I", os.path.join(ROOT, "tools", "generate_xdc.py"),
                        "--out", out], cwd=ROOT, check=True, capture_output=True)
        assert open(out, encoding="utf-8").read() == open(
            os.path.join(ROOT, "constraints", "candado_nexys4ddr.xdc"), encoding="utf-8").read()


def test_el_vhdl_versionado_coincide_con_lo_que_genera_el_codigo_python():
    """Si cambia el código Python y no se regeneró el VHDL, esta prueba falla."""
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([sys.executable, "-I", os.path.join(ROOT, "tools", "generate_hdl.py"),
                        "--outdir", tmp], cwd=ROOT, check=True, capture_output=True)
        for rel in ("candado_top.vhd", "candado_top_sim.vhd", "pck_myhdl_011.vhd"):
            a, b = os.path.join(ROOT, "hdl", rel), os.path.join(tmp, rel)
            # El encabezado incluye la ruta de salida; se compara el cuerpo.
            ta = open(a, encoding="utf-8").read().split("\n", 1)[1]
            tb = open(b, encoding="utf-8").read().split("\n", 1)[1]
            assert ta == tb, f"hdl/{rel} no está al día: ejecutar `make hdl`"
        for fn in sorted(os.listdir(os.path.join(ROOT, "hdl", "modules"))):
            ta = open(os.path.join(ROOT, "hdl", "modules", fn), encoding="utf-8").read().split("\n", 1)[1]
            tb = open(os.path.join(tmp, "modules", fn), encoding="utf-8").read().split("\n", 1)[1]
            assert ta == tb, f"hdl/modules/{fn} no está al día: ejecutar `make hdl`"

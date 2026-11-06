#!/usr/bin/env python3
"""Prueba de mutación: ¿la batería de pruebas detecta errores introducidos a propósito?

Para cada mutación copia ``src/`` y ``tests/`` a un directorio temporal, aplica
un cambio al diseño y ejecuta pytest. Una mutación está *detectada* ("killed")
si alguna prueba falla; si todas pasan ("survived") faltan pruebas.

Uso: ``python tools/mutation_check.py``  (tarda ~1-2 minutos)
"""

import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

MUTATIONS = [
    ("alarma nunca se activa (>= -> >)", "src/candado/fsm.py",
     "if fail_r >= MAX_ATTEMPTS:", "if fail_r > MAX_ATTEMPTS:"),
    ("ERROR vuelve siempre a LOCKED", "src/candado/fsm.py",
     "                if fail_r >= MAX_ATTEMPTS:\n                    next_state.next = t_state.ALARM\n                else:\n                    next_state.next = t_state.LOCKED",
     "                next_state.next = t_state.LOCKED"),
    ("antirrebote sin reinicio de cuenta", "src/candado/inputs.py",
     "        if s2 == stable:\n            cnt.next = 0\n        elif",
     "        if s2 == stable:\n            pass\n        elif"),
    ("BTNL y BTNC simultáneos: gana BTNC", "src/candado/fsm.py",
     "            elif btn_l:\n                if count > 0:\n                    del_en.next = True\n                if count <= 1:\n                    next_state.next = t_state.LOCKED\n            elif btn_c:\n                push_en.next = True\n        elif state == t_state.VALIDATE:",
     "            elif btn_c:\n                push_en.next = True\n            elif btn_l:\n                if count > 0:\n                    del_en.next = True\n                if count <= 1:\n                    next_state.next = t_state.LOCKED\n        elif state == t_state.VALIDATE:"),
    ("UNLOCKED no vence", "src/candado/fsm.py",
     "            if timeout or btn_d:", "            if btn_d:"),
    ("BTND no cierra el candado", "src/candado/fsm.py",
     "            if timeout or btn_d:", "            if timeout:"),
    ("BTNR vuelve a borrar los intentos fallidos (fuerza bruta)", "src/candado/fsm.py",
     "            if state == t_state.VALIDATE:\n                if match:",
     "            if btn_r:\n                fail_r.next = 0\n            elif state == t_state.VALIDATE:\n                if match:"),
    ("BTNR cancela la alarma", "src/candado/fsm.py",
     "        if state == t_state.ALARM:\n            # La alarma no se puede cancelar con los botones.\n            if timeout:",
     "        if state == t_state.ALARM and not btn_r:\n            # La alarma no se puede cancelar con los botones.\n            if timeout:"),
    ("comparador invertido", "src/candado/datapath.py",
     "match.next = seq == code", "match.next = seq != code"),
    ("orden de dígitos invertido", "src/candado/datapath.py",
     "seq.next = concat(d0, d1, d2, d3)", "seq.next = concat(d3, d2, d1, d0)"),
    ("CONFIG no guarda el código", "src/candado/fsm.py",
     "                code_we.next = True\n                clear_buf.next = True\n                next_state.next = t_state.UNLOCKED",
     "                clear_buf.next = True\n                next_state.next = t_state.UNLOCKED"),
    ("el reset duro no restaura el código", "src/candado/datapath.py",
     "        if rst_hard:\n            code.next = DEFAULT_CODE\n        elif we:",
     "        if False:\n            code.next = DEFAULT_CODE\n        elif we:"),
    ("el fallo se cuenta en cada ciclo de ERROR (no una sola vez)", "src/candado/fsm.py",
     "            if state == t_state.VALIDATE:\n                if match:",
     "            if state == t_state.VALIDATE or state == t_state.ERROR:\n                if match:"),
    ("temporizador de ERROR dura un tick menos", "src/candado/fsm.py",
     "if tcount >= ERROR_TICKS:", "if tcount >= ERROR_TICKS - 1:"),
    ("termómetro de LEDs desplazado", "src/candado/status.py",
     "        elif count == 2:\n            therm.next = 0b0011", "        elif count == 2:\n            therm.next = 0b0110"),
    ("display: intentos restantes sin actualizar", "src/candado/core.py",
     "attempts_left.next = MAX_ATTEMPTS - fail", "attempts_left.next = MAX_ATTEMPTS"),
    ("display: INPUT muestra los dígitos (no los oculta)", "src/candado/display.py",
     "                if state_code == S_CONFIG:", "                if True:"),
    ("sirena sonando fuera de ALARM", "src/candado/alarm.py",
     "        if not in_alarm:\n            tcnt.next = 0\n            sq.next = False\n        elif",
     "        if False:\n            tcnt.next = 0\n            sq.next = False\n        elif"),
    ("amplificador de audio siempre apagado", "src/candado/alarm.py",
     "        aud_sd.next = in_alarm", "        aud_sd.next = False"),
    ("los LEDs no parpadean en ALARM", "src/candado/status.py",
     "            if blink:\n                led.next = 0xFFFF", "            if True:\n                led.next = 0xFFFF"),
]


def run(mut):
    name, rel, old, new = mut
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copytree(os.path.join(ROOT, "src"), os.path.join(tmp, "src"))
        shutil.copytree(os.path.join(ROOT, "tests"), os.path.join(tmp, "tests"))
        shutil.copytree(os.path.join(ROOT, "tables"), os.path.join(tmp, "tables"))
        shutil.copytree(os.path.join(ROOT, "tools"), os.path.join(tmp, "tools"))
        path = os.path.join(tmp, rel)
        text = open(path, encoding="utf-8").read()
        if old not in text:
            return "ERROR", f"no se encontró el texto a mutar en {rel}"
        open(path, "w", encoding="utf-8").write(text.replace(old, new, 1))
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "tests", "-x", "-q", "-p", "no:cacheprovider"],
            cwd=tmp, capture_output=True, text=True)
        out = (proc.stdout + proc.stderr).strip().splitlines()
        failed = [l for l in out if l.startswith("FAILED")]
        if proc.returncode == 0:
            return "SOBREVIVIÓ", ""
        return "detectada", (failed[0][7:90] if failed else out[-1] if out else "")


def main():
    killed = 0
    for mut in MUTATIONS:
        status, info = run(mut)
        killed += status == "detectada"
        print(f"[{status:10s}] {mut[0]}" + (f"  <- {info}" if info else ""))
    print(f"\nMutaciones detectadas: {killed}/{len(MUTATIONS)}")
    sys.exit(0 if killed == len(MUTATIONS) else 1)


if __name__ == "__main__":
    main()

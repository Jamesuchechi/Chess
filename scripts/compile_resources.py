"""Compile Qt resource collection (.qrc) into Python module (resources_rc.py)."""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
QRC_FILE = ROOT_DIR / "assets" / "resources.qrc"
OUTPUT_FILE = ROOT_DIR / "src" / "chess_desktop" / "ui" / "resources_rc.py"


def compile_resources() -> int:
    """Compile resources using pyside6-rcc."""
    if not QRC_FILE.exists():
        print(f"Error: Resource file {QRC_FILE} not found.", file=sys.stderr)
        return 1

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Check for pyside6-rcc in PATH or current python environment
    rcc_bin = shutil.which("pyside6-rcc")
    if not rcc_bin:
        venv_bin = Path(sys.prefix) / "bin" / "pyside6-rcc"
        if venv_bin.exists():
            rcc_bin = str(venv_bin)

    if not rcc_bin:
        print("Warning: pyside6-rcc not found. Creating placeholder resources_rc.py.")
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("# Stub resources module\n")
        return 0

    cmd = [rcc_bin, str(QRC_FILE), "-o", str(OUTPUT_FILE)]
    print(f"Compiling resources: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error compiling resources: {result.stderr}", file=sys.stderr)
        return result.returncode

    print(f"Successfully compiled resources to {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(compile_resources())

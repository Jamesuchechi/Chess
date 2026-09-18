"""Packaging script using PyInstaller for Linux and Windows."""

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def get_project_root() -> Path:
    """Return the absolute path to the project root directory."""
    return Path(__file__).resolve().parent.parent


def build_executable(onedir: bool = False, clean: bool = True) -> int:
    """Build standalone Chess Desktop executable using PyInstaller."""
    root = get_project_root()
    entry_point = root / "src" / "chess_desktop" / "main.py"
    dist_dir = root / "dist"

    if not entry_point.exists():
        print(f"Error: Entry point not found: {entry_point}", file=sys.stderr)
        return 1

    # Check if pyinstaller is available
    pyinstaller_bin = shutil.which("pyinstaller")
    if not pyinstaller_bin:
        # Check in active virtual environment
        venv_bin = Path(sys.prefix) / ("Scripts" if os.name == "nt" else "bin") / "pyinstaller"
        if venv_bin.exists():
            pyinstaller_bin = str(venv_bin)
        else:
            print(
                "Error: PyInstaller not found. Install it with: uv pip install pyinstaller",
                file=sys.stderr,
            )
            return 1

    app_name = "chess-desktop" if platform.system() != "Windows" else "ChessDesktop"

    sep = ";" if platform.system() == "Windows" else ":"
    assets_src = root / "assets"
    assets_data = f"{assets_src}{sep}assets"

    cmd = [
        pyinstaller_bin,
        "--name",
        app_name,
        "--noconsole",
        "--add-data",
        assets_data,
        "--hidden-import",
        "PySide6.QtMultimedia",
        "--hidden-import",
        "PySide6.QtSvg",
        "--hidden-import",
        "chess",
        "--hidden-import",
        "sqlite3",
        "--paths",
        str(root / "src"),
    ]

    if onedir:
        cmd.append("--onedir")
    else:
        cmd.append("--onefile")

    if clean:
        cmd.append("--clean")

    cmd.append(str(entry_point))

    print(f"Building Chess Desktop for {platform.system()} ({platform.machine()})...")
    print(f"Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, cwd=root, check=False)
        if result.returncode == 0:
            output_path = dist_dir / (app_name + (".exe" if platform.system() == "Windows" else ""))
            print(f"\nBuild succeeded! Artifact located at:\n  {output_path}")
        else:
            print(f"\nBuild failed with exit code: {result.returncode}", file=sys.stderr)
        return result.returncode
    except Exception as exc:
        print(f"Execution error: {exc}", file=sys.stderr)
        return 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Package Chess Desktop into standalone executable")
    parser.add_argument(
        "--onedir",
        action="store_true",
        help="Create a directory distribution instead of single file",
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Do not clean cache/build directories before building",
    )
    args = parser.parse_args()

    sys.exit(build_executable(onedir=args.onedir, clean=not args.no_clean))


if __name__ == "__main__":
    main()

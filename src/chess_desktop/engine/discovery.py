"""Automatic discovery and verification of the Stockfish chess engine binary."""

import os
import shutil
import sys
from pathlib import Path


def is_executable_binary(path: Path | str) -> bool:
    """Check if the given path points to an existing executable file."""
    p = Path(path)
    return p.is_file() and os.access(p, os.X_OK)


def find_stockfish_binary(custom_path: str | Path | None = None) -> str | None:
    """Search for the Stockfish binary across standard platform locations.

    Args:
        custom_path: Optional user-configured executable path to check first.

    Returns:
        Absolute string path to a verified executable, or None if not found.
    """
    # 1. Custom user path if provided
    if custom_path:
        p = Path(custom_path).expanduser().resolve()
        return str(p) if is_executable_binary(p) else None

    # 2. System PATH lookup
    binary_names = ["stockfish.exe", "stockfish"] if sys.platform == "win32" else ["stockfish"]
    for name in binary_names:
        found_in_path = shutil.which(name)
        if found_in_path and is_executable_binary(found_in_path):
            return str(Path(found_in_path).resolve())

    # 3. Platform-specific known paths
    candidate_paths: list[Path] = []

    if sys.platform != "win32":
        # Linux / Unix / macOS standard paths
        candidate_paths.extend(
            [
                Path("/usr/games/stockfish"),
                Path("/usr/bin/stockfish"),
                Path("/usr/local/bin/stockfish"),
                Path("/snap/bin/stockfish"),
                Path.home() / ".local" / "bin" / "stockfish",
            ]
        )
    else:
        # Windows standard installation locations
        program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
        program_files_x86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
        local_app_data = os.environ.get("LOCALAPPDATA", "")

        for base in [program_files, program_files_x86, local_app_data]:
            if not base:
                continue
            sf_dir = Path(base) / "Stockfish"
            if sf_dir.exists():
                candidate_paths.append(sf_dir / "stockfish.exe")
                # Search for versioned names like stockfish_16_x64.exe
                candidate_paths.extend(sf_dir.glob("stockfish*.exe"))

    for candidate in candidate_paths:
        try:
            resolved = candidate.expanduser().resolve()
            if is_executable_binary(resolved):
                return str(resolved)
        except (PermissionError, OSError):
            continue

    return None

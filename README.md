# Chess Desktop

<div align="center">

[![CI](https://github.com/Jamesuchechi/Chess/actions/workflows/ci.yml/badge.svg)](https://github.com/Jamesuchechi/Chess/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![PySide6](https://img.shields.io/badge/GUI-PySide6%20Qt6-brightgreen.svg)](https://pypi.org/project/PySide6/)
[![Tests](https://img.shields.io/badge/tests-100%20passed-success.svg)](tests/)
[![Type Checked](https://img.shields.io/badge/types-mypy%20strict-informational.svg)](src/)

**A polished, offline-first desktop chess application for Linux and Windows.**  
Local multiplayer & Player vs. Computer (Stockfish AI), built on a clean, layered Python & Qt architecture.

[Features](#-features) • [Install on Windows](#-install-on-windows) • [Install on Ubuntu / Linux](#-install-on-ubuntu--linux) • [Quick Start](#-quick-start) • [Keyboard Shortcuts](#-keyboard-shortcuts) • [Architecture](#-architecture) • [Contributing](#-contributing)

</div>

---

## ✨ Features

- **🎮 Local Multiplayer** — Seamless pass-and-play on one machine with zero account or internet requirements.
- **🤖 Player vs. Computer (Stockfish AI)** — Default match mode mirroring Chess.com with integrated UCI Stockfish engine, auto-discovery, and difficulty presets (Beginner to Master).
- **⚡ Asynchronous & Non-Blocking** — Stockfish searches run on dedicated background threads; search requests immediately abort on Undo, Resign, or New Game without UI freezes.
- **🖱️ Dual Move Interaction** — Intuitive click-to-move and fluid drag-and-drop with floating cursor preview and legal move highlighting dots.
- **⏱️ Monotonic Digital Clocks** — FIDE-compliant digital clocks driven by system monotonic timing (immune to clock drift). Presets for Bullet (`1+0`), Blitz (`3+0`, `3+2`, `5+0`), Rapid (`10+0`, `10+5`, `15+10`), Classical (`30+0`), and Custom time controls with increment and sub-second display.
- **🎨 Board Themes** — 5 curated themes: **Classic** (Green & Buff), **Wood** (Walnut & Ash), **Modern** (Slate & Gray), **Minimal** (Charcoal & White), and **High Contrast** (Accessible Black & White).
- **🔊 Custom Synthesized Sound Effects** — Rich audio cues for move, capture, check, castle, promotion, game start, and victory, with defensive graceful degradation if audio drivers are unavailable.
- **💾 SQLite Persistence & PGN Support** — Save and resume games locally, export to standard PGN, and import any PGN from Lichess or Chess.com with full move-by-move historical review and branching.
- **📜 Complete FIDE Rules** — Castling, en passant, promotion dialog, check, checkmate, stalemate, threefold repetition, 50-move rule, and insufficient material calculations.

---

## 🪟 Install on Windows

### Method 1: Desktop & Start Menu Shortcut (Recommended)

Open **PowerShell** in the project directory and run:

```powershell
# 1. Clone repository
git clone https://github.com/Jamesuchechi/Chess.git
cd Chess

# 2. Sync dependencies
uv sync
# (Or with standard pip: python -m venv .venv; .venv\Scripts\activate; pip install -e .)

# 3. Create Windows Desktop & Start Menu shortcuts
powershell -ExecutionPolicy Bypass -File scripts\install_windows.ps1
```

#### What this does:
1. Creates a desktop shortcut at `%USERPROFILE%\Desktop\Chess Desktop.lnk`
2. Adds a Start Menu shortcut under `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Chess Desktop.lnk`
3. Configures launching without popping up an extra black console window.

To uninstall shortcuts anytime:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_windows.ps1 -Uninstall
```

---

### Method 2: Build Standalone Windows Executable (`.exe`)

You can generate a standalone single-file `.exe` that runs anywhere without needing Python:

```powershell
python scripts\build_dist.py
```
The resulting executable will be located at `dist\ChessDesktop.exe`.

---

### Stockfish on Windows
- **Auto-Discovery**: Chess Desktop automatically detects Stockfish if placed in:
  - `C:\Program Files\Stockfish\stockfish.exe`
  - `C:\Program Files (x86)\Stockfish\stockfish.exe`
  - `%LOCALAPPDATA%\Stockfish\stockfish.exe`
  - Any folder in your system `PATH`
- **Manual Selection**: You can also click **Browse...** in the New Game dialog to select any custom engine binary.
- **Fallback Engine**: If Stockfish is not installed, the application automatically uses its built-in pure-Python heuristic engine!

---

## 🐧 Install on Ubuntu / Linux

To install Chess Desktop as a native application with an application icon in your Ubuntu App Grid and launcher:

```bash
git clone https://github.com/Jamesuchechi/Chess.git
cd Chess
uv sync
bash scripts/install_desktop.sh
```

### What this does:
1. Installs the high-resolution vector icon to `~/.local/share/icons/hicolor/scalable/apps/chess-desktop.svg`
2. Creates the launcher script `~/.local/bin/chess-desktop`
3. Registers the desktop entry `~/.local/share/applications/chess-desktop.desktop`

You can now:
- Press the **Super** key on Ubuntu, type **"Chess Desktop"**, and hit Enter or pin it to your Ubuntu Dock!
- Run `chess-desktop` directly from your terminal.

To uninstall anytime:
```bash
bash scripts/install_desktop.sh --uninstall
```

---

## 💻 Quick Start (Development)

### 1. Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or standard Python virtual environment
- Optional: `stockfish` engine

### 2. Run Locally

**On Linux / macOS:**
```bash
git clone https://github.com/Jamesuchechi/Chess.git
cd Chess
uv sync
uv run chess-desktop
```

**On Windows (PowerShell / Command Prompt):**
```powershell
git clone https://github.com/Jamesuchechi/Chess.git
cd Chess
uv sync
uv run chess-desktop
```
*(Alternatively: `python -m chess_desktop.main` after activating your virtual environment)*

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl + N` | Start a New Game |
| `Ctrl + O` | Open / Load Saved Game |
| `Ctrl + S` | Save Current Game |
| `Ctrl + Shift + S` | Save Game As... |
| `Ctrl + Z` | Undo Last Move (or 2-ply against Computer) |
| `Ctrl + ,` | Preferences / Settings Dialog |
| `F` | Flip Board Orientation |
| `Left Arrow` | Step Backward in Move History (Review mode) |
| `Right Arrow` | Step Forward in Move History |
| `Home` | Jump to First Move |
| `End` | Jump to Live Position |
| `Esc` | Clear Selection / Dismiss Popups |

---

## 🏗️ Architecture

Chess Desktop is structured in strict hierarchical layers. **The UI never talks directly to python-chess or Stockfish**; all communication flows through orchestration services:

```text
┌────────────────────────────────────────────────────────┐
│                   PySide6 Qt UI Layer                  │
│   (MainWindow, BoardWidget, ClockWidget, Dialogs)      │
└───────────────────────────┬────────────────────────────┘
                            │ Qt Signals & Methods
┌───────────────────────────▼────────────────────────────┐
│                    Services Layer                      │
│   (GameService, SaveService, SettingsService, Sounds)   │
└───────────┬───────────────────────┬────────────────────┘
            │                       │
┌───────────▼───────────┐ ┌─────────▼───────────┐ ┌──────▼───────────┐
│     Domain Core       │ │   Stockfish Engine  │ │  SQLite Database  │
│   (GameState, Board,  │ │ (EngineWorker, UCI, │ │  (Repositories,   │
│    Clock, PGN)        │ │  Difficulty)        │ │   PGN import)     │
└───────────────────────┘ └─────────────────────┘ └───────────────────┘
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for full architectural documentation.

---

## 🧪 Testing & Code Quality

Chess Desktop includes an automated test suite covering rules, engine, clocks, persistence, audio fallback, and UI dialogs:

```bash
# Run all tests
uv run pytest

# Check code formatting & linter
uv run ruff check .
uv run ruff format --check .

# Static type checking
uv run mypy src/
```

---

## 📦 Standalone Packaging (PyInstaller)

To build a standalone executable for distribution:

```bash
# Single binary
python scripts/build_dist.py

# Directory bundle
python scripts/build_dist.py --onedir
```
Executable will be generated in `dist/chess-desktop` (Linux) or `dist/ChessDesktop.exe` (Windows).

---

## 🤝 Contributing

Contributions are welcome! Please check out [CONTRIBUTING.md](CONTRIBUTING.md) for our workflow, conventions, and branch policies.

---

## 📄 License

Distributed under the **Apache 2.0 License**. See [`LICENSE`](LICENSE) for details.
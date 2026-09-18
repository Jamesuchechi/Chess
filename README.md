# Chess Desktop

A polished, offline-first desktop chess application for Linux and Windows — local multiplayer and Player vs Computer (Stockfish), built on a clean, layered Python architecture.

Chess Desktop is not a demo. It's built to feel like a finished product: correct chess rules end to end, a responsive Qt UI, save/load, PGN import/export, and an engine layer that never blocks the interface.

---

## Features

- **Local multiplayer** — two players, one machine, no account or network required
- **Dual move interaction** — intuitive click-to-move and fluid drag-and-drop with floating cursor preview
- **Captured pieces & material counter** — real-time captured pieces display and point advantage indicator (+3, etc.)
- **Player vs Computer** — Stockfish via UCI with auto-discovery and beginner-to-expert difficulty presets
- **Non-blocking engine & instant cancellation** — Stockfish runs asynchronously; searches abort instantly on Undo, Resign, or New Game
- **Full rules coverage** — castling, en passant, promotion, check/checkmate/stalemate, threefold repetition, fifty-move rule, insufficient material
- **Move history & review mode** — SAN notation, scrollable, click-to-review with read-only board protection
- **Save / load / PGN** — SQLite-backed saved games, PGN import and export
- **Board flipping, themes, piece sets, sound** — configurable, persisted between launches, with Linux audio fallback
- **Chess clocks** — standard time controls with increment
- **Fully offline** — no account, no telemetry by default, no internet dependency

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for how these fit together, [`docs/PRODUCT.md`](docs/PRODUCT.md) for the complete product specification, and [`docs/TODO.md`](docs/TODO.md) for current build status.

---

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.11+ | Fast to build and test a UI-heavy app in |
| GUI | PySide6 (Qt) | Native desktop widgets, vector SVG rendering, high-DPI scaling |
| Chess rules | [`python-chess`](https://python-chess.readthedocs.io/) | Authoritative rules engine — we never reimplement chess logic |
| Engine | Stockfish (UCI) | Standard, strong, well-documented protocol |
| Persistence | SQLite | Zero-config local storage |
| Packaging | PyInstaller | Single executable, no Python install required for end users |

---

## Project Layout

```text
chess-desktop/
├── src/chess_desktop/
│   ├── app/           # main.py, application bootstrap
│   ├── domain/        # Game, Player, GameState — pure data, no I/O
│   ├── chess/         # python-chess wrapper: moves, notation, rules
│   ├── engine/        # Stockfish process management, UCI, difficulty mapping
│   ├── persistence/   # SQLite database, repositories, models
│   ├── services/      # GameService, SaveService, SettingsService — orchestration
│   └── ui/            # PySide6 windows, widgets, dialogs, board rendering
├── assets/            # piece sets, icons, sounds, board themes, resources.qrc
├── tests/             # unit / integration / ui
└── docs/              # ARCHITECTURE.md, PRODUCT.md, DEVELOPMENT.md, TODO.md, TROUBLESHOOTING.md
```

The rule that matters most: **UI never talks to `python-chess` or Stockfish directly.** Everything routes through `services/`. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Getting Started

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) for dependency management
- [Stockfish](https://stockfishchess.org/download/) installed (optional — auto-discovered on standard system paths or configured in Settings)

### Install

```bash
git clone <repo-url>
cd chess-desktop
uv sync
```

`uv sync` creates `.venv` and installs everything from `pyproject.toml`/`uv.lock` — no manual venv activation step required for the commands below.

### Run

```bash
uv run python -m chess_desktop.app.main
```

### Test

```bash
uv run pytest
uv run ruff check .
uv run mypy src/
```

See [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) for the full dev workflow, and [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) if Stockfish isn't being detected.

---

## Status

Early development — see [`docs/TODO.md`](docs/TODO.md) for the current phase and what's next.

## Non-Goals (v1)

Online multiplayer, accounts, cloud sync, chat, tournaments, mobile apps. These are explicitly deferred — see the roadmap in [`docs/TODO.md`](docs/TODO.md).

## License

Apache 2.0. See [`LICENSE`](LICENSE) for details.
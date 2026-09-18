# Development Guide

## Setup

Dependencies are managed with [uv](https://docs.astral.sh/uv/) — `pyproject.toml` + `uv.lock`, no `requirements.txt`, no manual venv juggling.

```bash
git clone <repo-url>
cd chess-desktop
uv sync
cp .env.example .env
```

`uv sync` reads `uv.lock` and creates/updates `.venv` with exact pinned versions. Commit `uv.lock` — it's what makes builds reproducible across machines and CI.

Install Stockfish separately (only needed to run/test Player-vs-Computer):

- **Linux:** `sudo apt install stockfish` (or build from source)
- **Windows:** download from [stockfishchess.org](https://stockfishchess.org/download/), add the binary to `PATH` or set `ENGINE_PATH` in `.env`

## Running the app

```bash
uv run python -m chess_desktop.app.main
```

## Adding dependencies

```bash
uv add pyside6                # runtime dependency
uv add --dev pytest ruff mypy # dev-only dependency group
```

This updates `pyproject.toml` and `uv.lock` together — don't hand-edit either file's dependency list.

## Testing

```bash
uv run pytest                     # all tests
uv run pytest tests/unit          # fast, no Qt/engine dependency
uv run pytest tests/integration   # full workflows (save/load, engine round-trip)
uv run pytest tests/ui            # widget-level, needs a display (use xvfb in CI on Linux)
```

Every chess rule (castling, en passant, promotion, repetition, fifty-move, insufficient material) needs a unit test under `tests/unit/chess/`. Every reported bug gets a regression test before the fix is considered done — see the pattern in `docs/troubleshooting.md` if you're adding one for a known issue.

## Linting & types

```bash
uv run ruff check .
uv run ruff format .
uv run mypy src/
```

Run these before opening a PR. CI should block on all three plus `pytest`.

## Project conventions

- **`python-chess` is the only chess-rules authority.** If you're about to write logic that decides whether a move is legal, stop — that belongs in `chess/`, backed by `python-chess`, not reimplemented.
- **No chess/DB/engine calls from `ui/`.** Widgets emit signals; `services/` decides what happens next.
- **Engine calls never touch the main thread.** See `docs/architecture.md#why-the-engine-runs-on-a-worker-thread`.
- **Type hints on public APIs.** `mypy` should stay clean — don't add ignores without a comment explaining why.
- **Small, focused modules.** If a file in `ui/` starts importing `sqlite3` or `chess.engine`, that's a sign it's grown a responsibility it shouldn't have.

## Adding a feature

1. Check `TODO.md` — is it already scoped into a phase?
2. Identify which layer it belongs to (`domain` / `chess` / `engine` / `persistence` / `services` / `ui`) before writing code.
3. Write the test first where the logic is non-trivial (chess rules, save/load round-trips, clock timing).
4. Implement, keeping the layer boundary from `docs/architecture.md`.
5. `uv run pytest && uv run ruff check . && uv run mypy src/` — all green.
6. Manually verify in the running app.
7. Update `TODO.md`.

## Building a distributable

```bash
uv run python scripts/compile_resources.py  # compiles assets/resources.qrc -> resources_rc.py
uv run python scripts/build.py              # produces a PyInstaller spec
uv run python scripts/package.py            # builds the platform executable
```

Always use Qt resource paths (`:/pieces/...`, `:/sounds/...`) rather than relative filesystem paths. Test on a clean machine/VM without a system Python before calling a build release-ready.

## High-DPI & SVG rendering

- All board pieces are rendered as vectors using `QSvgRenderer` directly inside `BoardWidget.paintEvent()`.
- Enable fractional scaling on application startup:
  ```python
  QApplication.setHighDpiScaleFactorRoundingPolicy(
      Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
  )
  ```
- Avoid rasterizing pieces to static-sized `QPixmap` caches unless resized.

## Audio dependencies (Linux)

Sound playback uses `PySide6.QtMultimedia.QSoundEffect`. On Linux, this requires GStreamer audio plugins:
```bash
sudo apt install libpulse-dev gstreamer1.0-plugins-good gstreamer1.0-pulseaudio
```
`SoundService` detects missing audio backends and logs a warning rather than failing or crashing.

## Database

SQLite file location and schema live in `persistence/database.py`. If you change the schema, add a migration step rather than mutating existing saved-game files in place — users' saved games must survive an app update.

## Logging

Standard `logging` module, levels `DEBUG`–`CRITICAL`. Engine failures, save/load failures, and unexpected game-state transitions should always log at `WARNING` or above. Don't log full board state or file paths at `INFO`/`DEBUG` in a way that would leak into shared logs — see `docs/TROUBLESHOOTING.md` for what to include when filing a bug.
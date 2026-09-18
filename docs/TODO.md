# TODO

Tracks build status against the product spec. Ordered so each phase produces something runnable — don't start a phase until the previous one's deliverable actually works.

Legend: `[ ]` not started · `[~]` in progress · `[x]` done

---

## Phase 0 — Foundation

- [x] `pyproject.toml` with dependencies (`PySide6`, `python-chess`, `pytest`, `pytest-qt`, `ruff`, `mypy`), managed via `uv` (`uv init`, `uv add`, commit `uv.lock`)
- [x] Package skeleton (`src/chess_desktop/{domain,chess,engine,persistence,services,ui}`)
- [x] Qt resource system (`.qrc` and compilation pipeline via `pyside6-rcc`)
- [x] Entry point (`app/main.py`) that opens an empty `QMainWindow`
- [x] Pytest + ruff + mypy configured and passing on empty project (`uv run pytest`)
- [x] `.env.example`, `.gitignore`

**Deliverable:** `python -m chess_desktop.app.main` opens a blank window.

---

## Phase 1 — Board & Rules (the core loop)

- [x] `chess/board.py` — thin wrapper around `python-chess.Board`
- [x] `chess/move_service.py` — legal move lookup, move execution, validation
- [x] `domain/game.py`, `domain/game_state.py` — authoritative game state
- [x] `ui/board/` — 64-square vector board widget (SVG rendered via `QSvgRenderer`), High-DPI support
- [x] Dual move interaction: click-to-select AND drag-and-drop with floating cursor preview
- [x] Captured pieces panel & real-time material advantage differential counter
- [x] Legal move highlighting (empty square vs. capture, visually distinct — not color-only)
- [x] Last-move highlight
- [x] Check highlight (king square glow & border)
- [x] Pawn promotion dialog (Queen/Rook/Bishop/Knight — no silent default)
- [x] Checkmate / stalemate / draw detection surfaced via `python-chess`, game-over dialog
- [x] Board flipping (`F` shortcut)
- [x] Move history panel (SAN, scrollable)

**Deliverable:** two humans can play a full legal game, start to checkmate/draw, on one machine with click or drag controls and material tracking. No save, no engine, no clock yet. **This is the milestone that proves the architecture — don't skip ahead of it.**

---

## Phase 2 — Game Controls

- [x] New Game (with unsaved-changes confirmation)
- [x] Undo (single move for local; player-move + computer reply when vs. computer in Phase 4)
- [x] Resign (with confirmation)
- [x] Offer/accept/decline draw (local multiplayer)
- [x] Move navigation with review mode semantics (board is read-only on past plies, "Resume" button, confirmation prompt before branching)

**Deliverable:** complete local multiplayer experience with safe historical review.

---

## Phase 3 — Persistence

- [x] SQLite schema (`persistence/models.py`, `persistence/database.py`)
- [x] `persistence/repositories.py` — save/load/list saved games
- [x] `services/save_service.py`
- [x] Save Game / Open Game / Save Game As (File menu)
- [x] PGN export
- [x] PGN import + review

**Deliverable:** a game can be saved, the app closed, reopened, and the game resumed without corruption. Import a real PGN from lichess/chess.com and review it move by move.

---

## Phase 4 — Engine (Stockfish)

- [ ] `engine/engine.py` — `ChessEngine` abstract interface
- [ ] `engine/stockfish.py` — UCI process management, isolated behind the interface
- [ ] Engine auto-discovery probing standard system paths (`/usr/bin/stockfish`, `/usr/games/stockfish`, Windows Program Files)
- [ ] Engine runs on a worker thread — **verify the UI never freezes while it's thinking**
- [ ] Search cancellation protocol: immediately send UCI `stop` and discard results if player undos, resigns, or starts new game
- [ ] `engine/difficulty.py` — Beginner→Expert mapped to depth/skill-level/time, no raw UCI params in the UI
- [ ] New Game dialog: Player vs Computer, color choice, difficulty
- [ ] Graceful failure when Stockfish isn't installed/found (human-readable error dialog, custom path browse button, local play unaffected)

**Deliverable:** Human vs Computer, all difficulty levels, UI stays responsive during engine search and search aborts cleanly on user interruption.

---

## Phase 5 — Clock

- [ ] Monotonic clock implementation (not wall-clock timestamps)
- [ ] Time control presets (Unlimited, 1+0, 3+0, 3+2, 5+0, 10+0, 10+5, 15+10, 30+0)
- [ ] Increment handling, switch-on-move, timeout → loss
- [ ] Clock state persisted in saved games

**Deliverable:** timed games work correctly, including on save/resume.

---

## Phase 6 — Polish & Packaging

- [ ] Board themes (Classic, Wood, Modern, Minimal, High Contrast)
- [ ] Multiple piece sets
- [ ] Sound effects (move, capture, check, castle, promotion, game start/end) with mute
- [ ] Audio fallback: graceful degradation if Linux GStreamer/PulseAudio drivers are missing
- [ ] Settings dialog (appearance, board, pieces, sound, engine path)
- [ ] Keyboard shortcut pass (Ctrl+N/O/S/Z/E, F, Esc, arrows, Home/End)
- [ ] Accessibility pass (focus states, contrast, no color-only state)
- [ ] PyInstaller build for Linux
- [ ] PyInstaller build for Windows
- [ ] Clean-install verification on both platforms

**Deliverable:** `1.0.0` release candidate.

---

## Explicitly deferred (not v1)

Online multiplayer · accounts/auth · cloud sync · chat · matchmaking · tournaments · leaderboards · spectator mode · chess variants · mobile apps.

## Backlog / ideas (post-1.0)

- Position setup / "load from FEN"
- Puzzle mode
- Opening recognition
- Game analysis (post-game engine review)
- Statistics dashboard (computed from stored games, not duplicated counters)
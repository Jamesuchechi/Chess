# Architecture

## Core principle

> The UI presents the game; the domain controls the game; the chess engine validates the game; persistence remembers the game.

Each layer only talks to the layer directly beneath it. The UI never imports `python-chess` or a Stockfish process directly — it goes through `services/`.

```text
                 ┌──────────────────┐
                 │   PySide6 UI     │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │ Game Controller  │
                 └────────┬─────────┘
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
      ┌──────────────┐        ┌──────────────┐
      │ Chess Service│        │ Engine Service│
      └──────┬───────┘        └──────┬───────┘
             │                       │
             ▼                       ▼
      ┌──────────────┐        ┌──────────────┐
      │ python-chess │        │  Stockfish   │
      └──────────────┘        └──────────────┘
             │
             ▼
      ┌──────────────┐
      │ Game State   │
      └──────┬───────┘
             │
             ▼
      ┌──────────────┐
      │ Persistence  │
      │   SQLite     │
      └──────────────┘
```

## Layers

### `domain/`
Plain data — `Game`, `Player`, `GameState`, enums. No I/O, no Qt, no `python-chess` imports. This is what gets serialized to/from SQLite and what the UI reads to render.

### `chess/`
The only place `python-chess` is imported. Wraps board representation, legal-move generation, move validation, and SAN/FEN/PGN notation. **Never reimplement check/checkmate/castling/en passant/repetition logic here or anywhere else** — `python-chess` is authoritative.

### `engine/`
Stockfish isolated behind a `ChessEngine` abstract interface:

```python
class ChessEngine:
    def get_best_move(self, board: chess.Board, difficulty: Difficulty) -> chess.Move:
        ...

class StockfishEngine(ChessEngine):
    ...
```

This buys two things: the UI/services never know they're talking to Stockfish specifically (swap engines later without touching callers), and it gives you a clean seam to run the engine on a worker thread.

### `persistence/`
SQLite access — `database.py` (connection/schema), `models.py` (row ↔ domain mapping), `repositories.py` (save/load/list queries). UI and domain code never write SQL.

### `services/`
Orchestration layer — the only thing the UI calls directly. `GameService` drives the move lifecycle, `SaveService` wraps persistence, `SettingsService` handles config. This is where cross-cutting concerns live (e.g., "make a move, then check if the engine needs to respond").

### `ui/`
PySide6 windows, widgets, dialogs, and the board renderer. Holds no chess logic — a click becomes an event, the event goes to `services/`, the response comes back and the UI redraws. If you find yourself writing `if board.is_check()` inside a widget, that logic belongs one layer down.

## Event flow (making a move)

```text
User clicks e2
      ↓
Board emits squareSelected(e2)
      ↓
Game Controller receives event
      ↓
Legal moves calculated (chess/move_service.py)
      ↓
Board highlights e3/e4
      ↓
User clicks e4
      ↓
Game Controller validates move
      ↓
python-chess pushes move
      ↓
Game State updates
      ↓
Move History updates
      ↓
Board redraws
      ↓
Clock switches
      ↓
Game status evaluated (check/mate/draw)
      ↓
Engine Service invoked if it's the computer's turn
```

## Why the engine runs on a worker thread

Stockfish search is not instant, and PySide6's main thread also drives the UI. If `StockfishEngine.get_best_move()` runs synchronously on the main thread, the window freezes for the duration of the search — clicks queue up, redraws stall, and the app looks broken.

```text
Qt UI Thread
     │
     ├── User Interaction
     ├── Board Rendering
     └── UI Updates
            │
            ▼
      Worker Thread
            │
            ▼
        Stockfish
```

Use a `QThread`/`QRunnable` + Qt signals to kick off the search and deliver the resulting move back to the main thread. Nothing outside `engine/` should know this thread exists.

## State management rule

There is exactly one authoritative `GameState`. The UI is a read-only view of it plus an event source into it — it never maintains its own parallel copy of "whose turn is it" or "is this move legal." If the UI and the domain state can ever disagree, that's a bug in the UI layer, not the domain layer.

## Application states

```text
IDLE → CONFIGURING_GAME → PLAYING ⇄ PAUSED
PLAYING → CHECK → CHECKMATE | DRAW | RESIGNED | TIMEOUT
PLAYING ⇄ REVIEWING (browsing past moves during play or post-game)
```

In the `REVIEWING` state:
* The board is read-only to prevent inadvertent move inputs.
* The UI displays a "Jump to Present / Resume" button.
* If a player plays a move while in `REVIEWING`, an explicit confirmation dialog triggers branching and truncates subsequent moves before returning to `PLAYING`.

---

## Captured pieces and material balance

The domain `GameState` tracks captured pieces and material differential.
* `chess/move_service.py` detects captures on each ply.
* `services/game_service.py` computes pieces missing from the board and calculates standard piece values ($P=1, N=3, B=3, R=5, Q=9$).
* The UI displays captured piece groups and an advantage badge (e.g. White `+3`) alongside each player card.

---

## Engine worker lifecycle and search cancellation

Stockfish searches must be abortable on demand:

```text
User clicks Undo / Resign / New Game
      ↓
Game Controller calls EngineService.cancel_search()
      ↓
Worker thread sends "stop" via UCI
      ↓
Worker discards pending callbacks
      ↓
Engine process resets to ready state
```

1. **Isolation:** The worker thread (`QThread` or `QRunnable`) manages the engine subprocess pipe.
2. **Cancellation:** When user interrupts (Undo, Resign, Reset), `stop` is written to standard input, late `bestmove` signals are suppressed, and the UI responds immediately.
3. **Shutdown:** On application close, `EngineService` cleanly transmits `quit` and joins the worker thread.

---

## Asset and Resource Architecture

* Vector assets (SVG piece sets, icons) and sound files (`.wav`) are declared in `assets/resources.qrc`.
* Compiled via `pyside6-rcc` into `src/chess_desktop/ui/resources_rc.py`.
* All UI widgets access assets via Qt resource URLs (`:/pieces/...`, `:/sounds/...`), guaranteeing bulletproof bundling in PyInstaller frozen executables without fragile filesystem path lookups.
* **Audio Backend Resilience:** `services/sound_service.py` guards `QSoundEffect` calls with runtime capability checks. If Linux audio drivers or GStreamer plugins are unavailable, audio degrades silently to `sound_enabled = False` without raising exceptions.
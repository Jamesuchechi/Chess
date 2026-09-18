# Chess Desktop App — Product Specification

---

# 1. Product Overview

## 1.1 Product Name

**Chess Desktop**

## 1.2 Description

Chess Desktop is a native, offline-first desktop chess application for Linux and Windows built with Python, PySide6 (Qt), python-chess, and Stockfish. The application delivers a high-quality chess experience including local multiplayer, Human vs Computer play, chess clocks, PGN/FEN import and export, move history, captured pieces tracking, multiple board/piece themes, sound effects, and persistent game storage via SQLite.

The application is structured using a strict layered architecture where the UI never implements chess rules or touches database/engine processes directly.

---

# 2. Product Vision

Chess Desktop aims to provide the polish, responsiveness, and aesthetic quality of modern web chess platforms (such as Lichess and Chess.com) within a lightweight, native, and completely offline desktop executable.

---

# 3. Product Goals

## 3.1 Primary Goals

### Goal 1 — Correct Chess Gameplay
* 100% adherence to FIDE chess rules powered by `python-chess`.
* Full support for castling, en passant, pawn promotion, check, checkmate, stalemate, threefold repetition, fifty-move rule, and insufficient material.

### Goal 2 — High-Quality Desktop UX
* Smooth, scalable vector-rendered chessboard (SVG).
* Dual move interaction: intuitive click-to-move AND fluid drag-and-drop.
* Captured pieces display with real-time material advantage differential.
* Responsive layouts that scale cleanly from compact laptop screens to 4K displays.
* Subtle animations, visual move indicators, and audio feedback.

### Goal 3 — Offline-First Experience
* Zero network requirements, zero account creation, zero telemetry by default.
* Fast local persistence with SQLite and standard PGN/FEN support.

### Goal 4 — Robust Architecture & Performance
* Strict layer separation (`domain/`, `chess/`, `engine/`, `persistence/`, `services/`, `ui/`).
* Engine calculations and I/O run strictly on worker threads; the Qt main UI thread never freezes.
* Immediate cancellation of engine computations when user resets, undos, or resigns.

---

# 4. Non-Goals for Version 1

The following features are explicitly deferred:
* Online multiplayer, accounts, cloud synchronization, and matchmaking.
* Chat, social features, and spectator modes.
* Chess variants (Crazyhouse, Chess960, etc.).
* Mobile operating systems.

---

# 5. Target Platforms

* **Linux (First-class target):** Ubuntu 22.04+, Fedora, Arch, Debian. Packaged as standalone executable or AppImage.
* **Windows (First-class target):** Windows 10, Windows 11 (64-bit executable).
* **macOS:** Secondary target for post-1.0.

---

# 6. Technology Stack

| Layer | Choice | Rationale |
|---|---|---|
| Language | Python 3.11+ | Modern typing, high developer velocity, rich ecosystem |
| Desktop GUI | PySide6 (Qt for Python) | Native performance, high-DPI awareness, custom vector painting |
| Chess Rules | `python-chess` | Authoritative FIDE-compliant rules engine; no hand-rolled rule logic |
| Chess Engine | Stockfish (via UCI) | Gold-standard open-source engine with adjustable skill levels |
| Persistence | SQLite | Zero-configuration local database for games and preferences |
| Packaging | PyInstaller | Single-file / directory distributable requiring no local Python |

---

# 7. Application Architecture

The system enforces a strict unidirectional dependency rule:
> **The UI presents the game; the domain controls the game; the chess engine validates the game; persistence remembers the game.**

```text
                 ┌────────────────────────┐
                 │       PySide6 UI       │
                 └───────────┬────────────┘
                             │
                             ▼
                 ┌────────────────────────┐
                 │    Game Controller     │
                 └───────────┬────────────┘
                             │
               ┌─────────────┴─────────────┐
               ▼                           ▼
       ┌──────────────┐            ┌──────────────┐
       │ Chess Service│            │ Engine Service│
       └───────┬──────┘            └───────┬──────┘
               │                           │
               ▼                           ▼
       ┌──────────────┐            ┌──────────────┐
       │ python-chess │            │  Stockfish   │
       └──────────────┘            └──────────────┘
               │
               ▼
       ┌──────────────┐
       │  Game State  │
       └───────┬──────┘
               │
               ▼
       ┌──────────────┐
       │ Persistence  │
       │    SQLite    │
       └──────────────┘
```

### Module Layout:
* `chess_desktop/domain/`: Pure dataclasses (`Game`, `Player`, `GameState`, enums). No I/O, no Qt, no `python-chess`.
* `chess_desktop/chess/`: Authoritative wrapper around `python-chess`. Board setup, move validation, SAN/FEN/PGN conversion.
* `chess_desktop/engine/`: `ChessEngine` abstract interface, `StockfishEngine` UCI process manager, difficulty tuning, worker thread execution.
* `chess_desktop/persistence/`: SQLite connection, schema migrations, and repositories.
* `chess_desktop/services/`: Orchestration layer (`GameService`, `SaveService`, `SettingsService`).
* `chess_desktop/ui/`: Windows, widgets, board canvas, dialogs, theme styling.

---

# 8. Core Domain Model

`GameState` is the single source of truth for the entire application. It encapsulates:
* Active `python-chess` board stack
* Current turn and move count
* Move history list (SAN, UCI, timestamps)
* Captured pieces and material score differential
* Clock time remaining for White and Black
* Game status (`IN_PROGRESS`, `CHECKMATE`, `STALEMATE`, `DRAW_INSUFFICIENT_MATERIAL`, `DRAW_REPETITION`, `DRAW_FIFTY_MOVES`, `RESIGNED`, `TIMEOUT`)
* Active mode: `PLAYING` vs `REVIEWING`

---

# 9. Game Modes

## 9.1 Local Multiplayer
Two players take turns on the same workstation. No network connection required.

## 9.2 Player vs Computer
Human plays against Stockfish. Configurable player color (White, Black, or Random) and difficulty preset.

## 9.3 Computer vs Computer (Debug/Demo)
Engine matches for performance benchmarking and UI testing.

---

# 10. Game Difficulty System

Computer difficulty maps human-friendly labels to Stockfish UCI parameters without exposing raw engine configurations:

| Level | Skill Level (0–20) | Depth Limit | Time Limit (ms) | Approximate Elo |
|---|---|---|---|---|
| Beginner | 0 | 1 | 50 | ~800 |
| Easy | 4 | 3 | 150 | ~1100 |
| Medium | 10 | 6 | 400 | ~1500 |
| Hard | 16 | 12 | 1000 | ~1900 |
| Expert | 20 | 18 | 2000 | ~2400+ |

---

# 11. Chessboard UI & Rendering

## 11.1 Board Requirements
* 64 squares with configurable themes (Classic Green, Wood, Dark Modern, High Contrast).
* Scalable SVG pieces rendered crisply at any dimension via `QSvgRenderer`.
* Rank (1–8) and file (a–h) coordinate labels with automatic orientation flipping.
* Highlight layers:
  * Selected square highlight
  * Legal move indicators (small dots for empty squares; distinct corner markers/rings for captures)
  * Last move origin and destination highlights
  * King in check highlight (red radial glow and border)

---

# 12. Dual Move Interaction Model

To satisfy both casual and competitive desktop chess players, the board MUST support two simultaneous interaction models:

### 1. Click-to-Move
1. User clicks a square containing their piece $\rightarrow$ piece is selected, legal move targets highlight.
2. User clicks a highlighted target square $\rightarrow$ move is validated and executed.
3. User clicks another friendly piece $\rightarrow$ selection switches immediately.
4. User clicks an illegal square or empty non-target $\rightarrow$ selection clears.

### 2. Drag-and-Drop
1. User presses mouse button on a friendly piece and drags.
2. The dragged piece floats dynamically centered under the cursor at elevated z-order with a subtle drop shadow.
3. The origin square retains a translucent "ghost" of the piece.
4. Target squares under the cursor highlight on hover.
5. On mouse release:
   - If over a legal square $\rightarrow$ move executes.
   - If over an illegal square or off-board $\rightarrow$ piece snaps back smoothly to origin with no state change.
6. A quick press-and-release on the same square without movement acts as a click-to-select.

---

# 13. Captured Pieces & Material Balance

The UI must prominently display captured pieces and net material advantage adjacent to each player's status panel:

```text
┌─────────────────────────────────────────────────────────────┐
│ [Avatar] Black: Stockfish (Medium)      [ 04:32 ]           │
│ Captured: ♟ ♟ ♞                                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                        CHESSBOARD                           │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ [Avatar] White: Player 1                [ 04:55 ]  [+3]     │
│ Captured: ♙ ♙ ♙ ♗ ♖                                        │
└─────────────────────────────────────────────────────────────┘
```

### Material Evaluation Calculation:
* Piece values: Pawn = 1, Knight = 3, Bishop = 3, Rook = 5, Queen = 9.
* Total material is computed from the captured pieces list.
* The player with higher material shows a badge with the differential (e.g., `+3`).

---

# 14. Move History & Review Navigation Semantics

### 14.1 Display
* Standard algebraic notation (SAN) displayed in a scrollable, two-column table (Move #, White, Black).
* Clicking any move jumps the board view to that exact ply.

### 14.2 Active Play vs Review Mode
* When the user steps backward in history (via table click, left arrow, or Home key), the game enters **`REVIEWING`** state.
* **Read-Only Protection:** While in `REVIEWING` state, the board is strictly read-only. Clicking or dragging pieces does not move them, avoiding accidental state corruption.
* **Resume Control:** A prominent **"Jump to Present" / "Resume Game"** button returns the board to the live ply.
* **Branching Confirmation:** If the user attempts to play a new move from an earlier historical position, the app displays:
  ```text
  Create Move Branch?
  
  Playing a move from this historical position will truncate all 
  subsequent moves and start a new game line.
  
  [Cancel]  [Branch & Play]
  ```

---

# 15. Game Navigation Controls

Standard navigation buttons and shortcuts must be provided:
* `|<<` First Move (`Home`)
* `<` Previous Move (`Left Arrow`)
* `>` Next Move (`Right Arrow`)
* `>>|` Last Move / Live (`End`)
* `F` Flip Board
* `Ctrl + Z` Undo Move

---

# 16. Undo Semantics

* **Local Multiplayer:** Reverts exactly 1 half-move (one ply), restoring the previous player's turn and clock.
* **Player vs Computer:** Reverts 2 half-moves (the computer's reply AND the player's prior move), placing the human back in their pre-move state.
* Undo must never corrupt castling rights, en passant availability, repetition counts, or captured pieces. State is reconstructed directly via the `python-chess` board stack.

---

# 17. Engine Process Architecture & Search Cancellation

## 17.1 Worker Thread Isolation
Stockfish UCI communication runs exclusively inside a dedicated `QThread` or `QRunnable`. The PySide6 main event loop must never block waiting for engine output.

## 17.2 Immediate Search Cancellation
If the user clicks **Undo**, **Resign**, or **New Game** while Stockfish is calculating:
1. `EngineService` immediately sends the UCI command `stop` to the process.
2. The active search worker is flagged as canceled.
3. When the engine subsequently emits `bestmove`, the callback is safely ignored and discarded.
4. The engine process is reset to `isready` state without orphaned tasks or CPU spikes.

## 17.3 Subprocess Lifecycle
On application shutdown, the engine manager sends `quit`, waits up to 500ms for clean termination, and kills the subprocess if still running, ensuring no zombie processes linger.

---

# 18. Engine Auto-Discovery & Path Resolution

To spare end-users from technical command-line setup, the application automatically searches for a valid Stockfish binary on startup:

### Discovery Search Paths:
* **Linux:** `/usr/bin/stockfish`, `/usr/games/stockfish`, `/usr/local/bin/stockfish`, `~/.local/bin/stockfish`, and system `PATH`.
* **Windows:** `%LOCALAPPDATA%\Stockfish\stockfish.exe`, `%PROGRAMFILES%\Stockfish\stockfish.exe`, `%PROGRAMFILES(X86)%\Stockfish\stockfish.exe`, and system `PATH`.
* **macOS:** `/opt/homebrew/bin/stockfish`, `/usr/local/bin/stockfish`.

### Fallback Behavior:
* If Stockfish is detected: Enable Player vs Computer automatically.
* If Stockfish is not found:
  * Local multiplayer remains 100% active and uninhibited.
  * When Player vs Computer is selected, display a helpful dialog:
    ```text
    Chess Engine Not Found
    
    Stockfish was not detected on your system. You can install it 
    via your package manager or locate the executable manually.
    
    [Browse for Engine...]  [Cancel]
    ```
  * User can set and test a custom engine path in `Settings -> Engine`.

---

# 19. Live Evaluation Gauge (Optional Practice Aid)

An optional vertical evaluation bar beside the board displays live computer evaluation during Player vs Computer games or post-game review:
* Range: $-10.0$ (Black winning) to $+10.0$ (White winning), or mate counters (`M3`).
* Visuals: Split black/white bar with animated transition and numeric score badge.
* Can be toggled on/off in `View -> Show Evaluation Bar`.

---

# 20. Chess Clock System

* Accurate monotonic timing using `time.perf_counter()` rather than wall-clock time.
* Standard presets:
  * Bullet: `1+0`, `2+1`
  * Blitz: `3+0`, `3+2`, `5+0`, `5+3`
  * Rapid: `10+0`, `15+10`
  * Classical: `30+0`, `60+30`
  * Unlimited / Casual
* Auto-flagging: Clock reaching 0:00 triggers immediate timeout loss (or draw if opponent has insufficient mating material, per FIDE Article 6.9).

---

# 21. Critical Technical Considerations & Safeguards

### 21.1 PySide6 SVG Rendering & High-DPI
* Pieces are rendered using `QSvgRenderer` on `QPainter` within `BoardWidget.paintEvent()`.
* Fractional DPI scaling (`Qt.HighDpiScaleFactorRoundingPolicy.PassThrough`) is enabled on `QApplication` initialization to guarantee crisp lines on modern displays.

### 21.2 Qt Resource System (`.qrc`) Asset Bundling
* All SVG piece sets, icons, sounds, and theme definitions are compiled into a Python resource module (`resources_rc.py`) via `pyside6-rcc`.
* Assets are referenced in code via Qt resource URLs (e.g., `:/pieces/cburnett/wP.svg`).
* This eliminates filesystem relative-path issues when the app is packaged with PyInstaller into a standalone executable.

### 21.3 Linux Audio Backend Resilience
* Sound effects (`move.wav`, `capture.wav`, `check.wav`, `game_over.wav`) are played via PySide6's `QSoundEffect`.
* On minimalist Linux installations lacking GStreamer plugins or PulseAudio/PipeWire drivers, sound initialization can fail.
* The `SoundService` wraps audio calls with feature-detection: if audio playback fails or raises errors, it logs a `WARNING` and sets `sound_enabled = False` without crashing the game.

---

# 22. Persistence & PGN/FEN Handling

* **SQLite Database:** Stores game metadata, full PGN, final FEN, result, timestamps, and player details in `games` table.
* **Auto-Save:** Current game state is saved on every move to protect against unexpected termination.
* **PGN Import/Export:** Full compliance with standard Seven-Tag Roster and SAN movetext.
* **FEN Copy/Paste:** Fast position sharing to and from the clipboard.

---

# 23. Harmonized Development Roadmap

To ensure development produces runnable, verifiable milestones at every phase, the project follows this roadmap:

### Phase 0 — Foundation & Skeleton
* `pyproject.toml` with `uv` (PySide6, python-chess, pytest, pytest-qt, ruff, mypy).
* Directory skeleton (`domain/`, `chess/`, `engine/`, `persistence/`, `services/`, `ui/`, `app/`).
* Asset compilation pipeline (`pyside6-rcc`).
* Main window shell launches cleanly.

### Phase 1 — Board & Rules (Core Gameplay)
* Authoritative board wrapper and legal move service.
* 64-square vector board widget with High-DPI support.
* Dual move interaction: click-to-move AND drag-and-drop.
* Highlights: selected piece, legal moves (dots/rings), last move, check.
* Captured pieces panel and material advantage counter.
* Pawn promotion dialog.
* Full FIDE checkmate / draw detection and game-over banner.

### Phase 2 — Game Controls & Review
* New game, resign, draw offer, and board flipping.
* Move history list with SAN notation.
* Move navigation with `REVIEWING` state (read-only board and jump-to-present).
* Complete Undo mechanics (single-ply for local, two-ply for PvC).

### Phase 3 — Persistence & Storage
* SQLite database layer and repository.
* Save / Open / Auto-resume game functionality.
* PGN export and PGN import with move review.

### Phase 4 — Stockfish Engine Integration
* Abstract `ChessEngine` interface and UCI `StockfishEngine`.
* Automatic engine discovery across Linux and Windows standard paths.
* Asynchronous search on Qt worker thread (zero UI stutter).
* Instant search cancellation on user interrupt (Undo/Resign/New Game).
* Difficulty presets (Beginner to Expert).

### Phase 5 — Chess Clocks
* Monotonic clock engine with increment handling and timeout detection.
* Time control selector dialog.
* Clock persistence and resume.

### Phase 6 — Polish, Audio, & Packaging
* Board themes and multiple piece sets.
* Sound effects with graceful Linux audio fallback.
* Settings management dialog.
* PyInstaller executable builds for Linux and Windows.
* Clean installation verification.

---

# 24. Success Criteria

Chess Desktop is complete when a user can install the standalone app, play a fluid game using either clicks or dragging, clearly see captured material and clock state, play against a responsive Stockfish engine that never locks up the UI, save/resume games reliably, and enjoy a polished, beautiful desktop interface.

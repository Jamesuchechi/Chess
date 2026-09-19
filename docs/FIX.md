# Chess Desktop — Overhaul Task List

Context: PySide6 + python-chess + Stockfish (UCI) + SQLite, packaged with PyInstaller,
dependencies managed with uv. Layered architecture: domain / chess / engine / persistence
/ services / ui, with services as the only layer the UI talks to.

Work through the phases **in order**. Each task has a clear "done" condition — treat that
as the acceptance test before moving to the next task. Don't skip Phase 1; everything
after it depends on the engine no longer blocking the UI thread.

---

## Phase 1 — Fix the core bug (engine blocking the UI thread)

**Problem**: after the player moves, the UI appears to hang for ~2 seconds, then the
engine's move is applied instantly. This is a threading bug, not intentional "thinking
time" — the Stockfish UCI call is running synchronously on the GUI thread, freezing
repaint until it returns.

- [x] Move all engine calls (`engine.play(...)`, any UCI communication) off the main
      thread. Use `QThread` (or `QThreadPool` + `QRunnable`) — never call the engine
      directly from a UI event handler.
- [x] Implement an `EngineWorker(QThread)` with a `move_ready = Signal(chess.Move)`
      (and an `error = Signal(str)` for engine crashes/timeouts). `run()` does the
      blocking `engine.play()` call and emits the result.
- [x] On player move: disable board input → start `EngineWorker` → show a visible
      "thinking…" state (see Phase 2 for the visual) → on `move_ready`, apply the move
      on the main thread and re-enable input.
- [x] Give the engine an **explicit, intentional** think time via
      `chess.engine.Limit(time=...)`. Make this a difficulty setting (see Phase 4), not
      a hidden magic number. The delay the player sees should be an honest reflection of
      engine think time — not blocked I/O.
- [x] Handle engine crash / process death gracefully (catch the exception in the worker,
      emit `error`, surface a UI message, allow restarting the engine process without
      restarting the app).
- [x] Confirm: player can click around, resize the window, and interact with menus
      while the engine is "thinking," with no freeze at any point.

## Phase 2 — Rendering overhaul (chess.com-level feel)

- [x] Rebuild the board on `QGraphicsView` / `QGraphicsScene` if it isn't already
      (move away from a grid of plain widgets/buttons). This is the foundation for
      everything else in this phase.
- [x] Animate piece movement between squares with `QPropertyAnimation` — no more
      teleport-redraw on move. Include capture handling (captured piece fades/removes
      cleanly) and castling (both pieces animate).
- [x] Add drag-and-drop piece movement, with snap-back animation on illegal drop.
      Keep click-to-select/click-to-move as an alternative input method.
- [x] Highlight: last move's from/to squares, legal-move indicators (dots for empty
      squares, ring/border for capturable squares) when a piece is selected, and the
      king's square in a distinct color when in check.
- [x] Add a visible "engine thinking…" indicator (subtle animation or spinner near the
      move list / clock) tied to the `EngineWorker` running state from Phase 1.
- [x] Move list panel: algebraic notation, scrollable, auto-scrolls to latest move.
      Clicking a past move jumps the board view to that position (read-only replay is
      fine for v1 — don't allow editing history yet).
- [x] Per-side clocks (even a simple count-up/count-down is fine for v1). Make time
      control configurable (untimed / blitz / rapid presets).
- [x] Sound effects: move, capture, check, castle, game-over. Add a mute toggle in
      settings.
- [x] Swap in a proper SVG piece set (python-chess ships some; or use a free SVG set)
      and at least 2 board color themes, switchable in settings.
- [x] Promotion dialog (choose queen/rook/bishop/knight) instead of auto-queening.
- [x] Game-over modal: checkmate / stalemate / draw (50-move, threefold repetition,
      insufficient material) / resignation, each with a clear distinct message, and a
      "new game" / "rematch" action.
- [x] Resign and offer-draw actions available mid-game (draw offer can be a simple
      accept/decline in local/engine play; needed for real multiplayer in Phase 3).

## Phase 3 — LAN / hotspot multiplayer (two laptops)

Treat "hotspot" and "same Wi-Fi network" as the **same case** — once two laptops share
a network, this is plain LAN networking. Do not build Bluetooth for v1 (cross-platform
Bluetooth stacks on Windows/Linux are inconsistent and not worth the complexity right
now); design the transport layer so Bluetooth *could* be added later without touching
game logic.

- [x] Define a transport interface independent of game logic, e.g.:
      `connect_as_host(port)`, `connect_as_client(host_ip, port)`, `send_move(move)`,
      `on_move_received(callback)`, `send_message(type, payload)`, `disconnect()`.
      All game logic talks to this interface, never to sockets directly.
- [x] Implement the LAN transport using `asyncio` sockets (or WebSockets if you want
      easier debugging/future web-client reuse). JSON message protocol, e.g.:
      `{"type": "move", "uci": "e2e4"}`, `{"type": "resign"}`,
      `{"type": "draw_offer"}` / `{"type": "draw_response", "accept": bool}`,
      `{"type": "chat", "text": "..."}` (optional), `{"type": "sync_request"}`.
- [x] Host flow: pick a port, display the host's LAN IP (and hotspot SSID/instructions
      if hosting via hotspot) for the other player to enter.
- [x] Client flow: enter host IP + port, connect, confirm handshake before allowing
      moves.
- [x] Each side maintains its own `chess.Board()` and validates the incoming move is
      legal before applying it — never trust the wire blindly.
- [x] Handle disconnects and reconnection attempts gracefully (timeout + "opponent
      disconnected" state, with a manual reconnect option rather than crashing).
- [x] Sync-on-join: if a client reconnects mid-game, support resending full move
      history so both boards realign.
- [x] Reuse the Phase 2 UI (board, clocks, move list, resign/draw) unmodified for
      multiplayer games — multiplayer should feel like the same app, not a different
      mode bolted on.

## Phase 4 — Depth and polish (things worth adding beyond the original ask)

These aren't things you explicitly asked for, but they're what separates "a chess app"
from "a chess app people keep open." Prioritize top-down; cut from the bottom if time
is tight.

- [x] **Difficulty levels** exposed to the player (map to Stockfish `Skill Level` UCI
      option and/or think-time limits) — "easy / medium / hard" is enough for v1.
- [x] **Undo/takeback** for local and vs-computer games (not for competitive
      multiplayer — gate it off there, or require opponent approval).
- [x] **PGN export/import** — let players save and reload games. This also gives you
      the move-list-click-to-replay feature almost for free.
- [x] **Game history persistence** in SQLite — list of past games, results, and the
      ability to reopen and review one.
- [x] **Hints / "best move" analysis** using the same engine already wired up —
      show the top engine suggestion on demand, off by default.
- [x] **Board flip** for the second player's perspective (important once multiplayer
      exists — Phase 3 should not ship without this).
- [x] **Keyboard navigation / accessibility** basics — at minimum, don't block a
      keyboard-only user from selecting and moving pieces.
- [x] **Settings persistence** (theme, sound, difficulty, time control defaults) saved
      to SQLite or a local config file, restored on launch.
- [x] **Automated tests** for the pieces most prone to regression: move legality via
      python-chess integration, PGN round-trip, and the transport protocol's message
      handling (mock sockets). UI can stay manually tested for now.
- [x] **Packaging pass**: confirm PyInstaller build still works after all of the above
      (Qt resource bundling, Stockfish binary bundling per-OS, SVG assets included).

---

## Working notes for the agent

- Do not weaken the layered architecture (domain / chess / engine / persistence /
  services / ui) — new code (transport, worker threads, persistence additions) should
  slot into the existing layers, with UI still only talking to `services`.
- Each phase should be its own set of commits/PRs, not one giant change — Phase 1 in
  particular should ship alone and be verified before touching rendering.
- When a task says "confirm" or gives a "done" condition, treat that as the acceptance
  check before moving on — don't self-report a task complete without it holding.
# Chess Desktop — Bug Fix & Feature Directive

You are working in the `Chess` repo (PySide6 + python-chess + Stockfish UCI + SQLite,
layered architecture: domain / chess / engine / persistence / services / ui). Read
`docs/ARCHITECTURE.md` before touching anything. Do not weaken the layering — UI only
talks to `services`.

Work through the tasks **in the order given**. Each task has an explicit "done"
condition. Do not mark a task complete, move to the next one, or claim something is
fixed unless its done condition actually holds — verify it, don't assume it. If you
cannot verify a done condition (e.g. no display available for manual GUI testing),
say so explicitly instead of claiming success.

Do not batch unrelated fixes into one commit. One task = one focused commit with a
clear message referencing the bug.

---

## Task 1 — Fix silent engine-cancellation bug (P0, causes "black can't move")

**File**: `src/chess_desktop/engine/stockfish.py`, method `StockfishEngine.stop()`.

**Bug**: `_is_cancelled = True` is set unconditionally, even when no search is in
progress. `GameService.new_game()` calls `cancel_engine_search()` on every new game
regardless of whether the engine was idle. This poisons the *next* `search_best_move()`
call, which sees `_is_cancelled == True` and immediately raises `SearchCancelledError`
before ever sending `go` to Stockfish — silently, with no move produced and no error
surfaced. Net effect: the computer side (commonly Black) never plays its first move of
a new game, and the human can't move those pieces manually because
`GameService.try_move()` rejects moves when `current_player.player_type ==
PlayerType.COMPUTER`.

**Fix**: only set `_is_cancelled = True` when a search is actually active:

```python
def stop(self) -> None:
    """Send immediate UCI stop command."""
    with self._lock:
        if self._is_searching and self._process is not None:
            self._is_cancelled = True
            try:
                self._send_line("stop")
            except RuntimeError:
                pass
```

**Also audit**: `FallbackEngine.stop()` / `search_best_move()` for the same class of
bug (it currently resets `_stop_requested` unconditionally at the top of
`search_best_move()`, which is correct — confirm it stays correct, don't regress it).

**Done condition**:
- Add a unit test in `tests/unit/` that: starts a `StockfishEngine`, calls `stop()`
  while idle (no search running), then calls `search_best_move()` and asserts it
  returns a legal move instead of raising `SearchCancelledError`.
- Add a regression test that reproduces the real-world sequence: play a full game to
  completion (or a scripted N moves) → call `GameService.new_game()` → assert the
  computer side, if configured, actually produces a move (mock or use the real engine
  with a short time control in CI if Stockfish is available; otherwise use
  `FallbackEngine` plus an explicit test double for `StockfishEngine` behavior).
- Existing test suite still passes (`uv run pytest`).

---

## Task 2 — New Game dialog does not remember last-used mode (P1, UX root cause)

**File**: `src/chess_desktop/ui/dialogs/new_game_dialog.py`.

**Bug**: `NewGameDialog.__init__` always defaults to `_btn_vs_computer.setChecked(True)`
and White/human, every time the dialog is opened — including right after the user
played a "Pass & Play" local game. Combined with Task 1's bug, this silently drops
users into a broken vs-Computer game when they intended local multiplayer.

**Fix**:
- Persist the last-used game mode (`Pass & Play` vs `vs Computer`), last chosen color,
  and last difficulty via `SettingsService` (same pattern already used for theme /
  sound / thinking-delay settings — check `settings_service.py` and how it's backed by
  SQLite/config).
- On dialog open, restore these values instead of hardcoding `vs Computer` / White.
- Do not silently guess — if no prior setting exists, keep the current default
  (`vs Computer`) as the first-run default only.

**Done condition**:
- Closing and reopening `NewGameDialog` after selecting "Pass & Play" shows "Pass &
  Play" pre-selected on the next open, in the same session and after app restart.
- Add/extend a unit or widget test asserting the persisted mode round-trips through
  `SettingsService`.

---

## Task 3 — Engine calls are not actually off the GUI thread (P1)

**Files**: `src/chess_desktop/services/game_service.py` (`_trigger_engine_if_needed`,
`request_hint`, `restart_engine`), `src/chess_desktop/services/engine_worker.py`.

**Bug**: `EngineWorker.moveToThread(self._thread)` is called, but
`request_move(...)` and `request_hint(...)` are invoked as **direct Python method
calls** from the GUI thread (e.g. `worker.request_move(state.fen, moves_uci,
self._difficulty)`), not through a signal/slot connection or
`QMetaObject.invokeMethod`. A direct method call always executes synchronously on the
*caller's* thread regardless of `moveToThread()` — only signal-slot dispatch (or
explicit `invokeMethod` with `Qt.QueuedConnection`) actually marshals execution onto
the worker's thread. This means Stockfish's blocking subprocess I/O in
`search_best_move()` is very likely still running on the GUI thread, contradicting the
checked-off items in `docs/FIX.md` Phase 1 ("player can click around... no freeze").

**Fix**:
- Add request-side signals on `GameService` (or a thin dispatcher), e.g.
  `request_move_signal = Signal(str, list, object)`, connected to
  `worker.request_move` with `Qt.ConnectionType.QueuedConnection` explicitly (don't
  rely on `AutoConnection` inference — be explicit given the cross-thread requirement).
- Replace every direct `worker.request_move(...)` / `worker.request_hint(...)` call
  site with `self.request_move_signal.emit(...)` / equivalent.
- Confirm `EngineWorker` methods keep their `@Slot(...)` decorators with matching
  signatures so the queued connection can marshal arguments correctly.

**Done condition**:
- Provide before/after evidence: a test or documented manual repro showing the GUI
  event loop remains responsive (e.g. a `QTimer` tick counter that keeps incrementing,
  or processing `QApplication.processEvents()` in a test harness) while a
  long-movetime search (e.g. `movetime 3000`) is in flight. State plainly if this
  can't be verified headlessly in this environment, and what manual steps confirm it.
- No behavior regression: engine still fully responds, hints still work, cancel still
  works (this must not reintroduce Task 1's bug — re-run Task 1's tests after this
  change).

---

## Task 4 — Chess.com-style post-game analysis

Build a real game-review feature, not a cosmetic addition.

**Scope**:
1. **Engine layer**: extend `ChessEngine`/`StockfishEngine`/`FallbackEngine` so a
   search can also return a centipawn (or mate-distance) evaluation, not just a UCI
   move — parse Stockfish's `info depth N score cp X` / `score mate Y` lines. Keep the
   existing `search_best_move` return type stable; add a new method
   (`evaluate_position` or similar) rather than breaking the current UCI move contract.
2. **New `AnalysisService`** (in `services/`): given a completed `Game`'s full move
   list, for each ply, evaluate the position before and after the move at a fixed
   depth (e.g. depth 14-16, time-boxed), compute centipawn loss relative to the
   engine's top choice, and classify each move using standard buckets:
   - Best/Brilliant: 0 cp loss (or a move matching engine's top choice)
   - Excellent: <10 cp loss
   - Good: <50 cp loss
   - Inaccuracy: 50-100 cp loss
   - Mistake: 100-300 cp loss
   - Blunder: 300+ cp loss
   - Special-case mate-in-N swings (a move that turns a forced mate for you into a
     lost position is always a Blunder regardless of raw cp delta).
   Run this off the GUI thread using the same `EngineWorker` infrastructure — do not
   introduce a second instance of Task 3's bug.
3. **Persistence**: add an `analysis` table (or column) keyed by `game_id` in
   `persistence/models.py` / `repositories.py` so analysis is computed once and cached,
   not recomputed every time a saved game is reopened.
4. **UI**: annotate `history_panel.py`'s move list with a classification badge/icon
   per move, and add an evaluation bar / summary (best move count, blunder count,
   accuracy %) — model this on the existing move-list and clock widgets rather than
   inventing a new visual language. Clicking a move still jumps the board to that
   position (existing behavior) and should now also show what the engine's top
   alternative was, in san notation, next to the played move.
5. Trigger analysis on demand from the `GameOverDialog` ("Review Game" button, in
   addition to the existing "Review Board" / "New Game") and from the saved-games list
   for any completed game — not automatically for every game, since it's expensive.

**Done condition**:
- Unit tests for the classification thresholds (pure function, no Qt/engine
  dependency — test it in isolation with synthetic cp-loss inputs).
- Integration test that runs analysis on a short scripted game and asserts each move
  gets a classification and the cache round-trips through SQLite.
- Confirm analysis runs without blocking the GUI thread (same verification approach as
  Task 3).

---

## Cross-cutting requirements (apply to all tasks)

- Every fix ships with a test that fails on the pre-fix code and passes after. If you
  cannot write a test for something (e.g. genuine GUI-only behavior), say so explicitly
  and describe the manual verification steps instead of skipping silently.
- Do not touch unrelated code while in a task's diff. If you spot something else wrong
  while working, note it at the end of your summary instead of fixing it inline.
- Run the full test suite (`uv run pytest`) after each task and report pass/fail —
  don't just report the new test's result.
- If a "done condition" above can't actually be met as written (e.g. CI has no
  Stockfish binary), say so and propose the closest achievable equivalent — don't
  quietly weaken the check and claim it was satisfied.
- At the end, produce a short changelog mapping each task to its commit(s) and which
  done conditions were verified vs. which need manual confirmation from me.
# Troubleshooting

## Stockfish

**"The chess engine could not be started."**
The app couldn't find or launch a Stockfish binary. Check:
1. Is Stockfish installed? `stockfish --help` (Linux/macOS) or run the `.exe` directly (Windows) to confirm it starts.
2. Is it on `PATH`, or does `ENGINE_PATH` in your `.env` / Settings point at the correct binary?
3. Do you have execute permission on the binary (Linux: `chmod +x`)?

If it's genuinely missing, Player vs Computer is unavailable but local multiplayer still works fully — the app should degrade gracefully, not crash.

**Engine takes a long time / UI feels unresponsive during computer moves**
This should never happen — engine search runs on a worker thread (see `docs/ARCHITECTURE.md`). If the UI is freezing during Stockfish's turn, that's a regression: something has called the engine synchronously on the main thread. Treat it as a P0 bug, not a performance tuning issue.

**Engine returns illegal or unexpected moves**
Confirm the position sent to Stockfish (FEN) matches the actual board state — this is almost always a bug in how the position is serialized before being sent over UCI, not in Stockfish itself.

**Engine fails to terminate / zombie process on exit**
The engine process should be terminated with a `quit` command and joined on close. If you notice orphaned processes, verify `EngineService.shutdown()` is wired to `QApplication.aboutToQuit`.

## Save / Load

**Saved game won't load / app crashes opening a save**
Check `persistence/database.py` schema version against the save file. If the schema changed since the game was saved, you need a migration — see `docs/DEVELOPMENT.md#database`. Don't silently drop or "repair" a user's save file; fail loudly with a clear message and preserve the original file.

**Undo after loading a saved game behaves oddly**
Make sure the loaded board is rebuilt through `python-chess`'s board stack (from the stored move list or FEN), not reconstructed piece-by-piece manually — partial reconstruction is a common source of lost castling rights / en passant state after load.

## PGN / FEN

**Import fails on a PGN from lichess/chess.com**
`python-chess`'s PGN parser is strict about some real-world variations (extra headers, non-standard annotations). Log the parser error and show the user a clear "this file couldn't be read" message rather than a traceback — don't attempt to hand-patch the PGN text.

**Invalid FEN crashes position load**
Validate with `python-chess`'s own FEN validation before constructing a board from it; treat a failed validation as user input error, not an internal exception.

## UI & Audio

**No sound plays on Linux / GStreamer warning in console**
PySide6 `QSoundEffect` depends on GStreamer plugins. Run:
`sudo apt install libpulse-dev gstreamer1.0-plugins-good gstreamer1.0-pulseaudio`
If plugins are absent, `SoundService` disables audio gracefully without crashing. Check `Settings -> Sound` to confirm sound is enabled.

**Pieces appear blurry or pixelated on 4K / High-DPI screens**
Ensure piece graphics are rendered via `QSvgRenderer` on `QPainter` rather than converted to fixed-size bitmaps. Ensure `QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)` is called before creating `QApplication`.

**Legal-move highlights don't match what's actually legal**
This means UI state has drifted from the authoritative `GameState` — see the state management rule in `docs/ARCHITECTURE.md`. The fix is almost always "the UI computed something itself instead of asking `chess/move_service.py`," not a rendering bug.

**Board doesn't reflect the current position after undo/redo/navigation**
Confirm the board widget re-renders directly from `GameState.board` rather than incrementally patching squares — incremental patching is fragile across undo/navigate and easy to get subtly wrong.

## Packaging

**Assets (pieces/icons/sounds) missing in the packaged build but present when running from source**
Almost always a relative-path assumption that breaks once PyInstaller freezes the app. Ensure assets are compiled into `resources_rc.py` via `scripts/compile_resources.py` and accessed with `:/` URLs. See `docs/DEVELOPMENT.md#building-a-distributable`.

**App won't launch on a clean machine (no dev Python installed)**
Test the packaged executable on an actual clean VM before shipping — a machine with your dev Python/venv on `PATH` will mask missing bundled dependencies.

## Filing a bug

Include: OS + version, app version, steps to reproduce, the FEN or PGN of the position if chess-logic related, and relevant log lines (`WARNING`+). Every confirmed bug should get a regression test — see the pattern under `tests/unit/` once fixed, e.g. `test_undo_preserves_castling_rights()`.
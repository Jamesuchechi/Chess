# Contributing to Chess Desktop

Thank you for your interest in contributing to **Chess Desktop**! We welcome bug reports, feature suggestions, documentation improvements, and pull requests.

---

## Code of Conduct

All contributors and maintainers are expected to adhere to our [Code of Conduct](CODE_OF_CONDUCT.md).

---

## Architectural Guardrails

Before writing code, please review [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

The critical rules to maintain:
1. **Layer Separation**: The UI (`ui/`) must never directly interact with `python-chess` or Stockfish processes. All interactions must pass through the `services/` layer (`GameService`, `SaveService`, `SettingsService`).
2. **Authoritative State**: Core game rules, check, checkmate, stalemate, and move legality are delegated to `python-chess`. We never reimplement chess logic in the UI.
3. **Responsive UI**: Long-running operations (Stockfish engine calculations, audio, heavy disk I/O) must run on worker threads or asynchronously without ever freezing Qt's main thread.
4. **Offline First**: No network calls, user accounts, or external telemetry dependencies.

---

## Development Setup

### 1. Prerequisites
- Python 3.11 or higher
- [`uv`](https://docs.astral.sh/uv/) for lightning-fast environment and package management
- Optional: `stockfish` installed on your system (`sudo apt install stockfish` on Debian/Ubuntu)

### 2. Fork and Clone
```bash
git clone https://github.com/<your-username>/Chess.git
cd Chess
```

### 3. Sync Environment
```bash
uv sync --all-extras --dev
```

### 4. Run the Application Locally
```bash
uv run python -m chess_desktop.main
```

---

## Quality Checks & Testing

Before submitting a Pull Request, ensure that all automated checks pass locally:

### 1. Test Suite
```bash
uv run pytest
```
All tests must pass. When adding new features or fixing bugs, include accompanying unit or UI tests.

### 2. Code Style & Formatting
```bash
uv run ruff format --check .
uv run ruff check .
```
To automatically apply formatting and fixes:
```bash
uv run ruff format .
uv run ruff check --fix .
```

### 3. Static Type Checking
```bash
uv run mypy src/
```
The codebase enforces strict type safety without warnings or untyped defs.

---

## Pull Request Guidelines

1. **Branch Naming**: Use descriptive branch names (e.g. `feat/puzzle-mode`, `fix/clock-increment`, `docs/setup-guide`).
2. **Commit Messages**: Write concise, conventional commit messages (e.g. `feat: add opening recognition module`, `fix: handle edge case in draw offers`).
3. **Atomic Changes**: Keep PRs focused on a single change or feature whenever possible.
4. **CI Green**: All GitHub Actions CI checks must pass before merging.

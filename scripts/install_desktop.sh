#!/usr/bin/env bash
# ==============================================================================
# Chess Desktop — Ubuntu / Linux Desktop Installer
# ==============================================================================
# Installs Chess Desktop into the user's desktop environment:
#   - Launcher binary: ~/.local/bin/chess-desktop
#   - Application icon: ~/.local/share/icons/hicolor/scalable/apps/chess-desktop.svg
#   - Desktop entry:   ~/.local/share/applications/chess-desktop.desktop
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

BIN_DIR="${HOME}/.local/bin"
APP_DIR="${HOME}/.local/share/applications"
ICON_DIR="${HOME}/.local/share/icons/hicolor/scalable/apps"
FALLBACK_ICON_DIR="${HOME}/.local/share/icons"

DESKTOP_FILE="${APP_DIR}/chess-desktop.desktop"
LAUNCHER_FILE="${BIN_DIR}/chess-desktop"
ICON_FILE="${ICON_DIR}/chess-desktop.svg"
FALLBACK_ICON_FILE="${FALLBACK_ICON_DIR}/chess-desktop.svg"
SOURCE_ICON="${PROJECT_ROOT}/assets/icons/chess-desktop.svg"

uninstall() {
    echo "Uninstalling Chess Desktop..."
    rm -f "${DESKTOP_FILE}"
    rm -f "${LAUNCHER_FILE}"
    rm -f "${ICON_FILE}"
    rm -f "${FALLBACK_ICON_FILE}"
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "${APP_DIR}" 2>/dev/null || true
    fi
    echo "Chess Desktop uninstalled successfully."
    exit 0
}

if [[ "${1:-}" == "--uninstall" || "${1:-}" == "-u" ]]; then
    uninstall
fi

echo "======================================================"
echo "  Installing Chess Desktop for $(whoami)"
echo "  Project Root: ${PROJECT_ROOT}"
echo "======================================================"

# 0. Clean old python caches and rebuild Qt resources
echo "Clearing Python bytecode cache..."
find "${PROJECT_ROOT}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
rm -rf "${PROJECT_ROOT}/.pytest_cache" "${PROJECT_ROOT}/.mypy_cache" 2>/dev/null || true

echo "Recompiling Qt resources..."
if command -v uv >/dev/null 2>&1; then
    uv run python "${SCRIPT_DIR}/compile_resources.py" || true
elif [ -x "${PROJECT_ROOT}/.venv/bin/python" ]; then
    "${PROJECT_ROOT}/.venv/bin/python" "${SCRIPT_DIR}/compile_resources.py" || true
elif command -v python3 >/dev/null 2>&1; then
    python3 "${SCRIPT_DIR}/compile_resources.py" || true
fi

# 1. Create target directories
mkdir -p "${BIN_DIR}"
mkdir -p "${APP_DIR}"
mkdir -p "${ICON_DIR}"
mkdir -p "${FALLBACK_ICON_DIR}"

# 2. Install application icon
if [[ -f "${SOURCE_ICON}" ]]; then
    cp "${SOURCE_ICON}" "${ICON_FILE}"
    cp "${SOURCE_ICON}" "${FALLBACK_ICON_FILE}"
    echo "✔ Installed icon: ${ICON_FILE}"
else
    echo "⚠ Warning: Icon source ${SOURCE_ICON} not found, skipping icon install."
fi

# 3. Create launcher script
VENV_PYTHON="${PROJECT_ROOT}/.venv/bin/python"

cat <<EOF > "${LAUNCHER_FILE}"
#!/usr/bin/env bash
set -e

PROJECT_DIR="${PROJECT_ROOT}"
cd "\${PROJECT_DIR}"
export PYTHONPATH="\${PROJECT_DIR}/src:\${PYTHONPATH:-}"

if [ -x "${VENV_PYTHON}" ]; then
    exec "${VENV_PYTHON}" -m chess_desktop.main "\$@"
elif command -v uv >/dev/null 2>&1; then
    exec uv run python -m chess_desktop.main "\$@"
elif command -v python3 >/dev/null 2>&1; then
    exec python3 -m chess_desktop.main "\$@"
else
    echo "Error: Python interpreter not found." >&2
    exit 1
fi
EOF

chmod +x "${LAUNCHER_FILE}"
echo "✔ Created launcher: ${LAUNCHER_FILE}"

# 4. Create .desktop file
cat <<EOF > "${DESKTOP_FILE}"
[Desktop Entry]
Version=1.0
Type=Application
Name=Chess Desktop
GenericName=Chess Game
Comment=Polished offline-first desktop chess with Stockfish AI
Exec=${LAUNCHER_FILE}
Icon=chess-desktop
Terminal=false
Categories=Game;BoardGame;
Keywords=chess;game;board;stockfish;
StartupWMClass=chess-desktop
StartupNotify=true
EOF

chmod +x "${DESKTOP_FILE}"
echo "✔ Created desktop entry: ${DESKTOP_FILE}"

# 5. Refresh desktop caches
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "${APP_DIR}" 2>/dev/null || true
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "${HOME}/.local/share/icons/hicolor" 2>/dev/null || true
fi

echo ""
echo "======================================================"
echo "✔ Chess Desktop is now installed!"
echo ""
echo "You can launch it by:"
echo "  1. Searching 'Chess Desktop' in Ubuntu Application Grid"
echo "  2. Running: ~/.local/bin/chess-desktop"
echo "  3. Running: chess-desktop (if ~/.local/bin is in PATH)"
echo ""
echo "To uninstall anytime, run:"
echo "  ${SCRIPT_DIR}/install_desktop.sh --uninstall"
echo "======================================================"

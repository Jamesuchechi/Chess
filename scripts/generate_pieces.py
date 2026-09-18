"""Generate standard Cburnett piece SVGs using python-chess and register in resources.qrc."""

import sys
from pathlib import Path

import chess
import chess.svg

ROOT_DIR = Path(__file__).resolve().parent.parent
PIECES_DIR = ROOT_DIR / "assets" / "pieces"
QRC_FILE = ROOT_DIR / "assets" / "resources.qrc"

PIECES = [
    (chess.Piece(chess.PAWN, chess.WHITE), "wP.svg"),
    (chess.Piece(chess.KNIGHT, chess.WHITE), "wN.svg"),
    (chess.Piece(chess.BISHOP, chess.WHITE), "wB.svg"),
    (chess.Piece(chess.ROOK, chess.WHITE), "wR.svg"),
    (chess.Piece(chess.QUEEN, chess.WHITE), "wQ.svg"),
    (chess.Piece(chess.KING, chess.WHITE), "wK.svg"),
    (chess.Piece(chess.PAWN, chess.BLACK), "bP.svg"),
    (chess.Piece(chess.KNIGHT, chess.BLACK), "bN.svg"),
    (chess.Piece(chess.BISHOP, chess.BLACK), "bB.svg"),
    (chess.Piece(chess.ROOK, chess.BLACK), "bR.svg"),
    (chess.Piece(chess.QUEEN, chess.BLACK), "bQ.svg"),
    (chess.Piece(chess.KING, chess.BLACK), "bK.svg"),
]


def generate_pieces() -> int:
    """Generate SVG piece assets and update resources.qrc."""
    PIECES_DIR.mkdir(parents=True, exist_ok=True)

    file_entries: list[str] = []
    for piece, filename in PIECES:
        svg_content = chess.svg.piece(piece, size=120)
        svg_path = PIECES_DIR / filename
        with open(svg_path, "w", encoding="utf-8") as f:
            f.write(svg_content)
        file_entries.append(f"        <file>pieces/{filename}</file>")
        print(f"Generated {filename}")

    # Write updated resources.qrc
    qrc_content = (
        '<!DOCTYPE RCC>\n<RCC version="1.0">\n    <qresource prefix="/">\n'
        + "\n".join(file_entries)
        + "\n    </qresource>\n</RCC>\n"
    )
    with open(QRC_FILE, "w", encoding="utf-8") as f:
        f.write(qrc_content)
    print(f"Updated {QRC_FILE}")

    return 0


if __name__ == "__main__":
    sys.exit(generate_pieces())

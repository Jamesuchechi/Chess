"""Top-level entrypoint module forwarding to chess_desktop.app.main."""

import sys

from chess_desktop.app.main import main

if __name__ == "__main__":
    sys.exit(main())

"""Module entry point so ``python -m tantra.cli`` runs the CLI (ex 0004 closure)."""

from __future__ import annotations

import sys

from tantra.cli import main

if __name__ == "__main__":
    sys.exit(main())

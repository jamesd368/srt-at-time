"""Lets the package run as `python -m srtat`, useful from a source checkout
before the `srtat` console script is on PATH."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())

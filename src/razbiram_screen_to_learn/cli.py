"""Command-line entry point.

Only commands that are actually implemented are registered here. The full planned surface is in
``docs/architecture/REPOSITORY_BLUEPRINT.md``; it is a plan, not a promise that the code exists.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from razbiram_screen_to_learn import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="razbiram-screen-to-learn",
        description="Turn learning screens into reviewable, evidence-backed razbiram learncards.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    parser.parse_args(argv)
    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

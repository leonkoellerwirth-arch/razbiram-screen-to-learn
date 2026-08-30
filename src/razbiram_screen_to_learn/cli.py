"""Command-line entry point.

Only commands that are actually implemented are registered here. The full planned surface is in
``docs/architecture/REPOSITORY_BLUEPRINT.md``; it is a plan, not a promise that the code exists.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from razbiram_screen_to_learn import __version__
from razbiram_screen_to_learn.contracts import dump_document
from razbiram_screen_to_learn.pipeline import LIVE_CAPABILITIES, process_markup
from razbiram_screen_to_learn.quizlet import process_quizlet_payloads


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def _capabilities(extra: Sequence[str] | None) -> set[str]:
    return set(LIVE_CAPABILITIES) | set(extra or ())


def cmd_extract(args: argparse.Namespace) -> int:
    result = process_markup(_read(args.input), capabilities=_capabilities(args.capability))
    print(json.dumps(dump_document(result.document), indent=2))
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    result = process_markup(_read(args.input), capabilities=_capabilities(args.capability))
    if not result.issues:
        print("No issues. Every extracted card is internally consistent and exportable.")
        return 0
    for issue in result.issues:
        print(issue)
    blocking = sum(1 for issue in result.issues if issue.blocking)
    print(f"\n{blocking} blocking, {len(result.issues) - blocking} warning(s).", file=sys.stderr)
    return 1 if blocking else 0


def cmd_export(args: argparse.Namespace) -> int:
    result = process_markup(_read(args.input), capabilities=_capabilities(args.capability))
    for blocked in result.export.blocked:
        print(f"BLOCKED {blocked.card_id} ({blocked.family}): {blocked.reason}", file=sys.stderr)
    if result.export.deck is None:
        print("No deck written: every card was blocked.", file=sys.stderr)
        return 1
    payload = json.dumps(result.export.deck, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
        print(f"Wrote {args.output} ({result.export.deck['meta']['cardCount']} card(s)).")
    else:
        print(payload)
    return 0


def cmd_quizlet_import(args: argparse.Namespace) -> int:
    result = process_quizlet_payloads(
        _read(args.set_payload),
        api_payloads=[_read(path) for path in args.api_payload],
        origin=args.origin,
        path=args.source_path,
        term_locale=args.term_locale,
        definition_locale=args.definition_locale,
        capabilities=_capabilities(args.capability),
    )
    for issue in result.issues:
        if issue.blocking:
            print(issue, file=sys.stderr)
    if result.export.deck is None:
        print("No deck written: every card was blocked.", file=sys.stderr)
        return 1
    payload = json.dumps(result.export.deck, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
        print(f"Wrote {args.output} ({result.export.deck['meta']['cardCount']} card(s)).")
    else:
        print(payload)
    return 0


def cmd_studio(args: argparse.Namespace) -> int:
    from razbiram_screen_to_learn.studio.server import serve

    return serve(host=args.host, port=args.port, open_browser=not args.no_open)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="razbiram-screen-to-learn",
        description="Turn learning screens into reviewable, evidence-backed razbiram learncards.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command")

    def add_input_command(name: str, help_text: str, handler):
        command = sub.add_parser(name, help=help_text)
        command.add_argument("input", help="an HTML file to read")
        command.add_argument(
            "--capability",
            action="append",
            metavar="ID",
            help="declare an extra target capability, e.g. mcq.multiple-select.v1 (repeatable)",
        )
        command.set_defaults(handler=handler)
        return command

    add_input_command("extract", "extract Capture IR and print it", cmd_extract)
    add_input_command("validate", "report evidence, schema and capability issues", cmd_validate)
    export = add_input_command("export", "project to the target deck profile", cmd_export)
    export.add_argument("-o", "--output", help="write the deck here instead of stdout")

    quizlet = sub.add_parser(
        "quizlet-import",
        help="convert captured Quizlet set/API JSON payloads into the target deck profile",
    )
    quizlet.add_argument("set_payload", help="Quizlet set HTML, __NEXT_DATA__, or pageProps JSON")
    quizlet.add_argument(
        "--api-payload",
        action="append",
        default=[],
        metavar="PATH",
        help="captured /webapi/3.4/studiable-item-documents JSON payload (repeatable)",
    )
    quizlet.add_argument("-o", "--output", help="write the deck here instead of stdout")
    quizlet.add_argument("--origin", default="https://quizlet.com")
    quizlet.add_argument("--source-path", default="/quizlet-capture")
    quizlet.add_argument("--term-locale", default="en")
    quizlet.add_argument("--definition-locale", default="en")
    quizlet.add_argument(
        "--capability",
        action="append",
        metavar="ID",
        help="declare an extra target capability (repeatable)",
    )
    quizlet.set_defaults(handler=cmd_quizlet_import)

    studio = sub.add_parser("studio", help="serve the local drop-in studio")
    studio.add_argument("--host", default="127.0.0.1", help="loopback only by default")
    studio.add_argument("--port", type=int, default=8765)
    studio.add_argument("--no-open", action="store_true", help="do not open a browser")
    studio.set_defaults(handler=cmd_studio)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 0
    return handler(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

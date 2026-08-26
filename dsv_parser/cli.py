"""Command-line interface.

Three subcommands, each doing one thing to one file:

``parse``
    Read a DSV file and write the document as JSON — the workhorse. Reads stdin
    when the path is ``-``, so it composes in a shell pipeline.
``check``
    Read a DSV file and report only the diagnostics, exiting non-zero when data
    was lost. Built for CI and batch validation.
``spec``
    Print the element table this parser implements, generated from the table
    itself.

``serve`` is deliberately absent: the HTTP surface is an optional extra, and
running it is ``uvicorn dsv_parser.api:app`` — no wrapper worth maintaining.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .core.parser import ParseResult, parse_bytes
from .spec.render import describe_registry, render_text

EXIT_OK = 0
EXIT_DATA_LOSS = 1
EXIT_USAGE = 2


def _read_input(path: str) -> bytes:
    """Read the file to parse, from disk or stdin.

    Args:
        path: A filesystem path, or ``-`` for stdin.

    Returns:
        The raw bytes.
    """
    if path == "-":
        return sys.stdin.buffer.read()
    return Path(path).read_bytes()


def _write_json(payload: Any, destination: str | None, *, indent: int | None) -> None:
    """Write a JSON payload to a file or stdout.

    Args:
        payload: Anything :func:`json.dumps` accepts.
        destination: Output path, or ``None`` for stdout.
        indent: Indentation, or ``None`` for the compact single-line form.
    """
    text = json.dumps(payload, ensure_ascii=False, indent=indent, default=str)
    if destination is None:
        sys.stdout.write(text + "\n")
    else:
        Path(destination).write_text(text + "\n", encoding="utf-8")


def _report(result: ParseResult, stream: Any) -> None:
    """Print every diagnostic of a parse run.

    Args:
        result: The parse result.
        stream: Where to write — stderr for ``parse``, stdout for ``check``.
    """
    for entry in result.diagnostics.entries:
        print(entry.render(), file=stream)


def cmd_parse(args: argparse.Namespace) -> int:
    """Parse a file and emit the document as JSON.

    Args:
        args: Parsed CLI arguments.

    Returns:
        ``0`` on a clean parse, ``1`` when data was lost and ``--strict`` is set.
    """
    result = parse_bytes(_read_input(args.path))
    payload: Any
    if args.summary:
        payload = {
            "file_type": result.document.file_type,
            "version": result.document.version,
            "encoding": result.source.encoding,
            "zipped": result.source.zipped,
            "elements": result.document.element_counts(),
            "errors": len(result.diagnostics.errors),
            "warnings": len(result.diagnostics.warnings),
        }
    else:
        payload = result.document.model_dump(mode="json", exclude_none=args.exclude_none)
        if args.diagnostics:
            payload = {
                "document": payload,
                "diagnostics": [
                    entry.model_dump(mode="json", exclude_none=True)
                    for entry in result.diagnostics.entries
                ],
            }
    _write_json(payload, args.output, indent=None if args.compact else 2)
    if not args.quiet:
        _report(result, sys.stderr)
    return EXIT_DATA_LOSS if args.strict and not result.clean else EXIT_OK


def cmd_check(args: argparse.Namespace) -> int:
    """Validate a file and report its diagnostics.

    Args:
        args: Parsed CLI arguments.

    Returns:
        ``0`` when no data was lost, ``1`` otherwise.
    """
    result = parse_bytes(_read_input(args.path))
    _report(result, sys.stdout)
    errors = len(result.diagnostics.errors)
    warnings = len(result.diagnostics.warnings)
    counts = result.document.element_counts()
    total = sum(counts.values())
    file_type = result.document.file_type
    print(
        f"{args.path}: {file_type.value if file_type else 'unknown list kind'} "
        f"format {result.document.version or '?'}, {total} elements, "
        f"{errors} error(s), {warnings} warning(s)"
    )
    return EXIT_DATA_LOSS if errors else EXIT_OK


def cmd_spec(args: argparse.Namespace) -> int:
    """Print the element table this parser implements.

    Args:
        args: Parsed CLI arguments.

    Returns:
        Always ``0``.
    """
    if args.json:
        _write_json(describe_registry(), args.output, indent=2)
    elif args.output is None:
        sys.stdout.write(render_text())
    else:
        Path(args.output).write_text(render_text(), encoding="utf-8")
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser.

    Returns:
        The configured parser, with one subparser per subcommand.
    """
    parser = argparse.ArgumentParser(
        prog="dsv-parser",
        description="Parse DSV swim-meet interchange files (Format 5–8) into a typed schema.",
    )
    parser.set_defaults(handler=None)
    subcommands = parser.add_subparsers(dest="command", metavar="COMMAND")

    parse_cmd = subcommands.add_parser(
        "parse", help="Parse a DSV file and write the document as JSON."
    )
    parse_cmd.add_argument("path", help="Path to the DSV file, or '-' for stdin.")
    parse_cmd.add_argument("-o", "--output", help="Write to this path instead of stdout.")
    parse_cmd.add_argument(
        "--compact", action="store_true", help="Emit single-line JSON instead of indented."
    )
    parse_cmd.add_argument(
        "--exclude-none",
        action="store_true",
        help="Omit null fields — much smaller output, at the cost of a variable shape.",
    )
    parse_cmd.add_argument(
        "--diagnostics",
        action="store_true",
        help="Wrap the document together with the diagnostics in one envelope.",
    )
    parse_cmd.add_argument(
        "--summary",
        action="store_true",
        help="Emit only element counts and the header, not the document.",
    )
    parse_cmd.add_argument(
        "-q", "--quiet", action="store_true", help="Do not print diagnostics to stderr."
    )
    parse_cmd.add_argument(
        "--strict", action="store_true", help="Exit non-zero when any data was lost."
    )
    parse_cmd.set_defaults(handler=cmd_parse)

    check_cmd = subcommands.add_parser(
        "check", help="Validate a DSV file and report its diagnostics."
    )
    check_cmd.add_argument("path", help="Path to the DSV file, or '-' for stdin.")
    check_cmd.set_defaults(handler=cmd_check)

    spec_cmd = subcommands.add_parser(
        "spec", help="Print the element table this parser implements."
    )
    spec_cmd.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    spec_cmd.add_argument("-o", "--output", help="Write to this path instead of stdout.")
    spec_cmd.set_defaults(handler=cmd_spec)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI.

    Args:
        argv: Argument vector, defaulting to :data:`sys.argv`.

    Returns:
        The process exit code.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.handler is None:
        parser.print_help()
        return EXIT_USAGE
    return int(args.handler(args))

"""Command-line interface: `amiauia files|photos|capacity|all PATH`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__, capacity, files_analysis, photo_analysis, report
from .findings import Finding
from .scanner import scan


def _progress(i: int, n: int) -> None:
    if sys.stderr.isatty():
        print(f"\r  Analyzing photos {i}/{n}", end="" if i < n else "\n", file=sys.stderr)


def _output(findings: list[Finding], args: argparse.Namespace) -> None:
    print(report.console(findings))
    if args.json:
        report.to_json(findings, args.json)
        print(f"\nJSON report saved to {args.json}")
    if args.md:
        report.to_markdown(findings, args.md)
        print(f"Markdown report saved to {args.md}")


def cmd_files(args: argparse.Namespace) -> list[Finding]:
    files = scan(args.path, args.hidden)
    print(f"Scanned {len(files)} files in {args.path}", file=sys.stderr)
    return files_analysis.analyze(files)


def cmd_photos(args: argparse.Namespace) -> list[Finding]:
    files = scan(args.path, args.hidden)
    findings, keepers, _ = photo_analysis.analyze(files, _progress)
    if getattr(args, "selection", None):
        Path(args.selection).write_text("\n".join(p.path for p in keepers), encoding="utf-8")
        print(f"Keeper list saved to {args.selection}", file=sys.stderr)
    return findings


def cmd_capacity(args: argparse.Namespace) -> list[Finding]:
    data = capacity.record(args.path)
    key = str(Path(args.path).resolve())
    f = capacity.forecast(data[key], args.path)
    if f is None:
        n = len(data[key])
        print(f"Measurement recorded ({n}/3). Run this command daily: with 3 or more "
              "measurements AMIAUIA will predict when the disk will be full.", file=sys.stderr)
        return []
    return [f]


def cmd_all(args: argparse.Namespace) -> list[Finding]:
    return cmd_files(args) + cmd_photos(args) + cmd_capacity(args)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="amiauia",
        description="AMIAUIA: a statistical AI that analyzes your files and photos and gives you logical solutions.",
    )
    p.add_argument("--version", action="version", version=f"amiauia {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    def common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("path", help="Folder or drive to analyze")
        sp.add_argument("--json", metavar="FILE", help="Save the report as JSON")
        sp.add_argument("--md", metavar="FILE", help="Save the report as Markdown")
        sp.add_argument("--hidden", action="store_true", help="Include hidden files and folders")

    sp = sub.add_parser("files", help="Duplicates, space usage, stale files and ransomware alert")
    common(sp)
    sp.set_defaults(func=cmd_files)

    sp = sub.add_parser("photos", help="Photo culling, bursts, exposure and EXIF technical audit")
    common(sp)
    sp.add_argument("--selection", metavar="FILE", help="Save the list of keeper photos")
    sp.set_defaults(func=cmd_photos)

    sp = sub.add_parser("capacity", help="Record disk usage and predict when it will be full")
    common(sp)
    sp.set_defaults(func=cmd_capacity)

    sp = sub.add_parser("all", help="Run every analysis")
    common(sp)
    sp.add_argument("--selection", metavar="FILE", help="Save the list of keeper photos")
    sp.set_defaults(func=cmd_all)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not Path(args.path).exists():
        print(f"Error: path does not exist: {args.path}", file=sys.stderr)
        return 2
    _output(args.func(args), args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

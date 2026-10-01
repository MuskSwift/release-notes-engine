"""argparse CLI for Release Notes Engine v0."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

from .generate import generate, strip_leading_preamble, strip_wrapping_fences
from .validate import missing_headings


def slugify(notes: str, max_len: int = 48) -> str:
    """ASCII-ish slug from notes text: keep letters, digits, CJK; spaces become hyphens."""
    first_line = next((ln.strip() for ln in notes.splitlines() if ln.strip()), notes)
    text = first_line.strip().lower()
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^\w\u4e00-\u9fff\-]+", "", text, flags=re.UNICODE)
    text = re.sub(r"-{2,}", "-", text).strip("-._")
    if not text:
        text = hashlib.sha1(notes.encode("utf-8")).hexdigest()[:10]
    return text[:max_len]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="release-notes-engine",
        description=(
            "Release Notes Engine v0 — turn change notes (plus optional taboo) "
            "into a 5-heading Chinese changelog for end users."
        ),
    )
    parser.add_argument("--notes", help="Change notes as a string")
    parser.add_argument(
        "--notes-file",
        metavar="PATH",
        help="Path to a file containing change notes",
    )
    parser.add_argument("--taboo", help="Taboo / forbidden content as a string")
    parser.add_argument(
        "--taboo-file",
        metavar="PATH",
        help="Path to a file containing taboo / forbidden content",
    )
    parser.add_argument(
        "--out",
        help="Output markdown path (default: ./out/<slug>-release-notes.md)",
    )
    return parser.parse_args(argv)


def _read_text(path: str) -> str:
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"file not found: {path}")
    return file_path.read_text(encoding="utf-8")


def _join_sources(inline: str | None, file_path: str | None) -> str:
    parts: list[str] = []
    if inline and inline.strip():
        parts.append(inline.strip())
    if file_path:
        parts.append(_read_text(file_path).strip())
    return "\n\n".join(p for p in parts if p)


def resolve_inputs(args: argparse.Namespace) -> tuple[str, str]:
    notes = _join_sources(args.notes, args.notes_file)
    if not notes:
        raise ValueError("at least one of --notes or --notes-file is required")
    taboo = _join_sources(args.taboo, args.taboo_file)
    return notes, taboo


def resolve_out(out_arg: str | None, notes: str) -> Path:
    if out_arg:
        return Path(out_arg)
    return Path("out") / f"{slugify(notes)}-release-notes.md"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out_path: Path | None = None
    try:
        notes, taboo = resolve_inputs(args)
        markdown = strip_wrapping_fences(generate(notes, taboo))
        markdown = strip_leading_preamble(markdown)
        if not markdown.strip():
            raise RuntimeError("generation produced empty markdown")

        out_path = resolve_out(args.out, notes)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(markdown.rstrip() + "\n", encoding="utf-8")

        missing = missing_headings(markdown)
        if missing:
            try:
                out_path.unlink()
            except OSError:
                pass
            print("validation failed; missing headings:", file=sys.stderr)
            for heading in missing:
                print(f"  {heading}", file=sys.stderr)
            return 1

        print(str(out_path))
        return 0
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

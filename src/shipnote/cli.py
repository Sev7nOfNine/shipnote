"""Command-line interface for shipnote."""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from . import __version__
from .core import GitError, get_commits, render_markdown, resolve_range


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="shipnote",
        description="Generate clean, grouped release notes from your git history.",
    )
    parser.add_argument(
        "--from",
        dest="frm",
        metavar="REF",
        help="start ref (exclusive). Defaults to the latest tag, or the whole "
        "history if there are no tags.",
    )
    parser.add_argument(
        "--to",
        dest="to",
        metavar="REF",
        default="HEAD",
        help="end ref (inclusive). Defaults to HEAD.",
    )
    parser.add_argument(
        "-t",
        "--title",
        metavar="TEXT",
        help="heading for the notes, e.g. the version being released (v1.2.0).",
    )
    parser.add_argument(
        "--repo",
        metavar="OWNER/NAME",
        help="GitHub repo slug used to turn commits and PRs into links.",
    )
    parser.add_argument(
        "--base-url",
        metavar="URL",
        default="https://github.com",
        help="base URL for links (default: https://github.com).",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help="write the notes to FILE instead of stdout.",
    )
    parser.add_argument(
        "-C",
        dest="cwd",
        metavar="DIR",
        help="run as if shipnote were started in DIR.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s {0}".format(__version__),
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        rev_range = resolve_range(args.frm, args.to, cwd=args.cwd)
        commits = get_commits(rev_range, cwd=args.cwd)
    except GitError as exc:
        parser.exit(2, "shipnote: {0}\n".format(exc))

    notes = render_markdown(
        commits,
        title=args.title,
        repo=args.repo,
        base_url=args.base_url,
    )

    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(notes)
    else:
        sys.stdout.write(notes)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

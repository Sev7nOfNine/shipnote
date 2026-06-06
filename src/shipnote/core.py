"""Core logic for shipnote: parse git commits and render release notes.

The functions here are deliberately split into two layers:

* Pure functions (``parse_commit``, ``categorize``, ``render_markdown``) that
  operate on plain data and are trivially unit-testable without a git repo.
* Thin git wrappers (``run_git``, ``latest_tag``, ``get_commits``,
  ``resolve_range``) that shell out to ``git``.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

# A conventional-commit subject, e.g. "feat(api)!: add streaming endpoint".
_CONVENTIONAL_RE = re.compile(
    r"^(?P<type>[a-z]+)"
    r"(?:\((?P<scope>[^)]+)\))?"
    r"(?P<breaking>!)?"
    r":\s*(?P<subject>.+)$",
    re.IGNORECASE,
)

# A trailing PR reference GitHub appends on squash-merge, e.g. "(#42)".
_PR_RE = re.compile(r"\(#(\d+)\)\s*$")

# Map a conventional type to a human section title.
TYPE_SECTIONS: Dict[str, str] = {
    "feat": "Features",
    "fix": "Bug Fixes",
    "perf": "Performance",
    "refactor": "Refactoring",
    "docs": "Documentation",
    "test": "Tests",
    "build": "Build System",
    "ci": "CI",
    "style": "Styles",
    "chore": "Chores",
    "revert": "Reverts",
}

# The order sections appear in the rendered notes.
SECTION_ORDER: List[str] = [
    "Breaking Changes",
    "Features",
    "Bug Fixes",
    "Performance",
    "Refactoring",
    "Documentation",
    "Tests",
    "Build System",
    "CI",
    "Styles",
    "Chores",
    "Reverts",
    "Other",
]


class GitError(RuntimeError):
    """Raised when an underlying git command fails."""


@dataclass
class Commit:
    """A single parsed commit."""

    sha: str
    subject: str
    body: str = ""
    type: Optional[str] = None
    scope: Optional[str] = None
    breaking: bool = False
    pr: Optional[int] = None

    @property
    def short_sha(self) -> str:
        return self.sha[:7]


def parse_commit(sha: str, subject: str, body: str = "") -> Commit:
    """Parse a raw commit into a :class:`Commit`, recognising conventional commits."""
    subject = subject.strip()
    body = body.strip()

    pr: Optional[int] = None
    pr_match = _PR_RE.search(subject)
    if pr_match:
        pr = int(pr_match.group(1))
        # Drop the trailing "(#42)" so it is not repeated next to the link.
        subject = _PR_RE.sub("", subject).strip()

    breaking = "BREAKING CHANGE" in body or "BREAKING-CHANGE" in body

    match = _CONVENTIONAL_RE.match(subject)
    if not match:
        return Commit(sha=sha, subject=subject, body=body, breaking=breaking, pr=pr)

    ctype = match.group("type").lower()
    if match.group("breaking"):
        breaking = True

    return Commit(
        sha=sha,
        subject=match.group("subject").strip(),
        body=body,
        type=ctype,
        scope=match.group("scope"),
        breaking=breaking,
        pr=pr,
    )


def categorize(commits: Sequence[Commit]) -> "Dict[str, List[Commit]]":
    """Group commits into ordered sections.

    Breaking changes are surfaced in their own section and are not duplicated
    under their conventional type.
    """
    sections: Dict[str, List[Commit]] = {name: [] for name in SECTION_ORDER}
    for commit in commits:
        if commit.breaking:
            sections["Breaking Changes"].append(commit)
            continue
        section = TYPE_SECTIONS.get(commit.type or "", "Other")
        sections[section].append(commit)
    return {name: items for name, items in sections.items() if items}


def _render_commit(commit: Commit, repo: Optional[str], base_url: str) -> str:
    bullet = commit.subject
    if commit.scope:
        bullet = "**{0}:** {1}".format(commit.scope, bullet)

    refs: List[str] = []
    if commit.pr is not None:
        if repo:
            refs.append("[#{0}]({1}/{2}/pull/{0})".format(commit.pr, base_url, repo))
        else:
            refs.append("#{0}".format(commit.pr))
    if repo:
        refs.append(
            "[`{0}`]({1}/{2}/commit/{3})".format(
                commit.short_sha, base_url, repo, commit.sha
            )
        )
    else:
        refs.append("`{0}`".format(commit.short_sha))

    return "- {0} ({1})".format(bullet, ", ".join(refs))


def render_markdown(
    commits: Sequence[Commit],
    title: Optional[str] = None,
    repo: Optional[str] = None,
    base_url: str = "https://github.com",
) -> str:
    """Render grouped commits to a markdown release-notes string."""
    base_url = base_url.rstrip("/")
    lines: List[str] = []
    if title:
        lines.append("## {0}".format(title))
        lines.append("")

    sections = categorize(commits)
    if not sections:
        lines.append("_No notable changes._")
        return "\n".join(lines).rstrip() + "\n"

    for name in SECTION_ORDER:
        items = sections.get(name)
        if not items:
            continue
        lines.append("### {0}".format(name))
        for commit in items:
            lines.append(_render_commit(commit, repo, base_url))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


# --- git wrappers -------------------------------------------------------------

# Field/record separators unlikely to appear in commit text.
_FIELD_SEP = "\x1f"
_RECORD_SEP = "\x1e"


def run_git(args: Sequence[str], cwd: Optional[str] = None) -> str:
    """Run a git command and return stdout, raising :class:`GitError` on failure."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except FileNotFoundError as exc:  # git not installed
        raise GitError("git executable not found on PATH") from exc

    if result.returncode != 0:
        raise GitError(result.stderr.strip() or "git {0} failed".format(" ".join(args)))
    return result.stdout


def latest_tag(cwd: Optional[str] = None) -> Optional[str]:
    """Return the most recent tag reachable from HEAD, or ``None`` if there is none."""
    try:
        out = run_git(["describe", "--tags", "--abbrev=0"], cwd=cwd)
    except GitError:
        return None
    tag = out.strip()
    return tag or None


def resolve_range(
    frm: Optional[str], to: str, cwd: Optional[str] = None
) -> str:
    """Build the git revision range to read commits from.

    With no explicit ``frm``, fall back to the latest tag, then to the full
    history if the repo has no tags yet.
    """
    if frm:
        return "{0}..{1}".format(frm, to)
    tag = latest_tag(cwd=cwd)
    if tag:
        return "{0}..{1}".format(tag, to)
    return to


def get_commits(rev_range: str, cwd: Optional[str] = None) -> List[Commit]:
    """Read and parse commits in ``rev_range`` (newest first), skipping merges."""
    fmt = _FIELD_SEP.join(["%H", "%s", "%b"]) + _RECORD_SEP
    out = run_git(
        ["log", "--no-merges", "--format={0}".format(fmt), rev_range],
        cwd=cwd,
    )
    commits: List[Commit] = []
    for record in out.split(_RECORD_SEP):
        record = record.strip("\n")
        if not record:
            continue
        parts = record.split(_FIELD_SEP)
        sha = parts[0] if len(parts) > 0 else ""
        subject = parts[1] if len(parts) > 1 else ""
        body = parts[2] if len(parts) > 2 else ""
        if not sha:
            continue
        commits.append(parse_commit(sha, subject, body))
    return commits

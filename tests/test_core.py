"""Unit tests for shipnote's pure logic (no git repo required)."""

from shipnote.core import (
    Commit,
    categorize,
    parse_commit,
    render_markdown,
)


def test_parse_plain_commit():
    commit = parse_commit("a" * 40, "just a plain message")
    assert commit.type is None
    assert commit.subject == "just a plain message"
    assert commit.breaking is False
    assert commit.short_sha == "aaaaaaa"


def test_parse_conventional_with_scope():
    commit = parse_commit("b" * 40, "feat(api): add streaming endpoint")
    assert commit.type == "feat"
    assert commit.scope == "api"
    assert commit.subject == "add streaming endpoint"
    assert commit.breaking is False


def test_parse_breaking_bang():
    commit = parse_commit("c" * 40, "feat!: drop python 3.7")
    assert commit.type == "feat"
    assert commit.breaking is True


def test_parse_breaking_footer():
    commit = parse_commit(
        "d" * 40,
        "refactor: rework config",
        body="BREAKING CHANGE: config file moved",
    )
    assert commit.breaking is True


def test_parse_pr_reference():
    commit = parse_commit("e" * 40, "fix: handle empty range (#42)")
    assert commit.pr == 42
    assert commit.subject == "handle empty range"


def test_categorize_groups_and_drops_empty():
    commits = [
        parse_commit("1" * 40, "feat: a"),
        parse_commit("2" * 40, "fix: b"),
        parse_commit("3" * 40, "chore: c"),
    ]
    grouped = categorize(commits)
    assert set(grouped) == {"Features", "Bug Fixes", "Chores"}


def test_categorize_breaking_not_duplicated():
    commits = [parse_commit("4" * 40, "feat!: big change")]
    grouped = categorize(commits)
    assert "Breaking Changes" in grouped
    assert "Features" not in grouped


def test_render_unknown_type_goes_to_other():
    commits = [Commit(sha="f" * 40, subject="something", type="wip")]
    out = render_markdown(commits)
    assert "### Other" in out
    assert "- something (`fffffff`)" in out


def test_render_with_repo_links():
    commits = [parse_commit("a1b2c3d4e5" + "0" * 30, "fix: thing (#7)")]
    out = render_markdown(commits, title="v1.0.0", repo="me/proj")
    assert out.startswith("## v1.0.0")
    assert "[#7](https://github.com/me/proj/pull/7)" in out
    assert "https://github.com/me/proj/commit/" in out


def test_render_empty():
    out = render_markdown([])
    assert "No notable changes" in out


def test_render_section_order():
    commits = [
        parse_commit("1" * 40, "docs: d"),
        parse_commit("2" * 40, "feat: f"),
        parse_commit("3" * 40, "fix: x"),
    ]
    out = render_markdown(commits)
    assert out.index("### Features") < out.index("### Bug Fixes")
    assert out.index("### Bug Fixes") < out.index("### Documentation")

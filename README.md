# shipnote

**Generate clean, grouped release notes straight from your git history — with zero dependencies.**

`shipnote` reads the commits between two refs, understands
[Conventional Commits](https://www.conventionalcommits.org/), and renders tidy
markdown release notes grouped by Features, Bug Fixes, Performance, Breaking
Changes, and more. No config file, no extra packages, no network calls.

It is built for the boring-but-constant chore every maintainer knows: writing
the changelog at release time.

## Why

Most changelog tools pull in a tree of dependencies, want a config file, or lock
you into one commit convention. `shipnote` is a single small package that uses
nothing but the Python standard library and the `git` you already have. Drop it
into any project or CI job and get readable notes in one command.

## Install

```bash
pip install shipnote
# or, for an isolated CLI:
pipx install shipnote
```

Requires Python 3.8+ and `git` on your PATH.

## Usage

From inside a git repository:

```bash
# Notes from the latest tag up to HEAD
shipnote

# A titled section for a specific version, with commit/PR links
shipnote --title v1.2.0 --repo me/myproject

# An explicit range, written to a file
shipnote --from v1.1.0 --to v1.2.0 --output RELEASE_NOTES.md
```

If the repo has no tags yet, `shipnote` walks the whole history.

### Options

| Flag | Description |
| --- | --- |
| `--from REF` | Start ref, exclusive. Defaults to the latest tag. |
| `--to REF` | End ref, inclusive. Defaults to `HEAD`. |
| `-t`, `--title TEXT` | Heading for the notes, e.g. the version. |
| `--repo OWNER/NAME` | Turn commit hashes and `(#123)` PR refs into links. |
| `--base-url URL` | Base URL for links (default `https://github.com`). |
| `-o`, `--output FILE` | Write to a file instead of stdout. |
| `-C DIR` | Run as if started in `DIR`. |

## Example output

```markdown
## v1.2.0

### Breaking Changes
- drop Python 3.7 support (`a1b2c3d`)

### Features
- **api:** add streaming endpoint ([#42](https://github.com/me/proj/pull/42), [`9f8e7d6`](https://github.com/me/proj/commit/9f8e7d6))

### Bug Fixes
- handle an empty commit range gracefully (`c4d5e6f`)
```

## In CI

Use it in a release workflow to draft notes from the just-tagged range:

```yaml
- name: Draft release notes
  run: |
    pip install shipnote
    shipnote --title "${GITHUB_REF_NAME}" --repo "${GITHUB_REPOSITORY}" -o notes.md
```

## How it groups commits

Conventional types map to sections: `feat` → Features, `fix` → Bug Fixes,
`perf` → Performance, `docs` → Documentation, `refactor` → Refactoring,
`test` → Tests, `build` → Build System, `ci` → CI, `style` → Styles,
`chore` → Chores, `revert` → Reverts. Anything that does not match falls under
**Other**, so no commit is ever silently dropped. Commits marked breaking (a `!`
after the type, or a `BREAKING CHANGE` footer) are surfaced under **Breaking
Changes**.

## Development

```bash
pip install -e .
python -m pytest
```

## License

MIT — see [LICENSE](LICENSE).

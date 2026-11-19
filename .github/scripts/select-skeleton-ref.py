#!/usr/bin/env python3
"""Choose the skeleton release that update-from-skeleton may apply.

Left to itself, copier takes the newest version tag in the skeleton repository
and, with --trust, runs that tag's tasks. Anyone who can push to the skeleton can
create a tag on an unreviewed commit, so this picks the newest version tag whose
commit is on the skeleton's main branch, which only reviewed merges reach. The
workflow passes the result to copier as --vcs-ref.

  select-skeleton-ref.py --answers .copier-answers.yml --skeleton <clone> [--prereleases]

<clone> is a clone of the skeleton with all tags fetched. Prints the chosen tag.
Tags whose commit isn't on main are skipped with a warning. Exits 1, with the
reason on stderr, when the answers file names another source, no version tag on
main qualifies, or the choice is older than the version the repository has.
Needs the `packaging` library (copier orders versions with it too).
"""
import argparse
import os
import subprocess
import sys

from packaging.version import InvalidVersion, Version

OFFICIAL_SOURCE = "launchbynttdata/launch-terraform-skeleton"
SOURCE_FORMS = (
    f"gh:{OFFICIAL_SOURCE}",
    f"https://github.com/{OFFICIAL_SOURCE}",
    f"git@github.com:{OFFICIAL_SOURCE}",
)


def answers(path):
    """The top-level scalar values of a copier answers file."""
    values = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line[:1] in (" ", "\t", "#", "-") or ":" not in line:
                continue
            key, _, value = line.partition(":")
            values[key.strip()] = value.strip().strip("'\"")
    return values


def official(src_path):
    src = src_path.strip().rstrip("/")
    if src.endswith(".git"):
        src = src[: -len(".git")]
    return src in SOURCE_FORMS


def git(clone, *args, check=True):
    return subprocess.run(["git", "-C", clone, *args], check=check, capture_output=True, text=True)


def version(text):
    try:
        return Version(text)
    except InvalidVersion:
        return None


def warn(message):
    prefix = "::warning::" if os.environ.get("GITHUB_ACTIONS") == "true" else "warning: "
    print(f"{prefix}{message}", file=sys.stderr)


def select(answers_path, clone, prereleases, branch="origin/main"):
    """Return (tag, skipped). Raises ValueError with the reason when nothing may be applied."""
    values = answers(answers_path)
    src = values.get("_src_path", "")
    if not official(src):
        raise ValueError(f"{answers_path} names source {src!r}, not {OFFICIAL_SOURCE}")
    tags = [t for t in git(clone, "tag", "--list").stdout.split() if t]
    candidates = sorted(
        ((v, t) for t in tags for v in [version(t)] if v is not None and (prereleases or not v.is_prerelease)),
        reverse=True,
    )
    chosen, skipped = None, []
    for v, tag in candidates:
        commit = git(clone, "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}^{{commit}}").stdout.strip()
        if commit and git(clone, "merge-base", "--is-ancestor", commit, branch, check=False).returncode == 0:
            chosen = (v, tag)
            break
        skipped.append(tag)
    if chosen is None:
        raise ValueError(f"no {'version' if prereleases else 'stable version'} tag of the skeleton is on {branch}")
    current = version(values.get("_commit", ""))
    if current is not None and chosen[0] < current:
        raise ValueError(f"the newest skeleton tag on {branch} is {chosen[1]}, older than this "
                         f"repository's {values['_commit']}; not downgrading")
    return chosen[1], skipped


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--answers", required=True)
    ap.add_argument("--skeleton", required=True, help="a clone of the skeleton with all tags fetched")
    ap.add_argument("--prereleases", action="store_true")
    args = ap.parse_args(argv)
    try:
        tag, skipped = select(args.answers, args.skeleton, args.prereleases)
    except ValueError as e:
        print(f"select-skeleton-ref: {e}", file=sys.stderr)
        return 1
    for t in skipped:
        warn(f"skipped skeleton tag {t}: its commit is not on the skeleton's main branch")
    print(tag)
    return 0


if __name__ == "__main__":
    sys.exit(main())

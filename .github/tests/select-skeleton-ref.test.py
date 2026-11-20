#!/usr/bin/env python3
"""Tests select-skeleton-ref.py against a fixture skeleton repository, and checks
that reusable-update-from-skeleton.yml applies the tag it selects.

  uv run --no-project --with packaging python3 .github/tests/select-skeleton-ref.test.py
"""
import importlib.util
import os
import pathlib
import subprocess
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
SCRIPT = HERE.parent / "scripts" / "select-skeleton-ref.py"
WORKFLOW = HERE.parent / "workflows" / "reusable-update-from-skeleton.yml"

spec = importlib.util.spec_from_file_location("select_skeleton_ref", SCRIPT)
ssr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ssr)

GIT_ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
           "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True,
                          text=True, env=GIT_ENV).stdout.strip()


class SelectSkeletonRefTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = pathlib.Path(cls.tmp.name)
        origin = root / "origin"
        git(root, "init", "--quiet", "--initial-branch=main", str(origin))
        for tag in ("0.9.0", "0.10.0", "0.10.1-rc.0"):
            git(origin, "commit", "--quiet", "--allow-empty", "-m", tag)
            git(origin, "tag", tag)
        git(origin, "tag", "not-a-version")
        # A higher tag on an unreviewed branch, and one on a commit no branch contains.
        git(origin, "switch", "--quiet", "-c", "unreviewed")
        git(origin, "commit", "--quiet", "--allow-empty", "-m", "unreviewed")
        git(origin, "tag", "0.11.0")
        git(origin, "switch", "--quiet", "main")
        orphan = git(origin, "commit-tree", "-m", "orphan", git(origin, "rev-parse", "HEAD^{tree}"))
        git(origin, "tag", "0.12.0", orphan)
        # The workflow's clone: partial, no checkout, then every tag fetched.
        cls.clone = root / "skeleton"
        git(root, "clone", "--quiet", "--filter=blob:none", "--no-checkout", origin.as_uri(), str(cls.clone))
        git(cls.clone, "fetch", "--quiet", "--tags", "origin")
        cls.root = root

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def answers(self, src="gh:launchbynttdata/launch-terraform-skeleton", commit="0.9.0"):
        path = self.root / f"answers-{abs(hash((src, commit)))}.yml"
        path.write_text(f"# Changes here will be overwritten by Copier\n_commit: {commit}\n_src_path: {src}\n"
                        "provider: aws\nlist_value:\n  - _src_path: elsewhere\n")
        return str(path)

    def test_fixture_has_the_tags_it_needs(self):
        tags = set(git(self.clone, "tag", "--list").split())
        self.assertTrue({"0.9.0", "0.10.0", "0.10.1-rc.0", "0.11.0", "0.12.0", "not-a-version"} <= tags, tags)

    # --- good cases ---------------------------------------------------------------

    def test_stable_picks_the_newest_stable_tag_on_main_and_skips_the_others(self):
        tag, skipped = ssr.select(self.answers(), str(self.clone), prereleases=False)
        self.assertEqual(tag, "0.10.0")
        self.assertEqual(skipped, ["0.12.0", "0.11.0"])

    def test_prereleases_pick_the_newest_tag_on_main(self):
        tag, _ = ssr.select(self.answers(), str(self.clone), prereleases=True)
        self.assertEqual(tag, "0.10.1-rc.0")

    def test_already_current_is_not_a_downgrade(self):
        tag, _ = ssr.select(self.answers(commit="0.10.0"), str(self.clone), prereleases=False)
        self.assertEqual(tag, "0.10.0")

    def test_https_and_dot_git_sources_are_accepted(self):
        for src in ("https://github.com/launchbynttdata/launch-terraform-skeleton.git",
                    "https://github.com/launchbynttdata/launch-terraform-skeleton/",
                    "'gh:launchbynttdata/launch-terraform-skeleton'"):
            self.assertEqual(ssr.select(self.answers(src=src), str(self.clone), False)[0], "0.10.0", src)

    def test_a_nested_src_path_key_is_ignored(self):
        self.assertEqual(ssr.answers(self.answers())["_src_path"], "gh:launchbynttdata/launch-terraform-skeleton")

    def test_cli_prints_the_tag_and_warns_about_skipped_tags(self):
        r = subprocess.run(["python3", str(SCRIPT), "--answers", self.answers(), "--skeleton", str(self.clone)],
                           capture_output=True, text=True, env={**GIT_ENV, "GITHUB_ACTIONS": "true"})
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "0.10.0"), r.stderr)
        self.assertIn("::warning::skipped skeleton tag 0.11.0", r.stderr)
        self.assertIn("::warning::skipped skeleton tag 0.12.0", r.stderr)

    # --- bad cases ------------------------------------------------------------------

    def test_another_source_is_refused(self):
        for src in ("gh:someone/launch-terraform-skeleton", "https://github.com/launchbynttdata/other",
                    "gh:launchbynttdata/launch-terraform-skeleton-fork", ""):
            with self.assertRaisesRegex(ValueError, "names source"):
                ssr.select(self.answers(src=src), str(self.clone), False)

    def test_downgrade_is_refused(self):
        with self.assertRaisesRegex(ValueError, "not downgrading"):
            ssr.select(self.answers(commit="0.10.1-rc.0"), str(self.clone), prereleases=False)

    def test_no_tag_on_the_branch_is_refused_including_a_missing_branch(self):
        with self.assertRaisesRegex(ValueError, "no stable version tag"):
            ssr.select(self.answers(), str(self.clone), False, branch="origin/does-not-exist")

    def test_cli_exits_1_with_the_reason(self):
        r = subprocess.run(["python3", str(SCRIPT), "--answers", self.answers(src="gh:x/y"), "--skeleton",
                            str(self.clone)], capture_output=True, text=True, env=GIT_ENV)
        self.assertEqual((r.returncode, r.stdout), (1, ""))
        self.assertIn("names source", r.stderr)

    # --- wiring ---------------------------------------------------------------------

    def test_workflow_applies_the_selected_tag(self):
        text = WORKFLOW.read_text()
        self.assertIn("id: select-skeleton-ref", text)
        self.assertIn("/${{ job.workflow_sha }}/.github/scripts/select-skeleton-ref.py", text)
        self.assertIn("SKELETON_REF: ${{ steps.select-skeleton-ref.outputs.ref }}", text)
        self.assertIn('COPIER_FLAGS="--defaults --trust --vcs-ref $SKELETON_REF"', text)
        self.assertIn('if [ -z "$SKELETON_REF" ]; then', text)
        self.assertLess(text.index("id: select-skeleton-ref"), text.index("id: run-updates"))
        copier_calls = [l for l in text.splitlines() if "uv run copier" in l]
        self.assertEqual(len(copier_calls), 2, copier_calls)
        self.assertTrue(all("$COPIER_FLAGS" in l for l in copier_calls), copier_calls)


if __name__ == "__main__":
    unittest.main(verbosity=1)

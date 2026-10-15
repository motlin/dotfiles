#!/usr/bin/env python3
"""Test the replay-all and git-all recipes in the global justfile's git-rebase.just."""
import os
import pathlib
import subprocess
import tempfile
import unittest


GLOBAL_JUSTFILE = pathlib.Path(__file__).resolve().parent.parent / "config" / "just" / "justfile"

# Drop GIT_DIR, GIT_INDEX_FILE and friends that a commit hook exports, or they leak into the test repositories.
GIT_ENVIRONMENT = dict(
    {name: value for name, value in os.environ.items() if not name.startswith("GIT_")},
    GIT_CONFIG_GLOBAL=os.devnull,
    GIT_CONFIG_NOSYSTEM="1",
    GIT_AUTHOR_NAME="Test Author",
    GIT_AUTHOR_EMAIL="author@example.com",
    GIT_COMMITTER_NAME="Test Author",
    GIT_COMMITTER_EMAIL="author@example.com",
    OFFLINE="true",
    UPSTREAM_REMOTE="upstream",
    UPSTREAM_BRANCH="main",
)


def git(directory, *arguments, committer_date=None):
    environment = GIT_ENVIRONMENT
    if committer_date is not None:
        environment = dict(GIT_ENVIRONMENT, GIT_COMMITTER_DATE=committer_date, GIT_AUTHOR_DATE=committer_date)
    return subprocess.run(
        ["git", "-C", str(directory), *arguments],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    ).stdout.strip()


def commit_file(directory, name, contents, committer_date="2026-01-01T00:00:00"):
    pathlib.Path(directory, name).write_text(contents + "\n")
    git(directory, "add", name)
    git(directory, "commit", "--message", f"Set {name} to {contents}.", committer_date=committer_date)


def just(directory, recipe):
    return subprocess.run(
        ["just", "--justfile", str(GLOBAL_JUSTFILE), "--working-directory", str(directory), recipe],
        capture_output=True,
        text=True,
        env=GIT_ENVIRONMENT,
    )


def contains_upstream(directory, branch):
    return subprocess.run(
        ["git", "-C", str(directory), "merge-base", "--is-ancestor", "upstream/main", branch],
        env=GIT_ENVIRONMENT,
    ).returncode == 0


def head_reflog(directory):
    return git(directory, "reflog", "--format=%gs", "HEAD").splitlines()


def checkouts_since(directory, reflog_before):
    """Branches HEAD moved to since reflog_before; replay never moves HEAD and rebase-all checks out each branch."""
    new_entries = head_reflog(directory)[: -len(reflog_before)]
    return sorted({entry.rsplit(" to ", 1)[1] for entry in new_entries if entry.startswith("checkout: moving from")})


class RecipeTest(unittest.TestCase):
    def setUp(self):
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.root = pathlib.Path(temporary_directory.name)
        self.repository = self.root / "repository"
        upstream = self.root / "upstream.git"

        git(self.root, "init", "--quiet", "--bare", "--initial-branch=main", str(upstream))
        git(self.root, "init", "--quiet", "--initial-branch=main", str(self.repository))
        git(self.repository, "remote", "add", "upstream", str(upstream))
        commit_file(self.repository, "shared", "base")
        git(self.repository, "branch", "base")

    def publish_upstream_change(self):
        git(self.repository, "switch", "--quiet", "main")
        commit_file(self.repository, "shared", "upstream", committer_date="2026-01-02T00:00:00")
        git(self.repository, "push", "--quiet", "upstream", "main")
        git(self.repository, "fetch", "--quiet", "upstream")

    def topic_branch(self, name, start="base", file_name=None, contents=None, committer_date="2026-01-01T00:00:00"):
        git(self.repository, "switch", "--quiet", "--create", name, start)
        commit_file(self.repository, file_name or name, contents or name, committer_date=committer_date)


class ReplayAllTest(RecipeTest):
    def test_skips_the_current_branch_and_leaves_its_checkout_clean(self):
        self.topic_branch("current")
        self.publish_upstream_change()
        git(self.repository, "switch", "--quiet", "current")
        before = git(self.repository, "rev-parse", "current")

        result = just(self.repository, "replay-all")

        self.assertEqual(
            (result.returncode, git(self.repository, "rev-parse", "current"), git(self.repository, "status", "--porcelain")),
            (0, before, ""),
        )

    def test_skips_a_branch_checked_out_in_another_worktree(self):
        self.topic_branch("elsewhere")
        self.publish_upstream_change()
        worktree = self.root / "elsewhere"
        git(self.repository, "worktree", "add", "--quiet", str(worktree), "elsewhere")
        before = git(self.repository, "rev-parse", "elsewhere")

        result = just(self.repository, "replay-all")

        self.assertEqual(
            (result.returncode, git(self.repository, "rev-parse", "elsewhere"), git(worktree, "status", "--porcelain")),
            (0, before, ""),
        )

    def test_skips_a_stack_whose_lower_branch_is_checked_out(self):
        self.topic_branch("lower")
        self.topic_branch("upper", start="lower")
        self.publish_upstream_change()
        git(self.repository, "switch", "--quiet", "lower")
        before = (git(self.repository, "rev-parse", "lower"), git(self.repository, "rev-parse", "upper"))

        result = just(self.repository, "replay-all")

        self.assertEqual(
            (
                result.returncode,
                (git(self.repository, "rev-parse", "lower"), git(self.repository, "rev-parse", "upper")),
                git(self.repository, "status", "--porcelain"),
            ),
            (0, before, ""),
        )

    def test_moves_a_stack_together(self):
        self.topic_branch("lower")
        self.topic_branch("upper", start="lower")
        self.publish_upstream_change()

        result = just(self.repository, "replay-all")

        self.assertEqual(
            (
                result.returncode,
                contains_upstream(self.repository, "lower"),
                git(self.repository, "rev-parse", "upper^"),
            ),
            (0, True, git(self.repository, "rev-parse", "lower")),
        )

    def test_fails_after_replaying_the_branches_that_do_not_conflict(self):
        self.topic_branch("clean", committer_date="2026-01-01T00:00:00")
        self.topic_branch("conflicting", file_name="shared", contents="topic", committer_date="2026-01-01T01:00:00")
        self.publish_upstream_change()

        result = just(self.repository, "replay-all")

        self.assertEqual(
            (result.returncode, contains_upstream(self.repository, "clean"), contains_upstream(self.repository, "conflicting")),
            (1, True, False),
        )


class GitAllTest(RecipeTest):
    def test_replays_before_rebasing_so_a_conflict_does_not_block_other_branches(self):
        self.topic_branch("clean", committer_date="2026-01-01T00:00:00")
        self.topic_branch("conflicting", file_name="shared", contents="topic", committer_date="2026-01-01T01:00:00")
        self.publish_upstream_change()
        reflog_before = head_reflog(self.repository)

        result = just(self.repository, "git-all")

        self.assertEqual(
            (result.returncode != 0, contains_upstream(self.repository, "clean"), checkouts_since(self.repository, reflog_before)),
            (True, True, ["conflicting"]),
        )

    def test_rebases_only_the_branches_replay_cannot_handle(self):
        self.topic_branch("replayable")
        self.topic_branch("side")
        self.topic_branch("with-merge")
        git(self.repository, "merge", "--quiet", "--no-ff", "--no-edit", "side")
        self.publish_upstream_change()
        reflog_before = head_reflog(self.repository)

        result = just(self.repository, "git-all")

        self.assertEqual(
            (
                result.returncode,
                contains_upstream(self.repository, "replayable"),
                contains_upstream(self.repository, "with-merge"),
                checkouts_since(self.repository, reflog_before),
            ),
            (0, True, True, ["with-merge"]),
        )


if __name__ == "__main__":
    unittest.main()

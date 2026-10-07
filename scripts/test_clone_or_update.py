#!/usr/bin/env python3
"""Test the divergence handling in clone-or-update.sh."""
import os
import pathlib
import subprocess
import tempfile
import unittest


CLONE_SCRIPT = pathlib.Path(__file__).with_name("clone-or-update.sh")

# Drop GIT_DIR, GIT_INDEX_FILE and friends that a commit hook exports, or they leak into the test repositories.
GIT_ENVIRONMENT = dict(
    {name: value for name, value in os.environ.items() if not name.startswith("GIT_")},
    GIT_CONFIG_GLOBAL=os.devnull,
    GIT_CONFIG_NOSYSTEM="1",
    GIT_AUTHOR_NAME="Test Author",
    GIT_AUTHOR_EMAIL="author@example.com",
    GIT_COMMITTER_NAME="Test Author",
    GIT_COMMITTER_EMAIL="author@example.com",
)


def git(directory, *arguments):
    subprocess.run(
        ["git", "-C", str(directory), *arguments],
        check=True,
        capture_output=True,
        env=GIT_ENVIRONMENT,
    )


class WritableModeTest(unittest.TestCase):
    def test_diverged_clone_names_the_republish_command(self):
        with tempfile.TemporaryDirectory() as directory:
            base = pathlib.Path(directory, "clones")
            origin = pathlib.Path(directory, "origin.git")
            target = base / "example-org" / "example-repo"
            repository_url = "git@example.com:example-org/example-repo.git"

            origin.mkdir(parents=True)
            git(origin, "init", "--bare", "--initial-branch=main")
            target.parent.mkdir(parents=True)
            git(target.parent, "clone", str(origin), str(target))
            git(target, "commit", "--allow-empty", "--message", "Base commit.")
            git(target, "commit", "--allow-empty", "--message", "Published commit.")
            git(target, "push", "origin", "HEAD")
            git(target, "remote", "set-head", "origin", "main")
            git(target, "commit", "--amend", "--allow-empty", "--message", "Rewritten commit.")

            result = subprocess.run(
                ["bash", str(CLONE_SCRIPT), str(base), repository_url, "writable"],
                capture_output=True,
                text=True,
                env=GIT_ENVIRONMENT,
            )

            self.assertEqual(
                (result.returncode, result.stderr.splitlines()[-4:]),
                (
                    1,
                    [
                        f"{target} has diverged from origin/HEAD.",
                        "The usual cause is rebasing it onto a public upstream, which rewrites commits "
                        "origin already has. If that is what happened, republish it:",
                        f"    git -C {target} push --force-with-lease origin HEAD",
                        "Otherwise push or rebase it. Either way, rerun afterwards.",
                    ],
                ),
            )


if __name__ == "__main__":
    unittest.main()

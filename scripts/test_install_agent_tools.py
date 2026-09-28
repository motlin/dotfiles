#!/usr/bin/env python3
"""Test the skill installation functions in install-agent-tools.sh."""
import os
import pathlib
import subprocess
import tempfile
import unittest


INSTALL_SCRIPT = pathlib.Path(__file__).with_name("install-agent-tools.sh")


class InstallClaudeSkillsTest(unittest.TestCase):
    def test_installs_configured_skills_then_updates_all(self):
        with tempfile.TemporaryDirectory() as directory:
            log_path = pathlib.Path(directory, "npx.log")
            fake_npx = pathlib.Path(directory, "npx")
            fake_npx.write_text(f'#!/bin/sh\necho "$*" >> "{log_path}"\n')
            fake_npx.chmod(0o755)
            environment = dict(os.environ, PATH=f"{directory}:{os.environ['PATH']}")

            subprocess.run(
                ["bash", "-c", f'source "{INSTALL_SCRIPT}" && install_claude_skills'],
                check=True,
                env=environment,
            )

            self.assertEqual(
                log_path.read_text().splitlines(),
                [
                    "--yes skills add cloudflare/skills --global --agent claude-code "
                    "--skill agents-sdk cloudflare cloudflare-email-service "
                    "cloudflare-one cloudflare-one-migrations durable-objects "
                    "sandbox-stable turnstile-spin web-perf workers-best-practices "
                    "wrangler --yes",
                    "--yes skills add maxim-saplin/goal-sloc --global --agent claude-code "
                    "--skill goal-sloc --yes",
                    "--yes skills update --global --yes",
                ],
            )


if __name__ == "__main__":
    unittest.main()

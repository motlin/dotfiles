#!/usr/bin/env python3
"""Test install-1password-agent-tools.sh against fake claude and codex CLIs."""
import os
import pathlib
import subprocess
import tempfile
import unittest


SCRIPT = pathlib.Path(__file__).with_name("install-1password-agent-tools.sh")

FAKE_CLAUDE = """#!/bin/sh
echo "claude $*" >> "{log}"
case "$*" in
    "plugin marketplace list --json") printf '%s' '{marketplaces}' ;;
    "plugin list --json") printf '%s' '{plugins}' ;;
esac
"""

FAKE_CODEX = """#!/bin/sh
echo "codex $*" >> "{log}"
if [ "$*" = "mcp get 1password" ]; then
    exit {codex_get_status}
fi
"""


class Install1PasswordAgentToolsTest(unittest.TestCase):
    def run_script(self, marketplaces, plugins, codex_get_status):
        with tempfile.TemporaryDirectory() as directory:
            log = pathlib.Path(directory, "log")
            for name, template in {"claude": FAKE_CLAUDE, "codex": FAKE_CODEX}.items():
                path = pathlib.Path(directory, name)
                path.write_text(
                    template.format(
                        log=log,
                        marketplaces=marketplaces,
                        plugins=plugins,
                        codex_get_status=codex_get_status,
                    )
                )
                path.chmod(0o755)

            subprocess.run(
                ["bash", str(SCRIPT)],
                capture_output=True,
                check=True,
                env=dict(os.environ, PATH=f"{directory}:{os.environ['PATH']}"),
            )

            return log.read_text().splitlines()

    def test_installs_everything_on_a_fresh_mac(self):
        log = self.run_script('[{"name": "example-marketplace"}]', '[{"id": "example@example-marketplace"}]', 1)

        self.assertEqual(
            log,
            [
                "claude plugin marketplace list --json",
                "claude plugin marketplace add 1Password/1password-claude-plugin",
                "claude plugin list --json",
                "claude plugin install 1password@1password",
                "codex mcp get 1password",
                "codex mcp add 1password -- 1password-mcp",
            ],
        )

    def test_changes_nothing_when_already_installed(self):
        log = self.run_script('[{"name": "1password"}]', '[{"id": "1password@1password"}]', 0)

        self.assertEqual(
            log,
            [
                "claude plugin marketplace list --json",
                "claude plugin list --json",
                "codex mcp get 1password",
            ],
        )


if __name__ == "__main__":
    unittest.main()

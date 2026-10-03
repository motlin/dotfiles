#!/usr/bin/env python3
"""Test op-inject-if-signed-in.sh against a fake 1Password CLI."""
import os
import pathlib
import subprocess
import tempfile
import unittest


SCRIPT = pathlib.Path(__file__).with_name("op-inject-if-signed-in.sh")


class OpInjectIfSignedInTest(unittest.TestCase):
    def run_script(self, directory, accounts):
        log_path = pathlib.Path(directory, "op.log")
        fake_op = pathlib.Path(directory, "op")
        fake_op.write_text(
            f"""#!/bin/sh
echo "op $*" >> "{log_path}"
if [ "$1 $2" = "account list" ]; then
    printf '%s' "{accounts}"
fi
"""
        )
        fake_op.chmod(0o755)

        result = subprocess.run(
            [str(SCRIPT), "example.tpl", "example"],
            capture_output=True,
            check=True,
            env=dict(os.environ, PATH=f"{directory}:{os.environ['PATH']}"),
            text=True,
        )

        return log_path.read_text().splitlines(), result.stderr

    def test_injects_when_an_account_is_signed_in(self):
        with tempfile.TemporaryDirectory() as directory:
            log, stderr = self.run_script(directory, "URL EMAIL USER ID\\nmy.1password.com craig@example.com ABC\\n")

            self.assertEqual(
                (log, stderr),
                (
                    [
                        "op account list",
                        "op inject --force --in-file example.tpl --out-file example",
                    ],
                    "",
                ),
            )

    def test_skips_with_warning_when_no_account_is_configured(self):
        with tempfile.TemporaryDirectory() as directory:
            log, stderr = self.run_script(directory, "")

            self.assertEqual(
                (log, stderr),
                (
                    ["op account list"],
                    "Warning: 1Password CLI has no account yet, so example was not generated. "
                    "Turn on Settings > Developer > Integrate with 1Password CLI in the 1Password app, "
                    "then rerun ./install mac.\n",
                ),
            )


if __name__ == "__main__":
    unittest.main()

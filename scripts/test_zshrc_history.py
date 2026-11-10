#!/usr/bin/env python3
"""Test that zshrc sets history options before anything that can be interrupted."""
import pathlib
import subprocess
import unittest


ZSHRC = pathlib.Path(__file__).resolve().parent.parent / "zshrc"


class ZshrcHistoryTest(unittest.TestCase):
    def test_history_settings_precede_first_command(self):
        # Ctrl-C during startup aborts zshrc. A shell left with /etc/zshrc's SAVEHIST=1000 truncates
        # ~/.zsh_history to 1000 lines on exit, so everything up to the first slow command must set history.
        lines = ZSHRC.read_text().splitlines()
        first_command = next(index for index, line in enumerate(lines) if "direnv export" in line)
        prefix = "\n".join(lines[:first_command])
        script = (
            "HISTSIZE=2000; SAVEHIST=1000\n"
            f"{prefix}\n"
            'print "$HISTSIZE $SAVEHIST $options[extendedhistory] $options[incappendhistory]"'
        )
        result = subprocess.run(["zsh", "-f", "-c", script], check=True, capture_output=True, text=True)
        self.assertEqual(result.stdout, "1200000 1000000 on on\n")


if __name__ == "__main__":
    unittest.main()

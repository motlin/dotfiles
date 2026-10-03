#!/usr/bin/env python3
"""Test macos-defaults.sh against fake defaults, killall, and activateSettings."""
import os
import pathlib
import subprocess
import tempfile
import unittest


SCRIPT = pathlib.Path(__file__).with_name("defaults.sh")

# Stores each domain as one line per write, and skips a write it already holds,
# so a second run sees no change just as the real defaults would.
FAKE_DEFAULTS = """#!/bin/sh
echo "defaults $*" >> "{log}"
if [ "$1" = "-currentHost" ]; then
    shift
    host="currentHost."
fi
command="$1"
domain="$2"
shift 2
state="{state}/${{host}}${{domain}}"
# Mimics the error defaults gives for a protected domain without Full Disk Access.
if [ "$command" = write ] && [ "$domain" = "${{DENIED_DOMAIN:-}}" ]; then
    echo "Could not write domain $domain; exiting" >&2
    exit 1
fi
case "$command" in
    export)
        cat "$state" 2>/dev/null
        ;;
    write)
        line="$*"
        grep -qxF -- "$line" "$state" 2>/dev/null || echo "$line" >> "$state"
        ;;
esac
"""

FAKE_LOGGER = """#!/bin/sh
echo "$(basename "$0") $*" >> "{log}"
"""


class MacosDefaultsTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.directory.name)
        self.log = root / "log"
        state = root / "state"
        state.mkdir()
        bin_directory = root / "bin"
        bin_directory.mkdir()

        self.write_executable(bin_directory / "defaults", FAKE_DEFAULTS.format(log=self.log, state=state))
        self.write_executable(bin_directory / "killall", FAKE_LOGGER.format(log=self.log))
        self.activate_settings = bin_directory / "activateSettings"
        self.write_executable(self.activate_settings, FAKE_LOGGER.format(log=self.log))
        self.set_cursor_scale = bin_directory / "set-cursor-scale"
        self.write_executable(self.set_cursor_scale, FAKE_LOGGER.format(log=self.log))
        self.path = f"{bin_directory}:{os.environ['PATH']}"

    def tearDown(self):
        self.directory.cleanup()

    @staticmethod
    def write_executable(path, content):
        path.write_text(content)
        path.chmod(0o755)

    def run_script(self, denied_domain=""):
        if self.log.exists():
            self.log.unlink()
        self.result = subprocess.run(
            ["bash", str(SCRIPT)],
            capture_output=True,
            check=True,
            env=dict(
                os.environ,
                PATH=self.path,
                ACTIVATE_SETTINGS=str(self.activate_settings),
                SET_CURSOR_SCALE=str(self.set_cursor_scale),
                DENIED_DOMAIN=denied_domain,
            ),
            text=True,
        )
        return self.log.read_text().splitlines()

    def test_uses_standard_function_keys(self):
        log = self.run_script()

        self.assertIn("defaults write NSGlobalDomain com.apple.keyboard.fnState -bool true", log)

    def test_enables_tap_to_click_for_the_current_host(self):
        log = self.run_script()

        self.assertIn("defaults -currentHost write NSGlobalDomain com.apple.mouse.tapBehavior -int 1", log)

    def test_moves_between_spaces_with_f14_and_f15(self):
        log = self.run_script()

        move_left = next(line for line in log if "AppleSymbolicHotKeys -dict-add 79 " in line)
        move_right = next(line for line in log if "AppleSymbolicHotKeys -dict-add 81 " in line)
        self.assertIn("<integer>107</integer>", move_left)
        self.assertIn("<integer>113</integer>", move_right)

    def test_first_run_restarts_what_changed(self):
        log = self.run_script()

        self.assertEqual(
            [line for line in log if not line.startswith("defaults ")],
            ["killall Dock", "killall Finder", "set-cursor-scale 2.5", "activateSettings -u"],
        )

    def test_sets_a_larger_pointer(self):
        log = self.run_script()

        self.assertIn("defaults write com.apple.universalaccess mouseDriverCursorSize -float 2.5", log)

    def test_warns_instead_of_failing_without_full_disk_access(self):
        log = self.run_script(denied_domain="com.apple.universalaccess")

        self.assertNotIn("set-cursor-scale 2.5", log)
        self.assertIn("Full Disk Access", self.result.stderr)

    def test_second_run_restarts_nothing(self):
        self.run_script()

        log = self.run_script()

        self.assertEqual([line for line in log if not line.startswith("defaults ")], [])


if __name__ == "__main__":
    unittest.main()

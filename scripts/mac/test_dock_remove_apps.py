#!/usr/bin/env python3
"""Test dock-remove-apps.py against a fake defaults that stores a real plist."""
import os
import pathlib
import plistlib
import subprocess
import tempfile
import unittest


SCRIPT = pathlib.Path(__file__).with_name("dock-remove-apps.py")

FAKE_DEFAULTS = """#!/bin/sh
echo "defaults $*" >> "{log}"
case "$1" in
    export) cat "{plist}" ;;
    import) cat > "{plist}" ;;
esac
"""

FAKE_KILLALL = """#!/bin/sh
echo "killall $*" >> "{log}"
"""


def tile(bundle_identifier):
    return {"tile-data": {"bundle-identifier": bundle_identifier}, "tile-type": "file-tile"}


class DockRemoveAppsTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.directory.name)
        self.log = root / "log"
        self.plist = root / "dock.plist"
        self.plist.write_bytes(
            plistlib.dumps(
                {
                    "persistent-apps": [tile("com.example.Keep"), tile("com.example.Drop")],
                    "wvous-br-corner": 1,
                }
            )
        )
        for name, template in {"defaults": FAKE_DEFAULTS, "killall": FAKE_KILLALL}.items():
            path = root / name
            path.write_text(template.format(log=self.log, plist=self.plist))
            path.chmod(0o755)
        self.path = f"{root}:{os.environ['PATH']}"

    def tearDown(self):
        self.directory.cleanup()

    def run_script(self):
        if self.log.exists():
            self.log.unlink()
        subprocess.run(
            ["python3", str(SCRIPT), "com.example.Drop", "com.example.Absent"],
            capture_output=True,
            check=True,
            env=dict(os.environ, PATH=self.path),
        )
        return self.log.read_text().splitlines()

    def test_removes_only_the_listed_apps(self):
        self.run_script()

        self.assertEqual(
            plistlib.loads(self.plist.read_bytes()),
            {"persistent-apps": [tile("com.example.Keep")], "wvous-br-corner": 1},
        )

    def test_restarts_the_dock_after_a_change(self):
        log = self.run_script()

        self.assertEqual(
            log,
            ["defaults export com.apple.dock -", "defaults import com.apple.dock -", "killall Dock"],
        )

    def test_second_run_changes_nothing(self):
        self.run_script()

        log = self.run_script()

        self.assertEqual(log, ["defaults export com.apple.dock -"])


if __name__ == "__main__":
    unittest.main()

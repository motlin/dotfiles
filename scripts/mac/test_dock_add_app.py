#!/usr/bin/env python3
"""Test dock-add-app.py against a fake defaults that stores a real plist."""
import os
import pathlib
import plistlib
import subprocess
import tempfile
import unittest


SCRIPT = pathlib.Path(__file__).with_name("dock-add-app.py")

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

APP = "/Applications/Example Utility.app"
APP_URL = "file:///Applications/Example%20Utility.app/"


def tile(url):
    return {"tile-data": {"file-data": {"_CFURLString": url, "_CFURLStringType": 15}}, "tile-type": "file-tile"}


class DockAddAppTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.directory.name)
        self.log = root / "log"
        self.plist = root / "dock.plist"
        self.plist.write_bytes(plistlib.dumps({"persistent-apps": [tile("file:///Applications/Example%20Editor.app/")], "wvous-br-corner": 1}))
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
        subprocess.run(["python3", str(SCRIPT), APP], capture_output=True, check=True, env=dict(os.environ, PATH=self.path))
        return self.log.read_text().splitlines()

    def test_appends_the_app_to_the_dock(self):
        self.run_script()

        self.assertEqual(
            plistlib.loads(self.plist.read_bytes()),
            {"persistent-apps": [tile("file:///Applications/Example%20Editor.app/"), tile(APP_URL)], "wvous-br-corner": 1},
        )

    def test_restarts_the_dock_after_a_change(self):
        log = self.run_script()

        self.assertEqual(log, ["defaults export com.apple.dock -", "defaults import com.apple.dock -", "killall Dock"])

    def test_second_run_changes_nothing(self):
        self.run_script()

        log = self.run_script()

        self.assertEqual(log, ["defaults export com.apple.dock -"])


if __name__ == "__main__":
    unittest.main()

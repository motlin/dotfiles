#!/usr/bin/env python3
"""Remove apps from the Dock by bundle identifier.

Usage: dock-remove-apps.py <bundle-identifier> ...

Restarts the Dock only when one of the apps is there.
"""
import plistlib
import subprocess
import sys


def main(bundle_identifiers):
    exported = subprocess.run(
        ["defaults", "export", "com.apple.dock", "-"],
        capture_output=True,
        check=True,
    ).stdout
    dock = plistlib.loads(exported)

    apps = dock.get("persistent-apps", [])
    kept = [app for app in apps if app.get("tile-data", {}).get("bundle-identifier") not in bundle_identifiers]
    if len(kept) == len(apps):
        return

    dock["persistent-apps"] = kept
    subprocess.run(
        ["defaults", "import", "com.apple.dock", "-"],
        input=plistlib.dumps(dock),
        check=True,
    )
    subprocess.run(["killall", "Dock"], check=False)


if __name__ == "__main__":
    main(set(sys.argv[1:]))

#!/usr/bin/env python3
"""Add apps to the end of the Dock.

Usage: dock-add-app.py <app path> ...

Restarts the Dock only when one of the apps wasn't there.
"""
import pathlib
import plistlib
import subprocess
import sys


def main(app_paths):
    exported = subprocess.run(["defaults", "export", "com.apple.dock", "-"], capture_output=True, check=True).stdout
    dock = plistlib.loads(exported)
    apps = dock.setdefault("persistent-apps", [])
    present = {app.get("tile-data", {}).get("file-data", {}).get("_CFURLString") for app in apps}

    added = False
    for path in app_paths:
        url = pathlib.Path(path).as_uri() + "/"
        if url not in present:
            apps.append({"tile-data": {"file-data": {"_CFURLString": url, "_CFURLStringType": 15}}, "tile-type": "file-tile"})
            added = True
    if not added:
        return

    subprocess.run(["defaults", "import", "com.apple.dock", "-"], input=plistlib.dumps(dock), check=True)
    subprocess.run(["killall", "Dock"], check=False)


if __name__ == "__main__":
    main(sys.argv[1:])

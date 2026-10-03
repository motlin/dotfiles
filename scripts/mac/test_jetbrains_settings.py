#!/usr/bin/env python3
"""Test jetbrains-settings.sh against a fake home directory."""
import os
import pathlib
import subprocess
import tempfile
import unittest


SCRIPT = pathlib.Path(__file__).with_name("jetbrains-settings.sh")


class JetbrainsSettingsTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.directory.name)
        self.home = root / "home"
        self.jetbrains = self.home / "Library" / "Application Support" / "JetBrains"
        self.source = root / "jetbrains-settings"
        self.source.mkdir()
        (self.source / "Craig_Light.icls").write_text("light")
        (self.source / "Craig_Dark.icls").write_text("dark")
        (self.source / "live-templates.xml").write_text('<template name="region" />\n')
        (self.source / "postfixTemplates.xml").write_text("postfix")

    def tearDown(self):
        self.directory.cleanup()

    def run_script(self):
        return subprocess.run(
            ["bash", str(SCRIPT), str(self.source)],
            capture_output=True,
            check=True,
            env=dict(os.environ, HOME=str(self.home)),
            text=True,
        )

    def test_installs_color_schemes_into_each_ide(self):
        for ide in ["IntelliJIdea2026.2", "PyCharm2026.2"]:
            (self.jetbrains / ide).mkdir(parents=True)

        self.run_script()

        for ide in ["IntelliJIdea2026.2", "PyCharm2026.2"]:
            self.assertEqual((self.jetbrains / ide / "colors" / "Craig_Dark.icls").read_text(), "dark")

    def test_wraps_live_templates_in_the_craig_group(self):
        (self.jetbrains / "IntelliJIdea2026.2").mkdir(parents=True)

        self.run_script()

        self.assertEqual(
            (self.jetbrains / "IntelliJIdea2026.2" / "templates" / "Craig.xml").read_text(),
            '<templateSet group="Craig">\n<template name="region" />\n</templateSet>\n',
        )

    def test_keeps_existing_postfix_templates(self):
        options = self.jetbrains / "IntelliJIdea2026.2" / "options"
        options.mkdir(parents=True)
        (options / "postfixTemplates.xml").write_text("edited in the IDE")

        self.run_script()

        self.assertEqual((options / "postfixTemplates.xml").read_text(), "edited in the IDE")

    def test_skips_directories_that_are_not_ide_configs(self):
        (self.jetbrains / "Toolbox").mkdir(parents=True)
        (self.jetbrains / "consentOptions").mkdir(parents=True)

        self.run_script()

        self.assertFalse((self.jetbrains / "Toolbox" / "colors").exists())
        self.assertFalse((self.jetbrains / "consentOptions" / "colors").exists())

    def test_reports_when_no_ide_has_launched(self):
        result = self.run_script()

        self.assertIn("launch each IDE once", result.stdout)


if __name__ == "__main__":
    unittest.main()

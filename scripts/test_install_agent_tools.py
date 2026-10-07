#!/usr/bin/env python3
"""Test the skill installation functions in install-agent-tools.sh."""
import os
import pathlib
import shutil
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


def write_fake_command(directory, name, body):
    path = pathlib.Path(directory, name)
    path.write_text(f"#!/bin/sh\n{body}\n")
    path.chmod(0o755)


def run_sourced(command, environment):
    return subprocess.run(
        ["bash", "-c", f'source "{INSTALL_SCRIPT}" && {command}'],
        check=True,
        capture_output=True,
        env=environment,
        text=True,
    ).stdout


class CodexToolsEnabledTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.directory)
        self.environment = dict(os.environ, PATH=f"{self.directory}:{os.environ['PATH']}")
        self.environment.pop("DOTFILES_INSTALL_CODEX_TOOLS", None)

    def enabled(self):
        return run_sourced(
            "if codex_tools_enabled; then echo yes; else echo no; fi", self.environment
        ).strip()

    def test_explicit_true_enables_codex_tools(self):
        self.environment["DOTFILES_INSTALL_CODEX_TOOLS"] = "true"
        self.assertEqual(self.enabled(), "yes")

    def test_explicit_false_disables_codex_tools_even_when_codex_is_installed(self):
        write_fake_command(self.directory, "codex", "exit 0")
        self.environment["DOTFILES_INSTALL_CODEX_TOOLS"] = "false"
        self.assertEqual(self.enabled(), "no")

    def test_unset_falls_back_to_codex_on_path(self):
        write_fake_command(self.directory, "codex", "exit 0")
        self.assertEqual(self.enabled(), "yes")

    def test_unset_without_codex_on_path_disables_codex_tools(self):
        bin_directory = pathlib.Path(self.directory, "bin")
        bin_directory.mkdir()
        for name in ("bash", "jq"):
            os.symlink(shutil.which(name), bin_directory / name)
        self.environment["PATH"] = f"{bin_directory}:/usr/bin:/bin"
        self.assertEqual(self.enabled(), "no")


class InstallGithubStackToolsTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.directory)
        self.log_path = pathlib.Path(self.directory, "gh.log")
        self.environment = dict(
            os.environ,
            PATH=f"{self.directory}:{os.environ['PATH']}",
            DOTFILES_INSTALL_CODEX_TOOLS="false",
        )

    def install(self, installed_extensions):
        write_fake_command(
            self.directory,
            "gh",
            f'echo "$*" >> "{self.log_path}"\n'
            f'if [ "$1 $2" = "extension list" ]; then printf "{installed_extensions}"; fi',
        )
        run_sourced("install_github_stack_tools", self.environment)
        return self.log_path.read_text().splitlines()

    def test_installs_extension_when_missing(self):
        self.assertEqual(
            self.install(""),
            [
                "extension list",
                "extension install github/gh-stack",
                "skill install github/gh-stack gh-stack --agent claude-code --scope user --force",
            ],
        )

    def test_skips_extension_install_when_already_present(self):
        self.assertEqual(
            self.install("gh stack\\tgithub/gh-stack\\tv1.0.0\\n"),
            [
                "extension list",
                "skill install github/gh-stack gh-stack --agent claude-code --scope user --force",
            ],
        )


if __name__ == "__main__":
    unittest.main()

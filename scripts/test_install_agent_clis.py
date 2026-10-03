#!/usr/bin/env python3
"""Test install-agent-clis.sh against fake package managers and installers."""
import os
import pathlib
import subprocess
import tempfile
import unittest


INSTALL_SCRIPT = pathlib.Path(__file__).with_name("install-agent-clis.sh")


def write_executable(path, content):
    path.write_text(content)
    path.chmod(0o755)


class InstallAgentClisTest(unittest.TestCase):
    def run_script(self, directory, *, native_installed):
        bin_directory = pathlib.Path(directory, "bin")
        home = pathlib.Path(directory, "home")
        local_bin = home / ".local" / "bin"
        log_path = pathlib.Path(directory, "commands.log")
        bin_directory.mkdir()
        local_bin.mkdir(parents=True)

        if native_installed:
            write_executable(local_bin / "codex", "#!/bin/sh\n")
            write_executable(local_bin / "claude", "#!/bin/sh\n")

        write_executable(
            bin_directory / "mise",
            f"""#!/bin/sh
echo "mise $*" >> "{log_path}"
if [ "$1 $2 $3" = "ls --installed npm:@openai/codex" ]; then
    echo "npm:@openai/codex  0.0.1"
fi
""",
        )
        write_executable(
            bin_directory / "npm",
            f"""#!/bin/sh
echo "npm $*" >> "{log_path}"
[ "$1" != ls ] || [ "$4" = @anthropic-ai/claude-code ]
""",
        )
        write_executable(
            bin_directory / "brew",
            f"""#!/bin/sh
echo "brew $*" >> "{log_path}"
[ "$1" != list ] || [ "$3" = codex ]
""",
        )
        write_executable(
            bin_directory / "curl",
            f"""#!/bin/sh
echo "curl $*" >> "{log_path}"
echo 'echo "installer PATH=$PATH CODEX_NON_INTERACTIVE=$CODEX_NON_INTERACTIVE" >> "{log_path}"'
""",
        )

        subprocess.run(
            ["bash", str(INSTALL_SCRIPT)],
            check=True,
            env={"HOME": str(home), "PATH": f"{bin_directory}:/usr/bin:/bin"},
        )

        return log_path.read_text().splitlines(), local_bin, bin_directory

    def test_removes_other_installs_then_runs_native_installers(self):
        with tempfile.TemporaryDirectory() as directory:
            log, local_bin, bin_directory = self.run_script(directory, native_installed=False)

            installer_path = f"{local_bin}:{bin_directory}:/usr/bin:/bin"
            self.assertEqual(
                log,
                [
                    "mise ls --installed npm:@openai/codex",
                    "mise uninstall --all npm:@openai/codex",
                    "npm ls --global --depth=0 @openai/codex",
                    "brew list --cask codex",
                    "brew uninstall --cask codex",
                    "curl -fsSL https://chatgpt.com/codex/install.sh",
                    f"installer PATH={installer_path} CODEX_NON_INTERACTIVE=true",
                    "mise ls --installed npm:@anthropic-ai/claude-code",
                    "npm ls --global --depth=0 @anthropic-ai/claude-code",
                    "npm uninstall --global @anthropic-ai/claude-code",
                    "brew list --cask claude-code",
                    "curl -fsSL https://claude.ai/install.sh",
                    f"installer PATH={installer_path} CODEX_NON_INTERACTIVE=true",
                ],
            )

    def test_skips_native_installers_when_already_installed(self):
        with tempfile.TemporaryDirectory() as directory:
            log, _, _ = self.run_script(directory, native_installed=True)

            self.assertEqual(
                log,
                [
                    "mise ls --installed npm:@openai/codex",
                    "mise uninstall --all npm:@openai/codex",
                    "npm ls --global --depth=0 @openai/codex",
                    "brew list --cask codex",
                    "brew uninstall --cask codex",
                    "mise ls --installed npm:@anthropic-ai/claude-code",
                    "npm ls --global --depth=0 @anthropic-ai/claude-code",
                    "npm uninstall --global @anthropic-ai/claude-code",
                    "brew list --cask claude-code",
                ],
            )


if __name__ == "__main__":
    unittest.main()

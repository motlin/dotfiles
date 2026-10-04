#!/usr/bin/env python3
"""Test install-agent-clis.sh against fake package managers and installers."""
import pathlib
import subprocess
import tempfile
import unittest


INSTALL_SCRIPT = pathlib.Path(__file__).with_name("install-agent-clis.sh")


def write_executable(path, content):
    path.write_text(content)
    path.chmod(0o755)


class InstallAgentClisTest(unittest.TestCase):
    def run_script(self, directory, *, native_installed, shadowed_command=None):
        bin_directory = pathlib.Path(directory, "bin")
        home = pathlib.Path(directory, "home")
        local_bin = home / ".local" / "bin"
        log_path = pathlib.Path(directory, "commands.log")
        bin_directory.mkdir()
        local_bin.mkdir(parents=True)

        if native_installed:
            write_executable(local_bin / "codex", "#!/bin/sh\n")
            write_executable(local_bin / "claude", "#!/bin/sh\n")

        # A stale copy earlier on PATH, like a mise shim left behind by an older Node version.
        if shadowed_command is not None:
            write_executable(bin_directory / shadowed_command, "#!/bin/sh\n")

        write_executable(
            bin_directory / "mise",
            f"""#!/bin/sh
echo "mise $*" >> "{log_path}"
case "$*" in
    "ls --installed npm:@openai/codex") echo "npm:@openai/codex  0.0.1" ;;
    "ls --installed node") echo "node  24.13.0"; echo "node  26.10.0" ;;
    "exec node@24.13.0 -- npm ls --global --depth=0 @openai/codex") exit 0 ;;
    "exec "*" -- npm ls "*) exit 1 ;;
esac
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
case "$2" in
    *chatgpt.com*) command_name=codex ;;
    *) command_name=claude ;;
esac
echo 'echo "installer PATH=$PATH CODEX_NON_INTERACTIVE=$CODEX_NON_INTERACTIVE" >> "{log_path}"'
echo "printf '#!/bin/sh\\\\n' > \\"\\$HOME/.local/bin/$command_name\\""
echo "chmod +x \\"\\$HOME/.local/bin/$command_name\\""
""",
        )

        # Mirrors ./install, where mise shims come before ~/.local/bin.
        completed = subprocess.run(
            ["bash", str(INSTALL_SCRIPT)],
            capture_output=True,
            text=True,
            env={"HOME": str(home), "PATH": f"{bin_directory}:{local_bin}:/usr/bin:/bin"},
        )

        return completed, log_path.read_text().splitlines(), local_bin, bin_directory

    def test_removes_other_installs_then_runs_native_installers(self):
        with tempfile.TemporaryDirectory() as directory:
            completed, log, local_bin, bin_directory = self.run_script(directory, native_installed=False)

            installer_path = f"{local_bin}:{bin_directory}:{local_bin}:/usr/bin:/bin"
            self.assertEqual(
                (completed.returncode, completed.stderr, log),
                (
                    0,
                    "",
                    [
                        "mise ls --installed npm:@openai/codex",
                        "mise uninstall --all npm:@openai/codex",
                        "mise ls --installed node",
                        "mise exec node@24.13.0 -- npm ls --global --depth=0 @openai/codex",
                        "mise exec node@24.13.0 -- npm uninstall --global @openai/codex",
                        "mise exec node@26.10.0 -- npm ls --global --depth=0 @openai/codex",
                        "npm ls --global --depth=0 @openai/codex",
                        "brew list --cask codex",
                        "brew uninstall --cask codex",
                        "mise reshim",
                        "curl -fsSL https://chatgpt.com/codex/install.sh",
                        f"installer PATH={installer_path} CODEX_NON_INTERACTIVE=true",
                        "mise ls --installed npm:@anthropic-ai/claude-code",
                        "mise ls --installed node",
                        "mise exec node@24.13.0 -- npm ls --global --depth=0 @anthropic-ai/claude-code",
                        "mise exec node@26.10.0 -- npm ls --global --depth=0 @anthropic-ai/claude-code",
                        "npm ls --global --depth=0 @anthropic-ai/claude-code",
                        "npm uninstall --global @anthropic-ai/claude-code",
                        "brew list --cask claude-code",
                        "mise reshim",
                        "curl -fsSL https://claude.ai/install.sh",
                        f"installer PATH={installer_path} CODEX_NON_INTERACTIVE=true",
                    ],
                ),
            )

    def test_skips_native_installers_when_already_installed(self):
        with tempfile.TemporaryDirectory() as directory:
            completed, log, _, _ = self.run_script(directory, native_installed=True)

            self.assertEqual(
                (completed.returncode, completed.stderr, log),
                (
                    0,
                    "",
                    [
                        "mise ls --installed npm:@openai/codex",
                        "mise uninstall --all npm:@openai/codex",
                        "mise ls --installed node",
                        "mise exec node@24.13.0 -- npm ls --global --depth=0 @openai/codex",
                        "mise exec node@24.13.0 -- npm uninstall --global @openai/codex",
                        "mise exec node@26.10.0 -- npm ls --global --depth=0 @openai/codex",
                        "npm ls --global --depth=0 @openai/codex",
                        "brew list --cask codex",
                        "brew uninstall --cask codex",
                        "mise reshim",
                        "mise ls --installed npm:@anthropic-ai/claude-code",
                        "mise ls --installed node",
                        "mise exec node@24.13.0 -- npm ls --global --depth=0 @anthropic-ai/claude-code",
                        "mise exec node@26.10.0 -- npm ls --global --depth=0 @anthropic-ai/claude-code",
                        "npm ls --global --depth=0 @anthropic-ai/claude-code",
                        "npm uninstall --global @anthropic-ai/claude-code",
                        "brew list --cask claude-code",
                        "mise reshim",
                    ],
                ),
            )

    def test_fails_when_another_copy_still_comes_first_on_path(self):
        with tempfile.TemporaryDirectory() as directory:
            completed, _, local_bin, bin_directory = self.run_script(
                directory, native_installed=True, shadowed_command="codex"
            )

            self.assertEqual(
                (completed.returncode, completed.stderr),
                (
                    1,
                    f"codex resolves to {bin_directory}/codex instead of {local_bin}/codex;"
                    " remove that copy and run ./install again.\n",
                ),
            )


if __name__ == "__main__":
    unittest.main()

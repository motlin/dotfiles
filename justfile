set shell := ["bash", "-O", "globstar", "-c"]
set dotenv-filename := ".envrc"

# Excludes the JetBrains Toolbox launchers in bin/; Toolbox owns their formatting.
bash_scripts := "install bashrc bash_profile scripts/*.sh bin/add-eol bin/clean-worktrees bin/describe-image bin/rgb bin/set-url bin/should-skip-commit bin/tm bin/woof bin/woof.tpl bin/worktree"

# Sourced shell files (no shebang) that lint cleanly as bash. Add more as zsh-only syntax is fixed or excluded.
sourced_scripts := "alias alias.mac env"

default:
    @just --list --unsorted

# Check shell script formatting with shfmt and oxfmt
format:
    shfmt -d -i 4 -ci {{ bash_scripts }}
    shfmt -d -i 4 -ci -ln bash {{ sourced_scripts }}
    oxfmt --check

# Run shellcheck, markdownlint, and yamllint
lint:
    shellcheck {{ bash_scripts }}
    shellcheck --shell=bash {{ sourced_scripts }}
    markdownlint-cli2
    yamllint --strict .

# Run all pre-commit checks
precommit: format lint
    pre-commit run --all-files

push:
    git pushf public refs/heads/public:main
    git pushf private refs/heads/private:main
    git pushf public refs/heads/work:work

upstream_remote := env('UPSTREAM_REMOTE', "public")
upstream_branch := env('UPSTREAM_BRANCH', "main")

pull:
    git checkout main
    git pull public main --rebase
    git checkout private
    git pull private main --rebase

# git rebase onto configurable upstream/main
rebase:
    git fetch {{upstream_remote}} {{upstream_branch}}
    git rebase --interactive --autosquash {{upstream_remote}}/{{upstream_branch}}^

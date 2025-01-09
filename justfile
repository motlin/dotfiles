set shell := ["bash", "-O", "globstar", "-c"]
set dotenv-filename := ".envrc"

push:
    git pushf public main
    git pushf private private:main

upstream_remote := env('UPSTREAM_REMOTE', "public")
upstream_branch := env('UPSTREAM_BRANCH', "main")
# git rebase onto configurable upstream/main
rebase:
    git fetch {{upstream_remote}} {{upstream_branch}}
    git rebase --interactive --autosquash {{upstream_remote}}/{{upstream_branch}}^

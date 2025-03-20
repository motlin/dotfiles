set shell := ["bash", "-O", "globstar", "-c"]
set dotenv-filename := ".envrc"

default:
    @just --list --unsorted

push:
    git pushf public main
    git pushf private refs/heads/private:main

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

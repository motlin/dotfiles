# `git rebase` onto configurable upstream/main
[group('git-rebase')]
@rebase interactive="true": _check-local-modifications fetch
    just --global-justfile _run "git rebase {{ if interactive == 'true' { '--interactive' } else { '' } }} --autosquash --rebase-merges --update-refs {{ANSI_BRIGHT_RED}}{{ANSI_BOLD}}{{upstream_remote}}/{{upstream_branch}}{{ANSI_NORMAL}}"

# Rebase all branches onto configurable upstream/main or matching up-to-date origin branch
[group('git-rebase')]
rebase-all: _check-local-modifications fetch
    #!/usr/bin/env bash
    set -Eeuo pipefail

    branches=($(git for-each-ref --format='%(refname:short)' refs/heads/ --sort -committerdate --no-contains {{upstream_remote}}/{{upstream_branch}}))
    total=${#branches[@]}
    current=0

    for branch in "${branches[@]}"
    do
        current=$((current + 1))
        included_count=$(git branch --contains "$branch" | wc -l)
        if [ "$included_count" -gt 1 ]; then
            echo "[{{ANSI_YELLOW}}${current}{{ANSI_DEFAULT}}/${total}] {{ANSI_YELLOW}}Skipping{{ANSI_NORMAL}} branch {{ANSI_BRIGHT_GREEN}}{{ANSI_BOLD}}$branch{{ANSI_NORMAL}} as it is {{ANSI_BG_BRIGHT_CYAN}}{{ANSI_BLACK}}included in other branches{{ANSI_NORMAL}}"
            continue
        fi

        current_branch=$(git symbolic-ref --short HEAD 2>/dev/null || echo "")
        if [ "$branch" != "$current_branch" ] && git worktree list 2>/dev/null | grep -q "\[$branch\]"; then
            echo "[{{ANSI_YELLOW}}${current}{{ANSI_DEFAULT}}/${total}] {{ANSI_YELLOW}}Skipping{{ANSI_NORMAL}} branch {{ANSI_BRIGHT_GREEN}}{{ANSI_BOLD}}$branch{{ANSI_NORMAL}} as it is {{ANSI_BG_BRIGHT_MAGENTA}}{{ANSI_BLACK}}currently checked out in another worktree{{ANSI_NORMAL}}"
            continue
        fi

        if ! git checkout --quiet "$branch" 2>/dev/null; then
            echo "[{{ANSI_YELLOW}}${current}{{ANSI_DEFAULT}}/${total}] {{ANSI_YELLOW}}Skipping{{ANSI_NORMAL}} branch {{ANSI_BRIGHT_GREEN}}{{ANSI_BOLD}}$branch{{ANSI_NORMAL}} as it {{ANSI_BG_BRIGHT_BLUE}}{{ANSI_BLACK}}cannot be checked out{{ANSI_NORMAL}} (possibly in use by a worktree)"
            continue
        fi

        rebase_message="[{{ANSI_YELLOW}}${current}{{ANSI_DEFAULT}}/${total}] {{ANSI_GREEN}}Rebasing{{ANSI_NORMAL}} branch {{ANSI_BRIGHT_GREEN}}{{ANSI_BOLD}}$branch{{ANSI_NORMAL}} onto"

        # Check if origin/$branch exists
        if git rev-parse --verify origin/$branch &>/dev/null; then
            # Check if upstream/master is an ancestor of origin/$branch
            if git merge-base --is-ancestor {{upstream_remote}}/{{upstream_branch}} origin/$branch; then
                echo "$rebase_message {{ANSI_BRIGHT_RED}}{{ANSI_BOLD}}origin/$branch{{ANSI_NORMAL}} (because origin/$branch exists and is {{ANSI_CYAN}}up-to-date{{ANSI_NORMAL}} with {{upstream_remote}}/{{upstream_branch}})"
                git rebase --rebase-merges --update-refs --quiet origin/$branch
            else
                echo "$rebase_message {{ANSI_BRIGHT_RED}}{{ANSI_BOLD}}{{upstream_remote}}/{{upstream_branch}}{{ANSI_NORMAL}} (because origin/$branch exists but is {{ANSI_BLUE}}not an ancestor{{ANSI_NORMAL}})"
                git rebase --rebase-merges --update-refs --quiet {{upstream_remote}}/{{upstream_branch}}
            fi
        else
            echo "$rebase_message {{ANSI_BRIGHT_RED}}{{ANSI_BOLD}}{{upstream_remote}}/{{upstream_branch}}{{ANSI_NORMAL}} (because origin/$branch {{ANSI_MAGENTA}}does not exist{{ANSI_NORMAL}})"
            git rebase --rebase-merges --update-refs --quiet {{upstream_remote}}/{{upstream_branch}}
        fi
    done

alias ra := rebase-all

# `git absorb` into configurable upstream/main
[group('git-rebase')]
@absorb *FLAGS:
    just --global-justfile _run "git absorb --base {{ANSI_BRIGHT_RED}}{{ANSI_BOLD}}{{upstream_remote}}/{{upstream_branch}}{{ANSI_NORMAL}} --force {{FLAGS}}"

# `git worktree prune --verbose`
[group('git-rebase')]
worktree-prune:
    git worktree prune --verbose

# Delete local branches merged into configurable upstream/main
[group('git-rebase')]
delete-merged-local: fetch
    #!/usr/bin/env bash
    set -Eeu                         # No pipefail or the grep commands fail when nothing needs to be deleted

    git branch --merged remotes/{{upstream_remote}}/{{upstream_branch}} |
        grep --invert-match "^\*" |  # Exclude current branch
        grep --invert-match "^+" |   # Exclude branches checked out in worktrees (marked with +)
        sed 's/^[[:space:]]*//' |    # Trim leading whitespace
        xargs --no-run-if-empty git branch -D

# Delete branches from origin merged into configurable upstream/main
[group('git-rebase')]
delete-merged-remote: fetch
    #!/usr/bin/env bash
    set -Eeu
    if [ "{{offline}}" != "true" ]; then
        git branch --remote --list 'origin/*' --merged remotes/{{upstream_remote}}/{{upstream_branch}} \
            | grep --invert-match {{upstream_branch}} \
            | grep --invert-match HEAD \
            | grep "origin/" \
            | grep --invert-match "origin/pr/" \
            | cut -d "/" -f 2- \
            | xargs --no-run-if-empty git push --delete origin
    else
        echo "Skipping delete-remote-merged in offline mode"
    fi

# Delete local and remote branches that are merged into configurable upstream/main
[group('git-rebase')]
delete-merged: delete-merged-local delete-merged-remote

# Delete branches from origin matching a prefix pattern
[group('git-rebase')]
delete-prefix PREFIX: fetch
    #!/usr/bin/env bash
    set -Eeuo pipefail

    echo "🔍 Finding remote branches starting with '{{PREFIX}}'..."
    echo

    branches=$(git branch --remote --list "origin/{{PREFIX}}*" | sed 's/^[[:space:]]*origin\///' || true)

    if [ -z "$branches" ]; then
        echo "✅ No branches starting with '{{PREFIX}}' found on origin."
        exit 0
    fi

    branch_count=$(echo "$branches" | wc -l | xargs)
    echo "📋 Found $branch_count branch(es) to delete:"
    echo
    echo "$branches" | sed 's/^/  - /'
    echo

    read -p "❓ Delete these branches from origin? (y/N) " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Cancelled. No branches were deleted."
        exit 0
    fi

    echo "🗑️  Deleting branches..."
    echo

    branches_args=$(echo "$branches" | tr '\n' ' ')

    # shellcheck disable=SC2086
    git push origin --delete $branches_args

    echo
    echo "✅ Successfully deleted $branch_count branch(es) from origin."

# Delete branches from origin starting with fix-
[group('git-rebase')]
delete-fix-branches: (delete-prefix "fix-")

[group('git-rebase')]
git-all: rebase-all worktree-prune delete-merged
alias g := git-all

fail_fast := env('FAIL_FAST', "false")

git_tests := env('GIT_TESTS', "default")

# `git-test` on the range of commits between a configurable upstream/main and {{BRANCH}}
test-branch BRANCH="HEAD" TESTS=git_tests *FLAGS="--retest --verbose --verbose":
    #!/usr/bin/env bash
    branch="{{BRANCH}}"
    if [ "$branch" = "HEAD" ]; then
        branch=$(git branch --show-current)
        if [ -z "$branch" ]; then
            branch=$(git rev-parse HEAD)
        fi
    fi
    echo "$branch" > JUSTFILE_BRANCH
    tests=$([ -n "{{TESTS}}" ] && echo "--tests {{TESTS}}" || echo "")
    just --global-justfile _run "git test run {{ANSI_GRAY}}${tests}{{ANSI_DEFAULT}} {{FLAGS}} {{ANSI_BRIGHT_RED}}{{ANSI_BOLD}}{{upstream_remote}}/{{upstream_branch}}{{ANSI_NORMAL}}..{{ANSI_BRIGHT_GREEN}}{{ANSI_BOLD}}${branch}{{ANSI_NORMAL}}"

# `just test` all commits with configurable upstream/main as ancestor
test-all TESTS=git_tests *FLAGS="--retest --verbose --verbose":
    #!/usr/bin/env bash
    set -uo pipefail

    if [ "{{fail_fast}}" ]; then
        set -Ee
    fi

    branches=($(git for-each-ref --format='%(refname:short)' refs/heads/ --sort -committerdate --contains {{upstream_remote}}/{{upstream_branch}}))

    total_branches=${#branches[@]}
    echo "Found {{ANSI_YELLOW}}${total_branches}{{ANSI_DEFAULT}} branches containing remote ref {{ANSI_BRIGHT_RED}}{{ANSI_BOLD}}{{upstream_remote}}/{{upstream_branch}}{{ANSI_NORMAL}} as ancestor: {{ANSI_GREEN}}${branches[@]}{{ANSI_NORMAL}}"

    current=1
    for branch in "${branches[@]}"
    do
        echo -n "[{{ANSI_YELLOW}}${current}{{ANSI_DEFAULT}}/${total_branches}] "
        just --global-justfile _run "{{ANSI_BRIGHT_RED}}just{{ANSI_DEFAULT}} --global-justfile test-branch {{ANSI_BRIGHT_GREEN}}{{ANSI_BOLD}}\"${branch}\"{{ANSI_NORMAL}} {{ANSI_GRAY}}'{{TESTS}}'{{ANSI_DEFAULT}} {{FLAGS}}"
        ((current++))
    done

alias ta := test-all

# `just test results` all branches with configurable upstream/main as ancestor
test-results:
    #!/usr/bin/env bash
    set -uo pipefail

    branches=($(git for-each-ref --format='%(refname:short)' refs/heads/ --sort -committerdate --contains {{upstream_remote}}/{{upstream_branch}}))

    total_branches=${#branches[@]}
    echo "Found {{ANSI_YELLOW}}${total_branches}{{ANSI_DEFAULT}} branches containing remote ref {{ANSI_BRIGHT_RED}}{{ANSI_BOLD}}{{upstream_remote}}/{{upstream_branch}}{{ANSI_NORMAL}}{{ANSI_DEFAULT}} as ancestor: {{ANSI_BRIGHT_GREEN}}${branches[@]}{{ANSI_NORMAL}}"

    current=1
    for branch in "${branches[@]}"
    do
        echo -n "[{{ANSI_YELLOW}}${current}{{ANSI_DEFAULT}}/${total_branches}] "
        just --global-justfile _run "git test results --color {{ANSI_BRIGHT_RED}}{{ANSI_BOLD}}{{upstream_remote}}/{{upstream_branch}}{{ANSI_NORMAL}}..{{ANSI_BRIGHT_GREEN}}{{ANSI_BOLD}}${branch}{{ANSI_NORMAL}}"
        ((current++))
    done

# Fix the current commit and `git rebase`
test-fix:
    #!/usr/bin/env bash
    set -Eeuo pipefail

    echo "{{ANSI_BOLD}}Staging changes.{{ANSI_NORMAL}}"
    just --global-justfile _run "git add --update"

    echo "{{ANSI_BOLD}}Committing fixup.{{ANSI_NORMAL}}"
    just --global-justfile _run "git commit --quiet --fixup {{ANSI_BOLD}}{{ANSI_CYAN}}HEAD{{ANSI_NORMAL}}"

    echo "{{ANSI_BOLD}}Checking for unstaged files.{{ANSI_NORMAL}}"
    just --global-justfile _check-local-modifications

    BRANCH=$(cat JUSTFILE_BRANCH)
    echo "Rebasing the last branch used with just test-fix: {{ANSI_BRIGHT_GREEN}}{{ANSI_BOLD}}$BRANCH{{ANSI_NORMAL}}"
    just --global-justfile _run "git rebase --quiet --onto HEAD HEAD^ {{ANSI_BRIGHT_GREEN}}{{ANSI_BOLD}}$BRANCH{{ANSI_NORMAL}}"
    just --global-justfile _run "git checkout --quiet $BRANCH"

    echo "{{ANSI_BOLD}}Squashing changes.{{ANSI_NORMAL}}"
    just --global-justfile _run "just --global-justfile rebase"

    echo "{{ANSI_BOLD}}Cleaning up.{{ANSI_NORMAL}}"
    just --global-justfile _run "rm {{ANSI_YELLOW}}JUSTFILE_BRANCH{{ANSI_NORMAL}}"

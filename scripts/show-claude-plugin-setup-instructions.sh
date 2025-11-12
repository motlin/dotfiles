#!/usr/bin/env bash

set -euo pipefail

if [ ! -L ~/.claude/plugins/marketplaces/motlin-claude-code-plugins ]; then
    echo ""
    echo "🔌 Run these commands to set up the marketplace and plugins:"
    echo "/plugin marketplace add ~/.claude/plugins/marketplaces/motlin-claude-code-plugins"
    echo "/plugin install markdown-tasks@motlin-claude-code-plugins"
    echo ""
fi

if [ ! -L ~/.claude/plugins/marketplaces/claude-code-plugins ]; then
    echo ""
    echo "🔌 Run these commands to set up the marketplace and plugins:"
    echo "/plugin marketplace add ~/.claude/plugins/marketplaces/claude-code-plugins"
    echo "/plugin install pr-review-toolkit@claude-code-plugins"
    echo "/plugin install commit-commands@claude-code-plugins"
    echo "/plugin install feature-dev@claude-code-plugins"
    echo "/plugin install agent-sdk-dev@claude-code-plugins"
    echo ""
fi

if [ ! -L ~/.claude/plugins/marketplaces/anthropic-agent-skills ]; then
    echo ""
    echo "🔌 Run these commands to set up the marketplace and plugins:"
    echo "/plugin marketplace add ~/.claude/plugins/marketplaces/anthropic-agent-skills"
    echo "/plugin install example-skills@anthropic-agent-skills"
    echo ""
fi

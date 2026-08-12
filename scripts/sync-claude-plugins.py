#!/usr/bin/env python3
"""Synchronize configured Claude plugin marketplaces and plugins.

Research reads Claude's marketplace and plugin state plus the local settings and
marketplace manifests. Diff computation is pure so callers can report or apply
the returned actions separately.

Usage:
    sync-claude-plugins.py [--verbose] [--json]
"""
import argparse
import json
import os
import subprocess
import sys


CLAUDE_SETTINGS = os.path.expanduser("~/.claude/settings.json")
CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "install-agent-tools.config.json",
)
PLUGIN_ACTIONS = ("add", "remove", "unchanged")


def sh(args):
    return subprocess.run(
        args,
        capture_output=True,
        check=True,
        text=True,
    ).stdout


def read_json(path):
    with open(path) as file:
        return json.load(file)


def research(config):
    marketplaces = json.loads(
        sh(["claude", "plugin", "marketplace", "list", "--json"])
    )
    installed = json.loads(sh(["claude", "plugin", "list", "--json"]))
    settings = read_json(CLAUDE_SETTINGS) if os.path.exists(CLAUDE_SETTINGS) else {}
    marketplaces_by_name = {
        marketplace["name"]: marketplace for marketplace in marketplaces
    }
    manifests = {}

    for specification in config["claudeMarketplaces"]:
        if specification["plugins"] != "*":
            continue
        marketplace = marketplaces_by_name.get(specification["name"])
        if marketplace is None:
            continue
        manifest_path = os.path.join(
            marketplace["installLocation"],
            ".claude-plugin",
            "marketplace.json",
        )
        manifests[specification["name"]] = read_json(manifest_path)

    return marketplaces, installed, settings, manifests


def desired_plugin_names(specification, manifests):
    if specification["plugins"] != "*":
        return specification["plugins"]

    manifest = manifests.get(specification["name"])
    if manifest is None:
        return None

    exclusions = set(specification.get("excludePlugins", []))
    return [
        plugin["name"]
        for plugin in manifest["plugins"]
        if plugin["name"] not in exclusions
    ]


def compute_actions(config, marketplaces, installed, settings, manifests):
    actions = []
    marketplaces_by_name = {
        marketplace["name"]: marketplace for marketplace in marketplaces
    }
    installed_ids = {plugin["id"] for plugin in installed}
    enabled_plugins = settings.get("enabledPlugins", {})
    desired_ids = set()
    pending_marketplaces = set()

    for specification in config["claudeMarketplaces"]:
        name = specification["name"]
        marketplace = marketplaces_by_name.get(name)
        if marketplace is None:
            actions.append({
                "action": "add",
                "marketplace": name,
                "source": specification["source"],
            })
        elif marketplace["source"] == "github":
            if marketplace["repo"] != specification["source"]:
                raise ValueError(
                    f"Marketplace {name} source mismatch: expected "
                    f"{specification['source']}, found {marketplace['repo']}"
                )
        else:
            actions.append({
                "action": "migrate",
                "marketplace": name,
                "source": specification["source"],
            })

        plugin_names = desired_plugin_names(specification, manifests)
        if plugin_names is None:
            pending_marketplaces.add(name)
            actions.append({
                "action": "pending",
                "marketplace": name,
            })
            continue

        for plugin_name in plugin_names:
            plugin_id = f"{plugin_name}@{name}"
            desired_ids.add(plugin_id)
            action = "unchanged" if plugin_id in installed_ids else "add"
            actions.append({"action": action, "id": plugin_id})
            if plugin_id not in enabled_plugins:
                actions.append({"action": "enable", "id": plugin_id})

    managed_marketplaces = {
        specification["name"]
        for specification in config["claudeMarketplaces"]
    }

    for plugin in installed:
        plugin_id = plugin["id"]
        marketplace_name = plugin_id.rpartition("@")[2]
        if (
            plugin["scope"] == "user"
            and marketplace_name in managed_marketplaces
            and marketplace_name not in pending_marketplaces
            and plugin_id not in desired_ids
        ):
            actions.append({"action": "remove", "id": plugin_id})

    for plugin_id in enabled_plugins:
        marketplace_name = plugin_id.rpartition("@")[2]
        if (
            marketplace_name in managed_marketplaces
            and marketplace_name not in pending_marketplaces
            and plugin_id not in desired_ids
        ):
            actions.append({"action": "forget", "id": plugin_id})

    return actions


def action_marketplace(action):
    if "id" in action:
        return action["id"].rpartition("@")[2]
    return action["marketplace"]


def format_summary_table(actions):
    marketplace_names = {
        action_marketplace(action)
        for action in actions
        if "id" in action or "marketplace" in action
    }
    counts = {
        name: {plugin_action: 0 for plugin_action in PLUGIN_ACTIONS}
        for name in marketplace_names
    }

    for action in actions:
        if action["action"] not in PLUGIN_ACTIONS or "id" not in action:
            continue
        counts[action_marketplace(action)][action["action"]] += 1

    marketplace_width = max(
        28,
        len("Marketplace"),
        *(len(name) for name in marketplace_names),
    )
    header = (
        f"{'Marketplace':<{marketplace_width}}  "
        f"{'Add':>3}  {'Remove':>6}  {'Unchanged':>9}"
    )
    separator = "-" * len(header)
    lines = [header, separator]

    for name in sorted(marketplace_names):
        marketplace_counts = counts[name]
        lines.append(
            f"{name:<{marketplace_width}}  "
            f"{marketplace_counts['add']:>3}  "
            f"{marketplace_counts['remove']:>6}  "
            f"{marketplace_counts['unchanged']:>9}"
        )

    totals = {
        plugin_action: sum(
            marketplace_counts[plugin_action]
            for marketplace_counts in counts.values()
        )
        for plugin_action in PLUGIN_ACTIONS
    }
    lines.extend([
        separator,
        f"{'TOTAL':<{marketplace_width}}  "
        f"{totals['add']:>3}  {totals['remove']:>6}  "
        f"{totals['unchanged']:>9}",
    ])
    return lines


def format_marketplace_actions(actions):
    lines = []
    symbols = {"add": "+", "migrate": "~", "pending": "?"}

    for action in actions:
        if "marketplace" not in action:
            continue
        if action["action"] == "add":
            detail = f"{action['marketplace']} ({action['source']})"
        elif action["action"] == "migrate":
            detail = f"{action['marketplace']} -> {action['source']}"
        elif action["action"] == "pending":
            detail = f"{action['marketplace']} plugins pending"
        else:
            continue
        lines.append(f"  {symbols[action['action']]} {detail}")

    return lines


def format_report(actions, verbose=False):
    lines = format_summary_table(actions)
    lines.extend(["", "Changes:"])
    symbols = {"add": "+", "remove": "-", "unchanged": "="}
    listed_actions = [
        action
        for action in actions
        if "id" in action
        and action["action"] in PLUGIN_ACTIONS
        and (verbose or action["action"] != "unchanged")
    ]
    if listed_actions:
        lines.extend(
            f"  {symbols[action['action']]} {action['id']}"
            for action in listed_actions
        )
    else:
        lines.append("  None")

    marketplace_lines = format_marketplace_actions(actions)
    if marketplace_lines:
        lines.extend(["", "Marketplaces:", *marketplace_lines])

    enable_count = sum(action["action"] == "enable" for action in actions)
    orphan_count = sum(action["action"] == "forget" for action in actions)
    lines.extend([
        "",
        f"Enable state: {enable_count} enabledPlugins keys to add",
        f"Settings: {orphan_count} orphaned enabledPlugins keys",
        "Note: unchanged plugins are still refreshed with "
        "`claude plugin update`.",
    ])
    return "\n".join(lines)


def parse_args(args=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="list every plugin action, including unchanged plugins",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit raw action records as JSON",
    )
    return parser.parse_args(args)


def main(args=None):
    options = parse_args(args)
    config = read_json(CONFIG_PATH)
    state = research(config)
    actions = compute_actions(config, *state)

    if options.json:
        print(json.dumps(actions, indent=2))
    else:
        print(format_report(actions, verbose=options.verbose))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Synchronize configured Claude plugin marketplaces and plugins.

Research reads Claude's marketplace and plugin state plus the local settings and
marketplace manifests. Diff computation is pure so callers can report or apply
the returned actions separately.

Usage:
    sync-claude-plugins.py [--verbose] [--json] [--yes] [--dry-run]
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile


CLAUDE_SETTINGS = os.path.expanduser("~/.claude/settings.json")
CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "install-agent-tools.config.json",
)
PLUGIN_ACTIONS = ("add", "remove", "unchanged")
UNATTENDED_ACTIONS = frozenset(("add", "enable", "pending", "unchanged"))


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


def confirm_actions(
    actions,
    yes=False,
    dry_run=False,
    input_stream=None,
    output_stream=None,
):
    input_stream = sys.stdin if input_stream is None else input_stream
    output_stream = sys.stderr if output_stream is None else output_stream

    if dry_run:
        return []
    if yes:
        return actions
    if input_stream.isatty():
        print(
            "Apply these changes? [y/N] ",
            end="",
            flush=True,
            file=output_stream,
        )
        answer = input_stream.readline().strip().lower()
        if answer in ("y", "yes"):
            return actions
        print("No changes applied.", file=output_stream)
        return []

    actions_to_apply = [
        action
        for action in actions
        if action["action"] in UNATTENDED_ACTIONS
    ]
    if len(actions_to_apply) != len(actions):
        print(
            "Skipping removals because stdin is not a TTY; re-run this "
            "script manually to review and confirm them.",
            file=output_stream,
        )
    return actions_to_apply


def action_is_selected(actions, action_name, field, value):
    return any(
        action["action"] == action_name and action.get(field) == value
        for action in actions
    )


def uninstall_plugin(plugin_id):
    sh([
        "claude",
        "plugin",
        "uninstall",
        "--prune",
        "--yes",
        "--scope",
        "user",
        plugin_id,
    ])


def apply_marketplaces(config, marketplaces, installed, actions):
    marketplaces_by_name = {
        marketplace["name"]: marketplace for marketplace in marketplaces
    }
    uninstalled_plugin_ids = set()

    for specification in config["claudeMarketplaces"]:
        name = specification["name"]
        source = specification["source"]
        marketplace = marketplaces_by_name.get(name)

        if marketplace is None:
            if action_is_selected(actions, "add", "marketplace", name):
                sh(["claude", "plugin", "marketplace", "add", source])
            continue

        if marketplace["source"] == "github":
            if marketplace["repo"] != source:
                raise ValueError(
                    f"Marketplace {name} source mismatch: expected "
                    f"{source}, found {marketplace['repo']}"
                )
            sh(["claude", "plugin", "marketplace", "update", name])
            continue

        if not action_is_selected(actions, "migrate", "marketplace", name):
            continue

        print(
            f"Migrating Claude {name} from {marketplace['source']} "
            f"source to github {source}.",
            file=sys.stderr,
        )
        remove_command = [
            "claude",
            "plugin",
            "marketplace",
            "remove",
            name,
        ]
        try:
            sh(remove_command)
        except subprocess.CalledProcessError:
            for plugin in installed:
                if plugin["id"].rpartition("@")[2] != name:
                    continue
                uninstall_plugin(plugin["id"])
                uninstalled_plugin_ids.add(plugin["id"])
            sh(remove_command)
        sh(["claude", "plugin", "marketplace", "add", source])

    return uninstalled_plugin_ids


def settings_bytes(settings):
    return (json.dumps(settings, indent=2) + "\n").encode()


def write_settings_atomic(settings, path=CLAUDE_SETTINGS):
    contents = settings_bytes(settings)
    directory = os.path.dirname(path)
    prefix = f"{os.path.basename(path)}.agent-tools."
    descriptor, temporary_path = tempfile.mkstemp(dir=directory, prefix=prefix)

    try:
        if os.path.exists(path):
            os.chmod(temporary_path, os.stat(path).st_mode)
        with os.fdopen(descriptor, "wb") as temporary_file:
            descriptor = None
            temporary_file.write(contents)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        with open(path, "rb") as settings_file:
            if settings_file.read() == contents:
                os.unlink(temporary_path)
                return False

        os.replace(temporary_path, path)
        return True
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)


def reconcile_settings(actions, path=CLAUDE_SETTINGS):
    if not os.path.exists(path):
        return False

    enable_ids = [
        action["id"] for action in actions if action["action"] == "enable"
    ]
    forget_ids = [
        action["id"] for action in actions if action["action"] == "forget"
    ]
    if not enable_ids and not forget_ids:
        return False

    settings = read_json(path)
    updated_settings = dict(settings)
    enabled_plugins = updated_settings.get("enabledPlugins")
    if enabled_plugins is None:
        if not enable_ids:
            return False
        enabled_plugins = {}
    elif not isinstance(enabled_plugins, dict):
        raise ValueError("Claude settings enabledPlugins must be an object")
    else:
        enabled_plugins = dict(enabled_plugins)
    updated_settings["enabledPlugins"] = enabled_plugins

    for plugin_id in enable_ids:
        if plugin_id not in enabled_plugins:
            enabled_plugins[plugin_id] = True
    for plugin_id in forget_ids:
        enabled_plugins.pop(plugin_id, None)

    if updated_settings == settings:
        return False
    return write_settings_atomic(updated_settings, path)


def apply_actions(config, marketplaces, installed, actions):
    uninstalled_plugin_ids = apply_marketplaces(
        config,
        marketplaces,
        installed,
        actions,
    )

    for action in actions:
        if action["action"] == "add" and "id" in action:
            sh(["claude", "plugin", "install", action["id"]])
        elif action["action"] == "unchanged":
            operation = (
                "install"
                if action["id"] in uninstalled_plugin_ids
                else "update"
            )
            sh(["claude", "plugin", operation, action["id"]])

    for action in actions:
        if (
            action["action"] == "remove"
            and action["id"] not in uninstalled_plugin_ids
        ):
            uninstall_plugin(action["id"])

    reconcile_settings(actions)


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
    parser.add_argument(
        "--yes",
        action="store_true",
        help="apply all changes, including removals, without prompting",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report changes without applying them",
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
    actions_to_apply = confirm_actions(
        actions,
        yes=options.yes,
        dry_run=options.dry_run,
    )
    if actions_to_apply or (
        not options.dry_run
        and (options.yes or not sys.stdin.isatty())
    ):
        apply_actions(config, *state[:2], actions_to_apply)
    return 0


if __name__ == "__main__":
    sys.exit(main())

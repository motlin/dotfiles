#!/usr/bin/env python3
"""Synchronize configured Claude plugin marketplaces and plugins.

Research reads Claude's marketplace and plugin state plus the local settings and
marketplace manifests. Diff computation is pure so callers can report or apply
the returned actions separately.

Usage:
    sync-claude-plugins.py
"""
import json
import os
import subprocess


CLAUDE_SETTINGS = os.path.expanduser("~/.claude/settings.json")


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

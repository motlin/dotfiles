#!/usr/bin/env python3
"""Test the pure diff logic used by sync-claude-plugins.py."""
import importlib.util
import pathlib
import unittest


ASSERTIONS = unittest.TestCase()
SYNC_SCRIPT = pathlib.Path(__file__).with_name("sync-claude-plugins.py")
MANAGED_MARKETPLACE = "motlin-claude-code-plugins"
MANAGED_SOURCE = "motlin/claude-code-plugins"


def compute_actions(config, marketplaces, installed, settings, manifests):
    specification = importlib.util.spec_from_file_location("sync_claude_plugins", SYNC_SCRIPT)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module.compute_actions(config, marketplaces, installed, settings, manifests)


def config_for(plugins, exclude_plugins=None, name=MANAGED_MARKETPLACE,
               source=MANAGED_SOURCE):
    marketplace = {"name": name, "source": source, "plugins": plugins}
    if exclude_plugins is not None:
        marketplace["excludePlugins"] = exclude_plugins
    return {"titlePluginNames": [], "claudeMarketplaces": [marketplace]}


def marketplace(name=MANAGED_MARKETPLACE, repo=MANAGED_SOURCE,
                source="github"):
    return {
        "name": name,
        "source": source,
        "repo": repo,
        "installLocation": f"/tmp/test/marketplaces/{name}",
    }


def installed_plugin(name, marketplace_name=MANAGED_MARKETPLACE,
                     scope="user", enabled=False):
    return {
        "id": f"{name}@{marketplace_name}",
        "version": "1.23.0",
        "scope": scope,
        "enabled": enabled,
    }


def test_undeclared_user_scope_plugin_is_removed():
    actions = compute_actions(
        config_for([]),
        [marketplace()],
        [installed_plugin("bash-audit-log")],
        {"enabledPlugins": {}},
        {},
    )

    ASSERTIONS.assertEqual(actions, [
        {
            "action": "remove",
            "id": "bash-audit-log@motlin-claude-code-plugins",
        },
    ])


def test_project_scope_plugin_is_spared():
    actions = compute_actions(
        config_for([]),
        [marketplace()],
        [installed_plugin("project-helper", scope="project")],
        {"enabledPlugins": {}},
        {},
    )

    ASSERTIONS.assertEqual(actions, [])


def test_plugin_from_unmanaged_marketplace_is_untouched():
    actions = compute_actions(
        config_for([]),
        [
            marketplace(),
            marketplace(
                name="nextdns",
                repo="/tmp/test/marketplaces/nextdns",
                source="directory",
            ),
        ],
        [installed_plugin("nextdns-helper", marketplace_name="nextdns")],
        {"enabledPlugins": {}},
        {},
    )

    ASSERTIONS.assertEqual(actions, [])


def test_wildcard_plugins_honor_exclusions():
    actions = compute_actions(
        config_for("*", exclude_plugins=["ghostty-titles"]),
        [marketplace()],
        [
            installed_plugin("bash-audit-log", enabled=True),
            installed_plugin("ghostty-titles"),
        ],
        {
            "enabledPlugins": {
                "bash-audit-log@motlin-claude-code-plugins": True,
            },
        },
        {
            MANAGED_MARKETPLACE: {
                "name": MANAGED_MARKETPLACE,
                "plugins": [
                    {"name": "bash-audit-log", "source": "./plugins/bash-audit-log"},
                    {"name": "ghostty-titles", "source": "./plugins/ghostty-titles"},
                ],
            },
        },
    )

    ASSERTIONS.assertEqual(actions, [
        {
            "action": "unchanged",
            "id": "bash-audit-log@motlin-claude-code-plugins",
        },
        {
            "action": "remove",
            "id": "ghostty-titles@motlin-claude-code-plugins",
        },
    ])


def test_declared_missing_plugin_is_added_and_enabled():
    actions = compute_actions(
        config_for(["skill-creator"]),
        [marketplace()],
        [],
        {"enabledPlugins": {}},
        {},
    )

    ASSERTIONS.assertEqual(actions, [
        {
            "action": "add",
            "id": "skill-creator@motlin-claude-code-plugins",
        },
        {
            "action": "enable",
            "id": "skill-creator@motlin-claude-code-plugins",
        },
    ])


def test_installed_declared_plugin_is_unchanged():
    actions = compute_actions(
        config_for(["skill-creator"]),
        [marketplace()],
        [installed_plugin("skill-creator", enabled=True)],
        {
            "enabledPlugins": {
                "skill-creator@motlin-claude-code-plugins": True,
            },
        },
        {},
    )

    ASSERTIONS.assertEqual(actions, [
        {
            "action": "unchanged",
            "id": "skill-creator@motlin-claude-code-plugins",
        },
    ])


def test_orphaned_enabled_plugin_key_is_forgotten():
    actions = compute_actions(
        config_for([]),
        [marketplace()],
        [],
        {
            "enabledPlugins": {
                "old-plugin@motlin-claude-code-plugins": False,
            },
        },
        {},
    )

    ASSERTIONS.assertEqual(actions, [
        {
            "action": "forget",
            "id": "old-plugin@motlin-claude-code-plugins",
        },
    ])


def test_existing_false_enabled_plugin_value_is_preserved():
    actions = compute_actions(
        config_for(["skill-creator"]),
        [marketplace()],
        [installed_plugin("skill-creator")],
        {
            "enabledPlugins": {
                "skill-creator@motlin-claude-code-plugins": False,
            },
        },
        {},
    )

    ASSERTIONS.assertEqual(actions, [
        {
            "action": "unchanged",
            "id": "skill-creator@motlin-claude-code-plugins",
        },
    ])


def test_github_marketplace_repo_mismatch_raises():
    with ASSERTIONS.assertRaisesRegex(
        ValueError,
        "^Marketplace caveman source mismatch: expected motlin/caveman, "
        "found example/caveman$",
    ):
        compute_actions(
            config_for(["caveman"], name="caveman", source="motlin/caveman"),
            [marketplace(name="caveman", repo="example/caveman")],
            [],
            {"enabledPlugins": {}},
            {},
        )


TEST_FUNCTIONS = (
    test_undeclared_user_scope_plugin_is_removed,
    test_project_scope_plugin_is_spared,
    test_plugin_from_unmanaged_marketplace_is_untouched,
    test_wildcard_plugins_honor_exclusions,
    test_declared_missing_plugin_is_added_and_enabled,
    test_installed_declared_plugin_is_unchanged,
    test_orphaned_enabled_plugin_key_is_forgotten,
    test_existing_false_enabled_plugin_value_is_preserved,
    test_github_marketplace_repo_mismatch_raises,
)


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(unittest.FunctionTestCase(test) for test in TEST_FUNCTIONS)

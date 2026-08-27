#!/usr/bin/env python3
"""Test the pure diff logic used by sync-claude-plugins.py."""
import importlib.util
import io
import json
import pathlib
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock


ASSERTIONS = unittest.TestCase()
SYNC_SCRIPT = pathlib.Path(__file__).with_name("sync-claude-plugins.py")
MANAGED_MARKETPLACE = "motlin-claude-code-plugins"
MANAGED_SOURCE = "motlin/claude-code-plugins"


def load_sync_module():
    specification = importlib.util.spec_from_file_location("sync_claude_plugins", SYNC_SCRIPT)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def compute_actions(config, marketplaces, installed, settings, manifests):
    module = load_sync_module()
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
        {
            "enabledPlugins": {
                "project-helper@motlin-claude-code-plugins": False,
            },
        },
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


def test_default_report_summarizes_plugins_and_settings_actions():
    module = load_sync_module()
    actions = [
        {"action": "unchanged", "id": "alpha-plugin@example-marketplace"},
        {"action": "add", "id": "beta-plugin@example-marketplace"},
        {"action": "enable", "id": "beta-plugin@example-marketplace"},
        {"action": "remove", "id": "old-plugin@second-marketplace"},
        {"action": "forget", "id": "orphan-plugin@second-marketplace"},
    ]

    report = module.format_report(actions)

    ASSERTIONS.assertEqual(
        report,
        "Marketplace                   Add  Remove  Unchanged\n"
        "----------------------------------------------------\n"
        "example-marketplace             1       0          1\n"
        "second-marketplace              0       1          0\n"
        "----------------------------------------------------\n"
        "TOTAL                           1       1          1\n"
        "\n"
        "Changes:\n"
        "  + beta-plugin@example-marketplace\n"
        "  - old-plugin@second-marketplace\n"
        "\n"
        "Enable state: 1 enabledPlugins keys to add\n"
        "Settings: 1 orphaned enabledPlugins keys\n"
        "Note: unchanged plugins are still refreshed with `claude plugin update`.",
    )


def test_verbose_report_lists_every_plugin_action():
    module = load_sync_module()
    actions = [
        {"action": "unchanged", "id": "alpha-plugin@example-marketplace"},
        {"action": "add", "id": "beta-plugin@example-marketplace"},
        {"action": "remove", "id": "old-plugin@example-marketplace"},
    ]

    report = module.format_report(actions, verbose=True)

    ASSERTIONS.assertEqual(
        report,
        "Marketplace                   Add  Remove  Unchanged\n"
        "----------------------------------------------------\n"
        "example-marketplace             1       1          1\n"
        "----------------------------------------------------\n"
        "TOTAL                           1       1          1\n"
        "\n"
        "Changes:\n"
        "  = alpha-plugin@example-marketplace\n"
        "  + beta-plugin@example-marketplace\n"
        "  - old-plugin@example-marketplace\n"
        "\n"
        "Enable state: 0 enabledPlugins keys to add\n"
        "Settings: 0 orphaned enabledPlugins keys\n"
        "Note: unchanged plugins are still refreshed with `claude plugin update`.",
    )


def test_report_lists_marketplace_actions_separately():
    module = load_sync_module()
    actions = [
        {
            "action": "add",
            "marketplace": "example-marketplace",
            "source": "example/marketplace",
        },
        {"action": "pending", "marketplace": "example-marketplace"},
        {
            "action": "migrate",
            "marketplace": "second-marketplace",
            "source": "example/second-marketplace",
        },
    ]

    report = module.format_report(actions)

    ASSERTIONS.assertEqual(
        report,
        "Marketplace                   Add  Remove  Unchanged\n"
        "----------------------------------------------------\n"
        "example-marketplace             0       0          0\n"
        "second-marketplace              0       0          0\n"
        "----------------------------------------------------\n"
        "TOTAL                           0       0          0\n"
        "\n"
        "Changes:\n"
        "  None\n"
        "\n"
        "Marketplaces:\n"
        "  + example-marketplace (example/marketplace)\n"
        "  ? example-marketplace plugins pending\n"
        "  ~ second-marketplace -> example/second-marketplace\n"
        "\n"
        "Enable state: 0 enabledPlugins keys to add\n"
        "Settings: 0 orphaned enabledPlugins keys\n"
        "Note: unchanged plugins are still refreshed with `claude plugin update`.",
    )


def test_json_flag_emits_raw_action_records():
    module = load_sync_module()
    actions = [
        {"action": "add", "id": "alpha-plugin@example-marketplace"},
        {"action": "enable", "id": "alpha-plugin@example-marketplace"},
    ]
    output = io.StringIO()

    with (
        mock.patch.object(module, "read_json", return_value={}),
        mock.patch.object(module, "research", return_value=([], [], {}, {})),
        mock.patch.object(module, "compute_actions", return_value=actions),
        mock.patch.object(module, "apply_actions") as apply_actions,
        mock.patch.object(module.sys, "stdin", io.StringIO()),
        redirect_stdout(output),
    ):
        result = module.main(["--json"])

    ASSERTIONS.assertEqual(
        (result, output.getvalue(), apply_actions.mock_calls),
        (
            0,
            f"{json.dumps(actions, indent=2)}\n",
            [mock.call({}, [], [], actions)],
        ),
    )


def test_confirmation_from_tty_requires_explicit_approval():
    module = load_sync_module()
    actions = [
        {"action": "add", "id": "alpha-plugin@example-marketplace"},
        {"action": "remove", "id": "old-plugin@example-marketplace"},
    ]
    input_stream = io.StringIO("yes\n")
    output_stream = io.StringIO()

    with mock.patch.object(input_stream, "isatty", return_value=True):
        actions_to_apply = module.confirm_actions(
            actions,
            input_stream=input_stream,
            output_stream=output_stream,
        )

    ASSERTIONS.assertEqual(
        (actions_to_apply, output_stream.getvalue()),
        (actions, "Apply these changes? [y/N] "),
    )


def test_confirmation_from_tty_declines_on_empty_response():
    module = load_sync_module()
    actions = [
        {"action": "remove", "id": "old-plugin@example-marketplace"},
    ]
    input_stream = io.StringIO("\n")
    output_stream = io.StringIO()

    with mock.patch.object(input_stream, "isatty", return_value=True):
        actions_to_apply = module.confirm_actions(
            actions,
            input_stream=input_stream,
            output_stream=output_stream,
        )

    ASSERTIONS.assertEqual(
        (actions_to_apply, output_stream.getvalue()),
        ([], "Apply these changes? [y/N] No changes applied.\n"),
    )


def test_non_tty_confirmation_skips_destructive_actions():
    module = load_sync_module()
    actions = [
        {"action": "add", "id": "alpha-plugin@example-marketplace"},
        {"action": "unchanged", "id": "beta-plugin@example-marketplace"},
        {"action": "enable", "id": "alpha-plugin@example-marketplace"},
        {"action": "remove", "id": "old-plugin@example-marketplace"},
        {"action": "forget", "id": "old-plugin@example-marketplace"},
        {
            "action": "migrate",
            "marketplace": "second-marketplace",
            "source": "example/second-marketplace",
        },
    ]
    output_stream = io.StringIO()

    actions_to_apply = module.confirm_actions(
        actions,
        input_stream=io.StringIO(),
        output_stream=output_stream,
    )

    ASSERTIONS.assertEqual(
        (actions_to_apply, output_stream.getvalue()),
        (
            [
                {"action": "add", "id": "alpha-plugin@example-marketplace"},
                {
                    "action": "unchanged",
                    "id": "beta-plugin@example-marketplace",
                },
                {"action": "enable", "id": "alpha-plugin@example-marketplace"},
            ],
            "Skipping removals because stdin is not a TTY; re-run this "
            "script manually to review and confirm them.\n",
        ),
    )


def test_yes_flag_allows_removals_without_reading_stdin():
    module = load_sync_module()
    actions = [
        {"action": "remove", "id": "old-plugin@example-marketplace"},
        {"action": "forget", "id": "old-plugin@example-marketplace"},
    ]
    input_stream = mock.Mock()
    output_stream = io.StringIO()

    actions_to_apply = module.confirm_actions(
        actions,
        yes=True,
        input_stream=input_stream,
        output_stream=output_stream,
    )

    ASSERTIONS.assertEqual(
        (actions_to_apply, input_stream.mock_calls, output_stream.getvalue()),
        (actions, [], ""),
    )


def test_dry_run_skips_all_actions_without_reading_stdin():
    module = load_sync_module()
    actions = [
        {"action": "add", "id": "alpha-plugin@example-marketplace"},
        {"action": "remove", "id": "old-plugin@example-marketplace"},
    ]
    input_stream = mock.Mock()
    input_stream.isatty.return_value = False
    output_stream = io.StringIO()

    actions_to_apply = module.confirm_actions(
        actions,
        dry_run=True,
        input_stream=input_stream,
        output_stream=output_stream,
    )

    ASSERTIONS.assertEqual(
        (actions_to_apply, input_stream.mock_calls, output_stream.getvalue()),
        (
            [],
            [mock.call.isatty()],
            "Removals are deferred because stdin is not a TTY; re-run this "
            "script manually to review and confirm them.\n",
        ),
    )


def test_apply_orders_marketplaces_plugins_prune_and_settings():
    module = load_sync_module()
    config = {
        "titlePluginNames": [],
        "claudeMarketplaces": [
            {
                "name": "example-marketplace",
                "source": "example/marketplace",
                "plugins": ["alpha-plugin", "beta-plugin"],
            },
            {
                "name": "second-marketplace",
                "source": "example/second-marketplace",
                "plugins": [],
            },
        ],
    }
    marketplaces = [
        marketplace(
            name="example-marketplace",
            repo="example/marketplace",
        ),
    ]
    installed = [
        installed_plugin(
            "beta-plugin",
            marketplace_name="example-marketplace",
        ),
        installed_plugin(
            "old-plugin",
            marketplace_name="example-marketplace",
        ),
    ]
    actions = [
        {
            "action": "add",
            "marketplace": "second-marketplace",
            "source": "example/second-marketplace",
        },
        {"action": "add", "id": "alpha-plugin@example-marketplace"},
        {"action": "enable", "id": "alpha-plugin@example-marketplace"},
        {"action": "unchanged", "id": "beta-plugin@example-marketplace"},
        {"action": "remove", "id": "old-plugin@example-marketplace"},
        {"action": "forget", "id": "old-plugin@example-marketplace"},
    ]

    with (
        mock.patch.object(module, "sh") as shell,
        mock.patch.object(module, "reconcile_settings") as reconcile_settings,
    ):
        module.apply_actions(
            config,
            marketplaces,
            installed,
            actions,
        )

    ASSERTIONS.assertEqual(
        (shell.mock_calls, reconcile_settings.mock_calls),
        (
            [
                mock.call([
                    "claude", "plugin", "marketplace", "update",
                    "example-marketplace",
                ]),
                mock.call([
                    "claude", "plugin", "marketplace", "add",
                    "example/second-marketplace",
                ]),
                mock.call([
                    "claude", "plugin", "install",
                    "alpha-plugin@example-marketplace",
                ]),
                mock.call([
                    "claude", "plugin", "update",
                    "beta-plugin@example-marketplace",
                ]),
                mock.call([
                    "claude", "plugin", "uninstall", "--prune", "--yes",
                    "--scope", "user", "old-plugin@example-marketplace",
                ]),
            ],
            [mock.call(actions)],
        ),
    )


def test_marketplace_migration_retries_after_uninstalling_plugins():
    module = load_sync_module()
    config = config_for(
        ["alpha-plugin"],
        name="example-marketplace",
        source="example/marketplace",
    )
    marketplaces = [
        marketplace(
            name="example-marketplace",
            repo="/tmp/test/example-marketplace",
            source="directory",
        ),
    ]
    installed = [
        installed_plugin(
            "alpha-plugin",
            marketplace_name="example-marketplace",
        ),
        installed_plugin(
            "old-plugin",
            marketplace_name="example-marketplace",
        ),
    ]
    actions = [
        {
            "action": "migrate",
            "marketplace": "example-marketplace",
            "source": "example/marketplace",
        },
        {"action": "unchanged", "id": "alpha-plugin@example-marketplace"},
        {"action": "remove", "id": "old-plugin@example-marketplace"},
        {"action": "forget", "id": "old-plugin@example-marketplace"},
    ]
    removal_error = subprocess.CalledProcessError(
        1,
        ["claude", "plugin", "marketplace", "remove", "example-marketplace"],
    )

    with (
        mock.patch.object(
            module,
            "sh",
            side_effect=[removal_error, "", "", "", "", ""],
        ) as shell,
        mock.patch.object(module, "reconcile_settings") as reconcile_settings,
        mock.patch.object(module.sys, "stderr", io.StringIO()) as error_stream,
    ):
        module.apply_actions(
            config,
            marketplaces,
            installed,
            actions,
        )

    ASSERTIONS.assertEqual(
        (
            shell.mock_calls,
            reconcile_settings.mock_calls,
            error_stream.getvalue(),
        ),
        (
            [
                mock.call([
                    "claude", "plugin", "marketplace", "remove",
                    "example-marketplace",
                ]),
                mock.call([
                    "claude", "plugin", "uninstall", "--prune", "--yes",
                    "--scope", "user", "alpha-plugin@example-marketplace",
                ]),
                mock.call([
                    "claude", "plugin", "uninstall", "--prune", "--yes",
                    "--scope", "user", "old-plugin@example-marketplace",
                ]),
                mock.call([
                    "claude", "plugin", "marketplace", "remove",
                    "example-marketplace",
                ]),
                mock.call([
                    "claude", "plugin", "marketplace", "add",
                    "example/marketplace",
                ]),
                mock.call([
                    "claude", "plugin", "install",
                    "alpha-plugin@example-marketplace",
                ]),
            ],
            [mock.call(actions)],
            "Migrating Claude example-marketplace from directory source to "
            "github example/marketplace.\n",
        ),
    )


def test_settings_reconciliation_preserves_existing_false_value():
    module = load_sync_module()
    settings = {
        "enabledPlugins": {
            "beta-plugin@example-marketplace": False,
            "old-plugin@example-marketplace": False,
        },
    }
    actions = [
        {"action": "enable", "id": "alpha-plugin@example-marketplace"},
        {"action": "forget", "id": "old-plugin@example-marketplace"},
    ]

    with (
        mock.patch.object(module.os.path, "exists", return_value=True),
        mock.patch.object(module, "read_json", return_value=settings),
        mock.patch.object(
            module,
            "write_settings_atomic",
            return_value=True,
        ) as write_settings,
    ):
        changed = module.reconcile_settings(
            actions,
            "/tmp/test/settings.json",
        )

    ASSERTIONS.assertEqual(
        (changed, settings, write_settings.mock_calls),
        (
            True,
            {
                "enabledPlugins": {
                    "beta-plugin@example-marketplace": False,
                    "old-plugin@example-marketplace": False,
                },
            },
            [
                mock.call(
                    {
                        "enabledPlugins": {
                            "beta-plugin@example-marketplace": False,
                            "alpha-plugin@example-marketplace": True,
                        },
                    },
                    "/tmp/test/settings.json",
                ),
            ],
        ),
    )


def test_settings_reconciliation_creates_missing_settings_file():
    module = load_sync_module()
    actions = [
        {"action": "enable", "id": "alpha-plugin@example-marketplace"},
    ]
    scratch_directory = SYNC_SCRIPT.parent.parent / ".llm"
    scratch_directory.mkdir(exist_ok=True)

    with tempfile.TemporaryDirectory(dir=scratch_directory) as directory:
        settings_path = pathlib.Path(directory) / "claude" / "settings.json"
        changed = module.reconcile_settings(actions, str(settings_path))
        result = (
            changed,
            settings_path.read_text(),
            sorted(path.name for path in settings_path.parent.iterdir()),
        )

    ASSERTIONS.assertEqual(
        result,
        (
            True,
            "{\n"
            '  "enabledPlugins": {\n'
            '    "alpha-plugin@example-marketplace": true\n'
            "  }\n"
            "}\n",
            ["settings.json"],
        ),
    )


def test_atomic_settings_write_replaces_only_changed_bytes():
    module = load_sync_module()
    scratch_directory = SYNC_SCRIPT.parent.parent / ".llm"
    scratch_directory.mkdir(exist_ok=True)
    settings = {"enabledPlugins": {"alpha-plugin@example-marketplace": True}}

    with tempfile.TemporaryDirectory(dir=scratch_directory) as directory:
        settings_path = pathlib.Path(directory) / "settings.json"
        settings_path.write_text('{"enabledPlugins": {}}\n')
        first_result = module.write_settings_atomic(settings, str(settings_path))

        with mock.patch.object(module.os, "replace") as replace:
            second_result = module.write_settings_atomic(
                settings,
                str(settings_path),
            )

        result = (
            first_result,
            second_result,
            settings_path.read_text(),
            replace.mock_calls,
            sorted(path.name for path in pathlib.Path(directory).iterdir()),
        )

    ASSERTIONS.assertEqual(
        result,
        (
            True,
            False,
            "{\n"
            '  "enabledPlugins": {\n'
            '    "alpha-plugin@example-marketplace": true\n'
            "  }\n"
            "}\n",
            [],
            ["settings.json"],
        ),
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
    test_default_report_summarizes_plugins_and_settings_actions,
    test_verbose_report_lists_every_plugin_action,
    test_report_lists_marketplace_actions_separately,
    test_json_flag_emits_raw_action_records,
    test_confirmation_from_tty_requires_explicit_approval,
    test_confirmation_from_tty_declines_on_empty_response,
    test_non_tty_confirmation_skips_destructive_actions,
    test_yes_flag_allows_removals_without_reading_stdin,
    test_dry_run_skips_all_actions_without_reading_stdin,
    test_apply_orders_marketplaces_plugins_prune_and_settings,
    test_marketplace_migration_retries_after_uninstalling_plugins,
    test_settings_reconciliation_preserves_existing_false_value,
    test_settings_reconciliation_creates_missing_settings_file,
    test_atomic_settings_write_replaces_only_changed_bytes,
)


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(unittest.FunctionTestCase(test) for test in TEST_FUNCTIONS)

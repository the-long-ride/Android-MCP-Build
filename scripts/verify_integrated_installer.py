"""Regression tests for embedded, CLI-independent MCP client installation."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from android_mcp import installer, lifecycle


class InstallerTests(unittest.TestCase):
    def setUp(self):
        context = tempfile.TemporaryDirectory()
        self.addCleanup(context.cleanup)
        self.home = Path(context.name)
        self.exe = self.home / "android-mcp.exe"
        self.exe.write_bytes(b"test-exe")
        self.skill = installer.embedded_skill()

    def test_skill_is_embedded_and_matches_source(self):
        source = Path(__file__).resolve().parents[1] / ".agents/skills/android-device-automation/SKILL.md"
        self.assertEqual(source.read_text(encoding="utf-8"), self.skill)

    def test_chatgpt_alias_writes_codex_config_without_any_cli(self):
        with patch.object(installer.shutil, "which", return_value=None):
            self.assertEqual(installer.install(["chatgpt"], self.exe, self.home, self.skill), 0)
        path = self.home / ".codex/config.toml"
        config = tomllib.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(config["mcp_servers"]["android-mcp"]["command"], str(self.exe))
        self.assertEqual(config["mcp_servers"]["android-mcp"]["startup_timeout_sec"], 60)
        self.assertTrue((self.home / ".agents/skills/android-device-automation/SKILL.md").is_file())

    def test_codex_toml_merge_preserves_other_sections(self):
        path = self.home / ".codex/config.toml"
        path.parent.mkdir(parents=True)
        previous = 'model = "gpt-6"\n\n[mcp_servers.other]\ncommand = "other.exe"\n'
        path.write_text(previous, encoding="utf-8")
        self.assertEqual(installer.install(["codex"], self.exe, self.home, self.skill), 0)
        config = tomllib.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(config["model"], "gpt-6")
        self.assertEqual(config["mcp_servers"]["other"]["command"], "other.exe")
        self.assertEqual(config["mcp_servers"]["android-mcp"]["command"], str(self.exe))
        self.assertEqual(path.with_suffix(".toml.bak").read_text(encoding="utf-8"), previous)

    def test_codex_existing_entry_requires_opt_in_replace(self):
        path = self.home / ".codex/config.toml"
        path.parent.mkdir(parents=True)
        initial = '[mcp_servers.android-mcp]\ncommand = "old.exe"\n\n[mcp_servers.other]\ncommand = "other.exe"\n'
        path.write_text(initial, encoding="utf-8")
        self.assertEqual(installer.install(["codex"], self.exe, self.home, self.skill), 0)
        self.assertEqual(path.read_text(encoding="utf-8"), initial)
        self.assertEqual(installer.install(["codex"], self.exe, self.home, self.skill, replace=True), 0)
        config = tomllib.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(config["mcp_servers"]["android-mcp"]["command"], str(self.exe))
        self.assertEqual(config["mcp_servers"]["other"]["command"], "other.exe")

    def test_codex_malformed_toml_not_overwritten(self):
        path = self.home / ".codex/config.toml"
        path.parent.mkdir(parents=True)
        path.write_text("invalid = {", encoding="utf-8")
        self.assertEqual(installer.install(["codex"], self.exe, self.home, self.skill), 1)
        self.assertEqual(path.read_text(encoding="utf-8"), "invalid = {")

    def test_claude_code_installs_without_cli(self):
        with patch.object(installer.shutil, "which", return_value=None):
            self.assertEqual(installer.install(["claude-code"], self.exe, self.home, self.skill), 0)
        root = json.loads((self.home / ".claude.json").read_text(encoding="utf-8"))
        self.assertEqual(root["mcpServers"]["android-mcp"]["command"], str(self.exe))
        self.assertTrue((self.home / ".claude/skills/android-device-automation/SKILL.md").is_file())

    def test_claude_desktop_is_distinct_from_claude_code(self):
        self.assertEqual(installer.install(["claude-desktop"], self.exe, self.home, self.skill), 0)
        path = self.home / "AppData/Roaming/Claude/claude_desktop_config.json"
        config = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(config["mcpServers"]["android-mcp"]["command"], str(self.exe))
        self.assertFalse((self.home / ".claude.json").exists())

    def test_claude_desktop_existing_msix_profile(self):
        profile = self.home / "AppData/Local/Packages/Claude_abc/LocalCache/Roaming/Claude"
        profile.mkdir(parents=True)
        config = profile / "claude_desktop_config.json"
        config.write_text('{"preferences":{"sidebarMode":"chat"}}', encoding="utf-8")
        self.assertEqual(installer.install(["claude-desktop"], self.exe, self.home, self.skill), 0)
        data = json.loads(config.read_text(encoding="utf-8"))
        self.assertEqual(data["preferences"]["sidebarMode"], "chat")
        self.assertEqual(data["mcpServers"]["android-mcp"]["command"], str(self.exe))

    def test_antigravity_ides_and_cli_skills(self):
        self.assertEqual(installer.install(["antigravity"], self.exe, self.home, self.skill), 0)
        data = json.loads((self.home / ".gemini/config/mcp_config.json").read_text(encoding="utf-8"))
        self.assertEqual(data["mcpServers"]["android-mcp"]["command"], str(self.exe))
        for path in installer._skill_paths("antigravity", self.home):
            self.assertEqual(path.read_text(encoding="utf-8"), self.skill)

    def test_opencode_preserves_existing_configuration(self):
        path = self.home / ".config/opencode/opencode.json"
        path.parent.mkdir(parents=True)
        initial = {"theme": "dark", "mcp": {"other": {"type": "remote", "url": "https://example.org/mcp"}}}
        path.write_text(json.dumps(initial), encoding="utf-8")
        self.assertEqual(installer.install(["opencode"], self.exe, self.home, self.skill), 0)
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["theme"], "dark")
        self.assertEqual(data["mcp"]["other"], initial["mcp"]["other"])
        self.assertEqual(data["mcp"]["android-mcp"]["command"], [str(self.exe)])
        self.assertEqual(json.loads(path.with_suffix(".json.bak").read_text()), initial)

    def test_opencode_jsonc_preserved(self):
        path = self.home / ".config/opencode/opencode.jsonc"
        path.parent.mkdir(parents=True)
        path.write_text('{\n// keep comments\n}', encoding="utf-8")
        self.assertEqual(installer.install(["opencode"], self.exe, self.home, self.skill), 1)
        self.assertFalse(path.with_suffix(".json").exists())

    def test_dry_run_for_all_does_not_write_anything(self):
        with patch.object(installer.shutil, "which", return_value=None):
            self.assertEqual(installer.install(
                list(installer.ALL_CLIENTS), self.exe, self.home, self.skill, dry_run=True,
            ), 0)
        self.assertFalse((self.home / ".codex").exists())
        self.assertFalse((self.home / ".claude.json").exists())
        self.assertFalse((self.home / ".gemini").exists())
        self.assertFalse((self.home / ".config").exists())


    def test_installed_list_and_targeted_uninstall_preserve_other_clients(self):
        other = self.home / ".claude.json"
        other.write_text('{"mcpServers":{"foreign":{"command":"other.exe"}}}', encoding="utf-8")
        self.assertEqual(installer.install(
            list(installer.ALL_CLIENTS), self.exe, self.home, self.skill,
        ), 0)
        found = lifecycle.installed_clients(self.exe, self.home, self.skill)
        self.assertEqual([x["target"] for x in found], list(installer.ALL_CLIENTS))
        self.assertTrue(all(x["mcp"] for x in found))
        self.assertEqual(lifecycle.uninstall(["claude"], self.exe, self.home, self.skill), 0)
        self.assertNotIn("claude", [x["target"] for x in lifecycle.installed_clients(
            self.exe, self.home, self.skill,
        )])
        claude = json.loads(other.read_text(encoding="utf-8"))
        self.assertIn("foreign", claude["mcpServers"])
        self.assertNotIn("android-mcp", claude["mcpServers"])
        self.assertTrue((self.home / ".codex/config.toml").exists())
        self.assertFalse((self.home / ".claude/skills/android-device-automation/SKILL.md").exists())
        self.assertEqual(lifecycle.uninstall(["claude"], self.exe, self.home, self.skill), 0)

    def test_uninstall_all_preserves_other_servers_and_user_data(self):
        self.home.joinpath(".codex").mkdir(parents=True)
        original = 'model = "gpt-6"\n\n[mcp_servers.other]\ncommand = "other.exe"\n'
        self.home.joinpath(".codex/config.toml").write_text(original, encoding="utf-8")
        self.assertEqual(installer.install(
            list(installer.ALL_CLIENTS), self.exe, self.home, self.skill,
        ), 0)
        self.assertEqual(lifecycle.uninstall(
            list(installer.ALL_CLIENTS), self.exe, self.home, self.skill,
        ), 0)
        self.assertEqual(lifecycle.installed_clients(self.exe, self.home, self.skill), [])
        remaining = tomllib.loads(
            (self.home / ".codex/config.toml").read_text(encoding="utf-8")
        )
        self.assertEqual(remaining["model"], "gpt-6")
        self.assertIn("other", remaining["mcp_servers"])
        self.assertNotIn("android-mcp", remaining["mcp_servers"])
        self.assertEqual(lifecycle.uninstall(
            list(installer.ALL_CLIENTS), self.exe, self.home, self.skill,
        ), 0)

    def test_dry_run_and_changed_skill_are_preserved(self):
        self.assertEqual(installer.install(["opencode"], self.exe, self.home, self.skill), 0)
        skill = installer._skill_paths("opencode", self.home)[0]
        skill.write_text("user-edited", encoding="utf-8")
        self.assertEqual(lifecycle.uninstall(
            ["opencode"], self.exe, self.home, self.skill, dry_run=True,
        ), 0)
        self.assertTrue(skill.exists())
        self.assertTrue(lifecycle.installed_clients(self.exe, self.home, self.skill)[0]["mcp"])
        self.assertEqual(lifecycle.uninstall(["opencode"], self.exe, self.home, self.skill), 0)
        self.assertEqual(skill.read_text(encoding="utf-8"), "user-edited")
        self.assertEqual(lifecycle.installed_clients(self.exe, self.home, self.skill), [])

    def test_uninstall_symlink_does_not_remove_destination(self):
        target = self.home / "owned" / "android-device-automation" / "SKILL.md"
        target.parent.mkdir(parents=True)
        target.write_text(self.skill, encoding="utf-8")
        link = installer._skill_paths("claude", self.home)[0]
        link.parent.mkdir(parents=True)
        try:
            link.symlink_to(target)
        except OSError:
            self.skipTest("Symlink creation not supported")
        self.assertEqual(lifecycle.uninstall(["claude"], self.exe, self.home, self.skill), 0)
        self.assertFalse(link.exists())
        self.assertFalse(link.is_symlink())
        self.assertEqual(target.read_text(encoding="utf-8"), self.skill)

    def test_unmanaged_mcp_registration_is_not_removed(self):
        config = self.home / ".claude.json"
        config.write_text(
            '{"mcpServers":{"android-mcp":{"command":"other.exe","args":[]}}}',
            encoding="utf-8",
        )
        self.assertEqual(lifecycle.uninstall(["claude"], self.exe, self.home, self.skill), 0)
        self.assertEqual(
            json.loads(config.read_text())["mcpServers"]["android-mcp"]["command"],
            "other.exe",
        )

    def test_install_all_without_any_cli(self):
        with patch.object(installer.shutil, "which", return_value=None):
            self.assertEqual(installer.install(
                list(installer.ALL_CLIENTS), self.exe, self.home, self.skill,
            ), 0)
        self.assertTrue((self.home / ".codex/config.toml").exists())
        self.assertTrue((self.home / ".claude.json").exists())
        self.assertTrue((self.home / "AppData/Roaming/Claude/claude_desktop_config.json").exists())
        self.assertTrue((self.home / ".gemini/config/mcp_config.json").exists())
        self.assertTrue((self.home / ".config/opencode/opencode.json").exists())


if __name__ == "__main__":
    unittest.main()

"""Validate portable skill copies and embedded installer source assets."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / ".agents/skills/android-device-automation/SKILL.md"
CLAUDE = ROOT / ".claude/skills/android-device-automation/SKILL.md"
EMBEDDED = ROOT / "src/android_mcp/skills/android-device-automation/SKILL.md"
MCP = ROOT / "src/android_mcp/__main__.py"
INSTALLER = ROOT / "src/android_mcp/installer.py"
ENTRY = ROOT / "scripts/windows_exe_entry.py"


def main() -> None:
    content = CANONICAL.read_text(encoding="utf-8")
    for name, skill in [("Claude", CLAUDE), ("EXE embedded", EMBEDDED)]:
        assert content == skill.read_text(encoding="utf-8"), f"{name} skill drifted"
    frontmatter = re.match(r"\A---\n(.*?)\n---\n", content, re.DOTALL)
    assert frontmatter, "Missing Agent Skill frontmatter"
    assert re.search(r"(?m)^name: android-device-automation$", frontmatter.group(1))
    assert re.search(r"(?m)^description: .{20,}$", frontmatter.group(1))
    assert "instructions=instructions" in MCP.read_text(encoding="utf-8")
    entry = ENTRY.read_text(encoding="utf-8")
    assert '"install"' in entry and "server_main()" in entry
    installer = INSTALLER.read_text(encoding="utf-8")
    for keyword in ("claude", "codex", "antigravity", "opencode",
                    "mcp_config.json", "opencode.json", "--all",
                    "--dry-run", "--replace", "embedded_skill"):
        assert keyword in installer, f"Installer missing {keyword}"
    print("Portable skills, embedded installer, and MCP dispatcher validated.")


if __name__ == "__main__":
    main()

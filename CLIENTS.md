# Android-MCP: GUI-first and CLI integration on Windows

The build outputs **one** portable \`android-mcp.exe\` containing the MCP server,
its Python dependencies, the Agent Skill, and an **optional local installer**.
Python, Android Studio, and separately installed LLMs are not required to run
the EXE. You still need **host-side ADB** and an authorized Android device.

## Install (no AI command-line application required)

1. Download **android-mcp-windows-exe** from [GitHub Actions](https://github.com/the-long-ride/Android-MCP-Build/actions/workflows/manual-build.yml).
2. Extract \`android-mcp.exe\` into a permanent directory, such as \`C:\Tools\Android-MCP\`.
3. Run in PowerShell:

\`\`\`powershell
cd C:\Tools\Android-MCP

# Safe preview: creates/changes nothing, including when Codex CLI is absent
.\android-mcp.exe install --all --dry-run

# Setup all supported desktop apps, IDEs and CLI clients
.\android-mcp.exe install --all

# Or just ChatGPT desktop's Codex host (does not require a codex CLI)
.\android-mcp.exe install chatgpt
.\android-mcp.exe install codex

# Other supported targets:
.\android-mcp.exe install claude
.\android-mcp.exe install claude-desktop
.\android-mcp.exe install antigravity
.\android-mcp.exe install opencode

# Update any existing Android-MCP registration to this EXE location
.\android-mcp.exe install --all --replace
\`\`\`

You **do not** manually launch \`android-mcp.exe\` in MCP mode: after setup,
your chosen agent app launches it through MCP stdio automatically. Restart
your app or reload its MCP configuration after installing.

### Which application uses which configuration?

| Target | Supported surfaces | MCP configuration written | Agent Skill |
|---|---|---|---|
| \`chatgpt\` / \`codex\` | **ChatGPT desktop Codex features**, Codex CLI, Codex IDE extension | \`~/.codex/config.toml\` | \`~/.agents/skills/android-device-automation/SKILL.md\` |
| \`claude\` / \`claude-code\` | Claude Code terminal, Code tab/IDE integrations | \`~/.claude.json\` (user scope) | \`~/.claude/skills/android-device-automation/SKILL.md\` |
| \`claude-desktop\` | Claude Desktop chat | \`%APPDATA%\Claude\claude_desktop_config.json\` (or an existing MSIX-virtualized config) | Uses built-in MCP server instructions |
| \`antigravity\` | Antigravity IDE, 2.0, CLI | \`~/.gemini/config/mcp_config.json\` | Both \`~/.gemini/config/skills/\` and \`~/.gemini/antigravity-cli/skills/\` |
| \`opencode\` | OpenCode desktop, IDE, terminal/CLI | \`~/.config/opencode/opencode.json\` (or \`OPENCODE_CONFIG\` when set) | \`~/.config/opencode/skills/\` |

The same EXE works in all clients because it speaks the common MCP
**stdio** protocol. The installer writes different settings for each client.
No client CLI executable is needed to install.

**ChatGPT app clarification:** ChatGPT desktop's *local Codex host*
shares \`config.toml\` with Codex CLI/IDE. Ordinary ChatGPT chats that
use **Plugins** have a separate plugin installation flow and may require
a local MCP plugin created or installed through the ChatGPT UI. Editing
\`~/.codex/config.toml\` **does not automatically make a tool available in
every ordinary ChatGPT conversation or in ChatGPT web/mobile**.

Codex's one-file executable startup may exceed the normal 10-second default;
the installer sets \`startup_timeout_sec = 60\`.

### Configuration safety

- \`--dry-run\` makes **no** client configuration or skill-file changes.
- Existing unrelated JSON and TOML settings are preserved.
- If an Android-MCP entry already exists, it is **preserved** unless
  \`--replace\` is explicitly requested.
- A \`.bak\` copy is written before changes to existing configuration files.
- Malformed JSON/TOML is not overwritten.
- If the active OpenCode config is \`opencode.jsonc\` (contains comments),
  the installer refuses to rewrite it; use OpenCode's configuration UI or
  edit that file directly, preserving comments.
- Claude Desktop on Windows has both traditional and MSIX-managed install
  variants. The installer checks for an **existing** virtualized
  \`claude_desktop_config.json\` and otherwise uses the standard profile
  location. If it is not detected by your Claude Desktop version, select
  *Settings > Developer > Edit Config* and check its actual location.
- Windows SmartScreen may flag unsigned PyInstaller executables. Download
  from trusted GitHub Actions runs and verify the commit before running them.

### Verify inside ChatGPT desktop

Use the ChatGPT desktop app's **Codex** environment, then open:

**Settings → MCP servers → android-mcp → Restart**.

You can also type \`/mcp\` in the Codex composer to inspect available servers.
The direct configuration file is \`%USERPROFILE%\.codex\config.toml\`.
Ask the Codex agent to list devices using Android-MCP.

### Verify other clients

- **Claude Code:** \`/mcp\` inside Claude Code, or \`claude mcp list\` if installed.
- **Claude Desktop:** Developer settings / local MCP connections.
- **Antigravity IDE:** MCP Servers → Manage MCP Servers → View raw config.
  **Antigravity CLI:** \`/mcp\` and \`/skills\`.
- **OpenCode:** Restart the desktop or terminal app, then check its MCP tools.

Before the first device interaction, run:

\`\`\`powershell
adb version
adb devices
\`\`\`

The connected phone should be listed with status \`device\`, not
\`unauthorized\`. ADB lives on the Windows host, **not** inside the EXE.

## What GitHub Actions tests

CI checks the EXE's MCP initialize/tool-discovery handshake, startup/shutdown,
embedded Agent Skill, and no-bundled-ADB requirement. Unit tests simulate
CLI-free installs and verify Codex TOML merging, Claude Code/Desktop
configurations, Antigravity IDE/CLI skills, OpenCode JSON config, backups,
dry runs, and \`--replace\`. The frozen EXE is used to create and validate
client configs on a GitHub-hosted Windows runner.

Real app UI behavior, client-specific policies/permissions, ChatGPT plugin
installation, and actual Android device interactions still need validation
on the user's machine.

### Relevant documentation

- [ChatGPT desktop/Codex MCP](https://learn.chatgpt.com/docs/extend/mcp?surface=app)
- [Claude Code MCP](https://code.claude.com/docs/en/mcp)
- [Claude Desktop local MCP](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop)
- [Antigravity MCP](https://www.antigravity.google/docs/mcp)
- [Antigravity Skills](https://www.antigravity.google/docs/skills)
- [OpenCode configuration](https://docs.opencode.ai/docs/config/)

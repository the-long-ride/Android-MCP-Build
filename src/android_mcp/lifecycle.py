"""Inspect and safely remove Android-MCP's per-client MCP and skill integration.

Only entries pointing to android-mcp.exe and unmodified Android-MCP skills are
managed. Other servers, unrelated instructions and symlink targets are kept.
"""
from __future__ import annotations

import argparse
import json
import ntpath
import os
from pathlib import Path
import re
import sys
import tomllib

from android_mcp import installer


def _normalize(name: str) -> str:
    return {"claude-code": "claude", "chatgpt": "codex"}.get(name, name)


def _config_path(client: str, home: Path) -> Path:
    if client == "claude":
        return home / ".claude.json"
    if client == "claude-desktop":
        return installer._claude_desktop_path(home)
    if client == "codex":
        return (Path(os.environ["CODEX_HOME"]).expanduser()
                if os.getenv("CODEX_HOME") else home / ".codex") / "config.toml"
    if client == "antigravity":
        return home / ".gemini/config/mcp_config.json"
    if client == "opencode":
        return (Path(os.environ["OPENCODE_CONFIG"]).expanduser()
                if os.getenv("OPENCODE_CONFIG") else home / ".config/opencode/opencode.json")
    raise ValueError(f"Unknown client: {client}")


def _mcp_section(client: str) -> str:
    return "mcp" if client == "opencode" else "mcpServers"


def _server_owned(entry: object, exe: Path) -> bool:
    if not isinstance(entry, dict):
        return False
    command = entry.get("command")
    if isinstance(command, list):
        if len(command) != 1 or not isinstance(command[0], str):
            return False
        command = command[0]
    if not isinstance(command, str):
        return False
    # A relocated Windows binary should remain uninstallable, but never remove
    # another server just because its name appears in an argument.
    return ntpath.basename(command).lower() == exe.name.lower()


def _load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except (ValueError, UnicodeError) as exc:
        raise RuntimeError(f"Invalid JSON, left untouched: {path}: {exc}") from exc
    if not isinstance(obj, dict):
        raise RuntimeError(f"Expected JSON object: {path}")
    return obj


def _load_toml(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return tomllib.loads(path.read_text(encoding="utf-8-sig"))
    except (ValueError, UnicodeError) as exc:
        raise RuntimeError(f"Invalid TOML, left untouched: {path}: {exc}") from exc


def _read_mcp(client: str, exe: Path, home: Path) -> tuple[Path, bool]:
    path = _config_path(client, home)
    if client == "opencode" and not path.exists() and path.with_suffix(".jsonc").exists():
        return path, False
    if client == "codex":
        data = _load_toml(path)
        servers = data.get("mcp_servers", {})
    else:
        data = _load_json(path)
        servers = data.get(_mcp_section(client), {})
    if not isinstance(servers, dict):
        raise RuntimeError(f"Invalid MCP server section in {path}")
    return path, _server_owned(servers.get(installer.SERVER_NAME), exe)


def _skill_owned(path: Path, content: str) -> bool:
    if path.is_symlink():
        # Unlink the link itself, never resolve then delete its target.
        # A broken symlink into the same named skill is also removable.
        target = path.resolve(strict=False)
        return target.name == "SKILL.md" and target.parent.name == installer.SKILL_NAME
    return path.is_file() and path.read_text(encoding="utf-8") == content


def installed_clients(exe: Path, home: Path, content: str) -> list[dict]:
    """Report actual per-client registrations and owned skill files."""
    result = []
    for client in installer.ALL_CLIENTS:
        config, mcp = _read_mcp(client, exe, home)
        skills = [p for p in installer._skill_paths(client, home) if
                  (p.exists() or p.is_symlink()) and _skill_owned(p, content)]
        if mcp or skills:
            result.append({
                "target": client,
                "mcp": mcp,
                "skills": [str(p) for p in skills],
                "config": str(config),
                "status": "installed" if mcp else "skill-only",
            })
    return result


def _remove_json_mcp(client: str, exe: Path, home: Path, dry_run: bool) -> bool:
    path = _config_path(client, home)
    if path.is_symlink():
        raise RuntimeError(f"Refusing to rewrite linked MCP configuration: {path}")
    data = _load_json(path)
    section = data.get(_mcp_section(client))
    if not isinstance(section, dict) or not _server_owned(section.get(installer.SERVER_NAME), exe):
        return False
    # Remove exactly our server. Preserve all other server entries and metadata.
    del section[installer.SERVER_NAME]
    if not section:
        del data[_mcp_section(client)]
    print(f"  {'Would remove' if dry_run else 'Removed'} MCP entry: {path}")
    installer._save(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n", dry_run)
    return True


_CODEX_TABLE = re.compile(
    r"""(?m)^[ \t]*\[mcp_servers\.(?:android-mcp|"android-mcp"|'android-mcp')\][ \t]*(?:#.*)?$"""
)
_NEXT_TABLE = re.compile(r"(?m)^[ \t]*\[{1,2}[^]\r\n]+]{1,2}[ \t]*(?:#.*)?$")


def _remove_codex_mcp(exe: Path, home: Path, dry_run: bool) -> bool:
    path = _config_path("codex", home)
    if path.is_symlink():
        raise RuntimeError(f"Refusing to rewrite linked MCP configuration: {path}")
    data = _load_toml(path)
    servers = data.get("mcp_servers", {})
    if not isinstance(servers, dict) or not _server_owned(servers.get(installer.SERVER_NAME), exe):
        return False
    original = path.read_text(encoding="utf-8-sig")
    match = _CODEX_TABLE.search(original)
    if not match:
        raise RuntimeError(f"Nonstandard Codex MCP entry, edit manually: {path}")
    next_match = _NEXT_TABLE.search(original, match.end())
    end = match.end() + next_match.start() if next_match else len(original)
    if next_match and (next_match.group().lstrip().startswith("[mcp_servers.android-mcp.")
                       or next_match.group().lstrip().startswith('["mcp_servers.android-mcp.')):
        raise RuntimeError(f"Nested Codex MCP tables, edit manually: {path}")
    result = original[:match.start()] + original[end:]
    if installer.SERVER_NAME in tomllib.loads(result).get("mcp_servers", {}):
        raise RuntimeError(f"Cannot safely remove Codex MCP entry: {path}")
    print(f"  {'Would remove' if dry_run else 'Removed'} MCP entry: {path}")
    installer._save(path, result, dry_run)
    return True


def uninstall(
    targets: list[str], exe: Path, home: Path, content: str, dry_run: bool = False,
) -> int:
    failures = 0
    for target in targets:
        client = _normalize(target)
        print(f"[{target}]")
        try:
            if client not in installer.ALL_CLIENTS:
                raise ValueError(f"Unsupported client: {target}")
            if client == "codex":
                removed = _remove_codex_mcp(exe, home, dry_run)
            else:
                removed = _remove_json_mcp(client, exe, home, dry_run)
            for path in installer._skill_paths(client, home):
                if not path.exists() and not path.is_symlink():
                    continue
                if not _skill_owned(path, content):
                    print(f"  Modified/unmanaged skill preserved: {path}")
                    continue
                print(f"  {'Would remove' if dry_run else 'Removed'} skill: {path}")
                if not dry_run:
                    path.unlink()  # symlinks: unlink ONLY the link
                    try:
                        path.parent.rmdir()  # only empty, tool-owned skill folder
                    except OSError:
                        pass
                removed = True
            if not removed:
                print("  No owned installation found.")
        except (OSError, ValueError, RuntimeError) as exc:
            failures += 1
            print(f"  ERROR: {exc}", file=sys.stderr)
    return int(failures > 0)


def main_uninstall(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="android-mcp.exe uninstall")
    parser.add_argument("client", nargs="?", choices=installer.CLIENTS)
    parser.add_argument("--all", action="store_true", help="Remove from every supported AI client")
    parser.add_argument("--dry-run", action="store_true")
    opts = parser.parse_args(argv)
    if bool(opts.client) == bool(opts.all):
        parser.error("specify one client or --all")
    try:
        return uninstall(
            list(installer.ALL_CLIENTS) if opts.all else [opts.client],
            installer.executable_path(), Path.home(), installer.embedded_skill(), opts.dry_run,
        )
    except (OSError, RuntimeError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")


def main_installed_list(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="android-mcp.exe installed-list")
    parser.parse_args(argv)
    try:
        records = installed_clients(
            installer.executable_path(), Path.home(), installer.embedded_skill()
        )
    except (OSError, RuntimeError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")
    if not records:
        print("No Android-MCP AI agent integrations found.")
    for item in records:
        print(f"{item['target']}: {item['status']} "
              f"(MCP={'yes' if item['mcp'] else 'no'}, skills={len(item['skills'])})")
    return 0

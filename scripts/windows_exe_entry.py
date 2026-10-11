"""Entry point for the single-file Windows MCP server and opt-in installer."""
from __future__ import annotations

import argparse
import sys


def _show_help() -> None:
    """Show both MCP-server options and the embedded install command."""
    parser = argparse.ArgumentParser(
        prog="android-mcp.exe",
        description="Android-MCP: control Android devices through a local MCP stdio server.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Commands:\n"
            "  install                   Configure an AI client and install its Agent Skill\n"
            "  install --all             Configure all supported AI client families\n"
            "  install --help            Show installer targets and options\n"
            "\n"
            "Examples:\n"
            "  android-mcp.exe install --all\n"
            "  android-mcp.exe install codex --dry-run\n"
            "  android-mcp.exe install claude-desktop --replace\n"
            "\n"
            "Run without arguments to start the MCP stdio server. Your AI client\n"
            "starts the server automatically after installation."
        ),
    )
    parser.add_argument("--device", metavar="DEVICE", help="ADB device serial or host:port")
    parser.add_argument(
        "--connection", "--transport",
        choices=("auto", "usb", "wifi"),
        help="Preferred device connection type",
    )
    parser.add_argument(
        "--wifi", nargs="?", const="", metavar="HOST",
        help="Use Wi-Fi ADB with optional HOST[:PORT] (default port 5555)",
    )
    parser.add_argument(
        "--usb", nargs="?", const="", metavar="SERIAL",
        help="Use USB ADB with optional device serial",
    )
    parser.print_help()


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "install":
        from android_mcp.installer import main as install_main
        return install_main(sys.argv[2:])
    if any(arg in ("--help", "-h") for arg in sys.argv[1:]):
        _show_help()
        return 0
    # No arguments (or MCP device flags) keep launching the stdio server.
    from android_mcp.__main__ import main as server_main
    server_main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

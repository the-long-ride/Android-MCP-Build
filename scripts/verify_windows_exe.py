"""Smoke-test the packaged Windows MCP executable without an Android device.

Runs a real MCP initialize + tools/list exchange over stdio. Connecting
to ADB is lazy, so the CI runner must NOT need ADB or Android Studio.
"""
import asyncio
import os
from pathlib import Path
import subprocess
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

EXPECTED_TOOLS = {
    "ListDevices", "ConnectDevice", "Device", "Snapshot", "Click",
    "ClickBySelector", "LongClick", "Swipe", "Type", "Drag",
    "Press", "Notification", "Wait", "WaitForElement",
}


async def run_mcp_smoke(exe: Path) -> None:
    params = StdioServerParameters(
        command=str(exe),
        args=[],
        env=dict(os.environ),
    )
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            init = await asyncio.wait_for(session.initialize(), timeout=90)
            advertised = getattr(init, 'instructions', '') or ''
            for token in ('Observe', 'ClickBySelector', 'Claude Code', 'Codex', 'Antigravity', 'OpenCode'):
                assert token in advertised, f'Frozen MCP server instructions missing {token}'
            print(f'MCP initialization instructions passed ({len(advertised)} chars).')
            result = await asyncio.wait_for(session.list_tools(), timeout=60)
            found = {tool.name for tool in result.tools}
            missing = EXPECTED_TOOLS - found
            if missing:
                raise AssertionError(f"Missing MCP tools: {sorted(missing)}")
            print(f"MCP stdio handshake passed; exposed {len(found)} tools.")


def main() -> None:
    exe = Path(sys.argv[1] if len(sys.argv) > 1 else "dist/android-mcp.exe").resolve()
    if not exe.is_file():
        raise FileNotFoundError(exe)
    # Always print the frozen application's output. A non-zero exit commonly
    # indicates a missing PyInstaller hidden import or runtime data file.
    # Using check=True without printing captured stderr hid the real failure.
    result = subprocess.run(
        [str(exe), "--help"],
        capture_output=True,
        text=True,
        errors="replace",
        timeout=90,
        check=False,
    )
    print(f"EXE --help exit code: {result.returncode}", flush=True)
    print(f"EXE stdout:\n{result.stdout or '(empty)'}", flush=True)
    print(f"EXE stderr:\n{result.stderr or '(empty)'}", flush=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"Frozen android-mcp.exe failed to start (exit {result.returncode}). "
            "Inspect the EXE stderr above for the underlying error."
        )
    for token in ("--device", "--connection", "install", "install --all", "install --help"):
        if token not in result.stdout:
            raise AssertionError(f"EXE --help does not show {token!r}")
    print("EXE --help includes MCP options and install command.")
    install_help = subprocess.run(
        [str(exe), "install", "--help"],
        capture_output=True,
        text=True,
        errors="replace",
        timeout=90,
        check=False,
    )
    if install_help.returncode != 0:
        print(f"install --help stderr:\\n{install_help.stderr}", flush=True)
        raise RuntimeError(f"EXE install --help exited with {install_help.returncode}")
    for token in ("--all", "--dry-run", "--replace", "codex", "claude-desktop", "antigravity", "opencode"):
        if token not in install_help.stdout:
            raise AssertionError(f"EXE install --help is missing {token!r}")
    print("EXE install --help lists all installer options.")
    asyncio.run(asyncio.wait_for(run_mcp_smoke(exe), timeout=180))
    # A tool-list handshake can succeed even when FastMCP/Docket raises an
    # exception during shutdown (e.g. fakeredis missing Lua/EVALSHA).
    # Close stdin immediately in a separate process and insist on exit 0.
    shutdown = subprocess.run(
        [str(exe)],
        input=b"",
        capture_output=True,
        timeout=120,
        check=False,
    )
    stderr = shutdown.stderr.decode("utf-8", errors="replace")
    print(f"MCP EOF shutdown exit code: {shutdown.returncode}", flush=True)
    # PyInstaller's Windows stdio teardown can emit a non-fatal traceback
    # saying "I/O operation on closed file" after the normal exit path.
    # Do not mask actual runtime errors or nonzero exit codes.
    fatal_markers = (
        "[PYI-", "redis.exceptions.ResponseError:",
        "ModuleNotFoundError:", "FileNotFoundError:",
        "ImportError:", "RuntimeError:",
    )
    fatal = shutdown.returncode != 0 or any(x in stderr for x in fatal_markers)
    if fatal:
        print(f"MCP shutdown stderr:\\n{stderr}", flush=True)
        raise RuntimeError("The standalone MCP server failed during shutdown")
    if "ValueError: I/O operation on closed file." in stderr:
        print("Note: harmless Windows/PyInstaller closed-stderr notice during shutdown.")
    print("MCP process shutdown exit status and fatal-error checks passed.", flush=True)


if __name__ == "__main__":
    main()

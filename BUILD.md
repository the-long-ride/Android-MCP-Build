# Build a standalone Windows Android-MCP executable

This fork includes a **manual GitHub Actions build** that creates
`android-mcp.exe` using PyInstaller. The EXE bundles the Python interpreter,
Android-MCP code, and Python dependencies. **It does not bundle or install
ADB, Android Studio, or an LLM.**

## Build on GitHub

1. Open [Manual Android-MCP Windows EXE](https://github.com/the-long-ride/Android-MCP-Build/actions/workflows/manual-build.yml).
2. Click **Run workflow**, choose the `master` branch, and confirm.
3. Open the completed run.
4. Under **Artifacts**, download **android-mcp-windows-exe**.
5. Extract the ZIP to get `android-mcp.exe`.

The workflow runs on `windows-latest` with Python 3.13 and PyInstaller
`--onefile --console`. The `--console` flag is intentional: MCP uses
standard input/output to communicate with Claude Code. Running the EXE by
double-clicking is **not** the intended usage.

The workflow smoke-tests the EXE's `--help` output and performs a real
MCP initialize + list-tools handshake. It also checks the PyInstaller
archive for a bundled `adb.exe`. A connected Android device is not needed
for those checks. **Actual Android UI interactions must still be tested
locally with a device.**


## Troubleshooting a failed EXE build

If the workflow fails at **Verify executable and MCP stdio protocol**,
look at the printed `EXE stdout` and `EXE stderr` in that step.
The verification script prints the **actual frozen-application exception**
instead of showing only `CalledProcessError`.

The build uses PyInstaller's `--debug=noarchive` collection mode because
the locked FastMCP 2.14.0 dependency stack includes `beartype`, for which
PyInstaller frozen-import incompatibilities have been reported.

On workflow failure, the artifact `android-mcp-exe-build-diagnostics`
includes PyInstaller's warning and import-graph files if available.

The custom hook in `scripts/pyinstaller_hooks/hook-adbutils.py` overrides
PyInstaller's standard hook, which normally collects a vendored `adb.exe`
from `adbutils`. The workflow explicitly checks that no `adb.exe` is
present in the EXE bundle.

A passing build test demonstrates CLI startup and MCP tool discovery, **not**
real Android device control. Check `adb devices` and make one device tool
call on the destination computer before relying on the build.

## Requirements on your Windows computer

- Claude Code.
- ADB installed on **the Windows host** (for example, standalone Android SDK
  Platform-Tools) and accessible on `PATH`, or configured using
  `ANDROID_MCP_ADB_PATH`.
- A connected, authorized Android device with USB debugging enabled, or a
  reachable Android emulator.

No installation of Python, uv, PyInstaller, Android Studio, or LLM API key is
needed to **run** the resulting Windows EXE.

> ADB is a host-side executable. The Android phone runs the debugging daemon
> (`adbd`). Android-MCP does not install ADB on the device.

## Register the EXE with Claude Code

Move the extracted EXE to a permanent folder, for example:
`C:\\Tools\\Android-MCP\\android-mcp.exe`.

Open PowerShell:

```powershell
adb version
adb devices

claude mcp add --scope user android-mcp -- "C:\\Tools\\Android-MCP\\android-mcp.exe"
claude mcp list
```

If ADB is not on `PATH`, set its path in the environment launching Claude Code
(or in your MCP server environment), then restart Claude Code:

```powershell
$env:ANDROID_MCP_ADB_PATH = "C:\\Tools\\platform-tools\\adb.exe"
claude
```

This project searches for existing ADB using the override
`ANDROID_MCP_ADB_PATH`, `PATH`, and known local SDK paths.
It never needs Android Studio to launch.

## Output, versus the previous workflow

| Previous build | Windows EXE build |
| --- | --- |
| `android_mcp-0.2.0-*.whl` | `android-mcp.exe` |
| `android_mcp-0.2.0.tar.gz` | One executable (downloaded in a GitHub artifact ZIP) |
| Python 3.13 needed on target | Python interpreter included |
| `uv pip install` to run | Run directly as an MCP server |
| Uses an existing ADB executable | Uses an existing ADB executable |

The EXE is an MCP **server**, not an Android app (APK). It runs on Windows.
You do not need a separate LLM API key; Claude Code does the reasoning.

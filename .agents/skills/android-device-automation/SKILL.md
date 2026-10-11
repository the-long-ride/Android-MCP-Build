---
name: android-device-automation
description: Control and test Android phones or emulators using the Android-MCP server. Use for navigating Android apps, inspecting screens, tapping, typing, swiping, reproducing UI bugs, and verifying mobile workflows with screenshots or accessibility hierarchy.
---

# Android device automation with Android-MCP

Use the **Android-MCP** server's tools for Android UI automation. The client agent (Claude Code, Codex, Antigravity, or OpenCode) performs all reasoning; Android-MCP is a direct device-control bridge, not an autonomous agent. Do not request an LLM API key for Android-MCP.

## Preconditions

1. Identify the active MCP tools by their exposed names, normally under server `android-mcp`.
2. Use `ListDevices` to inspect available devices. When several are connected, ask the user which to target; use `Device(action="connect", serial="...")` or `ConnectDevice` if needed.
3. If no usable device exists, ask the user to authorize USB debugging or connect Wi-Fi ADB. ADB must be installed on the **host computer**, not the phone. Never assume an emulator or device is available.
4. If the MCP server is unavailable, report the connection issue; do not fabricate tool results.

## Observe -> decide -> act -> verify

1. **Observe:** Call `Snapshot(use_vision=false)` for accessibility/UI hierarchy; use `Snapshot(use_vision=true)` when hierarchy is insufficient, UI is visual-only, or visual verification matters. Prefer unannotated screenshot only when coordinates/overlays interfere with interpretation.
2. **Ground targets:** Prefer `ClickBySelector(text=..., resourceId=..., description=..., className=...)` for stable elements. Prefer resource IDs or accessibility labels over coordinates. Use `Click(x,y)` only if the screen was recently observed and no reliable selector is available.
3. **Wait for state:** Use `WaitForElement` for asynchronous transitions. Use `Wait` only for a specific unavoidable time delay.
4. **Act:** Use `Click`, `LongClick`, `Swipe`, `Drag`, `Press`, and `Type` as appropriate. For text entry, focus the correct input first (e.g., with `ClickBySelector`); `Type` sends text to the focused field. Do not assume the `x,y` arguments of `Type` focus the field.
5. **Verify:** After navigation, data entry, or other meaningful operations, call `Snapshot` or `WaitForElement` to confirm the expected state. Do not report success without observed evidence.
6. **Recover:** On timeout or mismatch, re-observe the screen, handle dialogs, choose a fresh selector or grounded coordinate, and retry with a small limit. Do not blindly repeat failed taps on stale coordinates.

## Device and task safety

- Prefer a test phone/emulator. Do not install apps, erase data, change security settings, send messages, make purchases, or submit sensitive forms without clear user intent and appropriate confirmation.
- Screenshots and UI trees may include personal data. Include only necessary details in reports and avoid exposing passwords, OTPs, tokens, or private notifications.
- Do not invoke an undocumented `Shell` or `RunTask` MCP tool: this version exposes direct control tools, not an autonomous agent or a general-purpose ADB shell tool.
- `Notification` opens the notification shade; it is not a read-only notification retrieval operation.
- For multi-step tests, document actual actions, observed states, failures, and limitations. Distinguish assertions from verified facts.

## Example task

For "open Settings and verify Bluetooth": use `ListDevices`; connect the selected device; `Snapshot` to establish the state; navigate with selector or grounded UI controls; use `WaitForElement` after transitions; verify the Bluetooth state through `Snapshot`; summarize what was actually observed.

## MCP tool reference

Device: `ListDevices`, `ConnectDevice`, `Device`.
State: `Snapshot`.
Interaction: `Click`, `ClickBySelector`, `LongClick`, `Swipe`, `Drag`, `Type`, `Press`, `Notification`.
Synchronization: `Wait`, `WaitForElement`.

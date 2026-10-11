# Installs the Android-MCP EXE and portable Android device automation skill
# for one or more supported AI clients. This is opt-in and runs on Windows
# PowerShell 7+. It never installs ADB or an LLM.
[CmdletBinding()]
param(
    [ValidateSet('ClaudeCode', 'Codex', 'Antigravity', 'OpenCode')]
    [string[]]$Clients = @('ClaudeCode', 'Codex', 'Antigravity', 'OpenCode'),
    [string]$ExePath = (Join-Path $PSScriptRoot 'android-mcp.exe'),
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

$resolvedExe = (Resolve-Path -LiteralPath $ExePath -ErrorAction Stop).Path
if ([IO.Path]::GetExtension($resolvedExe) -ne '.exe') {
    throw "Expected Windows EXE; received: $resolvedExe"
}

$skillCandidates = @(
    (Join-Path $PSScriptRoot 'android-device-automation/SKILL.md'),
    (Join-Path (Split-Path $PSScriptRoot -Parent) '.agents/skills/android-device-automation/SKILL.md')
)
$skillSource = $skillCandidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
if (-not $skillSource) {
    throw 'Missing android-device-automation/SKILL.md; extract the complete GitHub build artifact.'
}

function Install-SkillFile([string]$target) {
    Write-Host "Skill: $target"
    if ($DryRun) { return }
    $parent = Split-Path -Parent $target
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    Copy-Item -LiteralPath $skillSource -Destination $target -Force
}

function Set-McpJson([string]$configPath, [string]$client) {
    Write-Host "MCP configuration ($client): $configPath"
    if ($DryRun) { return }
    $config = @{}
    if (Test-Path -LiteralPath $configPath -PathType Leaf) {
        # Preserve all existing unrelated settings. Invalid JSON must fail
        # rather than overwrite an existing user config.
        $text = Get-Content -LiteralPath $configPath -Raw
        if ($text.Trim()) {
            $config = ConvertFrom-Json -InputObject $text -AsHashtable -ErrorAction Stop
            if (-not ($config -is [System.Collections.IDictionary])) {
                throw "Configuration root must be an object: $configPath"
            }
        }
        Copy-Item -LiteralPath $configPath -Destination "$configPath.bak" -Force
    }
    if ($client -eq 'Antigravity') {
        if (-not $config.ContainsKey('mcpServers') -or $null -eq $config['mcpServers']) {
            $config['mcpServers'] = @{}
        }
        $config['mcpServers']['android-mcp'] = @{
            command = $resolvedExe
            args = @()
        }
    } else {
        if (-not $config.ContainsKey('mcp') -or $null -eq $config['mcp']) {
            $config['mcp'] = @{}
        }
        $config['mcp']['android-mcp'] = @{
            type = 'local'
            command = @($resolvedExe)
            enabled = $true
            timeout = 60000
        }
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $configPath) | Out-Null
    $json = ConvertTo-Json -InputObject $config -Depth 50
    [IO.File]::WriteAllText($configPath, $json + [Environment]::NewLine, [Text.UTF8Encoding]::new($false))
}

function Add-McpCli([string]$cli, [string[]]$cliArgs) {
    Write-Host "MCP ($cli): $cli $($cliArgs -join ' ')"
    if ($DryRun) { return }
    if (-not (Get-Command $cli -ErrorAction SilentlyContinue)) {
        throw "$cli was not found on PATH. Install the AI client first or select other -Clients."
    }
    & $cli @cliArgs
    if ($LASTEXITCODE -ne 0) {
        throw "$cli MCP registration failed (exit $LASTEXITCODE). If android-mcp already exists, remove the old entry in that client, then rerun."
    }
}

foreach ($client in ($Clients | Select-Object -Unique)) {
    switch ($client) {
        ClaudeCode {
            Install-SkillFile (Join-Path $HOME '.claude/skills/android-device-automation/SKILL.md')
            Add-McpCli 'claude' @('mcp', 'add', '--scope', 'user', 'android-mcp', '--', $resolvedExe)
        }
        Codex {
            Install-SkillFile (Join-Path $HOME '.agents/skills/android-device-automation/SKILL.md')
            Add-McpCli 'codex' @('mcp', 'add', 'android-mcp', '--', $resolvedExe)
        }
        Antigravity {
            Install-SkillFile (Join-Path $HOME '.gemini/config/skills/android-device-automation/SKILL.md')
            Set-McpJson (Join-Path $HOME '.gemini/config/mcp_config.json') 'Antigravity'
        }
        OpenCode {
            Install-SkillFile (Join-Path $HOME '.config/opencode/skills/android-device-automation/SKILL.md')
            Set-McpJson (Join-Path $HOME '.config/opencode/opencode.json') 'OpenCode'
        }
    }
}
if ($DryRun) {
    Write-Host 'Dry run completed: no changes made.'
} else {
    Write-Host 'Installation configured. Restart AI clients to reload MCP servers and skills.'
    Write-Host 'The host computer must have ADB on PATH or ANDROID_MCP_ADB_PATH set.'
}

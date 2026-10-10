#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$RepositoryPath,
    [switch]$CheckOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Resolve before inspecting, starting or stopping any OpenClaw process.
$selectionHelper = Join-Path $PSScriptRoot 'scripts\runtime-selection.mjs'
$runtimeSelectionJson = & node $selectionHelper
if ($LASTEXITCODE -ne 0) { throw 'Runtime selection is invalid. Hermes HUD runs inside Ubuntu on WSL2; use netclaw hud there.' }
$runtimeSelection = $runtimeSelectionJson | ConvertFrom-Json
if ($runtimeSelection.kind -ne 'openclaw') { throw 'Hermes HUD requires Ubuntu on WSL2. In the Linux checkout run netclaw hud.' }
$env:NETCLAW_RUNTIME = 'openclaw'
$env:OPENCLAW_HOME = $runtimeSelection.home
$env:OPENCLAW_STATE_DIR = $runtimeSelection.home
$env:OPENCLAW_CONFIG_PATH = $runtimeSelection.configPath

if (-not $RepositoryPath) { $RepositoryPath = $PSScriptRoot }
$apiPort = 3001
$apiUrl = "http://localhost:$apiPort"
$restartLock = [Threading.Mutex]::new($false, 'Local\NetClaw-API-Restart-3001')
$lockHeld = $false

function Get-ApiListeners {
    # Do not hide access errors: an incomplete inventory must never trigger a restart.
    @(Get-NetTCPConnection -State Listen -ErrorAction Stop |
        Where-Object LocalPort -eq $apiPort |
        Select-Object -ExpandProperty OwningProcess -Unique)
}
function Test-ApiHealth {
    try {
        $health = Invoke-RestMethod -Uri "$apiUrl/api/health" -TimeoutSec 3
        return $health.ok -eq $true -and $health.service -eq 'netclaw-visual-api'
    } catch { return $false }
}

try {
    try { $lockHeld = $restartLock.WaitOne(0) }
    catch [Threading.AbandonedMutexException] { $lockHeld = $true }
    if (-not $lockHeld) { throw 'Another NetClaw API restart is already in progress.' }

    $repo = (Resolve-Path -LiteralPath $RepositoryPath).Path
    $visual = Join-Path $repo 'ui\netclaw-visual'
    $server = Join-Path $visual 'server.js'
    if (-not (Test-Path -LiteralPath $server -PathType Leaf)) {
        throw "NetClaw server.js not found in $visual. Update the repository path in the launcher."
    }
    $node = (Get-Command node.exe -ErrorAction Stop).Source
    if (-not (Test-Path -LiteralPath (Join-Path $visual 'node_modules\express\package.json'))) {
        throw "Dependencies are missing. Run npm.cmd ci in $visual first."
    }
    & $node --check $server
    if ($LASTEXITCODE -ne 0) { throw 'server.js failed its syntax check. The running API was not stopped.' }

    Write-Host 'NetClaw API only - port 3001' -ForegroundColor Cyan
    Write-Host 'Canvas / visual frontend on port 3000 and OpenClaw are left alone.'
    $listeners = @(Get-ApiListeners)
    if ($listeners.Count -gt 1) { throw 'Multiple processes own port 3001; refusing to stop any of them.' }
    $existing = $null
    if ($listeners.Count -eq 1) {
        $existing = Get-CimInstance Win32_Process -Filter "ProcessId = $($listeners[0])"
        if (-not $existing -or $existing.Name -ne 'node.exe' -or -not (Test-ApiHealth)) {
            throw 'Port 3001 is occupied but cannot be verified as a healthy NetClaw Node API. Nothing was stopped.'
        }
        $entry = '(?i)(?:^|\s)(?:"' + [regex]::Escape($server) + '"|server\.js|\.\\server\.js)\s*$'
        if ($existing.CommandLine -notmatch $entry) {
            throw 'The listener does not run this NetClaw server.js. Nothing was stopped.'
        }
        Write-Host "Verified NetClaw API process $($existing.ProcessId)."
    }
    if ($CheckOnly) {
        Write-Host 'Preflight passed. No services were changed.' -ForegroundColor Green
        return
    }

    Write-Host 'SSH sessions will disconnect. In-memory collection data and login overrides reset.' -ForegroundColor Yellow
    if ($existing) {
        # Recheck identity immediately before stopping; never kill by process name.
        $current = Get-CimInstance Win32_Process -Filter "ProcessId = $($existing.ProcessId)"
        if (-not $current -or $current.CreationDate -ne $existing.CreationDate -or
            $current.CommandLine -ne $existing.CommandLine) { throw 'API process changed during preflight. Retry.' }
        Stop-Process -Id $existing.ProcessId -ErrorAction Stop
    }
    $deadline = (Get-Date).AddSeconds(10)
    while (@(Get-ApiListeners).Count -gt 0) {
        if ((Get-Date) -ge $deadline) { throw 'Port 3001 is still occupied. No replacement was launched.' }
        Start-Sleep -Milliseconds 300
    }

    $logDirectory = Join-Path $env:LOCALAPPDATA 'NetClaw\logs'
    $null = New-Item -ItemType Directory -Path $logDirectory -Force
    $stamp = (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
    $stdout = Join-Path $logDirectory "api-$stamp.log"
    $stderr = Join-Path $logDirectory "api-$stamp.error.log"
    # The child inherits this override only; restore the caller's environment afterward.
    $previousPort = $env:HUD_PORT
    try {
        $env:HUD_PORT = [string]$apiPort
        $started = Start-Process -FilePath $node -ArgumentList @(('"' + $server + '"')) `
            -WorkingDirectory $visual -WindowStyle Hidden -PassThru `
            -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    } finally { $env:HUD_PORT = $previousPort }

    Write-Host "Starting API. Logs: $logDirectory"
    $deadline = (Get-Date).AddSeconds(40)
    do {
        $started.Refresh()
        if ($started.HasExited) { throw "API exited during startup. Read $stderr" }
        if ((Test-ApiHealth) -and (@(Get-ApiListeners) -contains $started.Id)) {
            $lookup = Invoke-RestMethod -Uri "$apiUrl/api/topology/lookup" -Method Post `
                -ContentType 'application/json' -Body '{"type":"ip","value":"192.0.2.1"}' -TimeoutSec 5
            if (-not $lookup.PSObject.Properties['closest']) {
                throw 'API is healthy but closest-device correlation is not available. Check the repository version.'
            }
            Write-Host "API ready on port 3001 (PID $($started.Id)). Closest-device correlation enabled." -ForegroundColor Green
            Write-Host 'Refresh Canvas: http://localhost:3000/canvas.html'
            Write-Host 'Reconnect terminal sessions. If collection asks for credentials, enter them in Manage authorization.'
            return
        }
        Start-Sleep -Milliseconds 500
    } while ((Get-Date) -lt $deadline)
    throw "API did not become healthy within 40 seconds. Read $stderr"
} catch {
    Write-Host "Restart failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
} finally {
    if ($lockHeld) { $restartLock.ReleaseMutex() }
    $restartLock.Dispose()
}

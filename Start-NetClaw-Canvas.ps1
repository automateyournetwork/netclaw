#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$RepositoryPath,
    [ValidateRange(1024, 65535)][int]$Port = 3000,
    [switch]$NoBrowser,
    [switch]$NoPause
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
$canvasUrl = "http://localhost:$Port/canvas.html"

function Test-CanvasReady {
    try {
        $page = Invoke-WebRequest -Uri $canvasUrl -UseBasicParsing -TimeoutSec 2
        return $page.StatusCode -eq 200 -and $page.Content.Contains('NetClaw Canvas Chat')
    } catch { return $false }
}
function Test-FrontendPort {
    $client = [Net.Sockets.TcpClient]::new()
    try {
        $pending = $client.BeginConnect('localhost', $Port, $null, $null)
        if (-not $pending.AsyncWaitHandle.WaitOne(500)) { return $false }
        $client.EndConnect($pending)
        return $true
    } catch { return $false }
    finally { $client.Dispose() }
}

try {
    Write-Host "NetClaw Canvas frontend only - port $Port" -ForegroundColor Cyan
    Write-Host 'The NetClaw API and OpenClaw gateway are not started, stopped or restarted.'
    $visual = Join-Path (Resolve-Path -LiteralPath $RepositoryPath).Path 'ui\netclaw-visual'
    $vite = Join-Path $visual 'node_modules\vite\bin\vite.js'
    if (-not (Test-Path -LiteralPath (Join-Path $visual 'canvas.html'))) { throw "Canvas was not found in $visual. Check the repository path." }

    if (Test-CanvasReady) {
        Write-Host 'Canvas is already running. Reusing it.' -ForegroundColor Green
    } else {
        if (Test-FrontendPort) { throw "Port $Port is occupied but is not serving NetClaw Canvas. Nothing was stopped." }
        if (-not (Test-Path -LiteralPath $vite)) { throw "Vite is missing. Run npm.cmd ci in $visual first." }
        $node = (Get-Command node.exe -ErrorAction Stop).Source
        $logs = Join-Path $env:LOCALAPPDATA 'NetClaw\logs'
        $null = New-Item -ItemType Directory -Path $logs -Force
        $stamp = (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
        $stdout = Join-Path $logs "frontend-$stamp.log"
        $stderr = Join-Path $logs "frontend-$stamp.error.log"
        $previousApiPort = $env:HUD_PORT
        try {
            $env:HUD_PORT = '3001'
            $frontend = Start-Process -FilePath $node `
                -ArgumentList @(('"' + $vite + '"'), '--host', 'localhost', '--port', [string]$Port, '--strictPort') `
                -WorkingDirectory $visual -WindowStyle Hidden -PassThru `
                -RedirectStandardOutput $stdout -RedirectStandardError $stderr
        } finally { $env:HUD_PORT = $previousApiPort }
        $deadline = (Get-Date).AddSeconds(40)
        do {
            $frontend.Refresh()
            if ($frontend.HasExited) { throw "Frontend exited during startup. Read $stderr" }
            if (Test-CanvasReady) { break }
            if ((Get-Date) -ge $deadline) { throw "Canvas did not become ready. Read $stderr" }
            Start-Sleep -Milliseconds 400
        } while ($true)
        Write-Host "Frontend started (PID $($frontend.Id)). Logs: $logs" -ForegroundColor Green
    }
    Write-Host "Canvas ready: $canvasUrl" -ForegroundColor Green
    try {
        $health = Invoke-RestMethod -Uri 'http://localhost:3001/api/health' -TimeoutSec 2
        if ($health.service -ne 'netclaw-visual-api' -or -not $health.ok) { throw 'API not ready' }
    } catch {
        Write-Host 'Canvas is open, but the API is offline. Use Restart NetClaw API in this folder for SSH, collection and Intent.' -ForegroundColor Yellow
    }
    if (-not $NoBrowser) { Start-Process $canvasUrl }
} catch {
    Write-Host "Canvas startup failed: $($_.Exception.Message)" -ForegroundColor Red
    if (-not $NoPause) { $null = Read-Host 'Press Enter to close' }
    exit 1
}

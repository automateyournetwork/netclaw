#Requires -Version 5.1

[CmdletBinding()]
param(
    [ValidateSet('Canvas', 'HUD')]
    [string]$Interface = 'Canvas',

    [switch]$NoBrowser,

    [switch]$SkipGateway
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


$repoRoot = $PSScriptRoot
$visualRoot = Join-Path $repoRoot 'ui\netclaw-visual'
$canvasUrl = 'http://localhost:3000/canvas.html'
$hudUrl = 'http://localhost:3000/'
$targetUrl = if ($Interface -eq 'HUD') { $hudUrl } else { $canvasUrl }

function Write-Step {
    param([string]$Message)
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function ConvertTo-QuotedPowerShellLiteral {
    param([string]$Value)
    return "'" + $Value.Replace("'", "''") + "'"
}

function Resolve-RequiredCommand {
    param(
        [string[]]$Names,
        [string]$InstallHint
    )

    foreach ($name in $Names) {
        $resolved = Get-Command $name -ErrorAction SilentlyContinue
        if ($resolved) {
            return $resolved.Source
        }
    }

    throw "Required command '$($Names[0])' was not found. $InstallHint"
}

function Test-TcpPort {
    param(
        [int]$Port,
        [int]$TimeoutMilliseconds = 400
    )

    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $pending = $client.BeginConnect('127.0.0.1', $Port, $null, $null)
        if (-not $pending.AsyncWaitHandle.WaitOne($TimeoutMilliseconds)) {
            return $false
        }
        $client.EndConnect($pending)
        return $true
    }
    catch {
        return $false
    }
    finally {
        $client.Dispose()
    }
}

function Test-HttpContent {
    param(
        [string]$Url,
        [string]$ExpectedText = ''
    )

    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -lt 200 -or $response.StatusCode -ge 400) {
            return $false
        }
        return (-not $ExpectedText) -or $response.Content.Contains($ExpectedText)
    }
    catch {
        return $false
    }
}

function Test-OpenClawGateway {
    param([string]$OpenClawPath)

    try {
        & $OpenClawPath gateway health *> $null
        return $LASTEXITCODE -eq 0
    }
    catch {
        return $false
    }
}

function Wait-ForCondition {
    param(
        [scriptblock]$Condition,
        [string]$Description,
        [int]$TimeoutSeconds = 45
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        if (& $Condition) {
            Write-Host "    Ready: $Description" -ForegroundColor Green
            return
        }
        Start-Sleep -Milliseconds 500
    } while ((Get-Date) -lt $deadline)

    throw "Timed out waiting for $Description. Check the service window for its error output."
}

function Start-ServiceConsole {
    param(
        [string]$Title,
        [string]$WorkingDirectory,
        [string]$CommandText,
        [string]$ShellPath
    )

    $titleLiteral = ConvertTo-QuotedPowerShellLiteral $Title
    $wrappedCommand = "`$Host.UI.RawUI.WindowTitle = $titleLiteral; $CommandText"
    Start-Process -FilePath $ShellPath `
        -ArgumentList @('-NoLogo', '-NoProfile', '-NoExit', '-ExecutionPolicy', 'Bypass', '-Command', $wrappedCommand) `
        -WorkingDirectory $WorkingDirectory `
        -PassThru
}

if (-not (Test-Path -LiteralPath (Join-Path $visualRoot 'package.json'))) {
    throw "NetClaw Visual was not found at '$visualRoot'. Keep this script in the NetClaw repository root."
}

$nodePath = Resolve-RequiredCommand @('node.exe', 'node') 'Install a supported Node.js release, then reopen PowerShell.'
$npmPath = Resolve-RequiredCommand @('npm.cmd', 'npm') 'Install npm with Node.js, then reopen PowerShell.'
$shellPath = Resolve-RequiredCommand @('pwsh.exe', 'powershell.exe') 'PowerShell is required to launch the service consoles.'

Write-Host 'NetClaw startup' -ForegroundColor Green
Write-Host "Repository: $repoRoot"
Write-Host "Node:       $(& $nodePath --version)"

if (-not (Test-Path -LiteralPath (Join-Path $visualRoot 'node_modules'))) {
    Write-Step 'Installing NetClaw Visual dependencies (first run only)'
    Push-Location $visualRoot
    try {
        if (Test-Path -LiteralPath (Join-Path $visualRoot 'package-lock.json')) {
            & $npmPath ci
        }
        else {
            & $npmPath install
        }
        if ($LASTEXITCODE -ne 0) {
            throw "npm dependency installation failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }
}

if (-not $SkipGateway) {
    $openClawPath = Resolve-RequiredCommand @('openclaw.cmd', 'openclaw.ps1', 'openclaw') "Install OpenClaw and run 'openclaw onboard' first."
    $gatewayConfigPath = $env:OPENCLAW_CONFIG_PATH
    $gatewayPort = 18789
    $chatCompletionsEnabled = $false

    $openClawVersion = & $openClawPath --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "OpenClaw could not start with the installed Node.js version: $($openClawVersion -join ' ')"
    }
    Write-Host "OpenClaw:   $($openClawVersion -join ' ')"

    if (-not (Test-Path -LiteralPath $gatewayConfigPath)) {
        throw "OpenClaw has not been configured for this Windows user. Run 'openclaw onboard', then rerun this launcher."
    }

    try {
        $gatewayConfig = Get-Content -LiteralPath $gatewayConfigPath -Raw | ConvertFrom-Json
        $gatewayProperty = $gatewayConfig.PSObject.Properties['gateway']
        $gatewaySection = if ($gatewayProperty) { $gatewayProperty.Value } else { $null }
        if ($gatewaySection) {
            $portProperty = $gatewaySection.PSObject.Properties['port']
            if ($portProperty -and $portProperty.Value) {
                $gatewayPort = [int]$portProperty.Value
            }
            $httpProperty = $gatewaySection.PSObject.Properties['http']
            $httpSection = if ($httpProperty) { $httpProperty.Value } else { $null }
            $endpointsProperty = if ($httpSection) { $httpSection.PSObject.Properties['endpoints'] } else { $null }
            $endpointsSection = if ($endpointsProperty) { $endpointsProperty.Value } else { $null }
            $chatProperty = if ($endpointsSection) { $endpointsSection.PSObject.Properties['chatCompletions'] } else { $null }
            $chatSection = if ($chatProperty) { $chatProperty.Value } else { $null }
            $enabledProperty = if ($chatSection) { $chatSection.PSObject.Properties['enabled'] } else { $null }
            $chatCompletionsEnabled = $enabledProperty -and $enabledProperty.Value -eq $true
        }
    }
    catch {
        throw "OpenClaw configuration at '$gatewayConfigPath' is not valid JSON. Run 'openclaw configure' to repair it."
    }

    $gatewayWasRunning = Test-TcpPort $gatewayPort

    if (-not $chatCompletionsEnabled) {
        Write-Step 'Enabling the OpenClaw chat-completions endpoint'
        & $openClawPath config set gateway.http.endpoints.chatCompletions.enabled true
        if ($LASTEXITCODE -ne 0) {
            throw "OpenClaw could not enable chat completions (exit code $LASTEXITCODE)."
        }
        if ($gatewayWasRunning) {
            Write-Step 'Restarting the running gateway to apply chat-completions configuration'
            & $openClawPath gateway restart
            if ($LASTEXITCODE -ne 0) {
                throw "Chat completions were enabled, but the running gateway could not be restarted automatically. Close its terminal, rerun this launcher, and it will start with the new setting."
            }
            Wait-ForCondition { Test-OpenClawGateway $openClawPath } "restarted OpenClaw Gateway on port $gatewayPort" 60
        }
    }

    if (Test-TcpPort $gatewayPort) {
        if (-not (Test-OpenClawGateway $openClawPath)) {
            throw "Port $gatewayPort is occupied, but OpenClaw did not pass its health check. Stop the process using that port, then rerun this launcher."
        }
        Write-Host "OpenClaw Gateway is already healthy on port $gatewayPort." -ForegroundColor Green
    }
    else {
        Write-Step "Starting OpenClaw Gateway on port $gatewayPort"
        $openClawLiteral = ConvertTo-QuotedPowerShellLiteral $openClawPath
        $null = Start-ServiceConsole `
            -Title 'NetClaw - OpenClaw Gateway' `
            -WorkingDirectory $repoRoot `
            -CommandText "& $openClawLiteral gateway run" `
            -ShellPath $shellPath
        Wait-ForCondition { Test-OpenClawGateway $openClawPath } "OpenClaw Gateway on port $gatewayPort" 60
    }
}
else {
    Write-Host 'Skipping OpenClaw Gateway (-SkipGateway).' -ForegroundColor Yellow
}

$frontendReady = Test-HttpContent $canvasUrl 'NetClaw Canvas Chat'
$apiReady = Test-HttpContent 'http://localhost:3001/api/gateway/status'
$frontendPortBusy = Test-TcpPort 3000
$apiPortBusy = Test-TcpPort 3001

if ($frontendPortBusy -and -not $frontendReady) {
    throw 'Port 3000 is occupied by another application. Stop that application, then run Start-NetClaw again.'
}
if ($apiPortBusy -and -not $apiReady) {
    throw 'Port 3001 is occupied by another application. Stop that application, then run Start-NetClaw again.'
}

if ($frontendReady -and $apiReady) {
    Write-Host 'NetClaw Visual is already running on ports 3000 and 3001.' -ForegroundColor Green
}
elseif (-not $frontendReady -and -not $apiReady) {
    Write-Step 'Starting the NetClaw Visual API and frontend'
    $npmLiteral = ConvertTo-QuotedPowerShellLiteral $npmPath
    $null = Start-ServiceConsole `
        -Title 'NetClaw - Visual UI' `
        -WorkingDirectory $visualRoot `
        -CommandText "& $npmLiteral run dev" `
        -ShellPath $shellPath
}
elseif ($apiReady) {
    Write-Step 'Starting the NetClaw frontend (the API is already running)'
    $vitePath = Join-Path $visualRoot 'node_modules\.bin\vite.cmd'
    $viteLiteral = ConvertTo-QuotedPowerShellLiteral $vitePath
    $null = Start-ServiceConsole `
        -Title 'NetClaw - Visual Frontend' `
        -WorkingDirectory $visualRoot `
        -CommandText "& $viteLiteral --host" `
        -ShellPath $shellPath
}
else {
    Write-Step 'Starting the NetClaw Visual API (the frontend is already running)'
    $npmLiteral = ConvertTo-QuotedPowerShellLiteral $npmPath
    $null = Start-ServiceConsole `
        -Title 'NetClaw - Visual API' `
        -WorkingDirectory $visualRoot `
        -CommandText "& $npmLiteral run server" `
        -ShellPath $shellPath
}

Wait-ForCondition { Test-HttpContent $canvasUrl 'NetClaw Canvas Chat' } 'NetClaw frontend on port 3000' 60
Wait-ForCondition { Test-HttpContent 'http://localhost:3001/api/gateway/status' } 'NetClaw Visual API on port 3001' 60

if (-not $NoBrowser) {
    Write-Step "Opening the $Interface interface"
    Start-Process $targetUrl
}

Write-Host "`nNetClaw is ready." -ForegroundColor Green
Write-Host "Canvas: $canvasUrl"
Write-Host "HUD:    $hudUrl"
Write-Host 'To stop this development instance, close the NetClaw service windows opened by this launcher.'

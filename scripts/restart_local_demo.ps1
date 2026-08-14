[CmdletBinding()]
param(
    [string]$CeoUsername = "demo.executive",
    [switch]$NoBrowser
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$workspace = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$runtimeDirectory = Join-Path $workspace "tmp\runtime"
$pythonPath = Join-Path $workspace ".venv-phase1\Scripts\python.exe"
$celeryPath = Join-Path $workspace ".venv-phase1\Scripts\celery.exe"
$n8nContainer = "insight-n8n-local"
$proxyContainer = "insight-n8n-webhook-proxy"
$tunnelContainer = "insight-cloudflared-quick"
$disableTelegramAiFeatures = $false

function Write-Step {
    param([string]$Message)
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Assert-LastExitCode {
    param([string]$Operation)
    if ($LASTEXITCODE -ne 0) {
        throw "$Operation failed with exit code $LASTEXITCODE."
    }
}

function Test-DockerReady {
    & docker info *> $null
    return $LASTEXITCODE -eq 0
}

function Start-DockerDesktopIfNeeded {
    if (Test-DockerReady) {
        return
    }

    $dockerDesktop = Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"
    if (-not (Test-Path -LiteralPath $dockerDesktop)) {
        throw "Docker Desktop is not running and could not be found. Start Docker Desktop, then click the launcher again."
    }

    Write-Step "Starting Docker Desktop"
    Start-Process -FilePath $dockerDesktop | Out-Null
    $deadline = (Get-Date).AddMinutes(2)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 3
        if (Test-DockerReady) {
            return
        }
    }
    throw "Docker Desktop did not become ready within two minutes."
}

function Get-ContainerInspect {
    param([string]$Name)
    $json = & docker inspect $Name 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Required container '$Name' does not exist. Complete the initial n8n setup first."
    }
    return ($json | ConvertFrom-Json)[0]
}

function Get-ContainerEnvironment {
    param([object]$Container)
    $values = @{}
    foreach ($entry in @($Container.Config.Env)) {
        $parts = [string]$entry -split "=", 2
        if ($parts.Count -eq 2) {
            $values[$parts[0]] = $parts[1]
        }
    }
    return $values
}

function Get-RequiredEnvironmentValue {
    param(
        [hashtable]$Values,
        [string]$Name
    )
    $value = [string]$Values[$Name]
    if ([string]::IsNullOrWhiteSpace($value)) {
        throw "The n8n container is missing required configuration '$Name'."
    }
    return $value
}

function Get-OrCreateProjectAgentSigningSecret {
    $secretPath = Join-Path $runtimeDirectory "project-agent-n8n-secret.txt"
    if (Test-Path -LiteralPath $secretPath) {
        $existing = (Get-Content -LiteralPath $secretPath -Raw).Trim()
        if ([Text.Encoding]::UTF8.GetByteCount($existing) -lt 32) {
            throw "The retained local project-agent signing secret is invalid."
        }
        return $existing
    }

    $bytes = New-Object byte[] 32
    $generator = [Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $generator.GetBytes($bytes)
    }
    finally {
        $generator.Dispose()
    }
    $secret = [Convert]::ToBase64String($bytes)
    Set-Content -LiteralPath $secretPath -Value $secret -NoNewline
    return $secret
}

function Start-ContainerIfStopped {
    param([string]$Name)
    $state = (& docker inspect --format "{{.State.Status}}" $Name 2>$null).Trim()
    if ($LASTEXITCODE -ne 0) {
        throw "Required container '$Name' does not exist."
    }
    if ($state -ne "running") {
        & docker start $Name | Out-Null
        Assert-LastExitCode "Starting $Name"
    }
}

function Wait-ForContainerHealth {
    param(
        [string]$Name,
        [int]$TimeoutSeconds = 60
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $health = (& docker inspect --format "{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}" $Name 2>$null).Trim()
        if ($health -in @("healthy", "running")) {
            return
        }
        Start-Sleep -Seconds 2
    }
    throw "Container '$Name' did not become healthy."
}

function Get-CurrentTunnelUrl {
    param([string]$PreviousUrl = "")

    $deadline = (Get-Date).AddSeconds(45)
    $pattern = "https://[a-z0-9-]+\.trycloudflare\.com"
    while ((Get-Date) -lt $deadline) {
        $logs = & cmd.exe /d /c "docker logs $tunnelContainer 2>&1"
        $matches = @(
            $logs |
                Select-String -Pattern $pattern |
                ForEach-Object { [regex]::Match($_.Line, $pattern).Value } |
                Where-Object { $_ }
        )
        if ($matches.Count -gt 0) {
            $candidate = $matches[-1].TrimEnd("/")
            if ([string]::IsNullOrWhiteSpace($PreviousUrl) -or $candidate -ne $PreviousUrl) {
                return $candidate
            }
        }
        Start-Sleep -Seconds 2
    }
    throw "The Cloudflare quick tunnel did not publish a URL."
}

function Test-PublicTunnelReachable {
    param([string]$TunnelUrl)

    try {
        # The restricted proxy intentionally returns 404 at its root. Any HTTP
        # response proves that DNS, TLS, Cloudflare, and the proxy are reachable.
        Invoke-WebRequest -Uri "$TunnelUrl/" -Headers @{
            "User-Agent" = "InsightTracker/1.0"
        } -UseBasicParsing -TimeoutSec 15 -ErrorAction Stop | Out-Null
        return $true
    }
    catch {
        if ($null -ne $_.Exception.Response) {
            return $true
        }
    }

    # Some home routers cache a negative DNS answer for newly-created
    # trycloudflare hostnames. Resolve the same hostname through Cloudflare's
    # public resolver and keep TLS/SNI validation intact with curl --resolve.
    $uri = [System.Uri]$TunnelUrl
    foreach ($resolver in @("1.1.1.1", "8.8.8.8", "1.0.0.1")) {
        try {
            $publicAddress = @(
                Resolve-DnsName -Name $uri.Host -Server $resolver -Type A -DnsOnly -QuickTimeout -ErrorAction Stop |
                    Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_.IPAddress) } |
                    Select-Object -ExpandProperty IPAddress -First 1
            ) | Select-Object -First 1
            if ([string]::IsNullOrWhiteSpace([string]$publicAddress)) {
                continue
            }
            & curl.exe --silent --output NUL --max-time 15 --resolve (
                "$($uri.Host):443:$publicAddress"
            ) --user-agent "InsightTracker/1.0" "$($TunnelUrl.TrimEnd('/'))/"
            if ($LASTEXITCODE -eq 0) {
                return $true
            }
        }
        catch {
            # Home networks may block or time out one public resolver. Try the
            # next approved resolver before declaring the tunnel unreachable.
        }
    }
    return $false
}

function Get-ReachableTunnelUrl {
    $currentUrl = Get-CurrentTunnelUrl
    if (Test-PublicTunnelReachable $currentUrl) {
        return $currentUrl
    }

    Write-Step "Recovering the unreachable Telegram webhook tunnel"
    & docker restart $tunnelContainer | Out-Null
    Assert-LastExitCode "Restarting the Cloudflare quick tunnel"

    $replacementUrl = Get-CurrentTunnelUrl -PreviousUrl $currentUrl
    $deadline = (Get-Date).AddSeconds(60)
    while ((Get-Date) -lt $deadline) {
        if (Test-PublicTunnelReachable $replacementUrl) {
            return $replacementUrl
        }
        Start-Sleep -Seconds 5
    }
    throw "The replacement Cloudflare tunnel URL is not publicly reachable."
}

function Assert-N8nWorkflowsActive {
    $workflowIds = @("insightCeoReport01", "insightAgentReview01")
    $activeWorkflows = & docker exec $n8nContainer n8n list:workflow --active=true 2>$null
    Assert-LastExitCode "Checking the active n8n workflows"
    foreach ($workflowId in $workflowIds) {
        if (-not ($activeWorkflows | Where-Object { $_ -match "^$([regex]::Escape($workflowId))\|" })) {
            throw "Required n8n workflow '$workflowId' is not active. Publish it, then run the launcher again."
        }
    }
}

function Sync-N8nWebhookUrl {
    param(
        [string]$TunnelUrl,
        [string]$ProjectAgentSigningSecret
    )

    $container = Get-ContainerInspect $n8nContainer
    $environment = Get-ContainerEnvironment $container
    $desiredEnvironment = @{
        "N8N_WEBHOOK_URL" = "$TunnelUrl/"
        "N8N_EDITOR_BASE_URL" = "$TunnelUrl/"
        "INSIGHT_APP_BASE_URL" = "http://host.docker.internal:8000"
        "INSIGHT_PROJECT_AGENT_N8N_SECRET" = $ProjectAgentSigningSecret
        "NODE_FUNCTION_ALLOW_BUILTIN" = "crypto"
        "N8N_BLOCK_ENV_ACCESS_IN_NODE" = "false"
        "EXECUTIONS_DATA_SAVE_ON_SUCCESS" = "none"
        "EXECUTIONS_DATA_SAVE_ON_ERROR" = "none"
    }
    $requiresRecreation = $false
    foreach ($key in $desiredEnvironment.Keys) {
        if ([string]$environment[$key] -ne [string]$desiredEnvironment[$key]) {
            $environment[$key] = $desiredEnvironment[$key]
            $requiresRecreation = $true
        }
    }
    if (-not $requiresRecreation) {
        Start-ContainerIfStopped $n8nContainer
        return $environment
    }

    Write-Step "Updating n8n for the current temporary tunnel URL"
    $dataMount = @($container.Mounts | Where-Object { $_.Destination -eq "/home/node/.n8n" }) | Select-Object -First 1
    if ($null -eq $dataMount -or [string]::IsNullOrWhiteSpace([string]$dataMount.Name)) {
        throw "Refusing to recreate n8n because its persistent data volume was not found."
    }
    $network = @($container.NetworkSettings.Networks.PSObject.Properties.Name) | Select-Object -First 1
    if ([string]::IsNullOrWhiteSpace([string]$network)) {
        throw "Refusing to recreate n8n because its Docker network was not found."
    }

    & docker stop $n8nContainer | Out-Null
    Assert-LastExitCode "Stopping stale n8n container"
    & docker rm $n8nContainer | Out-Null
    Assert-LastExitCode "Removing stale n8n container"

    $arguments = @(
        "run", "-d",
        "--name", $n8nContainer,
        "--restart", "unless-stopped",
        "--network", [string]$network,
        "-p", "127.0.0.1:5678:5678",
        "-v", "$($dataMount.Name):/home/node/.n8n"
    )
    foreach ($key in @($environment.Keys | Sort-Object)) {
        $arguments += @("--env", "$key=$($environment[$key])")
    }
    $arguments += [string]$container.Config.Image
    & docker @arguments | Out-Null
    Assert-LastExitCode "Recreating n8n with the current tunnel URL"
    return $environment
}

function Get-LocalNetworkDetails {
    $addresses = [System.Collections.Generic.List[string]]::new()
    $primaryAddress = ""
    $primaryGateway = ""
    foreach ($adapter in [System.Net.NetworkInformation.NetworkInterface]::GetAllNetworkInterfaces()) {
        if ($adapter.OperationalStatus -ne [System.Net.NetworkInformation.OperationalStatus]::Up) {
            continue
        }
        $properties = $adapter.GetIPProperties()
        $gateway = @(
            $properties.GatewayAddresses |
                ForEach-Object { $_.Address } |
                Where-Object { $_.AddressFamily -eq [System.Net.Sockets.AddressFamily]::InterNetwork }
        ) | Select-Object -First 1
        foreach ($unicast in $properties.UnicastAddresses) {
            $address = $unicast.Address
            if (
                $address.AddressFamily -ne [System.Net.Sockets.AddressFamily]::InterNetwork -or
                $address.IsIPv6LinkLocal -or
                $address.ToString().StartsWith("127.") -or
                $address.ToString().StartsWith("169.254.")
            ) {
                continue
            }
            $addressText = $address.ToString()
            if (-not $addresses.Contains($addressText)) {
                $addresses.Add($addressText) | Out-Null
            }
            if ([string]::IsNullOrWhiteSpace($primaryAddress) -and $null -ne $gateway) {
                $primaryAddress = $addressText
                $primaryGateway = $gateway.ToString()
            }
        }
    }
    if ($addresses.Count -eq 0) {
        return [PSCustomObject]@{ Addresses = @(); Primary = $null; Gateway = $null }
    }
    if ([string]::IsNullOrWhiteSpace($primaryAddress)) {
        $primaryAddress = $addresses[0]
    }
    return [PSCustomObject]@{
        Addresses = $addresses.ToArray()
        Primary = $primaryAddress
        Gateway = $primaryGateway
    }
}

function Stop-WorkspaceProcessTree {
    param([int]$ProcessId)
    $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if ($null -eq $process) {
        return
    }
    $path = [string]$process.Path
    if ([string]::IsNullOrWhiteSpace($path) -or -not $path.StartsWith($workspace, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to stop process $ProcessId because it is outside the project workspace."
    }
    & taskkill.exe /PID $ProcessId /T /F *> $null
}

function Stop-ExistingLocalProcesses {
    Write-Step "Stopping earlier local Django and Celery processes"

    foreach ($pidFile in @("django.pid", "celery-worker.pid", "celery-beat.pid")) {
        $path = Join-Path $runtimeDirectory $pidFile
        if (Test-Path -LiteralPath $path) {
            $storedPid = 0
            if ([int]::TryParse((Get-Content -LiteralPath $path -Raw).Trim(), [ref]$storedPid)) {
                Stop-WorkspaceProcessTree $storedPid
            }
        }
    }

    foreach ($process in @(Get-Process -Name "celery" -ErrorAction SilentlyContinue)) {
        if ([string]$process.Path -and $process.Path.StartsWith($workspace, [System.StringComparison]::OrdinalIgnoreCase)) {
            Stop-WorkspaceProcessTree $process.Id
        }
    }

    $listeningLines = netstat.exe -ano -p tcp | Select-String -Pattern "LISTENING"
    foreach ($line in $listeningLines) {
        if ($line.Line -match "^\s*TCP\s+\S+:8000\s+\S+\s+LISTENING\s+(\d+)\s*$") {
            Stop-WorkspaceProcessTree ([int]$matches[1])
        }
    }
    Start-Sleep -Seconds 1
}

function Start-ApplicationProcesses {
    param([object]$Network)

    $networkAddresses = @($Network.Addresses | ForEach-Object { [string]$_ })
    $allowedHosts = @("localhost", "127.0.0.1", "[::1]", "host.docker.internal") + $networkAddresses
    $env:ALLOWED_HOSTS = ($allowedHosts | Select-Object -Unique) -join ","
    if ($disableTelegramAiFeatures) {
        $env:EXECUTIVE_BOT_ENABLED = "false"
        $env:EXECUTIVE_ASSISTANT_ENABLED = "false"
    }
    else {
        $env:EXECUTIVE_BOT_ENABLED = "true"
        $env:EXECUTIVE_ASSISTANT_ENABLED = "true"
    }
    Set-Content -LiteralPath (Join-Path $runtimeDirectory "allowed-hosts.txt") -Value $env:ALLOWED_HOSTS

    Write-Step "Applying migrations and checking Django"
    & $pythonPath manage.py migrate --noinput
    Assert-LastExitCode "Django migrations"
    & $pythonPath manage.py check
    Assert-LastExitCode "Django system check"

    Write-Step "Starting Django, Celery worker, and Celery Beat"
    $web = Start-Process -FilePath $pythonPath -ArgumentList @(
        "manage.py", "runserver", "0.0.0.0:8000", "--noreload"
    ) -WorkingDirectory $workspace -WindowStyle Hidden -RedirectStandardOutput (
        Join-Path $runtimeDirectory "django.stdout.log"
    ) -RedirectStandardError (
        Join-Path $runtimeDirectory "django.stderr.log"
    ) -PassThru

    $worker = Start-Process -FilePath $celeryPath -ArgumentList @(
        "-A", "config", "worker", "--pool=solo", "--loglevel=INFO",
        "--hostname=insight-local-worker@%h"
    ) -WorkingDirectory $workspace -WindowStyle Hidden -RedirectStandardOutput (
        Join-Path $runtimeDirectory "celery-worker.stdout.log"
    ) -RedirectStandardError (
        Join-Path $runtimeDirectory "celery-worker.stderr.log"
    ) -PassThru

    $beat = Start-Process -FilePath $celeryPath -ArgumentList @(
        "-A", "config", "beat", "--loglevel=INFO"
    ) -WorkingDirectory $workspace -WindowStyle Hidden -RedirectStandardOutput (
        Join-Path $runtimeDirectory "celery-beat.stdout.log"
    ) -RedirectStandardError (
        Join-Path $runtimeDirectory "celery-beat.stderr.log"
    ) -PassThru

    Set-Content -LiteralPath (Join-Path $runtimeDirectory "django.pid") -Value $web.Id
    Set-Content -LiteralPath (Join-Path $runtimeDirectory "celery-worker.pid") -Value $worker.Id
    Set-Content -LiteralPath (Join-Path $runtimeDirectory "celery-beat.pid") -Value $beat.Id
}

function Wait-ForHttp {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 60
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                return
            }
        }
        catch {
            Start-Sleep -Seconds 2
        }
    }
    throw "Service did not become ready: $Url"
}

function Get-LocalEnvironmentValue {
    param(
        [string]$Name,
        [string]$DefaultValue = ""
    )

    $processValue = [Environment]::GetEnvironmentVariable($Name, "Process")
    if ($null -ne $processValue) {
        return [string]$processValue
    }

    $environmentPath = Join-Path $workspace ".env"
    if (Test-Path -LiteralPath $environmentPath) {
        foreach ($rawLine in Get-Content -LiteralPath $environmentPath) {
            $line = $rawLine.Trim()
            if ([string]::IsNullOrWhiteSpace($line) -or $line.StartsWith("#")) {
                continue
            }
            $parts = $line -split "=", 2
            if ($parts.Count -eq 2 -and $parts[0].Trim() -eq $Name) {
                return $parts[1].Trim().Trim([char[]]@([char]34, [char]39))
            }
        }
    }
    return $DefaultValue
}

function ConvertTo-StrictLocalBoolean {
    param(
        [string]$Name,
        [string]$Value
    )

    switch ($Value.Trim().ToLowerInvariant()) {
        { $_ -in @("1", "true", "yes", "on") } { return $true }
        { $_ -in @("0", "false", "no", "off", "") } { return $false }
        default { throw "$Name must be a boolean value." }
    }
}

function Test-LmStudioConfigurationRequired {
    $fallbackEnabled = ConvertTo-StrictLocalBoolean -Name (
        "LM_STUDIO_FALLBACK_ENABLED"
    ) -Value (Get-LocalEnvironmentValue -Name "LM_STUDIO_FALLBACK_ENABLED" -DefaultValue "false")
    $briefingProvider = Get-LocalEnvironmentValue -Name "AI_BRIEFING_PROVIDER" -DefaultValue "fake"
    $agentProvider = Get-LocalEnvironmentValue -Name "PROJECT_AGENT_PROVIDER" -DefaultValue "fake"
    return (
        $fallbackEnabled -or
        $briefingProvider.Trim().ToLowerInvariant() -eq "lm_studio" -or
        $agentProvider.Trim().ToLowerInvariant() -eq "lm_studio"
    )
}

function Get-LmStudioCliPath {
    $command = Get-Command "lms.exe" -ErrorAction SilentlyContinue
    if ($null -eq $command) {
        $command = Get-Command "lms" -ErrorAction SilentlyContinue
    }
    if ($null -ne $command -and (Test-Path -LiteralPath $command.Source)) {
        return $command.Source
    }

    $candidate = Join-Path $env:USERPROFILE ".lmstudio\bin\lms.exe"
    if (Test-Path -LiteralPath $candidate) {
        return $candidate
    }
    throw "LM Studio CLI was not found. Install LM Studio and enable its lms command first."
}

function Invoke-BoundedLocalProcess {
    param(
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$LogName,
        [string]$Operation,
        [int]$TimeoutSeconds
    )

    $stdoutPath = Join-Path $runtimeDirectory "$LogName.stdout.log"
    $stderrPath = Join-Path $runtimeDirectory "$LogName.stderr.log"
    $process = Start-Process -FilePath $FilePath -ArgumentList $Arguments -WorkingDirectory (
        $workspace
    ) -WindowStyle Hidden -RedirectStandardOutput $stdoutPath -RedirectStandardError (
        $stderrPath
    ) -PassThru
    if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        throw "$Operation did not finish within $TimeoutSeconds seconds."
    }
    if ($process.ExitCode -ne 0) {
        throw "$Operation failed. Check $stderrPath."
    }
}

function Test-LmStudioReadiness {
    param(
        [switch]$ServerOnly,
        [int]$WaitSeconds = 0
    )

    $arguments = @(
        "-m", "scripts.lm_studio_readiness", "--quiet",
        "--wait-seconds", [string]$WaitSeconds
    )
    if ($ServerOnly) {
        $arguments += "--server-only"
    }
    & $pythonPath @arguments *> $null
    return $LASTEXITCODE -eq 0
}

function Assert-LmStudioReadiness {
    param(
        [switch]$ServerOnly,
        [int]$WaitSeconds = 0
    )

    $arguments = @(
        "-m", "scripts.lm_studio_readiness", "--quiet",
        "--wait-seconds", [string]$WaitSeconds
    )
    if ($ServerOnly) {
        $arguments += "--server-only"
    }
    $safeOutput = @(& $pythonPath @arguments 2>&1)
    if ($LASTEXITCODE -ne 0) {
        $message = [string]($safeOutput | Select-Object -Last 1)
        if ([string]::IsNullOrWhiteSpace($message)) {
            $message = "LM Studio readiness verification failed."
        }
        throw $message
    }
}

function Assert-LmStudioLoopbackListener {
    $listeners = @(
        Get-NetTCPConnection -State Listen -LocalPort 1234 -ErrorAction Stop
    )
    if ($listeners.Count -eq 0) {
        throw "LM Studio is not listening on its approved loopback port."
    }
    foreach ($listener in $listeners) {
        if ([string]$listener.LocalAddress -notin @("127.0.0.1", "::1")) {
            throw "LM Studio is exposed beyond loopback. Stop it and restart with bind 127.0.0.1."
        }
    }
}

function Test-LmStudioModelLoaded {
    param(
        [string]$CliPath,
        [string]$ModelId
    )

    $json = @(& $CliPath ps --json 2>$null) -join "`n"
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($json)) {
        return $false
    }
    try {
        $loadedModels = @($json | ConvertFrom-Json -ErrorAction Stop)
    }
    catch {
        return $false
    }
    foreach ($model in $loadedModels) {
        if ([string]$model.identifier -ceq $ModelId) {
            return $true
        }
    }
    return $false
}

function Start-LmStudioWhenRequired {
    Write-Step "Checking local LM Studio readiness"
    $cliPath = Get-LmStudioCliPath
    $modelId = (
        Get-LocalEnvironmentValue -Name "LM_STUDIO_MODEL_ID" -DefaultValue "openai/gpt-oss-20b"
    ).Trim()
    if ($modelId -notmatch "^[A-Za-z0-9][A-Za-z0-9._/:+\-]{0,199}$") {
        throw "The configured LM Studio model identifier is invalid."
    }
    if (Test-LmStudioReadiness) {
        Assert-LmStudioLoopbackListener
        if (Test-LmStudioModelLoaded -CliPath $cliPath -ModelId $modelId) {
            return
        }
    }

    if (-not (Test-LmStudioReadiness -ServerOnly)) {
        Invoke-BoundedLocalProcess -FilePath $cliPath -Arguments @(
            "server", "start", "--port", "1234", "--bind", "127.0.0.1"
        ) -LogName "lm-studio-server" -Operation "Starting the loopback LM Studio server" -TimeoutSeconds 45
        Assert-LmStudioReadiness -ServerOnly -WaitSeconds 45
    }
    Assert-LmStudioLoopbackListener

    if (
        (Test-LmStudioReadiness) -and
        (Test-LmStudioModelLoaded -CliPath $cliPath -ModelId $modelId)
    ) {
        return
    }

    $contextText = Get-LocalEnvironmentValue -Name "LM_STUDIO_CONTEXT_LENGTH" -DefaultValue "16384"
    $contextLength = 0
    if (-not [int]::TryParse($contextText, [ref]$contextLength) -or $contextLength -lt 4096 -or $contextLength -gt 131072) {
        throw "LM_STUDIO_CONTEXT_LENGTH must be between 4096 and 131072."
    }

    Write-Step "Loading the exact configured LM Studio model"
    Invoke-BoundedLocalProcess -FilePath $cliPath -Arguments @(
        "load", $modelId,
        "--identifier", $modelId,
        "--context-length", [string]$contextLength,
        "--parallel", "1",
        "--yes"
    ) -LogName "lm-studio-model-load" -Operation (
        "Loading the exact configured LM Studio model (no download is attempted)"
    ) -TimeoutSeconds 300
    Assert-LmStudioReadiness -WaitSeconds 120
    Assert-LmStudioLoopbackListener
}

function Disable-UnreadyLocalAiForThisLaunch {
    $script:disableTelegramAiFeatures = $false
    $env:LM_STUDIO_FALLBACK_ENABLED = "false"
    if ((Get-LocalEnvironmentValue -Name "AI_BRIEFING_PROVIDER" -DefaultValue "fake").Trim().ToLowerInvariant() -eq "lm_studio") {
        $env:AI_BRIEFING_ENABLED = "false"
        $script:disableTelegramAiFeatures = $true
    }
    if ((Get-LocalEnvironmentValue -Name "PROJECT_AGENT_PROVIDER" -DefaultValue "fake").Trim().ToLowerInvariant() -eq "lm_studio") {
        $env:PROJECT_AGENT_ENABLED = "false"
    }
}

function Configure-FirewallWhenElevated {
    param([object]$Network)
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    $isAdministrator = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdministrator) {
        return $false
    }
    $ruleName = "Insight Tracker Local Phone 8000"
    # A hotspot often makes the phone the default gateway, but on home Wi-Fi
    # the phone is a separate peer. LocalSubnet supports both cases without
    # exposing the development server beyond the current local network.
    $remoteAddress = "LocalSubnet"
    $existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
    if ($null -eq $existing) {
        New-NetFirewallRule -DisplayName $ruleName -Description (
            "Allow devices on the current local subnet to access Insight Tracker on TCP 8000."
        ) -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000 -RemoteAddress (
            $remoteAddress
        ) -Profile Any | Out-Null
    }
    else {
        Set-NetFirewallRule -DisplayName $ruleName -Enabled True -Action Allow -Profile Any | Out-Null
        Set-NetFirewallAddressFilter -AssociatedNetFirewallRule $existing -RemoteAddress $remoteAddress | Out-Null
    }
    return $true
}

try {
    Set-Location -LiteralPath $workspace
    New-Item -ItemType Directory -Path $runtimeDirectory -Force | Out-Null
    $dockerConfigDirectory = Join-Path $runtimeDirectory "docker-config"
    New-Item -ItemType Directory -Path $dockerConfigDirectory -Force | Out-Null
    $env:DOCKER_CONFIG = $dockerConfigDirectory
    if (-not (Test-Path -LiteralPath $pythonPath) -or -not (Test-Path -LiteralPath $celeryPath)) {
        throw "The local Python environment is missing. Run the repository dependency setup first."
    }

    $lmStudioConfigured = Test-LmStudioConfigurationRequired
    $lmStudioReady = $false
    if ($lmStudioConfigured) {
        try {
            Start-LmStudioWhenRequired
            $lmStudioReady = $true
        }
        catch {
            Disable-UnreadyLocalAiForThisLaunch
            Write-Host "`nLocal AI unavailable: $($_.Exception.Message)" -ForegroundColor Yellow
            Write-Host (
                "The website and Groq-primary paths will continue; local-provider and fallback paths are disabled for this launch."
            ) -ForegroundColor Yellow
        }
    }

    Start-DockerDesktopIfNeeded

    Write-Step "Starting PostgreSQL and Redis"
    & docker compose up -d db redis
    Assert-LastExitCode "Docker Compose startup"
    Wait-ForContainerHealth "insight-tracker-db-1"
    Wait-ForContainerHealth "insight-tracker-redis-1"

    Write-Step "Starting n8n webhook proxy and Cloudflare quick tunnel"
    Get-ContainerInspect $proxyContainer | Out-Null
    Get-ContainerInspect $tunnelContainer | Out-Null
    Start-ContainerIfStopped $proxyContainer
    Start-ContainerIfStopped $tunnelContainer
    $tunnelUrl = Get-ReachableTunnelUrl

    $projectAgentSigningSecret = Get-OrCreateProjectAgentSigningSecret
    $n8nEnvironment = Sync-N8nWebhookUrl -TunnelUrl $tunnelUrl -ProjectAgentSigningSecret $projectAgentSigningSecret
    $env:EXECUTIVE_BOT_CEO_USERNAME = $CeoUsername
    $env:EXECUTIVE_BOT_TELEGRAM_CHAT_ID = Get-RequiredEnvironmentValue $n8nEnvironment "INSIGHT_TELEGRAM_CEO_CHAT_ID"
    $env:EXECUTIVE_BOT_SIGNING_SECRET = Get-RequiredEnvironmentValue $n8nEnvironment "INSIGHT_N8N_SIGNING_SECRET"
    $env:PROJECT_AGENT_N8N_ENABLED = "true"
    $env:PROJECT_AGENT_N8N_SIGNING_SECRET = $projectAgentSigningSecret

    $network = Get-LocalNetworkDetails
    Stop-ExistingLocalProcesses
    Start-ApplicationProcesses $network

    Write-Step "Waiting for services"
    Wait-ForHttp "http://127.0.0.1:8000/health/"
    Wait-ForHttp "http://127.0.0.1:5678/healthz"
    Assert-N8nWorkflowsActive
    if (-not (Test-PublicTunnelReachable $tunnelUrl)) {
        throw "The Telegram webhook tunnel became unreachable during startup."
    }

    $firewallConfigured = Configure-FirewallWhenElevated $network
    $trackerUrl = "http://127.0.0.1:8000/"
    $n8nUrl = "http://127.0.0.1:5678/"

    Write-Host "`nInsight Tracker is ready." -ForegroundColor Green
    Write-Host "Tracker: $trackerUrl"
    Write-Host "n8n:     $n8nUrl"
    Write-Host "Tunnel:  $tunnelUrl"
    if ($lmStudioConfigured) {
        if ($lmStudioReady) {
            Write-Host "Local AI: LM Studio ready on loopback" -ForegroundColor Green
        }
        else {
            Write-Host "Local AI: unavailable and disabled for this launch" -ForegroundColor Yellow
        }
    }
    if (-not [string]::IsNullOrWhiteSpace([string]$network.Primary)) {
        $phoneUrl = "http://$($network.Primary):8000/"
        Write-Host "Phone:   $phoneUrl" -ForegroundColor Yellow
        if (-not $firewallConfigured) {
            Write-Host "If the phone link is blocked, right-click the launcher and choose 'Run as administrator' once." -ForegroundColor Yellow
        }
    }
    else {
        Write-Host "No hotspot/LAN IPv4 address was detected. Connect the laptop to the phone hotspot and run again." -ForegroundColor Yellow
    }
    Write-Host "Logs:    $runtimeDirectory"

    if (-not $NoBrowser) {
        Start-Process $trackerUrl | Out-Null
        Start-Process $n8nUrl | Out-Null
    }
}
catch {
    Write-Host "`nStartup failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Check Docker Desktop and the logs in: $runtimeDirectory" -ForegroundColor Red
    exit 1
}

exit 0

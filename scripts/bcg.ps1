# Business Capability Gateway — Service Management Script
# Usage: .\scripts\bcg.ps1 [start|stop|status] [-Host HOST] [-Port PORT]

param(
    [string]$Action = "start",
    [string]$HostAddr = "127.0.0.1",
    [int]$Port = 8765
)

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$HealthUrl  = "http://${HostAddr}:${Port}/health"

function Test-Health {
    try {
        $r = Invoke-WebRequest -Uri $HealthUrl -TimeoutSec 2 -ErrorAction Stop
        return ($r.StatusCode -eq 200)
    } catch {
        return $false
    }
}

switch ($Action) {
    "start" {
        if (Test-Health) {
            Write-Host "Gateway service already running: $HealthUrl"
            return
        }

        Write-Host "Starting gateway service (${HostAddr}:${Port})..."
        Start-Process -FilePath "python" `
            -ArgumentList "main.py", "start", "--host", $HostAddr, "--port", $Port `
            -WorkingDirectory $ProjectRoot `
            -WindowStyle Hidden

        $waited = 0
        $maxWait = 15
        while ($waited -lt $maxWait) {
            Start-Sleep -Seconds 1
            $waited++
            if (Test-Health) {
                Write-Host "Gateway service ready: $HealthUrl  (elapsed ${waited}s)"
                return
            }
        }
        Write-Host "Warning: service did not become ready within ${maxWait}s, please check manually"
    }
    "stop" {
        Write-Host "Stopping gateway service..."
        & python "$ProjectRoot\main.py" stop
    }
    "status" {
        if (Test-Health) {
            Write-Host "Gateway service running: $HealthUrl"
        } else {
            Write-Host "Gateway service not running"
        }
    }
    default {
        Write-Host "Unknown action: $Action. Available: start, stop, status"
    }
}

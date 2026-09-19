[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$SidecarPath,
  [int]$TimeoutSeconds = 60
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Fail([string]$Message) {
  throw "ILAIOS_DESKTOP_SIDECAR_SMOKE_BLOCKED: $Message"
}

function New-BearerToken {
  $bytes = New-Object byte[] 32
  $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
  try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
  return ([Convert]::ToBase64String($bytes)).TrimEnd('=').Replace('+','-').Replace('/','_')
}

function Read-BoundedLog([string]$Path) {
  if (-not (Test-Path $Path -PathType Leaf)) { return '<no log>' }
  $lines = @(Get-Content -Path $Path -ErrorAction SilentlyContinue)
  if ($lines.Count -gt 80) { $lines = @($lines | Select-Object -Last 80) }
  if ($lines.Count -eq 0) { return '<empty log>' }
  return ($lines -join "`n")
}

function Invoke-SidecarCycle {
  param(
    [Parameter(Mandatory = $true)][string]$Label,
    [Parameter(Mandatory = $true)][string]$DataRoot,
    [Parameter(Mandatory = $true)][string]$WorkRoot
  )

  $readyFile = Join-Path $WorkRoot "$Label-ready.json"
  $stdoutFile = Join-Path $WorkRoot "$Label-stdout.log"
  $stderrFile = Join-Path $WorkRoot "$Label-stderr.log"
  Remove-Item $readyFile,$stdoutFile,$stderrFile -Force -ErrorAction SilentlyContinue

  $token = New-BearerToken
  $previousToken = $env:ILAIOS_CONTROL_PLANE_TOKEN
  $env:ILAIOS_CONTROL_PLANE_TOKEN = $token
  $process = $null
  try {
    $process = Start-Process -FilePath $SidecarPath `
      -ArgumentList @('--data-root', $DataRoot, '--ready-file', $readyFile) `
      -RedirectStandardOutput $stdoutFile `
      -RedirectStandardError $stderrFile `
      -WindowStyle Hidden `
      -PassThru

    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    $ready = $null
    $lastProbeError = $null
    while ([DateTime]::UtcNow -lt $deadline) {
      $process.Refresh()
      if ($process.HasExited) {
        $stderr = Read-BoundedLog $stderrFile
        $stdout = Read-BoundedLog $stdoutFile
        Fail "$Label exited before identity readiness. ExitCode=$($process.ExitCode)`nSTDERR:`n$stderr`nSTDOUT:`n$stdout"
      }

      if (Test-Path $readyFile -PathType Leaf) {
        try {
          $candidate = Get-Content -Path $readyFile -Raw | ConvertFrom-Json
          if ($null -ne $candidate.identity_port -and [int]$candidate.identity_port -gt 0) {
            $identityPort = [int]$candidate.identity_port
            $uri = "http://127.0.0.1:$identityPort/v1/auth/providers"
            try {
              $response = Invoke-WebRequest -UseBasicParsing -Uri $uri -Headers @{
                Authorization = "Bearer $token"
              } -TimeoutSec 2
              if ([int]$response.StatusCode -eq 200) {
                $ready = $candidate
                break
              }
              $lastProbeError = "HTTP $($response.StatusCode)"
            }
            catch {
              $lastProbeError = $_.Exception.Message
            }
          }
        }
        catch {
          $lastProbeError = $_.Exception.Message
        }
      }
      Start-Sleep -Milliseconds 250
    }

    if ($null -eq $ready) {
      $stderr = Read-BoundedLog $stderrFile
      $stdout = Read-BoundedLog $stdoutFile
      Fail "$Label did not become identity-ready within ${TimeoutSeconds}s. LastProbe=$lastProbeError`nSTDERR:`n$stderr`nSTDOUT:`n$stdout"
    }

    $identityPort = [int]$ready.identity_port
    $shutdown = Invoke-WebRequest -UseBasicParsing `
      -Method Post `
      -Uri "http://127.0.0.1:$identityPort/v1/runtime/shutdown" `
      -Headers @{ Authorization = "Bearer $token" } `
      -ContentType 'application/json' `
      -Body '{}' `
      -TimeoutSec 3
    if ([int]$shutdown.StatusCode -ne 202) {
      Fail "$Label shutdown returned HTTP $($shutdown.StatusCode), expected 202"
    }

    $exitDeadline = [DateTime]::UtcNow.AddSeconds(8)
    while (-not $process.HasExited -and [DateTime]::UtcNow -lt $exitDeadline) {
      Start-Sleep -Milliseconds 200
      $process.Refresh()
    }
    if (-not $process.HasExited) {
      Fail "$Label accepted shutdown but did not exit within 8 seconds"
    }
    if ($process.ExitCode -ne 0) {
      $stderr = Read-BoundedLog $stderrFile
      Fail "$Label exited non-zero after graceful shutdown. ExitCode=$($process.ExitCode)`nSTDERR:`n$stderr"
    }

    Write-Host "ILAIOS_DESKTOP_SIDECAR_${Label}_IDENTITY_READY=PASS"
    Write-Host "ILAIOS_DESKTOP_SIDECAR_${Label}_GRACEFUL_SHUTDOWN=PASS"
  }
  finally {
    if ($null -ne $process) {
      try {
        $process.Refresh()
        if (-not $process.HasExited) { Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue }
      }
      catch { }
    }
    if ($null -eq $previousToken) {
      Remove-Item Env:ILAIOS_CONTROL_PLANE_TOKEN -ErrorAction SilentlyContinue
    }
    else {
      $env:ILAIOS_CONTROL_PLANE_TOKEN = $previousToken
    }
  }
}

if (-not (Test-Path $SidecarPath -PathType Leaf)) {
  Fail "Sidecar executable missing: $SidecarPath"
}
if ($TimeoutSeconds -lt 10 -or $TimeoutSeconds -gt 180) {
  Fail 'TimeoutSeconds must be between 10 and 180'
}

$workRoot = Join-Path ([IO.Path]::GetTempPath()) ("ilaios-sidecar-smoke-" + [Guid]::NewGuid().ToString('N'))
$dataRoot = Join-Path $workRoot 'durable-data'
New-Item -ItemType Directory -Force -Path $dataRoot | Out-Null
try {
  Invoke-SidecarCycle -Label 'COLD_START' -DataRoot $dataRoot -WorkRoot $workRoot
  Invoke-SidecarCycle -Label 'RESTART' -DataRoot $dataRoot -WorkRoot $workRoot
  Write-Host 'ILAIOS_DESKTOP_SIDECAR_PACKAGED_RUNTIME_SMOKE=PASS'
}
finally {
  Remove-Item $workRoot -Recurse -Force -ErrorAction SilentlyContinue
}

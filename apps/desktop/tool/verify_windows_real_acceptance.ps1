# Current-master Desktop real-acceptance checkpoint.
[CmdletBinding()]
param(
  [int]$StartupTimeoutSeconds = 90
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Fail([string]$Message) {
  throw "ILAIOS_DESKTOP_REAL_ACCEPTANCE_BLOCKED: $Message"
}

$desktopRoot = Split-Path -Parent $PSScriptRoot
$repoRoot = (Resolve-Path (Join-Path $desktopRoot '..\..')).Path
$release = Join-Path $desktopRoot 'build\windows\x64\runner\Release'
$desktopExe = Join-Path $release 'ilaios_desktop.exe'
$sidecarExe = Join-Path $release 'ilaios_control_plane.exe'
$fullBuild = Join-Path $PSScriptRoot 'build_and_run_windows_full.ps1'
$sidecarSmoke = Join-Path $PSScriptRoot 'smoke_control_plane_sidecar.ps1'
$evidenceRoot = Join-Path $repoRoot 'artifacts\desktop-real-acceptance'
$sourceHead = (git -C $repoRoot rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $sourceHead -notmatch '^[0-9a-f]{40}$') {
  Fail 'Exact source HEAD is unavailable.'
}

& $fullBuild -NoLaunch
if ($LASTEXITCODE -ne 0) { Fail 'Canonical full Windows build failed.' }
if (-not (Test-Path $desktopExe -PathType Leaf)) { Fail "Desktop executable missing: $desktopExe" }
if (-not (Test-Path $sidecarExe -PathType Leaf)) { Fail "Bundled sidecar missing: $sidecarExe" }

& $sidecarSmoke -SidecarPath $sidecarExe -TimeoutSeconds ([Math]::Min([Math]::Max($StartupTimeoutSeconds, 10), 180))
if ($LASTEXITCODE -ne 0) { Fail 'Packaged sidecar smoke failed.' }

New-Item -ItemType Directory -Force -Path $evidenceRoot | Out-Null
$startedAt = [DateTime]::UtcNow
$desktop = Start-Process -FilePath $desktopExe -PassThru
$deadline = [DateTime]::UtcNow.AddSeconds($StartupTimeoutSeconds)
$sidecar = $null
while ([DateTime]::UtcNow -lt $deadline) {
  $desktop.Refresh()
  if ($desktop.HasExited) {
    Fail "Desktop exited before runtime acceptance. ExitCode=$($desktop.ExitCode)"
  }
  $sidecar = Get-Process -Name 'ilaios_control_plane' -ErrorAction SilentlyContinue |
    Where-Object { $_.StartTime.ToUniversalTime() -ge $startedAt.AddSeconds(-2) } |
    Sort-Object StartTime -Descending |
    Select-Object -First 1
  if ($null -ne $sidecar) { break }
  Start-Sleep -Milliseconds 250
}
if ($null -eq $sidecar) {
  Fail 'Desktop stayed open but no bundled control-plane sidecar became observable.'
}

$evidence = [ordered]@{
  source_head = $sourceHead
  generated_at_utc = [DateTime]::UtcNow.ToString('o')
  canonical_full_build = 'PASS'
  bundled_sidecar_smoke = 'PASS'
  desktop_process_started = 'PASS'
  bundled_sidecar_observed = 'PASS'
  google_login_real_user = 'PENDING_HUMAN_EVIDENCE'
  system_online_visible = 'PENDING_HUMAN_EVIDENCE'
  canonical_agents_visible = 'PENDING_HUMAN_EVIDENCE'
  pixel_agents_visible_and_stateful = 'PENDING_HUMAN_EVIDENCE'
  real_factory_action_end_to_end = 'PENDING_HUMAN_EVIDENCE'
  restart_session_runtime = 'PENDING_HUMAN_EVIDENCE'
  screenshot_or_video_evidence = 'PENDING_HUMAN_EVIDENCE'
  overall_desktop_ready = 'BLOCKED'
}
$evidencePath = Join-Path $evidenceRoot ("acceptance-$sourceHead.json")
$evidence | ConvertTo-Json -Depth 4 | Set-Content -Path $evidencePath -Encoding utf8

Write-Host "ILAIOS_DESKTOP_ACCEPTANCE_SOURCE_HEAD=$sourceHead"
Write-Host "ILAIOS_DESKTOP_ACCEPTANCE_EVIDENCE=$evidencePath"
Write-Host 'ILAIOS_DESKTOP_CANONICAL_FULL_BUILD=PASS'
Write-Host 'ILAIOS_DESKTOP_BUNDLED_SIDECAR=PASS'
Write-Host 'ILAIOS_DESKTOP_REAL_USER_ACCEPTANCE=PENDING'
Write-Host 'ILAIOS_DESKTOP_READY=BLOCKED'
Write-Host 'Complete real Google login, online-state, canonical-agent, pixel-state, real factory action, restart/session, and screenshot/video evidence in this exact build before declaring Desktop ready.'

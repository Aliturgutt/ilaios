param(
  [switch]$NoLaunch
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$desktopRoot = Split-Path -Parent $PSScriptRoot
$release = Join-Path $desktopRoot 'build\windows\x64\runner\Release'
$desktopExe = Join-Path $release 'ilaios_desktop.exe'
$sidecarExe = Join-Path $release 'ilaios_control_plane.exe'
$sidecarBuilder = Join-Path $PSScriptRoot 'build_control_plane_sidecar.ps1'

Push-Location $desktopRoot
try {
  flutter pub get
  if ($LASTEXITCODE -ne 0) { throw 'flutter pub get failed.' }

  flutter build windows --release
  if ($LASTEXITCODE -ne 0) { throw 'Flutter Windows release build failed.' }

  & $sidecarBuilder -OutputDirectory $release
  if ($LASTEXITCODE -ne 0) { throw 'ILAIOS control-plane sidecar build failed.' }

  if (-not (Test-Path $desktopExe -PathType Leaf)) {
    throw "Desktop executable missing: $desktopExe"
  }
  if (-not (Test-Path $sidecarExe -PathType Leaf)) {
    throw "Control-plane sidecar missing: $sidecarExe"
  }

  Write-Host "ILAIOS_DESKTOP_EXE=$desktopExe"
  Write-Host "ILAIOS_CONTROL_PLANE_EXE=$sidecarExe"
  Write-Host 'ILAIOS_DESKTOP_FULL_LOCAL_BUILD=PASS'

  if (-not $NoLaunch) {
    Start-Process $desktopExe
  }
}
finally {
  Pop-Location
}

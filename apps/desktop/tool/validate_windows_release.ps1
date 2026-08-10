$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$DesktopRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $DesktopRoot

Write-Host '=== ILAIOS DESKTOP WINDOWS VALIDATION ==='
Write-Host "Root: $DesktopRoot"

flutter --version
flutter pub get
flutter analyze
flutter test
flutter build windows --release

$Exe = Join-Path $DesktopRoot 'build\windows\x64\runner\Release\ilaios_desktop.exe'
if (-not (Test-Path $Exe)) {
  throw "Release executable not found: $Exe"
}

$Item = Get-Item $Exe
if ($Item.Length -le 0) {
  throw 'Release executable is empty.'
}

$Version = $Item.VersionInfo
if ($Version.ProductName -ne 'ILAIOS Desktop') {
  throw "Unexpected ProductName: $($Version.ProductName)"
}

Write-Host "EXE=$Exe"
Write-Host "SIZE=$($Item.Length)"
Write-Host "PRODUCT=$($Version.ProductName)"
Write-Host "VERSION=$($Version.ProductVersion)"
Write-Host 'ILAIOS_DESKTOP_WINDOWS_VALIDATION=PASS'

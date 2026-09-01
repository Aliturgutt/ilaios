param(
  [Parameter(Mandatory = $true)]
  [string]$IdentityName,

  [Parameter(Mandatory = $true)]
  [string]$Publisher,

  [string]$Version = '0.1.0.1',
  [string]$OutputPath = ''
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$desktopRoot = Split-Path -Parent $PSScriptRoot
$buildScript = Join-Path $PSScriptRoot 'build_msix.ps1'

if (-not (Test-Path $buildScript)) {
  throw "MSIX build script not found: $buildScript"
}

if ([string]::IsNullOrWhiteSpace($IdentityName)) {
  throw 'IdentityName is required and must come from Partner Center.'
}
if ($IdentityName -eq 'ILAIOS.Desktop.CI') {
  throw 'The CI placeholder IdentityName cannot be used for a Store release candidate.'
}
if ($IdentityName -notmatch '^[A-Za-z0-9.-]+$') {
  throw 'IdentityName contains unsupported characters.'
}

if ([string]::IsNullOrWhiteSpace($Publisher)) {
  throw 'Publisher is required and must exactly match Partner Center Product identity.'
}
if ($Publisher -match 'ILAIOS-CI-UNSIGNED') {
  throw 'The CI placeholder Publisher cannot be used for a Store release candidate.'
}

if ($Version -notmatch '^\d+\.\d+\.\d+\.\d+$') {
  throw 'Version must be four numeric components.'
}

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
  $OutputPath = Join-Path $desktopRoot "build\msix\ILAIOS-Desktop-$Version-x64-store.msix"
}

$buildArgs = @{
  IdentityName = $IdentityName
  Publisher = $Publisher
  Version = $Version
  OutputPath = $OutputPath
}
& $buildScript @buildArgs
if ($LASTEXITCODE -ne 0) {
  throw "Store MSIX packaging failed with exit code $LASTEXITCODE"
}

if (-not (Test-Path $OutputPath)) {
  throw 'Store MSIX output was not created.'
}

$makeAppx = Get-ChildItem 'C:\Program Files (x86)\Windows Kits\10\bin\*\x64\makeappx.exe' -ErrorAction SilentlyContinue |
  Sort-Object FullName -Descending |
  Select-Object -First 1
if ($null -eq $makeAppx) {
  throw 'MakeAppx.exe was not found in the Windows SDK.'
}

$unpack = Join-Path $desktopRoot 'build\msix\store-validation'
Remove-Item $unpack -Recurse -Force -ErrorAction SilentlyContinue
& $makeAppx.FullName unpack /p $OutputPath /d $unpack /o
if ($LASTEXITCODE -ne 0) {
  throw 'Store MSIX unpack validation failed.'
}

$manifestPath = Join-Path $unpack 'AppxManifest.xml'
if (-not (Test-Path $manifestPath)) {
  throw 'Packaged AppxManifest.xml is missing.'
}

[xml]$manifest = Get-Content $manifestPath -Raw
$identity = $manifest.Package.Identity
if ($null -eq $identity) {
  throw 'Package Identity element is missing.'
}
if ([string]$identity.Name -ne $IdentityName) {
  throw "Packaged Identity Name mismatch. Expected '$IdentityName', got '$($identity.Name)'."
}
if ([string]$identity.Publisher -ne $Publisher) {
  throw "Packaged Publisher mismatch. Expected '$Publisher', got '$($identity.Publisher)'."
}
if ([string]$identity.Version -ne $Version) {
  throw "Packaged Version mismatch. Expected '$Version', got '$($identity.Version)'."
}

$hash = (Get-FileHash $OutputPath -Algorithm SHA256).Hash.ToLowerInvariant()
$evidencePath = Join-Path (Split-Path -Parent $OutputPath) 'store-release-evidence.json'
$evidence = [ordered]@{
  product = 'ILAIOS Desktop'
  package_path = (Resolve-Path $OutputPath).Path
  package_sha256 = $hash
  identity_name = $IdentityName
  publisher = $Publisher
  version = $Version
  signed_before_submission = $false
  signing_authority = 'Microsoft Store after certification'
  created_at_utc = [DateTime]::UtcNow.ToString('o')
}
$evidence | ConvertTo-Json -Depth 4 | Set-Content -Path $evidencePath -Encoding utf8

Write-Host "ILAIOS_DESKTOP_STORE_MSIX_PATH=$OutputPath"
Write-Host "ILAIOS_DESKTOP_STORE_MSIX_SHA256=$hash"
Write-Host "ILAIOS_DESKTOP_STORE_EVIDENCE=$evidencePath"
Write-Host 'ILAIOS_DESKTOP_STORE_SIGNED_BEFORE_SUBMISSION=false'
Write-Host 'ILAIOS_DESKTOP_STORE_SIGNING=MICROSOFT_STORE_AFTER_CERTIFICATION'
Write-Host 'ILAIOS_DESKTOP_STORE_PACKAGE_VALIDATION=PASS'

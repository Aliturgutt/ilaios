# Agent closure exact-master co-certification trigger; no package behavior change.
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$SourceSha,
  [Parameter(Mandatory = $true)][string]$RunId
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Fail([string]$Message) {
  throw "ILAIOS_DESKTOP_COMBINED_CI_BLOCKED: $Message"
}

function Run-Native([string]$Label, [scriptblock]$Command) {
  Write-Host "=== $Label ==="
  & $Command
  if ($LASTEXITCODE -ne 0) {
    Fail "$Label failed with exit $LASTEXITCODE"
  }
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$desktopRoot = Join-Path $repoRoot 'apps\desktop'
$patcher = Join-Path $PSScriptRoot 'apply_combined_typography_reference_patch.py'

if (-not (Test-Path $patcher -PathType Leaf)) { Fail "Patch helper missing: $patcher" }

Run-Native 'Apply fail-closed combined patch' { python $patcher $repoRoot }

Push-Location $desktopRoot
try {
  Run-Native 'Resolve locked dependencies' { flutter pub get --enforce-lockfile }
  Run-Native 'Format patched Dart' {
    dart format `
      lib/features/dashboard/reference_desktop_shell_v10.dart `
      lib/features/deliveries/deliveries_view.dart `
      lib/app/desktop_app.dart `
      lib/features/create/create_view.dart `
      lib/features/create/reference_asset_picker_core.dart `
      lib/identity/identity_client.dart `
      lib/reference_assets/reference_factory_target.dart `
      lib/reference_assets/reference_asset_ui_scope.dart `
      test/desktop_combined_typography_reference_ux_test.dart
  }
}
finally {
  Pop-Location
}

Run-Native 'Git diff whitespace check' { git -C $repoRoot diff --check }

$expected = @(
  'apps/desktop/lib/features/dashboard/reference_desktop_shell_v10.dart',
  'apps/desktop/lib/features/deliveries/deliveries_view.dart',
  'apps/desktop/lib/app/desktop_app.dart',
  'apps/desktop/lib/features/create/create_view.dart',
  'apps/desktop/lib/features/create/reference_asset_picker_core.dart',
  'apps/desktop/lib/identity/identity_client.dart',
  'apps/desktop/lib/reference_assets/reference_factory_target.dart',
  'apps/desktop/lib/reference_assets/reference_asset_ui_scope.dart',
  'apps/desktop/test/desktop_combined_typography_reference_ux_test.dart'
)
$changed = @(git -C $repoRoot diff --name-only)
$unexpected = @($changed | Where-Object { $_ -notin $expected })
if ($unexpected.Count -gt 0) {
  Fail "Unexpected patched files: $($unexpected -join ', ')"
}
foreach ($path in $expected) {
  if ($path -notin $changed) { Fail "Expected patched file missing: $path" }
}

# The formatter can re-indent unchanged layout. Compare ignoring whitespace so
# only semantic geometry changes are rejected.
$v10Semantic = @(git -C $repoRoot diff -w --ignore-blank-lines -- apps/desktop/lib/features/dashboard/reference_desktop_shell_v10.dart)
$forbidden = @($v10Semantic | Where-Object {
  $_ -match '^[+-](?![+-]).*(\bwidth\s*:|\bheight\s*:|EdgeInsets|SizedBox\(|\bpadding\s*:|\bmargin\s*:)'
})
if ($forbidden.Count -gt 0) {
  Fail "Protected shell geometry changed semantically:`n$($forbidden -join "`n")"
}

$patchEvidence = Join-Path $repoRoot 'desktop-combined-ci.patch'
git -C $repoRoot diff --binary | Out-File -Encoding utf8 $patchEvidence

Push-Location $desktopRoot
try {
  Run-Native 'Flutter analyze' { flutter analyze }
  Run-Native 'Required 1366x768 / 1440x900 / 1920x1080 viewport tests' {
    flutter test test/desktop_combined_typography_reference_ux_test.dart
  }
  Run-Native 'Full Desktop tests' { flutter test }
  Run-Native 'Windows release build' { flutter build windows --release }
  Run-Native 'Bundled control-plane sidecar build' { .\tool\build_control_plane_sidecar.ps1 }
}
finally {
  Pop-Location
}

$release = Join-Path $desktopRoot 'build\windows\x64\runner\Release'
$exe = Join-Path $release 'ilaios_desktop.exe'
$sidecar = Join-Path $release 'ilaios_control_plane.exe'
if (-not (Test-Path $exe -PathType Leaf)) { Fail "Release executable missing: $exe" }
if (-not (Test-Path $sidecar -PathType Leaf)) { Fail "Sidecar missing: $sidecar" }
if ((Get-Item $exe).Length -le 0) { Fail 'Release executable is empty' }
if ((Get-Item $sidecar).Length -le 0) { Fail 'Sidecar is empty' }
$version = (Get-Item $exe).VersionInfo
if ($version.ProductName -ne 'ILAIOS Desktop') { Fail "Unexpected ProductName: $($version.ProductName)" }
if ($version.CompanyName -ne 'ILAIOS') { Fail "Unexpected CompanyName: $($version.CompanyName)" }
Write-Host 'ILAIOS_DESKTOP_COMBINED_WINDOWS_BUILD=PASS'

$artifactParent = Join-Path $repoRoot 'artifacts'
$artifactRoot = Join-Path $artifactParent 'desktop-combined-final'
$runtime = Join-Path $artifactRoot 'runtime'
Remove-Item $artifactRoot -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $runtime | Out-Null
Copy-Item (Join-Path $release '*') $runtime -Recurse -Force

$installer = @'
[CmdletBinding()]
param([switch]$NoLaunch)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Fail([string]$Message) {
  throw "ILAIOS_DESKTOP_CI_INSTALL_BLOCKED: $Message"
}

function New-Shortcut {
  param([string]$ShortcutPath,[string]$TargetPath,[string]$WorkingDirectory)
  $shell = New-Object -ComObject WScript.Shell
  $shortcut = $shell.CreateShortcut($ShortcutPath)
  $shortcut.TargetPath = $TargetPath
  $shortcut.WorkingDirectory = $WorkingDirectory
  $shortcut.Description = 'ILAIOS Desktop'
  $shortcut.IconLocation = "$TargetPath,0"
  $shortcut.Save()
}

$runtime = Join-Path $PSScriptRoot 'runtime'
$sourceExe = Join-Path $runtime 'ilaios_desktop.exe'
$sourceSidecar = Join-Path $runtime 'ilaios_control_plane.exe'
if (-not (Test-Path $sourceExe -PathType Leaf)) { Fail "Runtime EXE missing: $sourceExe" }
if (-not (Test-Path $sourceSidecar -PathType Leaf)) { Fail "Runtime sidecar missing: $sourceSidecar" }

$installParent = Join-Path $env:LOCALAPPDATA 'Programs'
$installRoot = Join-Path $installParent 'ILAIOS Desktop'
$stage = Join-Path $installParent 'ILAIOS Desktop.__ci_verified_new'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$backup = Join-Path $env:LOCALAPPDATA "ILAIOS\InstallBackups\desktop-ci-verified\$stamp\ILAIOS Desktop"

Get-Process 'ilaios_desktop' -ErrorAction SilentlyContinue |
  Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 700
Remove-Item $stage -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $stage | Out-Null
Copy-Item (Join-Path $runtime '*') $stage -Recurse -Force

if (Test-Path $installRoot) {
  New-Item -ItemType Directory -Force -Path (Split-Path $backup -Parent) | Out-Null
  Move-Item $installRoot $backup
}
try {
  Move-Item $stage $installRoot
}
catch {
  if ((Test-Path $backup) -and -not (Test-Path $installRoot)) {
    Move-Item $backup $installRoot
  }
  throw
}

$installedExe = Join-Path $installRoot 'ilaios_desktop.exe'
$desktopShortcut = Join-Path ([Environment]::GetFolderPath('Desktop')) 'ILAIOS Desktop.lnk'
$startMenuDir = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\ILAIOS'
New-Item -ItemType Directory -Force -Path $startMenuDir | Out-Null
New-Shortcut -ShortcutPath $desktopShortcut -TargetPath $installedExe -WorkingDirectory $installRoot
New-Shortcut -ShortcutPath (Join-Path $startMenuDir 'ILAIOS Desktop.lnk') -TargetPath $installedExe -WorkingDirectory $installRoot

if (-not $NoLaunch) {
  try {
    $proc = Start-Process -FilePath $installedExe -WorkingDirectory $installRoot -PassThru
    Start-Sleep -Seconds 8
    $proc.Refresh()
    if ($proc.HasExited) {
      Fail "Installed Desktop exited during 8-second smoke. ExitCode=$($proc.ExitCode)"
    }
    Write-Host 'RUNTIME_SMOKE=PROCESS_ALIVE_AFTER_8S'
  }
  catch {
    Get-Process 'ilaios_desktop' -ErrorAction SilentlyContinue |
      Stop-Process -Force -ErrorAction SilentlyContinue
    Remove-Item $installRoot -Recurse -Force -ErrorAction SilentlyContinue
    if (Test-Path $backup) { Move-Item $backup $installRoot }
    throw
  }
}

Write-Host "INSTALL_ROOT=$installRoot"
Write-Host 'ILAIOS_DESKTOP_CI_VERIFIED_LOCAL_INSTALL=PASS'
'@
Set-Content -Path (Join-Path $artifactRoot 'INSTALL_ILAIOS_DESKTOP.ps1') -Value $installer -Encoding UTF8

$manifest = [ordered]@{
  status = 'CI_VERIFIED_WINDOWS_BUILD'
  source_sha = $SourceSha
  run_id = $RunId
  flutter = '3.44.9 / 6b182d2c7585eba26d4edce0f97630effd256c33'
  viewport_tests = @('1366x768','1440x900','1920x1080')
  static_analysis = 'PASS'
  full_flutter_tests = 'PASS'
  windows_release_build = 'PASS'
  sidecar_build = 'PASS'
  local_runtime_smoke = 'PENDING_USER_MACHINE'
}
$manifest | ConvertTo-Json -Depth 5 |
  Set-Content -Encoding UTF8 (Join-Path $artifactRoot 'CI_EVIDENCE.json')
Copy-Item $patchEvidence (Join-Path $artifactRoot 'desktop-combined-ci.patch')

$hashes = Get-ChildItem $runtime -File -Recurse | Sort-Object FullName | ForEach-Object {
  $relative = $_.FullName.Substring($runtime.Length + 1)
  $hash = (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
  "$hash  runtime/$($relative -replace '\\','/')"
}
$hashes | Set-Content -Encoding ascii (Join-Path $artifactRoot 'SHA256SUMS.txt')

$short = $SourceSha.Substring(0,8)
$zip = Join-Path $artifactParent "ILAIOS_DESKTOP_COMBINED_CI_VERIFIED_$short.zip"
Remove-Item $zip -Force -ErrorAction SilentlyContinue
Compress-Archive -Path (Join-Path $artifactRoot '*') -DestinationPath $zip -CompressionLevel Optimal
$zipHash = (Get-FileHash $zip -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -Encoding ascii -Path "$zip.sha256" -Value "$zipHash  $(Split-Path $zip -Leaf)"

Write-Host "FINAL_ZIP=$zip"
Write-Host "FINAL_ZIP_SHA256=$zipHash"
Write-Host 'ILAIOS_DESKTOP_COMBINED_CI_PACKAGE=PASS'

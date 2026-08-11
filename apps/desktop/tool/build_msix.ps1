param(
  [string]$IdentityName = 'ILAIOS.Desktop.CI',
  [string]$Publisher = 'CN=ILAIOS-CI-UNSIGNED',
  [string]$Version = '0.1.0.1',
  [string]$OutputPath = ''
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$desktopRoot = Split-Path -Parent $PSScriptRoot
$repoRoot = Resolve-Path (Join-Path $desktopRoot '..\..')
$releaseDir = Join-Path $desktopRoot 'build\windows\x64\runner\Release'
$templatePath = Join-Path $desktopRoot 'packaging\msix\AppxManifest.template.xml'
$brandMaster = Join-Path $repoRoot 'brand\assets\05-ilaios-app-icon.jpg'
$staging = Join-Path $desktopRoot 'build\msix\staging'
$assetsDir = Join-Path $staging 'Assets'
if ([string]::IsNullOrWhiteSpace($OutputPath)) {
  $OutputPath = Join-Path $desktopRoot "build\msix\ILAIOS-Desktop-$Version-x64-unsigned.msix"
}

if ($IdentityName -notmatch '^[A-Za-z0-9.-]+$') { throw 'IdentityName contains unsupported characters.' }
if ($Version -notmatch '^\d+\.\d+\.\d+\.\d+$') { throw 'Version must be four numeric components.' }
if (-not (Test-Path $releaseDir)) { throw "Windows release output not found: $releaseDir" }
if (-not (Test-Path (Join-Path $releaseDir 'ilaios_desktop.exe'))) { throw 'ILAIOS Desktop executable is missing.' }
if (-not (Test-Path $templatePath)) { throw "Manifest template not found: $templatePath" }
if (-not (Test-Path $brandMaster)) { throw "Canonical app icon master not found: $brandMaster" }

Remove-Item $staging -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $staging, $assetsDir | Out-Null
Copy-Item (Join-Path $releaseDir '*') $staging -Recurse -Force

Add-Type -AssemblyName System.Drawing
$source = [System.Drawing.Image]::FromFile($brandMaster)
try {
  function Write-ContainedPng([int]$Width, [int]$Height, [string]$Path) {
    $bitmap = New-Object System.Drawing.Bitmap($Width, $Height)
    try {
      $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
      try {
        $graphics.Clear([System.Drawing.Color]::Transparent)
        $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $graphics.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
        $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
        $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality

        $scale = [Math]::Min($Width / [double]$source.Width, $Height / [double]$source.Height)
        $drawWidth = [Math]::Max(1, [int][Math]::Round($source.Width * $scale))
        $drawHeight = [Math]::Max(1, [int][Math]::Round($source.Height * $scale))
        $x = [int][Math]::Floor(($Width - $drawWidth) / 2.0)
        $y = [int][Math]::Floor(($Height - $drawHeight) / 2.0)
        $graphics.DrawImage($source, $x, $y, $drawWidth, $drawHeight)
      } finally {
        $graphics.Dispose()
      }
      $bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
    } finally {
      $bitmap.Dispose()
    }
  }

  Write-ContainedPng 44 44 (Join-Path $assetsDir 'Square44x44Logo.png')
  Write-ContainedPng 150 150 (Join-Path $assetsDir 'Square150x150Logo.png')
  Write-ContainedPng 50 50 (Join-Path $assetsDir 'StoreLogo.png')
  Write-ContainedPng 310 150 (Join-Path $assetsDir 'Wide310x150Logo.png')
} finally {
  $source.Dispose()
}

$template = Get-Content $templatePath -Raw
$manifest = $template.Replace('__IDENTITY_NAME__', [System.Security.SecurityElement]::Escape($IdentityName))
$manifest = $manifest.Replace('__PUBLISHER__', [System.Security.SecurityElement]::Escape($Publisher))
$manifest = $manifest.Replace('__VERSION__', $Version)
[System.IO.File]::WriteAllText((Join-Path $staging 'AppxManifest.xml'), $manifest, (New-Object System.Text.UTF8Encoding($false)))

$makeAppx = Get-ChildItem 'C:\Program Files (x86)\Windows Kits\10\bin\*\x64\makeappx.exe' -ErrorAction SilentlyContinue |
  Sort-Object FullName -Descending |
  Select-Object -First 1
if ($null -eq $makeAppx) { throw 'MakeAppx.exe was not found in the Windows SDK.' }

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $OutputPath) | Out-Null
Remove-Item $OutputPath -Force -ErrorAction SilentlyContinue
& $makeAppx.FullName pack /d $staging /p $OutputPath /o
if ($LASTEXITCODE -ne 0) { throw "MakeAppx failed with exit code $LASTEXITCODE" }
if (-not (Test-Path $OutputPath)) { throw 'MSIX output was not created.' }

$package = Get-Item $OutputPath
if ($package.Length -le 0) { throw 'MSIX output is empty.' }
$hash = (Get-FileHash $OutputPath -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Host "ILAIOS_DESKTOP_MSIX_PATH=$OutputPath"
Write-Host "ILAIOS_DESKTOP_MSIX_SHA256=$hash"
Write-Host 'ILAIOS_DESKTOP_MSIX_SIGNED=false'
Write-Host 'ILAIOS_DESKTOP_MSIX_PACKAGING=PASS'

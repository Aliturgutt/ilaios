[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$SourceSha,
  [Parameter(Mandatory = $true)][string]$RunId
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Fail([string]$Message) {
  throw "ILAIOS_DESKTOP_V4_EVIDENCE_BLOCKED: $Message"
}

function Read-PngDimensions([string]$Path) {
  $bytes = [System.IO.File]::ReadAllBytes($Path)
  if ($bytes.Length -lt 24) { Fail "PNG too small: $Path" }
  $signature = @(137,80,78,71,13,10,26,10)
  for ($i = 0; $i -lt 8; $i++) {
    if ($bytes[$i] -ne $signature[$i]) { Fail "Invalid PNG signature: $Path" }
  }
  $width = ($bytes[16] -shl 24) -bor ($bytes[17] -shl 16) -bor ($bytes[18] -shl 8) -bor $bytes[19]
  $height = ($bytes[20] -shl 24) -bor ($bytes[21] -shl 16) -bor ($bytes[22] -shl 8) -bor $bytes[23]
  return @($width, $height)
}

if ($SourceSha -notmatch '^[0-9a-f]{40}$') { Fail "Invalid source SHA: $SourceSha" }

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$desktopRoot = Join-Path $repoRoot 'apps\desktop'
$sourceRoot = Join-Path $desktopRoot 'build\windows\x64\runner\Release\visual-evidence'
$artifactParent = Join-Path $repoRoot 'artifacts'
$artifactRoot = Join-Path $artifactParent 'desktop-v4-visual-evidence'

if (-not (Test-Path $sourceRoot -PathType Container)) {
  Fail "Visual evidence root missing: $sourceRoot"
}
Remove-Item $artifactRoot -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $artifactRoot | Out-Null

$combinations = @(
  @{ name = 'dark-1366x768'; theme = 'dark'; width = 1366; height = 768 },
  @{ name = 'dark-1440x900'; theme = 'dark'; width = 1440; height = 900 },
  @{ name = 'dark-1920x1080'; theme = 'dark'; width = 1920; height = 1080 },
  @{ name = 'light-1366x768'; theme = 'light'; width = 1366; height = 768 },
  @{ name = 'light-1440x900'; theme = 'light'; width = 1440; height = 900 },
  @{ name = 'light-1920x1080'; theme = 'light'; width = 1920; height = 1080 }
)

$entries = @()
foreach ($combo in $combinations) {
  $sourceDir = Join-Path $sourceRoot $combo.name
  if (-not (Test-Path $sourceDir -PathType Container)) { Fail "Combination missing: $($combo.name)" }
  $manifestPath = Join-Path $sourceDir 'manifest.json'
  if (-not (Test-Path $manifestPath -PathType Leaf)) { Fail "Manifest missing: $($combo.name)" }
  $manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json
  if ($manifest.schema -ne 'ilaios.desktop.v4.screenshot-evidence.v1') { Fail "Unexpected manifest schema: $($combo.name)" }
  if ($manifest.source_sha -ne $SourceSha) { Fail "Manifest SHA mismatch for $($combo.name): $($manifest.source_sha)" }
  if ([int]$manifest.screenshot_count -ne 10) { Fail "Screenshot count mismatch in manifest: $($combo.name)" }
  if ($manifest.theme -ne $combo.theme) { Fail "Theme mismatch: $($combo.name)" }
  if ([int]$manifest.viewport.width -ne $combo.width -or [int]$manifest.viewport.height -ne $combo.height) {
    Fail "Viewport mismatch in manifest: $($combo.name)"
  }

  $pngFiles = @(Get-ChildItem $sourceDir -File -Filter '*.png' | Sort-Object Name)
  if ($pngFiles.Count -ne 10) { Fail "Expected 10 PNGs for $($combo.name), found $($pngFiles.Count)" }

  $destDir = Join-Path $artifactRoot $combo.name
  New-Item -ItemType Directory -Force -Path $destDir | Out-Null
  Copy-Item $manifestPath (Join-Path $destDir 'manifest.json') -Force

  foreach ($png in $pngFiles) {
    $dimensions = Read-PngDimensions $png.FullName
    if ($dimensions[0] -ne $combo.width -or $dimensions[1] -ne $combo.height) {
      Fail "PNG dimensions mismatch for $($png.Name): $($dimensions[0])x$($dimensions[1])"
    }
    $hash = (Get-FileHash $png.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    $dest = Join-Path $destDir $png.Name
    Copy-Item $png.FullName $dest -Force
    $entries += [ordered]@{
      file = "$($combo.name)/$($png.Name)"
      sha256 = $hash
      bytes = (Get-Item $png.FullName).Length
      width = [int]$dimensions[0]
      height = [int]$dimensions[1]
      theme = $combo.theme
      source_sha = $SourceSha
    }
  }
}

if ($entries.Count -ne 60) { Fail "Expected exactly 60 PNG evidence entries, found $($entries.Count)" }

$rootManifest = [ordered]@{
  schema = 'ilaios.desktop.v4.visual-evidence.v1'
  source_sha = $SourceSha
  run_id = $RunId
  screenshot_count = $entries.Count
  combinations = @($combinations | ForEach-Object { $_.name })
  screenshots = $entries
}
$rootManifest | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 (Join-Path $artifactRoot 'evidence-manifest.json')

$entries | ForEach-Object { "$($_.sha256)  $($_.file)" } | Set-Content -Encoding ascii (Join-Path $artifactRoot 'SHA256SUMS.txt')
Set-Content -Encoding ascii -Path (Join-Path $artifactRoot 'SOURCE_SHA.txt') -Value $SourceSha

Write-Host "ILAIOS_DESKTOP_V4_SCREENSHOT_COUNT=$($entries.Count)"
Write-Host "ILAIOS_DESKTOP_V4_SOURCE_SHA=$SourceSha"
Write-Host 'ILAIOS_DESKTOP_V4_SCREENSHOT_EVIDENCE=PASS'

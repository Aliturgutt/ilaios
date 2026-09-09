[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$SourceSha,
  [Parameter(Mandatory = $true)][string]$RunId
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Fail([string]$Message) {
  throw "ILAIOS_DESKTOP_7_PAGE_EVIDENCE_BLOCKED: $Message"
}

function Read-PngDimensions([string]$Path) {
  $bytes = [System.IO.File]::ReadAllBytes($Path)
  if ($bytes.Length -lt 24) { Fail "PNG too small: $Path" }
  $signature = @(137,80,78,71,13,10,26,10)
  for ($i = 0; $i -lt 8; $i++) {
    if ($bytes[$i] -ne $signature[$i]) { Fail "Invalid PNG signature: $Path" }
  }
  $width = ([uint32]$bytes[16] -shl 24) -bor ([uint32]$bytes[17] -shl 16) -bor ([uint32]$bytes[18] -shl 8) -bor [uint32]$bytes[19]
  $height = ([uint32]$bytes[20] -shl 24) -bor ([uint32]$bytes[21] -shl 16) -bor ([uint32]$bytes[22] -shl 8) -bor [uint32]$bytes[23]
  return @($width, $height)
}

if ($SourceSha -notmatch '^[0-9a-f]{40}$') { Fail "Invalid source SHA: $SourceSha" }

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$desktopRoot = Join-Path $repoRoot 'apps\desktop'
$sourceDir = Join-Path $desktopRoot 'build\windows\x64\runner\Release\visual-evidence\canonical-light-1536x1024'
$referenceRoot = Join-Path $repoRoot 'docs\platform\desktop\Desktop_7_Page_References'
$artifactRoot = Join-Path $repoRoot 'artifacts\desktop-7-page-visual-evidence'

if (-not (Test-Path $sourceDir -PathType Container)) { Fail "Visual evidence root missing: $sourceDir" }
if (-not (Test-Path $referenceRoot -PathType Container)) { Fail "Canonical reference root missing: $referenceRoot" }

$expectedHashes = [ordered]@{
  '01_Ana_Sayfa.png' = '700b60c8199719cffc854adc21188a5c3b84d2ff707f74ea170acad138020d93'
  '02_Is_Akislari.png' = '94cc35b8329d2f4eec701434c35df935a08dfc1088612604d3803391aad6c3d7'
  '03_Ajanlar.png' = '32e7e90b91a07bbe250ce02898099af23b7267b82d7e347584e6b0668d5d20b2'
  '04_Ciktilar.png' = '22646276dbb0dd3ff0cd328a02f3a64708922b6d90b8bbe4cd60e2572ca649a1'
  '05_Onaylar.png' = '342c8c91e2b326c6560ae03625860ac2c3e68703e97b786b3119f9edda33c07d'
  '06_Kanitlar.png' = '3e5ba7c9ced5452b17212ae6e2a80e974c09bfc348a54f4548e0c8aa73c7bdc8'
  '07_Ayarlar.png' = 'db1996bc13b1423175289f0e01c5f43cf88c5693d8b76ee45d9be967fa536bde'
}

$manifestPath = Join-Path $sourceDir 'manifest.json'
if (-not (Test-Path $manifestPath -PathType Leaf)) { Fail 'Rendered manifest missing' }
$manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json
if ($manifest.schema -ne 'ilaios.desktop.7page.screenshot-evidence.v1') { Fail "Unexpected manifest schema: $($manifest.schema)" }
if ($manifest.source_sha -ne $SourceSha) { Fail "Manifest SHA mismatch: $($manifest.source_sha)" }
if ([int]$manifest.screenshot_count -ne 7) { Fail "Screenshot count mismatch: $($manifest.screenshot_count)" }
if ($manifest.theme -ne 'light') { Fail "Unexpected theme: $($manifest.theme)" }
if ([int]$manifest.viewport.width -ne 1536 -or [int]$manifest.viewport.height -ne 1024) { Fail 'Canonical viewport mismatch' }

$renderedPngs = @(Get-ChildItem $sourceDir -File -Filter '*.png' | Sort-Object Name)
if ($renderedPngs.Count -ne 7) { Fail "Expected 7 rendered PNGs, found $($renderedPngs.Count)" }

Remove-Item $artifactRoot -Recurse -Force -ErrorAction SilentlyContinue
$renderDir = Join-Path $artifactRoot 'renders'
$referenceDir = Join-Path $artifactRoot 'references'
New-Item -ItemType Directory -Force -Path $renderDir | Out-Null
New-Item -ItemType Directory -Force -Path $referenceDir | Out-Null
Copy-Item $manifestPath (Join-Path $artifactRoot 'render-manifest.json') -Force

$entries = @()
foreach ($fileName in $expectedHashes.Keys) {
  $referencePath = Join-Path $referenceRoot $fileName
  if (-not (Test-Path $referencePath -PathType Leaf)) { Fail "Canonical reference missing: $fileName" }
  $referenceHash = (Get-FileHash $referencePath -Algorithm SHA256).Hash.ToLowerInvariant()
  if ($referenceHash -ne $expectedHashes[$fileName]) { Fail "Canonical reference hash mismatch: $fileName" }
  $referenceDimensions = Read-PngDimensions $referencePath
  if ($referenceDimensions[0] -ne 1536 -or $referenceDimensions[1] -ne 1024) { Fail "Canonical reference dimensions mismatch: $fileName" }

  $renderPath = Join-Path $sourceDir $fileName
  if (-not (Test-Path $renderPath -PathType Leaf)) { Fail "Rendered page missing: $fileName" }
  $renderDimensions = Read-PngDimensions $renderPath
  if ($renderDimensions[0] -ne 1536 -or $renderDimensions[1] -ne 1024) { Fail "Rendered dimensions mismatch: $fileName" }
  $renderHash = (Get-FileHash $renderPath -Algorithm SHA256).Hash.ToLowerInvariant()

  Copy-Item $referencePath (Join-Path $referenceDir $fileName) -Force
  Copy-Item $renderPath (Join-Path $renderDir $fileName) -Force
  $entries += [ordered]@{
    file = $fileName
    reference_sha256 = $referenceHash
    render_sha256 = $renderHash
    width = 1536
    height = 1024
    source_sha = $SourceSha
  }
}

if ($entries.Count -ne 7) { Fail "Expected exactly 7 evidence entries, found $($entries.Count)" }

$rootManifest = [ordered]@{
  schema = 'ilaios.desktop.7page.visual-evidence.v1'
  source_sha = $SourceSha
  run_id = $RunId
  screenshot_count = $entries.Count
  canonical_reference = 'Desktop_7_Page_References_FIXED(1).zip'
  screenshots = $entries
}
$rootManifest | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 (Join-Path $artifactRoot 'evidence-manifest.json')
Set-Content -Encoding ascii -Path (Join-Path $artifactRoot 'SOURCE_SHA.txt') -Value $SourceSha

Write-Host "ILAIOS_DESKTOP_7_PAGE_SCREENSHOT_COUNT=$($entries.Count)"
Write-Host "ILAIOS_DESKTOP_7_PAGE_SOURCE_SHA=$SourceSha"
Write-Host 'ILAIOS_DESKTOP_7_PAGE_SCREENSHOT_EVIDENCE=PASS'

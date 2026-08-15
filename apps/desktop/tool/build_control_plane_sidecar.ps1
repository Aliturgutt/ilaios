param(
  [string]$OutputDirectory = ''
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$desktopRoot = Split-Path -Parent $PSScriptRoot
$repoRoot = Resolve-Path (Join-Path $desktopRoot '..\..')
$entrypoint = Join-Path $desktopRoot 'sidecar\ilaios_control_plane_sidecar.py'
$brandLogo = Join-Path $repoRoot 'brand\assets\03-ilaios-symbol-dark.jpg'
if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
  $OutputDirectory = Join-Path $desktopRoot 'build\windows\x64\runner\Release'
}

if (-not (Test-Path $entrypoint)) { throw "Sidecar entrypoint missing: $entrypoint" }
if (-not (Test-Path $brandLogo)) { throw "Official ILAIOS brand logo missing: $brandLogo" }
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null

python -m pip install --disable-pip-version-check `
  'pyinstaller==6.21.0' `
  'requests==2.34.2' `
  'python-dotenv==1.2.2' `
  'PyJWT[crypto]==2.13.0' `
  'cryptography==49.0.0'
if ($LASTEXITCODE -ne 0) { throw 'Desktop sidecar build dependencies failed to install.' }

$work = Join-Path $desktopRoot 'build\sidecar\work'
$spec = Join-Path $desktopRoot 'build\sidecar\spec'
$dist = Join-Path $desktopRoot 'build\sidecar\dist'
$metadata = Join-Path $desktopRoot 'build\sidecar\metadata'
Remove-Item (Join-Path $desktopRoot 'build\sidecar') -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $work, $spec, $dist, $metadata | Out-Null

$sourceHead = (& git -C $repoRoot rev-parse HEAD).Trim().ToLowerInvariant()
if ($LASTEXITCODE -ne 0 -or $sourceHead -notmatch '^[0-9a-f]{40}$') {
  throw 'Unable to bind Desktop sidecar to an exact source HEAD SHA.'
}
$sourceHeadFile = Join-Path $metadata 'source-head.txt'
[System.IO.File]::WriteAllText($sourceHeadFile, $sourceHead, [System.Text.UTF8Encoding]::new($false))

$env:PYTHONPATH = $repoRoot
Push-Location $repoRoot
try {
  python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --console `
    --name ilaios_control_plane `
    --paths $repoRoot `
    --hidden-import jwt `
    --hidden-import jwt.algorithms `
    --add-data "$brandLogo;brand/assets" `
    --add-data "$sourceHeadFile;build-metadata" `
    --workpath $work `
    --specpath $spec `
    --distpath $dist `
    $entrypoint
  if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed to build the ILAIOS control-plane sidecar.' }
}
finally {
  Pop-Location
}

$built = Join-Path $dist 'ilaios_control_plane.exe'
if (-not (Test-Path $built)) { throw "Sidecar executable missing: $built" }
$target = Join-Path $OutputDirectory 'ilaios_control_plane.exe'
Copy-Item $built $target -Force
if ((Get-Item $target).Length -le 0) { throw 'Bundled control-plane executable is empty.' }
$hash = (Get-FileHash $target -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Host "ILAIOS_DESKTOP_SIDECAR_PATH=$target"
Write-Host "ILAIOS_DESKTOP_SIDECAR_SHA256=$hash"
Write-Host "ILAIOS_DESKTOP_SOURCE_HEAD=$sourceHead"
Write-Host 'ILAIOS_DESKTOP_SIDECAR_BUILD=PASS'

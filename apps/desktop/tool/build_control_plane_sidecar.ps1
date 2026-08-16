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

# The Windows sidecar source and CI contract target Python 3.12. Building with
# an older local interpreter can fail while importing first-party modules (for
# example, pre-PEP-701 f-string parsing) even though the exact source is valid
# under the canonical Windows CI interpreter. Fail before dependency install or
# packaging so local and CI builds cannot silently use different runtimes.
$pythonVersion = (& python -c "import sys; print('%d.%d' % sys.version_info[:2])").Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($pythonVersion)) {
  throw 'Unable to resolve the Python interpreter for Desktop sidecar build.'
}
if ($pythonVersion -ne '3.12') {
  throw "Desktop sidecar build requires Python 3.12; resolved Python $pythonVersion."
}
Write-Host "ILAIOS_DESKTOP_PYTHON=$pythonVersion"

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
  # Fail before packaging if a required first-party runtime or identity module
  # is absent or not importable in the active Windows build environment.
  python -c "import services.desktop_oidc_microsoft; import services.desktop_oidc_windows; import services.integrations.web_factory"
  if ($LASTEXITCODE -ne 0) {
    throw 'Desktop sidecar source import smoke failed for required identity/integration modules.'
  }

  # PyInstaller can miss package children on some local Python environments
  # even when imports are statically reachable through package __init__ files.
  # Collect the bounded first-party integrations package explicitly so local
  # Windows builds and CI produce the same runnable composition root. The OIDC
  # Windows/Microsoft modules are statically imported by the sidecar entrypoint
  # and the pre-package smoke above prevents an omitted source dependency.
  python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --console `
    --name ilaios_control_plane `
    --paths $repoRoot `
    --hidden-import jwt `
    --hidden-import jwt.algorithms `
    --collect-submodules services.integrations `
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
if ((Get-Item $built).Length -le 0) { throw 'Bundled control-plane executable is empty.' }

# A successful PyInstaller exit is not sufficient evidence that the frozen
# composition root is runnable. --help imports the complete module graph before
# argparse exits, so this catches missing first-party modules without starting a
# runtime or using secrets.
& $built --help *> $null
if ($LASTEXITCODE -ne 0) {
  throw 'Packaged Desktop sidecar import smoke failed.'
}
Write-Host 'ILAIOS_DESKTOP_SIDECAR_IMPORT_SMOKE=PASS'

$target = Join-Path $OutputDirectory 'ilaios_control_plane.exe'
Copy-Item $built $target -Force
if ((Get-Item $target).Length -le 0) { throw 'Bundled control-plane executable is empty.' }
$hash = (Get-FileHash $target -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Host "ILAIOS_DESKTOP_SIDECAR_PATH=$target"
Write-Host "ILAIOS_DESKTOP_SIDECAR_SHA256=$hash"
Write-Host "ILAIOS_DESKTOP_SOURCE_HEAD=$sourceHead"
Write-Host 'ILAIOS_DESKTOP_SIDECAR_BUILD=PASS'

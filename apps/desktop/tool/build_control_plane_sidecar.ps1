# Final Agent closure exact-master recertification trigger; no package behavior change.
# Agent closure exact-master co-certification trigger; no package behavior change.
param(
  [string]$OutputDirectory = ''
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$desktopRoot = Split-Path -Parent $PSScriptRoot
$repoRoot = Resolve-Path (Join-Path $desktopRoot '..\..')
$entrypoint = Join-Path $desktopRoot 'sidecar\ilaios_control_plane_sidecar.py'
$brandLogo = Join-Path $repoRoot 'brand\assets\03-ilaios-symbol-dark.jpg'
$identityProviders = Join-Path $desktopRoot 'packaging\identity\oidc-providers.public.json'
$softwareFactorySkills = Join-Path $repoRoot 'tools\software-factory\skills'
$securityFactorySkills = Join-Path $repoRoot 'tools\security-factory\skills'
$skillEngineeringSkills = Join-Path $repoRoot 'tools\skill-engineering\skills'
$webFactorySkills = Join-Path $repoRoot 'tools\web-factory\skills'
$webBrowserSkills = Join-Path $repoRoot 'tools\web-factory\browser-skills'
if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
  $OutputDirectory = Join-Path $desktopRoot 'build\windows\x64\runner\Release'
}

if (-not (Test-Path $entrypoint)) { throw "Sidecar entrypoint missing: $entrypoint" }
if (-not (Test-Path $brandLogo)) { throw "Official ILAIOS brand logo missing: $brandLogo" }
if (-not (Test-Path $identityProviders)) { throw "Desktop public identity metadata missing: $identityProviders" }
if (-not (Test-Path $softwareFactorySkills -PathType Container)) {
  throw "Canonical Software Factory skills missing: $softwareFactorySkills"
}
if (-not (Test-Path $securityFactorySkills -PathType Container)) {
  throw "Canonical Security Factory skills missing: $securityFactorySkills"
}
if (-not (Test-Path $skillEngineeringSkills -PathType Container)) {
  throw "Canonical Skill Engineering skills missing: $skillEngineeringSkills"
}
if (-not (Test-Path $webFactorySkills -PathType Container)) {
  throw "Canonical Web Factory skills missing: $webFactorySkills"
}
if (-not (Test-Path $webBrowserSkills -PathType Container)) {
  throw "Canonical BrowserQA skills missing: $webBrowserSkills"
}
if (-not (Test-Path (Join-Path $skillEngineeringSkills 'skill-create\SKILL.md') -PathType Leaf)) {
  throw 'Canonical Skill Engineering runtime package skill-create is missing.'
}
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null

$identityDocument = Get-Content -Raw $identityProviders | ConvertFrom-Json
if ($null -eq $identityDocument) { throw 'Desktop public identity metadata is invalid.' }
foreach ($provider in @($identityDocument)) {
  if ($null -ne $provider.PSObject.Properties['client_secret']) {
    throw 'Desktop public identity metadata must not contain client_secret.'
  }
  if ([string]::IsNullOrWhiteSpace([string]$provider.client_id)) {
    throw 'Desktop public identity metadata contains an empty client_id.'
  }
}

$skillFiles = @(Get-ChildItem -Path $softwareFactorySkills -Recurse -Filter 'SKILL.md' -File)
if ($skillFiles.Count -lt 25) {
  throw "Canonical Software Factory skill registry is incomplete: found $($skillFiles.Count)."
}
$securitySkillFiles = @(Get-ChildItem -Path $securityFactorySkills -Recurse -Filter 'SKILL.md' -File)
if ($securitySkillFiles.Count -ne 5) {
  throw "Canonical Security Factory methodology registry is incomplete: found $($securitySkillFiles.Count)."
}
$webSkillFiles = @(Get-ChildItem -Path $webFactorySkills -Recurse -Filter 'SKILL.md' -File)
if ($webSkillFiles.Count -ne 12) {
  throw "Canonical Web Factory skill registry is incomplete: found $($webSkillFiles.Count)."
}
$browserSkillFiles = @(Get-ChildItem -Path $webBrowserSkills -Recurse -Filter 'SKILL.md' -File)
if ($browserSkillFiles.Count -ne 5) {
  throw "Canonical BrowserQA skill registry is incomplete: found $($browserSkillFiles.Count)."
}

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
  python -c "import services.desktop_oidc_microsoft; import services.desktop_oidc_windows; import services.integrations.web_factory; import services.p0_runtime_composition; import services.web_agent_execution; import services.web_agent_runtime; import services.web_agent_skill_catalog; import services.browser_runtime_composition; import services.runtime.ai_provider_adapter; import services.runtime.security_agent_adapters; import services.security_methodology_analysis; import services.security_methodology_skills; import services.skill_engineering_catalog; import services.skill_engineering_runtime"
  if ($LASTEXITCODE -ne 0) {
    throw 'Desktop sidecar source import smoke failed for required identity/integration/agent modules.'
  }

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
    --add-data "$identityProviders;desktop-identity" `
    --add-data "$sourceHeadFile;build-metadata" `
    --add-data "$softwareFactorySkills;tools/software-factory/skills" `
    --add-data "$securityFactorySkills;tools/security-factory/skills" `
    --add-data "$skillEngineeringSkills;tools/skill-engineering/skills" `
    --add-data "$webFactorySkills;tools/web-factory/skills" `
    --add-data "$webBrowserSkills;tools/web-factory/browser-skills" `
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

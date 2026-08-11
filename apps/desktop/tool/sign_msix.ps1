param(
  [Parameter(Mandatory = $true)][string]$MsixPath,
  [Parameter(Mandatory = $true)][string]$PfxPath,
  [Parameter(Mandatory = $true)][string]$PfxPassword,
  [Parameter(Mandatory = $true)][string]$ExpectedPublisher
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if (-not (Test-Path $MsixPath)) { throw "MSIX file not found: $MsixPath" }
if (-not (Test-Path $PfxPath)) { throw "Signing certificate not found: $PfxPath" }
if ([string]::IsNullOrWhiteSpace($PfxPassword)) { throw 'Signing certificate password is required.' }
if ([string]::IsNullOrWhiteSpace($ExpectedPublisher)) { throw 'Expected publisher identity is required.' }

$cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2
try {
  $cert.Import(
    $PfxPath,
    $PfxPassword,
    [System.Security.Cryptography.X509Certificates.X509KeyStorageFlags]::EphemeralKeySet
  )
  if (-not $cert.HasPrivateKey) { throw 'Signing certificate does not contain a private key.' }
  if ($cert.Subject -ne $ExpectedPublisher) {
    throw "Signing certificate subject does not match package Publisher. Expected '$ExpectedPublisher', got '$($cert.Subject)'."
  }

  $now = [DateTime]::UtcNow
  if ($now -lt $cert.NotBefore.ToUniversalTime()) {
    throw "Signing certificate is not valid before $($cert.NotBefore.ToUniversalTime().ToString('o'))."
  }
  if ($now -gt $cert.NotAfter.ToUniversalTime()) {
    throw "Signing certificate expired at $($cert.NotAfter.ToUniversalTime().ToString('o'))."
  }

  $codeSigningOid = '1.3.6.1.5.5.7.3.3'
  $ekuExtension = $cert.Extensions | Where-Object {
    $_ -is [System.Security.Cryptography.X509Certificates.X509EnhancedKeyUsageExtension]
  } | Select-Object -First 1
  if ($null -ne $ekuExtension) {
    $hasCodeSigning = $false
    foreach ($oid in $ekuExtension.EnhancedKeyUsages) {
      if ($oid.Value -eq $codeSigningOid) { $hasCodeSigning = $true; break }
    }
    if (-not $hasCodeSigning) { throw 'Signing certificate does not permit code signing.' }
  }
} finally {
  $cert.Dispose()
}

$signTool = Get-ChildItem 'C:\Program Files (x86)\Windows Kits\10\bin\*\x64\signtool.exe' -ErrorAction SilentlyContinue |
  Sort-Object FullName -Descending |
  Select-Object -First 1
if ($null -eq $signTool) { throw 'SignTool.exe was not found in the Windows SDK.' }

& $signTool.FullName sign /fd SHA256 /f $PfxPath /p $PfxPassword $MsixPath
if ($LASTEXITCODE -ne 0) { throw "SignTool sign failed with exit code $LASTEXITCODE" }

& $signTool.FullName verify /pa /v $MsixPath
if ($LASTEXITCODE -ne 0) { throw "SignTool verification failed with exit code $LASTEXITCODE" }

$hash = (Get-FileHash $MsixPath -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Host "ILAIOS_DESKTOP_SIGNED_MSIX_SHA256=$hash"
Write-Host 'ILAIOS_DESKTOP_MSIX_SIGNED=true'
Write-Host 'ILAIOS_DESKTOP_MSIX_SIGNATURE_VALIDATION=PASS'

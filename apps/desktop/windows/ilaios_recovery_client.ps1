param(
  [Parameter(Mandatory = $true)][string]$BaseUrl,
  [Parameter(Mandatory = $true)][string]$Token,
  [Parameter(Mandatory = $true)][ValidateSet("Prepare", "Execute")][string]$Mode,
  [Parameter(Mandatory = $true)][string]$RequestId,
  [string]$Objective = "Create and deliver a governed video from Windows Desktop",
  [string]$GrantId = ""
)

$ErrorActionPreference = "Stop"
$headers = @{ Authorization = "Bearer $Token" }
if ($Mode -eq "Prepare") {
  $payload = @{
    operation = "prepare_windows_video"
    request_id = $RequestId
    objective = $Objective
    now = [DateTimeOffset]::UtcNow.ToString("o")
  }
} else {
  if ([string]::IsNullOrWhiteSpace($GrantId)) {
    throw "GrantId is required for Execute"
  }
  $payload = @{
    operation = "execute_windows_video"
    request_id = $RequestId
    grant_id = $GrantId
    now = [DateTimeOffset]::UtcNow.ToString("o")
  }
}

$response = Invoke-RestMethod `
  -Uri "$BaseUrl/v1/product-proof/commands" `
  -Method Post `
  -Headers $headers `
  -ContentType "application/json" `
  -Body ($payload | ConvertTo-Json -Compress)

@{
  windows_runtime = @{
    os_version = [System.Environment]::OSVersion.VersionString
    process_path = [System.Diagnostics.Process]::GetCurrentProcess().Path
    powershell_version = $PSVersionTable.PSVersion.ToString()
  }
  response = $response
} | ConvertTo-Json -Depth 12 -Compress

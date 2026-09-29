param(
    [string]$BaseUrl = "http://127.0.0.1:8000"
)

$healthUrl = "$($BaseUrl.TrimEnd('/'))/api/health"

Write-Host "Testing Financial Model API:"
Write-Host "  $healthUrl"

try {
    $response = Invoke-RestMethod -Uri $healthUrl -Method Get -TimeoutSec 10 -ErrorAction Stop
}
catch {
    Write-Error "Could not reach the Financial Model API at $healthUrl"
    Write-Error $_.Exception.Message
    exit 1
}

if ($null -eq $response -or $response.status -ne "ok") {
    Write-Error "API responded, but /api/health did not return status=ok."
    if ($null -ne $response) {
        $response | ConvertTo-Json
    }
    exit 1
}

Write-Host "API health check passed: status=ok"
exit 0

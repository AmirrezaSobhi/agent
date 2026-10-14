$ErrorActionPreference = 'Stop'
# Uses Windows certificate chain and hostname verification. No credentials,
# trust-store modification, certificate callback or redirect is permitted.
$request = [Net.HttpWebRequest]::Create('https://gitlab.local/api/v4/version')
$request.AllowAutoRedirect = $false
$request.Timeout = 5000
try {
    try { $response = $request.GetResponse() }
    catch [Net.WebException] {
        if (-not $_.Exception.Response) { throw }
        $response = $_.Exception.Response
    }
    if ([int]$response.StatusCode -notin @(200,401)) { throw 'Unexpected GitLab API response.' }
    [ordered]@{schema_version=1;status='PASS';chain_and_hostname_verified=$true;api_status=[int]$response.StatusCode;token_sent=$false} | ConvertTo-Json -Compress
}
finally { if ($response) { $response.Dispose() } }

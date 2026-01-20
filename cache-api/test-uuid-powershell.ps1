# PowerShell Script to Test UUID Login Tracking API
# Run this script: .\test-uuid-powershell.ps1

Write-Host "=== UUID LOGIN TRACKING - PowerShell Test ===" -ForegroundColor Cyan
Write-Host ""

# Test 1: UUID Login
Write-Host "TEST 1: UUID Login with Tracking" -ForegroundColor Yellow
Write-Host "Endpoint: POST /auth/uuid" -ForegroundColor Gray
Write-Host ""

$body = @{
    uuid = "powershell-test-uuid-001"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/auth/uuid" `
        -Method Post `
        -Body $body `
        -ContentType "application/json"
    
    Write-Host "Status: Success" -ForegroundColor Green
    Write-Host "UUID: $($response.uuid)"
    Write-Host "Authenticated: $($response.authenticated)"
    Write-Host "Record ID: $($response.tracking.record_id)"
    Write-Host "IP Address: $($response.tracking.ip_address)"
    Write-Host ""
    
} catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Make sure the server is running: python main.py" -ForegroundColor Yellow
}

# Test 2: View All Logs (Admin)
Write-Host ""
Write-Host "TEST 2: View All UUID Tracking Logs (Admin)" -ForegroundColor Yellow
Write-Host "Endpoint: GET /admin/uuid-logs" -ForegroundColor Gray
Write-Host ""

$headers = @{
    Authorization = "Bearer eternitylabsadmin"
}

try {
    $logs = Invoke-RestMethod -Uri "http://localhost:8001/admin/uuid-logs?limit=5" `
        -Method Get `
        -Headers $headers
    
    Write-Host "Status: Success" -ForegroundColor Green
    Write-Host "Total Records: $($logs.total)"
    Write-Host "Showing: $($logs.count) records"
    Write-Host ""
    Write-Host "Recent login attempts:" -ForegroundColor Cyan
    
    foreach ($log in $logs.logs) {
        Write-Host "  Record ID: $($log.id)"
        Write-Host "  UUID: $($log.uuid)"
        Write-Host "  IP: $($log.ip_address)"
        Write-Host "  Time: $($log.timestamp)"
        Write-Host "  ---"
    }
    
} catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: Filter by UUID
Write-Host ""
Write-Host "TEST 3: Filter Logs by Specific UUID" -ForegroundColor Yellow
Write-Host "Endpoint: GET /admin/uuid-logs?uuid=..." -ForegroundColor Gray
Write-Host ""

try {
    $filtered = Invoke-RestMethod -Uri "http://localhost:8001/admin/uuid-logs?uuid=powershell-test-uuid-001" `
        -Method Get `
        -Headers $headers
    
    Write-Host "Status: Success" -ForegroundColor Green
    Write-Host "Found $($filtered.total) login(s) for UUID: powershell-test-uuid-001"
    Write-Host ""
    
} catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 4: Security Test (No Auth)
Write-Host ""
Write-Host "TEST 4: Security - Access Without Token" -ForegroundColor Yellow
Write-Host ""

try {
    $noAuth = Invoke-RestMethod -Uri "http://localhost:8001/admin/uuid-logs" -Method Get
    Write-Host "Warning: Security may not be working!" -ForegroundColor Red
} catch {
    if ($_.Exception.Response.StatusCode -eq 403 -or $_.Exception.Response.StatusCode -eq 401) {
        Write-Host "Status: Security Working!" -ForegroundColor Green
        Write-Host "Access denied without authentication (Expected)" -ForegroundColor Gray
    } else {
        Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=== All Tests Completed ===" -ForegroundColor Cyan

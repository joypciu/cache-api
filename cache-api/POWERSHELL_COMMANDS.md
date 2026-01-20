# PowerShell Commands for UUID Login Tracking API

## Quick Commands (Copy & Paste)

### Start the Server
```powershell
cd F:\cacheFile\cache-api
$env:PYTHONIOENCODING = "utf-8"
python main.py
```

### Test 1: UUID Login (No Auth Required)
```powershell
Invoke-RestMethod -Uri "http://localhost:8001/auth/uuid" -Method Post -Body '{"uuid":"my-test-uuid-123"}' -ContentType "application/json"
```

### Test 2: View All Tracking Logs (Admin Token)
```powershell
Invoke-RestMethod -Uri "http://localhost:8001/admin/uuid-logs" -Headers @{Authorization="Bearer eternitylabsadmin"}
```

### Test 3: Filter by Specific UUID
```powershell
Invoke-RestMethod -Uri "http://localhost:8001/admin/uuid-logs?uuid=my-test-uuid-123" -Headers @{Authorization="Bearer eternitylabsadmin"}
```

### Run Full Test Suite
```powershell
.\test-uuid-powershell.ps1
```

---

## Authentication Tokens

**Admin Token (for viewing logs):**
```
eternitylabsadmin
```

**Non-Admin Token (cache only):**
```
12345
```

---

## Step-by-Step Testing

**Step 1:** Open PowerShell in `F:\cacheFile\cache-api`

**Step 2:** Start the server:
```powershell
$env:PYTHONIOENCODING = "utf-8"; python main.py
```

**Step 3:** Open a NEW PowerShell window and test:
```powershell
# Login with UUID
Invoke-RestMethod -Uri "http://localhost:8001/auth/uuid" -Method Post -Body '{"uuid":"test-123"}' -ContentType "application/json"

# View the logs (admin)
Invoke-RestMethod -Uri "http://localhost:8001/admin/uuid-logs" -Headers @{Authorization="Bearer eternitylabsadmin"}
```

---

## Why bash commands don't work in PowerShell:

**Bash (Linux/Git Bash):**
```bash
curl -X POST "http://localhost:8001/auth/uuid" -H "Content-Type: application/json" -d '{"uuid":"test"}'
```

**PowerShell (Windows):**
```powershell
Invoke-RestMethod -Uri "http://localhost:8001/auth/uuid" -Method Post -Body '{"uuid":"test"}' -ContentType "application/json"
```

PowerShell uses `Invoke-RestMethod` or `Invoke-WebRequest` instead of `curl`.

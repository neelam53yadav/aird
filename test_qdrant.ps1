# Qdrant Connectivity Test Script
Write-Host "Testing Qdrant connectivity..." -ForegroundColor Green

# Test 1: Check if port is accessible
Write-Host "`n1. Testing port 6333 accessibility..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:6333/health" -Method GET -TimeoutSec 10
    Write-Host "✅ Qdrant is accessible on port 6333" -ForegroundColor Green
    Write-Host "Response: $($response.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "❌ Qdrant is NOT accessible on port 6333" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 2: Check collections endpoint
Write-Host "`n2. Testing collections endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:6333/collections" -Method GET -TimeoutSec 10
    Write-Host "✅ Collections endpoint is working" -ForegroundColor Green
    $collections = $response.Content | ConvertFrom-Json
    Write-Host "Found $($collections.result.collections.Count) collections" -ForegroundColor Green
} catch {
    Write-Host "❌ Collections endpoint failed" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: Check Docker container status
Write-Host "`n3. Checking Docker container status..." -ForegroundColor Yellow
try {
    $container = docker ps --filter "name=primedata-qdrant" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    if ($container -match "primedata-qdrant") {
        Write-Host "✅ Qdrant container is running" -ForegroundColor Green
        Write-Host $container -ForegroundColor Green
    } else {
        Write-Host "❌ Qdrant container is NOT running" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Could not check Docker container status" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 4: Check container logs
Write-Host "`n4. Checking Qdrant container logs..." -ForegroundColor Yellow
try {
    $logs = docker logs primedata-qdrant --tail 10 2>&1
    Write-Host "Last 10 log lines:" -ForegroundColor Cyan
    Write-Host $logs -ForegroundColor Cyan
} catch {
    Write-Host "❌ Could not retrieve container logs" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`nTest completed!" -ForegroundColor Green


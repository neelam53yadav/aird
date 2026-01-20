# Memory monitoring script for PrimeData development (Windows PowerShell)
# Monitors Docker container memory usage and system memory
# Usage: .\scripts\check_memory.ps1

param(
    [string]$ContainerRuntime = "docker"
)

$ErrorActionPreference = "Stop"

# Colors for output (Windows PowerShell compatible)
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

Write-ColorOutput "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" "Cyan"
Write-ColorOutput "📊 Memory Usage Monitor" "Cyan"
Write-ColorOutput "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" "Cyan"
Write-Host ""

# Detect container runtime (Docker or Podman)
$detectedRuntime = "none"
if (Get-Command docker -ErrorAction SilentlyContinue) {
    try {
        docker info 2>&1 | Out-Null
        $detectedRuntime = "docker"
    } catch {
        # Docker not running
    }
}

if ($detectedRuntime -eq "none" -and (Get-Command podman -ErrorAction SilentlyContinue)) {
    try {
        podman info 2>&1 | Out-Null
        $detectedRuntime = "podman"
    } catch {
        # Podman not running
    }
}

if ($detectedRuntime -eq "none") {
    Write-ColorOutput "❌ Neither Docker nor Podman is running" "Red"
    exit 1
}

# Container runtime to use
$runtime = if ($ContainerRuntime) { $ContainerRuntime } else { $detectedRuntime }

# Docker container memory usage
Write-ColorOutput "🐳 Container Memory Usage ($runtime)" "Green"
Write-Host ""

try {
    # Check if containers exist
    $containers = & $runtime ps --format "{{.Names}}" 2>$null | Select-String "aird-"
    
    if ($containers) {
        $containerNames = $containers | ForEach-Object { $_.Line }
        
        # Show container stats
        & $runtime stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}" $containerNames 2>$null
        
        Write-Host ""
        
        # Calculate total memory (simplified - parse memory usage)
        $totalMem = 0
        $stats = & $runtime stats --no-stream --format "{{.MemUsage}}" $containerNames 2>$null
        foreach ($stat in $stats) {
            if ($stat -match "(\d+\.?\d*)([KMGT]?i?B)") {
                $value = [double]$matches[1]
                $unit = $matches[2]
                switch ($unit) {
                    "MiB" { $totalMem += $value }
                    "GiB" { $totalMem += ($value * 1024) }
                    "KiB" { $totalMem += ($value / 1024) }
                    default { $totalMem += $value }
                }
            }
        }
        
        if ($totalMem -gt 0) {
            $totalMemMB = [math]::Round($totalMem)
            Write-ColorOutput "Total Container Memory Usage ($runtime): ~${totalMemMB}MB" "Cyan"
            
            if ($totalMemMB -gt 6000) {
                Write-ColorOutput "⚠️  WARNING: Container memory usage is high (>6GB). Consider using test-only services." "Red"
            } elseif ($totalMemMB -gt 4000) {
                Write-ColorOutput "⚠️  WARNING: Container memory usage is moderate (>4GB). Monitor system memory." "Yellow"
            }
        }
    } else {
        Write-ColorOutput "No PrimeData containers are running" "Yellow"
        Write-ColorOutput "Start services with: python run.py dev --services-only" "Yellow"
        Write-ColorOutput "Or test services with: python run.py dev --services-only" "Yellow"
    }
} catch {
    Write-ColorOutput "Error checking container status: $_" "Red"
}

Write-Host ""
Write-ColorOutput "💻 System Memory (Windows)" "Green"
Write-Host ""

# Windows system memory info using WMI
try {
    $os = Get-WmiObject Win32_OperatingSystem
    $cs = Get-WmiObject Win32_ComputerSystem
    
    $totalMemory = [math]::Round($os.TotalVisibleMemorySize / 1MB, 2)
    $freeMemory = [math]::Round($os.FreePhysicalMemory / 1MB, 2)
    $usedMemory = $totalMemory - $freeMemory
    $usedPercent = [math]::Round(($usedMemory / $totalMemory) * 100, 1)
    $availablePercent = [math]::Round(($freeMemory / $totalMemory) * 100, 1)
    
    Write-Host "Platform: Windows"
    Write-Host "Total Memory: ${totalMemory} GB"
    Write-Host "Used: ${usedMemory} GB ($usedPercent%)"
    Write-Host "Available: ${freeMemory} GB ($availablePercent%)"
    Write-Host ""
    
    # Warnings
    if ($usedPercent -gt 85) {
        Write-ColorOutput "⚠️  CRITICAL: System memory usage is very high (>85%). Close applications or reduce Docker memory limits." "Red"
    } elseif ($usedPercent -gt 75) {
        Write-ColorOutput "⚠️  WARNING: System memory usage is high (>75%). Consider using test-only services." "Yellow"
    } elseif ($freeMemory -lt 2) {
        Write-ColorOutput "⚠️  WARNING: Less than 2GB available memory. System may swap." "Yellow"
    } else {
        Write-ColorOutput "✅ System memory usage is within acceptable limits" "Green"
    }
} catch {
    Write-ColorOutput "⚠️  Could not retrieve system memory information: $_" "Yellow"
}

Write-Host ""
Write-ColorOutput "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" "Cyan"
Write-ColorOutput "💡 Recommendations for 8GB Systems:" "Cyan"
Write-ColorOutput "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" "Cyan"
Write-Host ""
Write-Host "1. Use test-only services for testing:"
Write-ColorOutput "   python run.py dev --services-only" "Green"
Write-Host ""
Write-Host "2. Use OpenAI API embeddings (saves ~500MB-1GB):"
Write-Host "   Set OPENAI_API_KEY and USE_OPENAI_EMBEDDINGS=true"
Write-Host ""
Write-Host "3. Stop unnecessary containers:"
Write-ColorOutput "   python run.py dev --skip-docker" "Green"
Write-Host ""
Write-Host "4. Close other memory-intensive applications"
Write-Host ""
Write-ColorOutput "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" "Cyan"

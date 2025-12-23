# PrimeData Migration Runner (Windows PowerShell)
# Ensures migrations run only inside a virtualenv with safety checks

param(
    [Parameter(Position=0)]
    [string]$Command = "help",
    
    [Parameter(Position=1)]
    [string]$Message = ""
)

$ErrorActionPreference = "Stop"

# Colors for output (PowerShell)
function Write-ColorOutput($ForegroundColor, $Message) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    Write-Output $Message
    $host.UI.RawUI.ForegroundColor = $fc
}

# Get script directory and project root
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$BackendDir = Join-Path $ProjectRoot "backend"

Set-Location $BackendDir

Write-Output "=== PrimeData Migration Runner ==="
Write-Output "Backend directory: $BackendDir"
Write-Output ""

# Check if we're in a virtualenv
if (-not $env:VIRTUAL_ENV) {
    Write-ColorOutput Red "ERROR: Not in a virtualenv!"
    Write-Output "Please activate your virtualenv first:"
    Write-Output "  .venv\Scripts\Activate.ps1  # or your venv path"
    Write-Output "  # OR"
    Write-Output "  python -m venv .venv && .venv\Scripts\Activate.ps1"
    exit 1
}

# Verify which Python is being used
$PythonExec = python -c "import sys; print(sys.executable)"
Write-ColorOutput Green "Using Python: $PythonExec"
Write-Output ""

# Check if Python is from venv
if ($PythonExec -notlike "*$env:VIRTUAL_ENV*") {
    Write-ColorOutput Red "ERROR: Python executable is not from the active virtualenv!"
    Write-Output "Expected venv path: $env:VIRTUAL_ENV"
    Write-Output "Python path: $PythonExec"
    exit 1
}

# Verify alembic is installed
try {
    python -c "import alembic" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "alembic not found"
    }
} catch {
    Write-ColorOutput Red "ERROR: alembic is not installed in the virtualenv!"
    Write-Output "Please install dependencies: pip install -r requirements.txt"
    exit 1
}

# Execute command
switch ($Command.ToLower()) {
    "generate" {
        if ([string]::IsNullOrWhiteSpace($Message)) {
            Write-ColorOutput Red "ERROR: Migration message required"
            Write-Output "Usage: .\run_migrations.ps1 generate '<migration message>'"
            exit 1
        }
        
        Write-ColorOutput Yellow "Generating migration: $Message"
        alembic revision --autogenerate -m "$Message"
        
        # Get the latest migration file
        $LatestMigration = Get-ChildItem -Path "alembic\versions\*.py" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        Write-Output ""
        Write-ColorOutput Green "Migration generated: $($LatestMigration.FullName)"
        Write-Output ""
        Write-ColorOutput Yellow "Reviewing migration for dangerous operations..."
        
        # Check for dangerous operations
        $DangerousOps = Select-String -Path $LatestMigration.FullName -Pattern "(op\.drop_table|op\.drop_column|op\.alter_column.*nullable=True.*existing_nullable=False)" -AllMatches
        
        if ($DangerousOps) {
            Write-ColorOutput Red "WARNING: Potentially dangerous operations found:"
            $DangerousOps | ForEach-Object { Write-Output $_.Line }
            Write-Output ""
            Write-ColorOutput Yellow "Please review the migration file manually before applying!"
            Write-Output "File: $($LatestMigration.FullName)"
        } else {
            Write-ColorOutput Green "No dangerous operations detected."
        }
    }
    
    "upgrade" {
        if ($env:MIGRATION_REVIEWED -ne "1") {
            Write-ColorOutput Red "ERROR: Migration review required!"
            Write-Output "Set MIGRATION_REVIEWED=1 to proceed with upgrade"
            Write-Output ""
            Write-Output "Example:"
            Write-Output "  `$env:MIGRATION_REVIEWED='1'; .\run_migrations.ps1 upgrade"
            exit 1
        }
        
        Write-ColorOutput Green "Applying migrations..."
        alembic upgrade head
        Write-ColorOutput Green "Migrations applied successfully!"
    }
    
    "current" {
        Write-Output "Current database revision:"
        alembic current
    }
    
    "history" {
        Write-Output "Migration history:"
        alembic history
    }
    
    default {
        Write-Output "Usage: .\run_migrations.ps1 <command> [args]"
        Write-Output ""
        Write-Output "Commands:"
        Write-Output "  generate '<message>'  - Generate a new migration (autogenerate)"
        Write-Output "  upgrade               - Apply migrations (requires MIGRATION_REVIEWED=1)"
        Write-Output "  current               - Show current database revision"
        Write-Output "  history               - Show migration history"
        Write-Output ""
        Write-Output "Examples:"
        Write-Output "  .\run_migrations.ps1 generate 'Add AIRD pipeline tracking fields'"
        Write-Output "  `$env:MIGRATION_REVIEWED='1'; .\run_migrations.ps1 upgrade"
    }
}





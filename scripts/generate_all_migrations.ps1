# Generate all missing AIRD migrations
# Run this from backend/ directory inside venv

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path (Split-Path -Parent $ScriptDir) "backend"

Set-Location $BackendDir

Write-Output "=== Generating Missing AIRD Migrations ==="
Write-Output ""

# M0: Pipeline tracking fields
Write-Output "Generating M0: Pipeline tracking fields..."
alembic revision --autogenerate -m "add_aird_pipeline_tracking_to_pipeline_runs"

# M1: Playbook and preprocessing
Write-Output "Generating M1: Playbook and preprocessing..."
alembic revision --autogenerate -m "add_playbook_and_preprocessing_to_products"

# M2: Trust scoring and policy
Write-Output "Generating M2: Trust scoring and policy..."
alembic revision --autogenerate -m "add_trust_scoring_and_policy_to_products"

# M3: Report paths
Write-Output "Generating M3: Report paths..."
alembic revision --autogenerate -m "add_report_paths_to_products"

# M4: Document and vector metadata tables
Write-Output "Generating M4: Document and vector metadata tables..."
alembic revision --autogenerate -m "add_document_and_vector_metadata_tables"

# M5: ACL table
Write-Output "Generating M5: ACL table..."
alembic revision --autogenerate -m "add_acls_table"

Write-Output ""
Write-Output "=== Migration Generation Complete ==="
Write-Output "Review all generated migrations before applying!"




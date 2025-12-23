#!/bin/bash
# Generate all missing AIRD migrations
# Run this from backend/ directory inside venv

set -e

cd "$(dirname "$0")/../backend"

echo "=== Generating Missing AIRD Migrations ==="
echo ""

# M0: Pipeline tracking fields
echo "Generating M0: Pipeline tracking fields..."
alembic revision --autogenerate -m "add_aird_pipeline_tracking_to_pipeline_runs"

# M1: Playbook and preprocessing
echo "Generating M1: Playbook and preprocessing..."
alembic revision --autogenerate -m "add_playbook_and_preprocessing_to_products"

# M2: Trust scoring and policy
echo "Generating M2: Trust scoring and policy..."
alembic revision --autogenerate -m "add_trust_scoring_and_policy_to_products"

# M3: Report paths
echo "Generating M3: Report paths..."
alembic revision --autogenerate -m "add_report_paths_to_products"

# M4: Document and vector metadata tables
echo "Generating M4: Document and vector metadata tables..."
alembic revision --autogenerate -m "add_document_and_vector_metadata_tables"

# M5: ACL table
echo "Generating M5: ACL table..."
alembic revision --autogenerate -m "add_acls_table"

echo ""
echo "=== Migration Generation Complete ==="
echo "Review all generated migrations before applying!"




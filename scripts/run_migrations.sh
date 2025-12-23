#!/bin/bash
# PrimeData Migration Runner (Linux/macOS)
# Ensures migrations run only inside a virtualenv with safety checks

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"

cd "$BACKEND_DIR"

echo "=== PrimeData Migration Runner ==="
echo "Backend directory: $BACKEND_DIR"
echo ""

# Check if we're in a virtualenv
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${RED}ERROR: Not in a virtualenv!${NC}"
    echo "Please activate your virtualenv first:"
    echo "  source .venv/bin/activate  # or your venv path"
    echo "  # OR"
    echo "  python -m venv .venv && source .venv/bin/activate"
    exit 1
fi

# Verify which Python is being used
PYTHON_EXEC=$(python -c "import sys; print(sys.executable)")
echo -e "${GREEN}Using Python: $PYTHON_EXEC${NC}"
echo ""

# Check if Python is from venv
if [[ "$PYTHON_EXEC" != *"$VIRTUAL_ENV"* ]]; then
    echo -e "${RED}ERROR: Python executable is not from the active virtualenv!${NC}"
    echo "Expected venv path: $VIRTUAL_ENV"
    echo "Python path: $PYTHON_EXEC"
    exit 1
fi

# Verify alembic is installed
if ! python -c "import alembic" 2>/dev/null; then
    echo -e "${RED}ERROR: alembic is not installed in the virtualenv!${NC}"
    echo "Please install dependencies: pip install -r requirements.txt"
    exit 1
fi

# Parse command
COMMAND="${1:-help}"

case "$COMMAND" in
    generate)
        MESSAGE="${2:-}"
        if [ -z "$MESSAGE" ]; then
            echo -e "${RED}ERROR: Migration message required${NC}"
            echo "Usage: $0 generate '<migration message>'"
            exit 1
        fi
        
        echo -e "${YELLOW}Generating migration: $MESSAGE${NC}"
        alembic revision --autogenerate -m "$MESSAGE"
        
        # Get the latest migration file
        LATEST_MIGRATION=$(ls -t alembic/versions/*.py | head -1)
        echo ""
        echo -e "${GREEN}Migration generated: $LATEST_MIGRATION${NC}"
        echo ""
        echo -e "${YELLOW}Reviewing migration for dangerous operations...${NC}"
        
        # Check for dangerous operations
        DANGEROUS_OPS=$(grep -E "(op\.drop_table|op\.drop_column|op\.alter_column.*nullable=True.*existing_nullable=False)" "$LATEST_MIGRATION" || true)
        
        if [ -n "$DANGEROUS_OPS" ]; then
            echo -e "${RED}WARNING: Potentially dangerous operations found:${NC}"
            echo "$DANGEROUS_OPS"
            echo ""
            echo -e "${YELLOW}Please review the migration file manually before applying!${NC}"
            echo "File: $LATEST_MIGRATION"
        else
            echo -e "${GREEN}No dangerous operations detected.${NC}"
        fi
        ;;
    
    upgrade)
        if [ "$MIGRATION_REVIEWED" != "1" ]; then
            echo -e "${RED}ERROR: Migration review required!${NC}"
            echo "Set MIGRATION_REVIEWED=1 to proceed with upgrade"
            echo ""
            echo "Example:"
            echo "  MIGRATION_REVIEWED=1 $0 upgrade"
            exit 1
        fi
        
        echo -e "${GREEN}Applying migrations...${NC}"
        alembic upgrade head
        echo -e "${GREEN}Migrations applied successfully!${NC}"
        ;;
    
    current)
        echo "Current database revision:"
        alembic current
        ;;
    
    history)
        echo "Migration history:"
        alembic history
        ;;
    
    help|*)
        echo "Usage: $0 <command> [args]"
        echo ""
        echo "Commands:"
        echo "  generate '<message>'  - Generate a new migration (autogenerate)"
        echo "  upgrade               - Apply migrations (requires MIGRATION_REVIEWED=1)"
        echo "  current               - Show current database revision"
        echo "  history               - Show migration history"
        echo ""
        echo "Examples:"
        echo "  $0 generate 'Add AIRD pipeline tracking fields'"
        echo "  MIGRATION_REVIEWED=1 $0 upgrade"
        ;;
esac





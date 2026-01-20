# PrimeData Development Makefile
# Common development tasks for local setup and daily development
#
# NOTE:
# - `make backend` will always load backend/.env.local (permanent fix for MINIO_HOST etc.)
# - `make services/stop/clean` uses infra/docker-compose.yml (Docker Compose)
# - If you're using Podman, keep infra services started via your existing flow (run.py dev --services-only)

SHELL := /bin/bash

.PHONY: help setup dev install install-backend install-frontend \
        services migrate backend frontend stop clean \
        backend-env frontend-env print-env

# -----------------------------
# Helpers / env loaders
# -----------------------------
BACKEND_ENV_FILE := backend/.env.local
FRONTEND_ENV_FILE := ui/.env/local

define load_backend_env
	set -a; \
	if [ -f "$(BACKEND_ENV_FILE)" ]; then source "$(BACKEND_ENV_FILE)"; fi; \
	set +a;
endef

define load_frontend_env
	set -a; \
	if [ -f "$(FRONTEND_ENV_FILE)" ]; then source "$(FRONTEND_ENV_FILE)"; fi; \
	set +a;
endef

# -----------------------------
# Default target
# -----------------------------
help:
	@echo "PrimeData Development Commands:"
	@echo ""
	@echo "  make setup        - One-time setup: install deps + services + migrations"
	@echo "  make install      - Install backend and frontend dependencies"
	@echo "  make services     - Start/restart Docker services only"
	@echo "  make migrate      - Run database migrations only"
	@echo "  make backend      - Start backend server (loads backend/.env.local)"
	@echo "  make frontend     - Start frontend server"
	@echo "  make dev          - Show instructions for running dev servers"
	@echo "  make stop         - Stop all Docker services"
	@echo "  make clean        - Stop services and remove volumes (destructive)"
	@echo ""
	@echo "Utilities:"
	@echo "  make backend-env  - Print env vars from backend/.env.local (sanity check)"
	@echo "  make frontend-env - Print env vars from ui/.env/local (sanity check)"
	@echo "  make print-env    - Show effective MINIO_HOST/MINIO_PORT etc (backend load)"
	@echo ""

# -----------------------------
# Install both backend and frontend dependencies
# -----------------------------
install: install-backend install-frontend

install-backend:
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "📦 Installing backend dependencies..."
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@python scripts/install_backend.py
	@echo ""

install-frontend:
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "📦 Installing frontend dependencies..."
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	cd ui && npm install
	@echo ""
	@echo "✅ Frontend dependencies installed"

# -----------------------------
# One-time setup
# -----------------------------
setup: install
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🐳 Starting Docker services..."
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	python run.py dev --services-only
	@echo ""
	@echo "⏳ Waiting for services to be ready..."
	@python -c "import time; time.sleep(10)"
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "📊 Running database migrations..."
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	$(MAKE) migrate
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "✅ Setup complete!"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "Next steps:"
	@echo "  Terminal 1: make backend"
	@echo "  Terminal 2: make frontend"
	@echo ""

dev:
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🔧 Starting development servers..."
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "Run these commands in separate terminals:"
	@echo ""
	@echo "  Terminal 1 (Backend):"
	@echo "    make backend"
	@echo ""
	@echo "  Terminal 2 (Frontend):"
	@echo "    make frontend"
	@echo ""

# -----------------------------
# Start backend server (PERMANENT ENV LOAD FIX)
# -----------------------------
backend:
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🔧 Starting backend server..."
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@$(call load_backend_env) \
	python start_backend.py

# -----------------------------
# Start frontend server
# (Next.js loads ui/.env/local by default; we keep target simple)
# -----------------------------
frontend:
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🎨 Starting frontend server..."
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	cd ui && npm run dev

# -----------------------------
# Docker services management
# -----------------------------
services:
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🐳 Starting Docker services..."
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	python run.py dev --services-only

migrate:
	@echo "📊 Running database migrations..."
	cd backend && python -m alembic upgrade head

stop:
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🛑 Stopping services..."
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	python run.py dev --stop-services

clean:
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🧹 Cleaning up services and volumes..."
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "⚠️  WARNING: This will remove all volumes and data!"
	@echo "Press Ctrl+C to cancel, or wait 5 seconds to continue..."
	@python -c "import time; time.sleep(5)"
	python run.py dev --clean-volumes
	@echo ""
	@echo "✅ Cleanup complete"

# -----------------------------
# Utilities (debug / sanity checks)
# -----------------------------
backend-env:
	@echo "---- $(BACKEND_ENV_FILE) ----"
	@if [ -f "$(BACKEND_ENV_FILE)" ]; then cat "$(BACKEND_ENV_FILE)"; else echo "Missing: $(BACKEND_ENV_FILE)"; fi

frontend-env:
	@echo "---- $(FRONTEND_ENV_FILE) ----"
	@if [ -f "$(FRONTEND_ENV_FILE)" ]; then cat "$(FRONTEND_ENV_FILE)"; else echo "Missing: $(FRONTEND_ENV_FILE)"; fi

print-env:
	@$(call load_backend_env) \
	echo "Effective backend env (after loading $(BACKEND_ENV_FILE)):"; \
	echo "  MINIO_HOST=$${MINIO_HOST:-<unset>}"; \
	echo "  MINIO_PORT=$${MINIO_PORT:-<unset>}"; \
	echo "  MINIO_HOST_PORT=$${MINIO_HOST_PORT:-<unset>}"; \
	echo "  S3_ENDPOINT=$${S3_ENDPOINT:-<unset>}"; \
	echo "  STORAGE_ENDPOINT=$${STORAGE_ENDPOINT:-<unset>}"

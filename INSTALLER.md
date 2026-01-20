# PrimeData Cross-Platform Installer

This document describes the installer options available for PrimeData on Windows, macOS, and Linux.

## Quick Start

## Recommended Installer Flow (All OS)

PrimeData uses **one cross-platform installer**:

- `scripts/install.py` — installs Python backend deps + UI deps and creates `.env.local` files.

Then each OS has a small wrapper:

- **Windows**: `scripts\setup_windows.bat` (checks Python/Node, then calls `python scripts\install.py`)
- **macOS/Linux**: run `python3 scripts/install.py` directly

This design keeps the installer logic in one place and avoids OS-specific duplication.

### Windows

**Option 1: Automated Installer (Recommended)**
```batch
REM Double-click setup_windows.bat or run from Command Prompt:
scripts\setup_windows.bat
```

**Option 2: Python Installer**
```batch
python scripts\install.py
```

### macOS/Linux

**Option 1: Python Installer (Recommended)**
```bash
python3 scripts/install.py
```

**Option 2: Makefile**
```bash
make setup
```

## What the Installer Does

The installer performs the following steps automatically:

1. **Prerequisites Check**
   - Verifies Python 3.11+ is installed
   - Verifies Node.js 18+ is installed
   - Checks for Docker or Podman
   - Verifies Git is available

2. **Virtual Environment Setup**
   - Creates Python virtual environment (`.venv` or `venv`)
   - Configures platform-specific paths (Windows vs Unix)

3. **Dependency Installation**
   - Installs backend Python dependencies from `backend/requirements.txt`
   - Installs frontend Node.js dependencies via `npm install`
   - Upgrades pip to latest version

4. **Configuration Files**
   - Creates `.env.local` files from examples if they don't exist
   - Provides instructions for editing configuration

5. **Next Steps**
   - Provides platform-specific instructions for starting services
   - Shows database migration commands
   - Lists commands for starting backend and frontend

## Platform-Specific Notes

### Windows

- **Installer**: `scripts\setup_windows.bat` or `scripts\install.py`
- **Memory Check**: PowerShell script: `scripts\check_memory.ps1`
- **Services**: Use `python run.py dev --services-only`
- **Commands**: Python scripts work natively, Makefile requires WSL/Git Bash
- **Podman (Windows)**: Supported. Install **Podman Desktop** and ensure the Podman machine/VM is running. If you see Docker-daemon errors, enable Podman’s Docker API compatibility or install the Docker CLI shim so tools expecting `docker` still work.

### macOS

- **Installer**: `python3 scripts/install.py` or `make setup`
- **Memory Check**: `bash scripts/check_memory.sh`
- **Services**: Use `make services` or `python run.py dev --services-only`
- **Commands**: Makefile works natively, or use Python scripts

### Linux

- **Installer**: `python3 scripts/install.py` or `make setup`
- **Memory Check**: `bash scripts/check_memory.sh`
- **Services**: Use `make services` or `python run.py dev --services-only`
- **Commands**: Makefile works natively, or use Python scripts
- **Permissions**: May need to add user to docker group: `sudo usermod -aG docker $USER`

## Troubleshooting

### Installer Fails

**Issue**: Installer reports missing prerequisites
**Solution**: Install missing software (Python, Node.js, Docker) and run installer again

**Issue**: Using Podman but the app says "Cannot connect to Docker daemon"
**Solution**:
- Ensure Podman Desktop is running and the Podman machine is started
- Enable Podman “Docker API compatibility” (or install the docker CLI shim)
- Re-run: `python run.py dev --services-only`

**Issue**: Permission errors on Linux/macOS
**Solution**: Use `sudo` only if absolutely necessary, prefer user-level installation

**Issue**: Virtual environment creation fails
**Solution**: Ensure Python `venv` module is available: `python -m venv --help`

### Dependencies Installation Fails

**Issue**: Backend dependencies fail to install
**Solution**: 
- Check internet connection
- Try upgrading pip: `pip install --upgrade pip`
- Check Python version: `python --version` (requires 3.11+)

**Issue**: Frontend dependencies fail to install
**Solution**:
- Check Node.js version: `node --version` (requires 18+)
- Clear npm cache: `npm cache clean --force`
- Try deleting `node_modules` and `package-lock.json` and reinstalling

### Configuration Issues

**Issue**: `.env.local` files not created
**Solution**: Copy example files manually:
- `backend/env.example` → `backend/.env.local`
- `infra/env/services.example.env` → `infra/.env.local`
- `infra/env/ui.example.env.local` → `ui/.env.local`

## Manual Installation

If the installer fails, you can perform manual installation:

1. **Create virtual environment**:
   - Windows: `python -m venv .venv && .venv\Scripts\activate`
   - macOS/Linux: `python3 -m venv .venv && source .venv/bin/activate`

2. **Install dependencies**:
   ```bash
   pip install -r backend/requirements.txt
   cd ui && npm install
   ```

3. **Configure environment**:
   - Copy and edit `.env.local` files from examples

4. **Start services**:
   - Use `python run.py dev --services-only` (cross-platform)
   - Or use `make services` (macOS/Linux only)

5. **Run migrations**:
   ```bash
   # Windows
   .venv\Scripts\python.exe -m alembic upgrade head
   
   # macOS/Linux
   .venv/bin/python -m alembic upgrade head
   ```

## Next Steps After Installation

1. **Edit Configuration**: Update `.env.local` files with your settings
2. **Start Services**: Run Docker/Podman services
3. **Run Migrations**: Initialize database schema
4. **Start Application**: Run backend and frontend servers
5. **Access UI**: Open http://localhost:3000 in your browser

For detailed setup instructions, see [README.md](README.md).

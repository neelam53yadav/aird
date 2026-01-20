#!/usr/bin/env python3
"""
PrimeData Development/Production Wrapper Script
Simplified version that uses .env.local files
"""

import os
import sys
import subprocess
import platform
import time
from pathlib import Path
from typing import Optional, Tuple

class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    """Print formatted header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text:^60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_success(text: str):
    """Print success message."""
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")

def print_warning(text: str):
    """Print warning message."""
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")

def print_error(text: str):
    """Print error message."""
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")

def print_info(text: str):
    """Print info message."""
    print(f"{Colors.OKCYAN}ℹ️  {text}{Colors.ENDC}")

def _run_ok(cmd: list[str]) -> bool:
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def detect_container_runtime() -> Tuple[Optional[str], Optional[str]]:
    """
    Detect container runtime. Prefers explicit CONTAINER_RUNTIME if set.
    Returns: (runtime, hint_message)
    runtime: "docker" | "podman" | None
    """
    forced = (os.environ.get("CONTAINER_RUNTIME") or "").strip().lower()
    if forced in {"docker", "podman"}:
        return forced, f"Using CONTAINER_RUNTIME={forced}"

    # Auto-detect in a stable order: docker first, then podman.
    if _run_ok(["docker", "--version"]):
        return "docker", "Detected Docker"
    if _run_ok(["podman", "--version"]):
        return "podman", "Detected Podman"
    return None, None

def check_container_runtime(runtime: str) -> bool:
    """Check runtime is installed and usable."""
    if runtime == "docker":
        if not _run_ok(["docker", "--version"]):
            print_error("Docker is not installed or not in PATH")
            print_info("Install Docker from: https://docs.docker.com/get-docker/")
            return False
        # If daemon isn't running, docker info returns non-zero.
        if not _run_ok(["docker", "info"]):
            print_error("Docker daemon is not reachable (is Docker Desktop running?)")
            return False
        return True

    if runtime == "podman":
        if not _run_ok(["podman", "--version"]):
            print_error("Podman is not installed or not in PATH")
            print_info("Install Podman Desktop from: https://podman-desktop.io/")
            return False
        # If podman machine isn't running on macOS/Windows, podman info returns non-zero.
        if not _run_ok(["podman", "info"]):
            print_error("Podman is not reachable (is Podman machine/VM running?)")
            return False
        return True

    print_error(f"Unknown container runtime: {runtime}")
    return False

def get_compose_cmd(runtime: str) -> list[str]:
    """
    Returns the compose command as argv list.
    - docker: ['docker', 'compose'] (or ['docker-compose'])
    - podman: ['podman', 'compose'] (or ['podman-compose'])
    """
    if runtime == "docker":
        if _run_ok(["docker", "compose", "version"]):
            return ["docker", "compose"]
        return ["docker-compose"]

    if runtime == "podman":
        if _run_ok(["podman", "compose", "version"]):
            return ["podman", "compose"]
        # podman-compose is a separate binary on many distros.
        if _run_ok(["podman-compose", "--version"]):
            return ["podman-compose"]
        print_error("Podman compose is not available.")
        print_info("Install one of: 'podman compose' (newer Podman) or 'podman-compose' (package).")
        return []

    return []

def check_env_files(mode: str) -> bool:
    """Check if required .env.local files exist."""
    root_dir = Path(__file__).parent
    backend_env = root_dir / "backend" / ".env.local"
    infra_env = root_dir / "infra" / ".env.local"
    
    missing = []
    if not backend_env.exists():
        missing.append(f"backend/.env.local")
    if not infra_env.exists():
        missing.append(f"infra/.env.local")
    
    if missing:
        print_warning(f"Missing .env.local files: {', '.join(missing)}")
        print_info("Create these files based on env.example files")
        return False
    
    print_success("All .env.local files found")
    return True

def start_services(mode: str, runtime: str) -> bool:
    """Start services using Docker or Podman compose."""
    print_header(f"Starting Services ({runtime})")
    
    root_dir = Path(__file__).parent
    infra_dir = root_dir / "infra"
    compose_file = infra_dir / f"docker-compose{'.prod' if mode == 'prod' else ''}.yml"
    env_file = infra_dir / ".env.local"
    
    if not compose_file.exists():
        print_error(f"Docker Compose file not found: {compose_file}")
        return False
    
    compose_cmd = get_compose_cmd(runtime)
    if not compose_cmd:
        return False
    
    # Build and start services
    cmd = [
        *compose_cmd,
        "-f", str(compose_file),
    ]
    
    # Add --env-file if .env.local exists, otherwise docker-compose will use .env
    if env_file.exists():
        cmd.extend(["--env-file", str(env_file)])
    
    cmd.extend(["up", "-d", "--build"])
    
    print_info(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, cwd=infra_dir, check=True)
        print_success("Services started")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to start services: {e}")
        return False

def stop_services(mode: str, runtime: str, remove_volumes: bool = False) -> bool:
    """Stop services using compose down (optionally remove volumes)."""
    print_header(f"Stopping Services ({runtime})")
    root_dir = Path(__file__).parent
    infra_dir = root_dir / "infra"
    compose_file = infra_dir / f"docker-compose{'.prod' if mode == 'prod' else ''}.yml"
    env_file = infra_dir / ".env.local"

    compose_cmd = get_compose_cmd(runtime)
    if not compose_cmd:
        return False

    cmd = [*compose_cmd, "-f", str(compose_file)]
    if env_file.exists():
        cmd.extend(["--env-file", str(env_file)])
    cmd.append("down")
    if remove_volumes:
        cmd.append("-v")

    print_info(f"Running: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, cwd=infra_dir, check=True)
        print_success("Services stopped")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to stop services: {e}")
        return False

def run_migrations() -> bool:
    """Run database migrations."""
    print_header("Running Database Migrations")
    
    root_dir = Path(__file__).parent
    backend_dir = root_dir / "backend"
    
    # Find Python executable
    venv_path = find_venv()
    python_exe = get_python_executable(venv_path)
    
    cmd = [python_exe, "-m", "alembic", "upgrade", "head"]
    
    print_info(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, cwd=backend_dir, check=True)
        print_success("Migrations completed")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Migrations failed: {e}")
        return False

def find_venv() -> Optional[Path]:
    """Find virtual environment."""
    current_dir = Path.cwd()
    for venv_name in [".venv", "venv"]:
        venv_path = current_dir / venv_name
        if venv_path.exists():
            return venv_path
    return None

def get_python_executable(venv_path: Optional[Path] = None) -> str:
    """Get Python executable path."""
    if venv_path:
        system = platform.system()
        if system == "Windows":
            python_exe = venv_path / "Scripts" / "python.exe"
        else:
            python_exe = venv_path / "bin" / "python"
        
        if python_exe.exists():
            return str(python_exe)
    
    return sys.executable

def start_backend(mode: str):
    """Start backend server."""
    print_header("Starting Backend Server")
    print_info("Backend will start on http://localhost:8000")
    print_info("Press Ctrl+C to stop")
    print()
    
    root_dir = Path(__file__).parent
    backend_dir = root_dir / "backend"
    
    venv_path = find_venv()
    python_exe = get_python_executable(venv_path)
    
    # Set PYTHONPATH
    src_path = backend_dir / "src"
    pythonpath = str(src_path)
    existing_pythonpath = os.environ.get("PYTHONPATH", "")
    if existing_pythonpath:
        pythonpath = f"{pythonpath}{os.pathsep}{existing_pythonpath}"
    os.environ["PYTHONPATH"] = pythonpath
    
    cmd = [
        python_exe,
        "-m", "uvicorn",
        "src.primedata.api.app:app",
        "--reload" if mode == "dev" else "",
        "--host", "0.0.0.0",
        "--port", "8000"
    ]
    cmd = [c for c in cmd if c]  # Remove empty strings
    
    try:
        subprocess.run(cmd, cwd=backend_dir, check=True)
    except KeyboardInterrupt:
        print("\n" + "="*60)
        print_success("Shutting down...")
    except subprocess.CalledProcessError as e:
        print_error(f"Backend failed to start: {e}")
        sys.exit(1)

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="PrimeData Development/Production Wrapper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py dev              # Start in development mode
  python run.py dev --services-only    # Only start services (Docker/Podman)
  python run.py dev --skip-docker      # Skip services (already running) [legacy flag]
  python run.py dev --skip-migrations  # Skip database migrations
  python run.py prod             # Start in production mode
        """
    )
    parser.add_argument("mode", choices=["dev", "prod"], 
                       help="Run mode: dev or prod")
    parser.add_argument("--skip-docker", action="store_true", 
                       help="Skip starting services (legacy flag name)")
    parser.add_argument("--skip-migrations", action="store_true", 
                       help="Skip database migrations")
    parser.add_argument("--services-only", action="store_true", 
                       help="Only start services, don't start backend")
    parser.add_argument("--stop-services", action="store_true",
                       help="Stop services and exit")
    parser.add_argument("--clean-volumes", action="store_true",
                       help="Stop services, remove volumes, and exit (destructive)")
    
    args = parser.parse_args()
    
    print_header(f"PrimeData - {args.mode.upper()} Mode")
    
    runtime, hint = detect_container_runtime()
    if hint:
        print_info(hint)

    if not runtime:
        print_error("Neither Docker nor Podman was found.")
        print_info("Install Docker Desktop: https://docs.docker.com/get-docker/")
        print_info("Or install Podman Desktop: https://podman-desktop.io/")
        sys.exit(1)

    if not check_container_runtime(runtime):
        sys.exit(1)
    
    # Check .env.local files
    if not check_env_files(args.mode):
        print_warning("Continuing anyway... (make sure your .env.local files are configured)")
    
    if args.clean_volumes:
        if not stop_services(args.mode, runtime, remove_volumes=True):
            sys.exit(1)
        return

    if args.stop_services:
        if not stop_services(args.mode, runtime, remove_volumes=False):
            sys.exit(1)
        return

    # Start services (unless explicitly skipped)
    if not args.skip_docker:
        if not start_services(args.mode, runtime):
            print_error("Failed to start services")
            sys.exit(1)
    
    if args.services_only:
        print_success("Services started. Exiting.")
        return
    
    # Run migrations
    if not args.skip_migrations:
        print_info("Waiting for database to be ready...")
        time.sleep(5)
        
        if not run_migrations():
            print_warning("Migrations failed, but continuing...")
    
    # Start backend
    start_backend(args.mode)

if __name__ == "__main__":
    main()


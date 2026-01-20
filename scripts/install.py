#!/usr/bin/env python3
"""
PrimeData Cross-Platform Installer
Installs and configures PrimeData on Windows, macOS, and Linux
Usage: 
  Windows: python scripts\install.py
  macOS/Linux: python3 scripts/install.py
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path
from typing import Optional, List, Tuple


class Colors:
    """ANSI color codes for terminal output (works on Windows 10+)."""
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


def check_command(command: str, name: str, install_instructions: str) -> bool:
    """Check if a command is available."""
    if shutil.which(command):
        print_success(f"{name} is installed")
        return True
    else:
        print_error(f"{name} is not installed")
        print_info(f"Install: {install_instructions}")
        return False


def check_prerequisites() -> Tuple[bool, List[str]]:
    """Check if all prerequisites are met."""
    print_header("Checking Prerequisites")
    
    missing = []
    system = platform.system()
    
    # Check Python
    python_version = sys.version_info
    if python_version.major >= 3 and python_version.minor >= 11:
        print_success(f"Python {python_version.major}.{python_version.minor} is installed")
    else:
        print_error(f"Python 3.11+ required (found {python_version.major}.{python_version.minor})")
        if system == "Windows":
            missing.append("Install Python from https://www.python.org/downloads/")
        elif system == "Darwin":
            missing.append("Install Python: brew install python@3.11")
        else:
            missing.append("Install Python: sudo apt-get install python3.11 python3-venv python3-pip")
    
    # Check Node.js
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print_success(f"Node.js {result.stdout.strip()} is installed")
        else:
            raise FileNotFoundError
    except FileNotFoundError:
        print_error("Node.js is not installed")
        if system == "Windows":
            missing.append("Install Node.js from https://nodejs.org/")
        elif system == "Darwin":
            missing.append("Install Node.js: brew install node@18")
        else:
            missing.append("Install Node.js: curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash - && sudo apt-get install -y nodejs")
    
    # Check Docker or Podman
    docker_available = check_command("docker", "Docker", 
        "Install Docker Desktop from https://www.docker.com/products/docker-desktop" if system == "Windows" 
        else "Install Docker: sudo apt-get install docker.io" if system != "Darwin" 
        else "Install Docker Desktop from https://www.docker.com/products/docker-desktop")
    
    podman_available = check_command("podman", "Podman",
        "Install Podman Desktop from https://podman-desktop.io/" if system == "Windows"
        else "Install Podman: sudo apt-get install podman" if system != "Darwin"
        else "Install Podman Desktop from https://podman-desktop.io/")
    
    if not docker_available and not podman_available:
        missing.append("Install Docker or Podman (required for services)")
    
    # Check Git
    git_available = check_command("git", "Git",
        "Install Git from https://git-scm.com/downloads" if system == "Windows"
        else "Install Git: brew install git" if system == "Darwin"
        else "Install Git: sudo apt-get install git")
    
    if not git_available:
        missing.append("Install Git (recommended)")
    
    # Check bc on Linux (for memory monitoring)
    if system == "Linux":
        bc_available = check_command("bc", "bc (calculator)",
            "Install bc: sudo apt-get install bc")
        if not bc_available:
            print_warning("bc not installed - memory monitoring script may not work")
    
    return len(missing) == 0, missing


def setup_virtual_environment(root_dir: Path) -> Optional[Path]:
    """Create Python virtual environment."""
    print_header("Setting Up Python Virtual Environment")
    
    venv_path = root_dir / ".venv"
    
    if venv_path.exists():
        print_info("Virtual environment already exists")
        return venv_path
    
    print_info("Creating virtual environment...")
    try:
        subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
        print_success("Virtual environment created")
        return venv_path
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to create virtual environment: {e}")
        return None


def install_backend_dependencies(venv_path: Path, root_dir: Path) -> bool:
    """Install backend Python dependencies."""
    print_header("Installing Backend Dependencies")
    
    system = platform.system()
    if system == "Windows":
        pip_exe = venv_path / "Scripts" / "pip.exe"
    else:
        pip_exe = venv_path / "bin" / "pip"
    
    requirements_file = root_dir / "backend" / "requirements.txt"
    
    if not requirements_file.exists():
        print_error(f"requirements.txt not found: {requirements_file}")
        return False
    
    print_info("Installing Python packages...")
    try:
        subprocess.run([str(pip_exe), "install", "--upgrade", "pip"], check=True)
        subprocess.run([str(pip_exe), "install", "-r", str(requirements_file)], check=True)
        print_success("Backend dependencies installed")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to install backend dependencies: {e}")
        return False


def install_frontend_dependencies(root_dir: Path) -> bool:
    """Install frontend Node.js dependencies."""
    print_header("Installing Frontend Dependencies")
    
    ui_dir = root_dir / "ui"
    
    if not ui_dir.exists():
        print_error(f"UI directory not found: {ui_dir}")
        return False
    
    print_info("Installing Node.js packages...")
    try:
        subprocess.run(["npm", "install"], cwd=str(ui_dir), check=True)
        print_success("Frontend dependencies installed")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to install frontend dependencies: {e}")
        return False


def create_env_files(root_dir: Path) -> bool:
    """Create .env.local files from examples if they don't exist."""
    print_header("Creating Environment Files")
    
    env_files = [
        ("backend", "env.example", ".env.local"),
        ("infra", "env/services.example.env", ".env.local"),
        ("ui", "env.example.local", ".env.local"),
    ]
    
    created = False
    for base_dir, example_file, target_file in env_files:
        example_path = root_dir / base_dir / example_file
        target_path = root_dir / base_dir / target_file
        
        if target_path.exists():
            print_info(f"{target_path} already exists (skipping)")
            continue
        
        if example_path.exists():
            try:
                shutil.copy(example_path, target_path)
                print_success(f"Created {target_path} from {example_file}")
                print_warning(f"Please edit {target_path} with your configuration")
                created = True
            except Exception as e:
                print_error(f"Failed to create {target_path}: {e}")
        else:
            print_warning(f"Example file not found: {example_path}")
    
    if created:
        print_warning("⚠️  IMPORTANT: Edit the .env.local files with your configuration before running the application!")
    
    return True


def main():
    """Main installation function."""
    print_header("PrimeData Installer")
    print_info(f"Platform: {platform.system()} {platform.release()}")
    print_info(f"Python: {sys.version}")
    
    root_dir = Path(__file__).parent.parent
    
    # Check prerequisites
    prerequisites_met, missing = check_prerequisites()
    if not prerequisites_met:
        print_error("\n❌ Some prerequisites are missing:")
        for item in missing:
            print(f"   - {item}")
        print("\nPlease install the missing prerequisites and run the installer again.")
        sys.exit(1)
    
    print_success("\n✅ All prerequisites are met!")
    
    # Setup virtual environment
    venv_path = setup_virtual_environment(root_dir)
    if not venv_path:
        print_error("Failed to create virtual environment. Exiting.")
        sys.exit(1)
    
    # Install backend dependencies
    if not install_backend_dependencies(venv_path, root_dir):
        print_error("Failed to install backend dependencies. Exiting.")
        sys.exit(1)
    
    # Install frontend dependencies
    if not install_frontend_dependencies(root_dir):
        print_error("Failed to install frontend dependencies. Exiting.")
        sys.exit(1)
    
    # Create environment files
    create_env_files(root_dir)
    
    # Final instructions
    print_header("Installation Complete!")
    print_success("✅ PrimeData has been installed successfully!")
    print("\n📋 Next Steps:")
    print("\n1. Configure environment variables:")
    print("   - Edit backend/.env.local")
    print("   - Edit infra/.env.local")
    print("   - Edit ui/.env.local")
    print("\n2. Start services:")
    system = platform.system()
    if system == "Windows":
        print("   python run.py dev --services-only")
    else:
        print("   python run.py dev --services-only  (recommended)")
        print("   # If you use Podman on macOS/Linux, run:")
        print("   #   CONTAINER_RUNTIME=podman python run.py dev --services-only")
        print("   # Or: make services")
    print("\n3. Run database migrations:")
    if system == "Windows":
        python_exe = venv_path / "Scripts" / "python.exe"
        print(f"   {python_exe} -m alembic upgrade head")
    else:
        python_exe = venv_path / "bin" / "python"
        print(f"   {python_exe} -m alembic upgrade head")
    print("\n4. Start the application:")
    if system == "Windows":
        print("   Terminal 1: python start_backend.py")
        print("   Terminal 2: cd ui && npm run dev")
    else:
        print("   Terminal 1: make backend")
        print("   Terminal 2: make frontend")
    print("\n📚 For more information, see README.md")
    print()


if __name__ == "__main__":
    main()

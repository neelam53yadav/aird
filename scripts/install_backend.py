#!/usr/bin/env python3
"""
Helper script to install backend dependencies.
Cross-platform script that handles virtual environment creation and dependency installation.
"""
import subprocess
import sys
from pathlib import Path


def main():
    """Install backend dependencies in virtual environment or system Python."""
    root_dir = Path(__file__).parent.parent
    backend_dir = root_dir / "backend"
    requirements_file = backend_dir / "requirements.txt"
    
    if not requirements_file.exists():
        print(f"Error: requirements.txt not found at {requirements_file}")
        sys.exit(1)
    
    # Find or create venv
    venv_path = None
    for venv_name in ['.venv', 'venv']:
        venv = root_dir / venv_name
        if venv.exists():
            venv_path = venv
            print(f"Found virtual environment: {venv_path}")
            break
    
    if not venv_path:
        print("Creating Python virtual environment...")
        venv_path = root_dir / '.venv'
        try:
            subprocess.run(
                [sys.executable, '-m', 'venv', str(venv_path)],
                check=True,
                cwd=str(root_dir)
            )
            print(f"Created virtual environment: {venv_path}")
        except subprocess.CalledProcessError as e:
            print(f"Error creating virtual environment: {e}")
            sys.exit(1)
    
    # Determine pip executable
    if sys.platform == 'win32':
        pip_exe = venv_path / 'Scripts' / 'pip.exe'
        python_exe = venv_path / 'Scripts' / 'python.exe'
    else:
        pip_exe = venv_path / 'bin' / 'pip'
        python_exe = venv_path / 'bin' / 'python'
    
    if not pip_exe.exists():
        print("Warning: pip not found in venv, using system pip")
        pip_cmd = [sys.executable, '-m', 'pip']
    else:
        pip_cmd = [str(pip_exe)]
        print(f"Using pip from virtual environment: {pip_exe}")
    
    # Install dependencies
    try:
        print(f"Installing dependencies from {requirements_file}...")
        subprocess.run(
            pip_cmd + ['install', '-r', str(requirements_file)],
            check=True,
            cwd=str(root_dir)
        )
        print("✅ Backend dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()


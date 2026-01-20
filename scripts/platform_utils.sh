#!/bin/bash
# Platform detection utilities for PrimeData scripts
# Provides cross-platform detection functions for macOS and Linux
# Usage: source scripts/platform_utils.sh

# Detect OS type
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]] || [[ "$OSTYPE" == "linux"* ]]; then
        echo "linux"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "win32" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

# Detect CPU architecture
detect_arch() {
    local os=$(detect_os)
    
    if [[ "$os" == "macos" ]]; then
        # macOS: uname -m returns arm64 for Apple Silicon, x86_64 for Intel
        uname -m
    elif [[ "$os" == "linux" ]]; then
        # Linux: uname -m returns x86_64, aarch64, armv7l, etc.
        uname -m
    else
        # Fallback for other platforms
        uname -m 2>/dev/null || echo "unknown"
    fi
}

# Detect container runtime (Docker or Podman)
detect_container_runtime() {
    if command -v docker > /dev/null 2>&1 && docker info > /dev/null 2>&1; then
        echo "docker"
    elif command -v podman > /dev/null 2>&1 && podman info > /dev/null 2>&1; then
        echo "podman"
    else
        echo "none"
    fi
}

# Check if a command is available
command_exists() {
    command -v "$1" > /dev/null 2>&1
}

# Get platform-specific Python executable path (for virtual environments)
get_python_executable() {
    local venv_path="$1"
    local os=$(detect_os)
    
    if [[ -z "$venv_path" ]]; then
        # No venv path provided, use system Python
        if command_exists python3; then
            echo "python3"
        elif command_exists python; then
            echo "python"
        else
            echo ""
        fi
        return
    fi
    
    if [[ "$os" == "windows" ]]; then
        # Windows: venv/Scripts/python.exe
        local python_exe="${venv_path}/Scripts/python.exe"
        if [[ -f "$python_exe" ]]; then
            echo "$python_exe"
        else
            echo ""
        fi
    else
        # Unix-like (macOS/Linux): venv/bin/python
        local python_exe="${venv_path}/bin/python"
        if [[ -f "$python_exe" ]]; then
            echo "$python_exe"
        else
            echo ""
        fi
    fi
}

# Get platform-specific pip executable path (for virtual environments)
get_pip_executable() {
    local venv_path="$1"
    local os=$(detect_os)
    
    if [[ -z "$venv_path" ]]; then
        # No venv path provided, use system pip
        if command_exists pip3; then
            echo "pip3"
        elif command_exists pip; then
            echo "pip"
        else
            echo ""
        fi
        return
    fi
    
    if [[ "$os" == "windows" ]]; then
        # Windows: venv/Scripts/pip.exe
        local pip_exe="${venv_path}/Scripts/pip.exe"
        if [[ -f "$pip_exe" ]]; then
            echo "$pip_exe"
        else
            echo ""
        fi
    else
        # Unix-like (macOS/Linux): venv/bin/pip
        local pip_exe="${venv_path}/bin/pip"
        if [[ -f "$pip_exe" ]]; then
            echo "$pip_exe"
        else
            echo ""
        fi
    fi
}

# Check if running in a virtual environment
is_in_venv() {
    if [[ -n "${VIRTUAL_ENV:-}" ]]; then
        echo "true"
    else
        echo "false"
    fi
}

# Get the compose command (docker compose or docker-compose)
get_compose_cmd() {
    local runtime="${1:-$(detect_container_runtime)}"
    
    if [[ "$runtime" == "podman" ]]; then
        if command_exists podman && podman compose version > /dev/null 2>&1; then
            echo "podman compose"
        elif command_exists podman-compose; then
            echo "podman-compose"
        else
            echo ""
        fi
    elif [[ "$runtime" == "docker" ]]; then
        if command_exists docker && docker compose version > /dev/null 2>&1; then
            echo "docker compose"
        elif command_exists docker-compose; then
            echo "docker-compose"
        else
            echo ""
        fi
    else
        echo ""
    fi
}

# Check if bc (calculator) is available (needed for memory calculations)
check_bc_available() {
    if command_exists bc; then
        echo "true"
    else
        echo "false"
    fi
}

# Print platform information (useful for debugging)
print_platform_info() {
    echo "Platform Information:"
    echo "  OS: $(detect_os)"
    echo "  Architecture: $(detect_arch)"
    echo "  Container Runtime: $(detect_container_runtime)"
    echo "  In Virtual Environment: $(is_in_venv)"
    echo "  Python Available: $(command_exists python3 && echo 'yes' || echo 'no')"
    echo "  Docker Available: $(command_exists docker && echo 'yes' || echo 'no')"
    echo "  Podman Available: $(command_exists podman && echo 'yes' || echo 'no')"
    echo "  bc Available: $(check_bc_available)"
}

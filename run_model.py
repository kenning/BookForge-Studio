#!/usr/bin/env python3
"""
Model Runner Script

Usage: python run_model.py <model_name>
Example: python run_model.py dia

This script will:
1. Check if the model exists
2. Create a virtual environment if needed
3. Install dependencies
4. Run the model service
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path


def get_python_executable():
    """Find the best Python 3.10+ executable."""
    # Try different Python executables in order of preference
    candidates = ["python3.10", "python3.11", "python3.12", "python3", "python"]

    for candidate in candidates:
        try:
            result = subprocess.run(
                [candidate, "--version"], capture_output=True, text=True, check=True
            )
            version_line = result.stdout.strip()
            if "Python 3.1" in version_line:  # 3.10, 3.11, 3.12, etc.
                return candidate
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue

    # Fallback - try current Python
    if sys.version_info >= (3, 10):
        return sys.executable

    print("Error: Python 3.10+ not found.")
    print("Please install Python 3.10 or later and try again.")
    sys.exit(1)


def get_venv_paths(model_dir):
    """Get virtual environment paths for the current platform."""
    venv_dir = model_dir / "venv"

    if platform.system() == "Windows":
        python_exe = venv_dir / "Scripts" / "python.exe"
        pip_exe = venv_dir / "Scripts" / "pip.exe"
    else:
        python_exe = venv_dir / "bin" / "python"
        pip_exe = venv_dir / "bin" / "pip"

    return venv_dir, python_exe, pip_exe


def create_venv(model_dir, python_exe):
    """Create virtual environment."""
    venv_dir, _, _ = get_venv_paths(model_dir)

    print(f"Creating virtual environment at {venv_dir}")

    try:
        subprocess.run([python_exe, "-m", "venv", str(venv_dir)], check=True)
        print("Virtual environment created successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to create virtual environment: {e}")
        return False


def check_venv_health(model_dir):
    """Check if the virtual environment is healthy (has pip)."""
    _, python_exe, _ = get_venv_paths(model_dir)

    try:
        # Test if pip is available
        result = subprocess.run(
            [str(python_exe), "-m", "pip", "--version"],
            capture_output=True,
            cwd=model_dir,
        )
        return result.returncode == 0
    except Exception:
        return False


def install_dependencies(model_dir):
    """Install dependencies in the virtual environment."""
    _, python_exe, pip_exe = get_venv_paths(model_dir)
    requirements_file = model_dir / "requirements.txt"

    if not requirements_file.exists():
        print(f"Requirements file not found: {requirements_file}")
        return False

    print("Installing dependencies...")

    try:
        # Upgrade pip first
        subprocess.run(
            [str(python_exe), "-m", "pip", "install", "--upgrade", "pip"],
            check=True,
            cwd=model_dir,
        )

        # Install PyTorch with CUDA support on Windows
        if platform.system() == "Windows":
            print("Installing PyTorch with CUDA support for Windows...")
            subprocess.run([
                str(pip_exe), "install", 
                "torch", "torchvision", "torchaudio", 
                "--index-url", "https://download.pytorch.org/whl/cu118"
            ], check=True, cwd=model_dir)
        else:
            # On Linux/Mac, default installation usually works
            subprocess.run([
                str(pip_exe), "install", "torch", "torchvision", "torchaudio"
            ], check=True, cwd=model_dir)

        # Install requirements
        subprocess.run(
            [str(pip_exe), "install", "-r", "requirements.txt"],
            check=True,
            cwd=model_dir,
        )

        print("Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to install dependencies: {e}")
        return False


def run_service(model_dir, service_file, extra_args=None):
    """Run the model service."""
    _, python_exe, _ = get_venv_paths(model_dir)

    if extra_args is None:
        extra_args = []

    print(f"Starting {service_file.stem} service...")
    if extra_args:
        print(f"Additional arguments: {' '.join(extra_args)}")
    print("Press Ctrl+C to stop the service (service is still starting)")
    print("-" * 50)

    try:
        # Run the service with extra arguments
        cmd = [str(python_exe), str(service_file)] + extra_args
        subprocess.run(cmd, cwd=model_dir, check=True)
    except KeyboardInterrupt:
        print("\nService stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"Service failed: {e}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_model.py <model_name> [additional_args...]")
        print("Example: python run_model.py dia")
        print("Example: python run_model.py mock --fast-delay")
        sys.exit(1)

    model_name = sys.argv[1]
    extra_args = sys.argv[2:]  # Pass through any additional arguments
    script_dir = Path(__file__).parent
    model_dir = script_dir / "models" / model_name

    # Check if model exists
    if not model_dir.exists():
        print(f"Model '{model_name}' not found in models/ directory")
        available_models = [
            d.name for d in (script_dir / "models").iterdir() if d.is_dir()
        ]
        if available_models:
            print(f"Available models: {', '.join(available_models)}")
        sys.exit(1)

    # Find service file
    service_files = list(model_dir.glob("*_service.py"))
    if not service_files:
        print(f"No service file found in {model_dir}")
        print("Expected a file ending with '_service.py'")
        sys.exit(1)

    service_file = service_files[0]
    venv_dir, python_exe, pip_exe = get_venv_paths(model_dir)

    print(f"Setting up {model_name} model")
    print(f"Model directory: {model_dir}")

    # Find Python executable
    system_python = get_python_executable()
    print(f"Using Python: {system_python}")

    # Check if venv exists and is healthy
    if not venv_dir.exists():
        print("Virtual environment not found, creating...")
        if not create_venv(model_dir, system_python):
            sys.exit(1)
    else:
        print("Virtual environment found, checking health...")
        if not check_venv_health(model_dir):
            print("Virtual environment is corrupted, recreating...")
            import shutil

            shutil.rmtree(venv_dir)
            if not create_venv(model_dir, system_python):
                sys.exit(1)
        else:
            print("Virtual environment is healthy")

    # Check if dependencies are installed
    requirements_file = model_dir / "requirements.txt"
    if requirements_file.exists():
        try:
            # Quick check if main dependencies are installed
            result = subprocess.run(
                [str(python_exe), "-c", "import fastapi, transformers"],
                capture_output=True,
                cwd=model_dir,
            )
            if result.returncode != 0:
                print("Dependencies missing or outdated, installing...")
                if not install_dependencies(model_dir):
                    sys.exit(1)
            else:
                print("Dependencies already installed")
        except Exception:
            print("Installing dependencies...")
            if not install_dependencies(model_dir):
                sys.exit(1)

    # Special handling for vibevoice model - install flash_attn
    if model_name == "vibevoice":
        _, python_exe, pip_exe = get_venv_paths(model_dir)
        print("Installing flash_attn for vibevoice model...")
        try:
            subprocess.run(
                [str(pip_exe), "install", "flash-attn>=2.0", "--no-build-isolation"],
                check=True,
                cwd=model_dir,
            )
            print("flash_attn installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"Warning: Failed to install flash_attn: {e}")
            print("The service may still work, but performance might be reduced")

    # Run the service
    run_service(model_dir, service_file, extra_args)


if __name__ == "__main__":
    main()

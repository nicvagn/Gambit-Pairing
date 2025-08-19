#!/usr/bin/env python3
import importlib.util
import subprocess
import sys
import tomllib


def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"Running: {description}")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout.strip())
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error {description}: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr.strip()}")
        return False
    except FileNotFoundError:
        print(f"Command not found: {cmd[0]}")
        return False


def load_pyproject_dependencies():
    """Load dependencies from pyproject.toml"""
    try:
        with open("pyproject.toml", "rb") as f:
            data = tomllib.load(f)
        # Get main dependencies
        dependencies = data.get("project", {}).get("dependencies", [])
        # Get dev dependencies
        dev_dependencies = (
            data.get("project", {}).get("optional-dependencies", {}).get("dev", [])
        )
        return dependencies, dev_dependencies
    except FileNotFoundError:
        print("Error: pyproject.toml not found in current directory")
        return None, None
    except Exception as e:
        print(f"Error reading pyproject.toml: {e}")
        return None, None


def main():
    # Ensure pip is up to date
    print("Ensuring pip is up to date")
    if not run_command(
        [sys.executable, "-m", "ensurepip", "--upgrade"], "updating pip"
    ):
        sys.exit(1)

    black = importlib.util.find_spec("black")
    isort = importlib.util.find_spec("isort")
    if not black or not isort:
        # Load dependencies from pyproject.toml
        dependencies, dev_dependencies = load_pyproject_dependencies()
        if dependencies is None:
            sys.exit(1)

        # Install main dependencies
        if dependencies:
            print("Installing dependencies")
            cmd = [sys.executable, "-m", "pip", "install"] + dependencies
            if not run_command(cmd, "installing main dependencies"):
                sys.exit(1)
        else:
            print("No main dependencies found")

        # Install dev dependencies
        if dev_dependencies:
            print("Installing dev dependencies")
            cmd = [sys.executable, "-m", "pip", "install"] + dev_dependencies
            if not run_command(cmd, "installing dev dependencies"):
                sys.exit(1)
        else:
            print("No dev dependencies found")

    # Run formatters - exit if they fail
    if not run_command([sys.executable, "-m", "isort", "src"], "Formatting with isort"):
        print("isort failed. Ensure current working dir is git root")
        sys.exit(1)
    print("------- isort ran ----------")

    if not run_command([sys.executable, "-m", "black", "src"], "Formatting with black"):
        print("black failed. Ensure current working dir is git root")
        sys.exit(1)
    print("------- black ran ----------")

    print("----- src formatted --------")
    print("--- Hint: ensure new formatted files are added to any commit. ---")


if __name__ == "__main__":
    main()

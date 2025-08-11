#!/usr/bin/env python3

import os
import subprocess
import sys
from pathlib import Path


def main():
    # Get the directory where this script is located
    script_dir = Path(__file__).parent.absolute()

    print("Ensuring dependencies")

    # Run the dependency script
    dependency_script = script_dir / "ensure_all_dependencies.py"
    try:
        subprocess.run([sys.executable, str(dependency_script)], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running dependency script: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"Dependency script not found: {dependency_script}")
        sys.exit(1)

    print("Installing with pyinstaller")

    # Run pyinstaller with the spec file
    spec_file = script_dir / "gambit-pairing.spec"
    try:
        subprocess.run(["pyinstaller", str(spec_file)], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running pyinstaller: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("pyinstaller not found. Make sure it's installed and in your PATH")
        sys.exit(1)

    print("Build completed successfully!")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Cross-platform formatting script that doesn't rely on any shell interpreter.
"""
import subprocess
import sys
from pathlib import Path


def main():
    # Get the script directory (where this script is located)
    script_dir = Path(__file__).parent.resolve()

    # Define paths
    formatting_script = script_dir / "src/gambitpairing/resources/scripts/formatting.py"
    target_dir = script_dir / "src/gambitpairing"

    # Verify the formatting script exists
    if not formatting_script.exists():
        print(
            f"Error: Formatting script not found at {formatting_script}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Run the formatting command
    try:
        result = subprocess.run(
            [
                sys.executable,  # Use the same Python interpreter
                str(formatting_script),
                "--target",
                str(target_dir),
            ],
            check=True,
        )

        print("Formatting completed successfully!")
        sys.exit(result)
    except subprocess.CalledProcessError as e:
        print(f"Formatting failed with exit code {e.returncode}", file=sys.stderr)
        sys.exit(e.returncode)
    except FileNotFoundError:
        print("Error: Python interpreter not found", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

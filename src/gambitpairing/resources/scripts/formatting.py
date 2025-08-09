#!/usr/bin/env python3
"""
Formatting script for the project.
Runs black, isort, and optionally other formatters.
"""


import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a shell command and handle errors."""
    print(f"Running {description}...")
    try:
        result = subprocess.run(
            cmd, shell=True, check=True, capture_output=True, text=True
        )
        print(f"NICE! {description} completed successfully")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"SAD! {description} failed:")
        print(e.stderr)
        return False


def format_code(check_only=False, target_dir="."):
    """Format code using black and isort."""
    success = True

    # Black formatting
    black_cmd = f"black {'--check --diff' if check_only else ''} {target_dir}"
    if not run_command(black_cmd, "Black formatting"):
        success = False

    # Import sorting with isort
    isort_cmd = f"isort {'--check-only --diff' if check_only else ''} {target_dir}"
    if not run_command(isort_cmd, "Import sorting"):
        success = False

    return success


def lint_code(target_dir="."):
    """Run linting tools."""
    success = True

    # Ruff linting (if available)
    if run_command("which ruff", "Checking for ruff") or run_command(
        "where ruff", "Checking for ruff"
    ):
        if not run_command(f"ruff check {target_dir}", "Ruff linting"):
            success = False
    else:
        # Fallback to flake8
        if not run_command(f"flake8 {target_dir}", "Flake8 linting"):
            success = False

    return success


def format():
    """Main entry point for the formatting script."""
    parser = argparse.ArgumentParser(description="Format and lint Python code")
    parser.add_argument(
        "--check", action="store_true", help="Check formatting without making changes"
    )
    parser.add_argument(
        "--lint", action="store_true", help="Run linting in addition to formatting"
    )
    parser.add_argument(
        "--target",
        default=".",
        help="Target directory to format (default: current directory)",
    )

    args = parser.parse_args()

    print("Starting code formatting...")

    # Format code
    format_success = format_code(check_only=args.check, target_dir=args.target)

    # Optionally run linting
    lint_success = True
    if args.lint:
        lint_success = lint_code(target_dir=args.target)

    # Summary
    if format_success and lint_success:
        action = "checked" if args.check else "formatted"
        print(f"Code successfully {action}!")
        sys.exit(0)
    else:
        print("Some operations failed. Please review the output above.")
        sys.exit(1)


if __name__ == "__main__":
    format()

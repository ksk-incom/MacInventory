"""Prerequisites checker for MacInventory.

Verifies required and optional tools are available before running inventory.

Usage:
    # As script with JSON output (for agents)
    python3 check_prerequisites.py --json

    # As script with human-readable output
    python3 check_prerequisites.py

    # As module
    from utils.check_prerequisites import check_all_prerequisites
    results = check_all_prerequisites()
"""

import subprocess
import json
import sys
import re
from typing import Optional


def check_python3() -> tuple[bool, Optional[str], Optional[str]]:
    """Check Python 3 availability and version.

    Returns:
        Tuple of (is_available, version, error_message)
    """
    try:
        result = subprocess.run(
            ["python3", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            # Output format: "Python 3.12.1"
            output = result.stdout.strip() or result.stderr.strip()
            match = re.search(r"Python (\d+\.\d+(?:\.\d+)?)", output)
            version = match.group(1) if match else output
            return True, version, None
        return False, None, "python3 returned non-zero exit code"
    except FileNotFoundError:
        return False, None, "python3 not found"
    except subprocess.TimeoutExpired:
        return False, None, "Timeout checking Python version"
    except Exception as e:
        return False, None, f"Error: {e}"


def check_pyyaml() -> tuple[bool, Optional[str], Optional[str]]:
    """Check PyYAML availability and version.

    Returns:
        Tuple of (is_available, version, error_message)
    """
    try:
        result = subprocess.run(
            ["python3", "-c", "import yaml; print(yaml.__version__)"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            return True, version, None
        # Check if it's an import error
        stderr = result.stderr.strip()
        if "ModuleNotFoundError" in stderr or "ImportError" in stderr:
            return False, None, "PyYAML not installed"
        return False, None, stderr or "Unknown error"
    except FileNotFoundError:
        return False, None, "python3 not found"
    except subprocess.TimeoutExpired:
        return False, None, "Timeout checking PyYAML"
    except Exception as e:
        return False, None, f"Error: {e}"


def check_homebrew() -> tuple[bool, Optional[str], Optional[str]]:
    """Check Homebrew availability and version.

    Returns:
        Tuple of (is_available, version, error_message)
    """
    try:
        result = subprocess.run(
            ["brew", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            # Output format: "Homebrew 4.4.0"
            output = result.stdout.strip().split("\n")[0]
            match = re.search(r"Homebrew (\d+\.\d+(?:\.\d+)?)", output)
            version = match.group(1) if match else output
            return True, version, None
        return False, None, "brew returned non-zero exit code"
    except FileNotFoundError:
        return False, None, "Homebrew not installed"
    except subprocess.TimeoutExpired:
        return False, None, "Timeout checking Homebrew"
    except Exception as e:
        return False, None, f"Error: {e}"


def check_mas() -> tuple[bool, Optional[str], Optional[str]]:
    """Check mas (Mac App Store CLI) availability and version.

    Returns:
        Tuple of (is_available, version, error_message)
    """
    try:
        result = subprocess.run(
            ["mas", "version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            return True, version, None
        return False, None, "mas returned non-zero exit code"
    except FileNotFoundError:
        return False, None, "mas not installed"
    except subprocess.TimeoutExpired:
        return False, None, "Timeout checking mas"
    except Exception as e:
        return False, None, f"Error: {e}"


def check_all_prerequisites() -> dict:
    """Run all prerequisite checks and return structured results.

    Returns:
        Dictionary with status, checks, and summary
    """
    checks = {}

    # Required tools
    available, version, error = check_python3()
    checks["python3"] = {
        "available": available,
        "version": version,
        "error": error,
        "required": True,
        "install_cmd": "Pre-installed on macOS (or install via brew install python)"
    }

    available, version, error = check_pyyaml()
    checks["pyyaml"] = {
        "available": available,
        "version": version,
        "error": error,
        "required": True,
        "install_cmd": "pip3 install pyyaml"
    }

    # Optional tools
    available, version, error = check_homebrew()
    checks["homebrew"] = {
        "available": available,
        "version": version,
        "error": error,
        "required": False,
        "install_cmd": '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
    }

    available, version, error = check_mas()
    checks["mas"] = {
        "available": available,
        "version": version,
        "error": error,
        "required": False,
        "install_cmd": "brew install mas"
    }

    # Calculate summary
    total = len(checks)
    available_count = sum(1 for c in checks.values() if c["available"])
    missing_required = [name for name, c in checks.items() if c["required"] and not c["available"]]
    missing_optional = [name for name, c in checks.items() if not c["required"] and not c["available"]]

    # Determine overall status
    if missing_required:
        status = "missing_required"
    elif missing_optional:
        status = "missing_optional"
    else:
        status = "ready"

    return {
        "status": status,
        "checks": checks,
        "summary": {
            "total": total,
            "available": available_count,
            "missing_required": len(missing_required),
            "missing_optional": len(missing_optional)
        }
    }


def format_human_readable(results: dict) -> str:
    """Format results for human-readable output.

    Args:
        results: Results dictionary from check_all_prerequisites()

    Returns:
        Formatted string for terminal output
    """
    lines = ["Prerequisites Check", "=" * 19]

    # Required tools
    lines.append("\nRequired:")
    for name in ["python3", "pyyaml"]:
        check = results["checks"][name]
        if check["available"]:
            lines.append(f"  [OK] {name.title()} {check['version']}")
        else:
            lines.append(f"  [--] {name.title()} (install: {check['install_cmd']})")

    # Optional tools
    lines.append("\nOptional:")
    for name in ["homebrew", "mas"]:
        check = results["checks"][name]
        if check["available"]:
            lines.append(f"  [OK] {name.title()} {check['version']}")
        else:
            lines.append(f"  [--] {name.title()} (install: {check['install_cmd']})")

    # Status
    status = results["status"]
    if status == "ready":
        lines.append("\nStatus: Ready to proceed")
    elif status == "missing_optional":
        lines.append("\nStatus: Ready (some optional tools missing)")
    else:
        lines.append("\nStatus: Missing required tools - install them before continuing")

    return "\n".join(lines)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Check MacInventory prerequisites"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON for machine parsing"
    )

    args = parser.parse_args()
    results = check_all_prerequisites()

    if args.json:
        # Clean up None values for JSON output
        for check in results["checks"].values():
            if check["version"] is None:
                del check["version"]
            if check["error"] is None:
                del check["error"]
        print(json.dumps(results, indent=2))
    else:
        print(format_human_readable(results))

    # Exit with error code if required tools are missing
    sys.exit(0 if results["status"] != "missing_required" else 1)

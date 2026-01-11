"""Scanner for Homebrew packages and Mac App Store applications.

Scans brew list (formulae and casks), brew tap, and mas list for
comprehensive package inventory.
"""

import subprocess
from typing import Optional


def _run_command(cmd: list[str], timeout: int = 60) -> Optional[str]:
    """Run a command and return its stdout, or None on failure.

    Args:
        cmd: Command and arguments as a list
        timeout: Timeout in seconds

    Returns:
        stdout as string, or None if command failed
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def _check_homebrew_installed() -> bool:
    """Check if Homebrew is installed and accessible."""
    return _run_command(["brew", "--version"]) is not None


def scan_formulae() -> dict:
    """Scan installed Homebrew formulae.

    Returns:
        Dictionary with 'formulae' list containing package info
    """
    formulae = []
    errors = []

    if not _check_homebrew_installed():
        return {
            "formulae": [],
            "count": 0,
            "errors": [{"error": "Homebrew not installed"}],
        }

    # Get list of installed formulae with versions
    output = _run_command(["brew", "list", "--formula", "--versions"])
    if output is None:
        errors.append({"error": "Failed to run 'brew list --formula'"})
    else:
        for line in output.split("\n"):
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 2:
                name = parts[0]
                versions = parts[1:]  # Some packages have multiple versions
                formulae.append(
                    {
                        "name": name,
                        "version": versions[0] if versions else None,
                        "all_versions": versions,
                    }
                )
            elif len(parts) == 1:
                formulae.append(
                    {
                        "name": parts[0],
                        "version": None,
                        "all_versions": [],
                    }
                )

    return {
        "formulae": formulae,
        "count": len(formulae),
        "errors": errors,
    }


def scan_casks() -> dict:
    """Scan installed Homebrew casks.

    Returns:
        Dictionary with 'casks' list containing package info
    """
    casks = []
    errors = []

    if not _check_homebrew_installed():
        return {
            "casks": [],
            "count": 0,
            "errors": [{"error": "Homebrew not installed"}],
        }

    # Get list of installed casks with versions
    output = _run_command(["brew", "list", "--cask", "--versions"])
    if output is None:
        errors.append({"error": "Failed to run 'brew list --cask'"})
    else:
        for line in output.split("\n"):
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 2:
                name = parts[0]
                version = parts[1]
                casks.append(
                    {
                        "name": name,
                        "version": version,
                    }
                )
            elif len(parts) == 1:
                casks.append(
                    {
                        "name": parts[0],
                        "version": None,
                    }
                )

    return {
        "casks": casks,
        "count": len(casks),
        "errors": errors,
    }


def scan_taps() -> dict:
    """Scan tapped Homebrew repositories.

    Returns:
        Dictionary with 'taps' list
    """
    taps = []
    errors = []

    if not _check_homebrew_installed():
        return {
            "taps": [],
            "count": 0,
            "errors": [{"error": "Homebrew not installed"}],
        }

    output = _run_command(["brew", "tap"])
    if output is None:
        errors.append({"error": "Failed to run 'brew tap'"})
    else:
        for line in output.split("\n"):
            tap = line.strip()
            if tap:
                taps.append(tap)

    return {
        "taps": taps,
        "count": len(taps),
        "errors": errors,
    }


def scan_mas() -> dict:
    """Scan Mac App Store applications installed via mas CLI.

    Requires mas to be installed (brew install mas).

    Returns:
        Dictionary with 'apps' list containing app ID, name, and version
    """
    apps = []
    errors = []

    # Check if mas is installed
    if _run_command(["mas", "version"]) is None:
        return {
            "apps": [],
            "count": 0,
            "errors": [{"error": "mas CLI not installed (brew install mas)"}],
        }

    # Get list of installed MAS apps
    output = _run_command(["mas", "list"])
    if output is None:
        errors.append({"error": "Failed to run 'mas list'"})
    else:
        for line in output.split("\n"):
            if not line.strip():
                continue

            # Format: "123456789  App Name (1.2.3)"
            parts = line.split(maxsplit=1)
            if len(parts) >= 2:
                app_id = parts[0]
                rest = parts[1]

                # Extract version from parentheses at end
                version = None
                name = rest
                if rest.endswith(")") and "(" in rest:
                    paren_idx = rest.rfind("(")
                    name = rest[:paren_idx].strip()
                    version = rest[paren_idx + 1 : -1]

                apps.append(
                    {
                        "id": app_id,
                        "name": name,
                        "version": version,
                    }
                )
            elif len(parts) == 1:
                apps.append(
                    {
                        "id": parts[0],
                        "name": None,
                        "version": None,
                    }
                )

    return {
        "apps": apps,
        "count": len(apps),
        "errors": errors,
    }


def scan() -> dict:
    """Scan all Homebrew-related package sources.

    Combines results from formulae, casks, and taps.

    Returns:
        Dictionary with all Homebrew package information
    """
    formulae_result = scan_formulae()
    casks_result = scan_casks()
    taps_result = scan_taps()

    return {
        "formulae": formulae_result["formulae"],
        "formulae_count": formulae_result["count"],
        "casks": casks_result["casks"],
        "casks_count": casks_result["count"],
        "taps": taps_result["taps"],
        "taps_count": taps_result["count"],
        "errors": formulae_result["errors"] + casks_result["errors"] + taps_result["errors"],
    }


if __name__ == "__main__":
    import json

    print("=== Homebrew Scan ===")
    result = scan()
    print(json.dumps(result, indent=2))

    print("\n=== Mac App Store Scan ===")
    mas_result = scan_mas()
    print(json.dumps(mas_result, indent=2))

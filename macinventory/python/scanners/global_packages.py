"""Scanner for globally installed packages (npm -g, pip, cargo, gem).

Scans for globally installed packages across various package managers.
"""

import subprocess
import json as json_lib
from pathlib import Path
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


def _check_command_exists(cmd: str) -> bool:
    """Check if a command exists in PATH."""
    return _run_command(["which", cmd]) is not None


def scan_npm_global() -> dict:
    """Scan globally installed npm packages.

    Returns:
        Dictionary with 'packages' list
    """
    result = {
        "installed": False,
        "packages": [],
        "errors": [],
    }

    if not _check_command_exists("npm"):
        return result

    result["installed"] = True

    # Get global packages in JSON format
    output = _run_command(["npm", "list", "-g", "--depth=0", "--json"])
    if output is None:
        # Try without JSON (older npm versions)
        output = _run_command(["npm", "list", "-g", "--depth=0"])
        if output:
            for line in output.split("\n"):
                line = line.strip()
                if "@" in line and not line.startswith("/"):
                    # Parse "package@version" format
                    # Handle scoped packages like @org/package@version
                    if line.startswith("├──") or line.startswith("└──"):
                        line = line.replace("├──", "").replace("└──", "").strip()

                    at_idx = line.rfind("@")
                    if at_idx > 0:
                        name = line[:at_idx]
                        version = line[at_idx + 1 :]
                        result["packages"].append(
                            {
                                "name": name,
                                "version": version,
                            }
                        )
    else:
        try:
            data = json_lib.loads(output)
            dependencies = data.get("dependencies", {})
            for name, info in dependencies.items():
                if isinstance(info, dict):
                    result["packages"].append(
                        {
                            "name": name,
                            "version": info.get("version"),
                        }
                    )
                else:
                    result["packages"].append(
                        {
                            "name": name,
                            "version": str(info) if info else None,
                        }
                    )
        except json_lib.JSONDecodeError as e:
            result["errors"].append({"error": f"Failed to parse npm JSON output: {e}"})

    result["packages"].sort(key=lambda x: x["name"].lower())
    return result


def scan_pip() -> dict:
    """Scan pip installed packages (user site-packages).

    Only scans user-installed packages, not system packages.

    Returns:
        Dictionary with 'packages' list
    """
    result = {
        "installed": False,
        "packages": [],
        "errors": [],
    }

    # Try pip3 first, then pip
    pip_cmd = None
    for cmd in ["pip3", "pip"]:
        if _check_command_exists(cmd):
            pip_cmd = cmd
            break

    if pip_cmd is None:
        return result

    result["installed"] = True

    # Get list of packages in JSON format (user packages only)
    output = _run_command([pip_cmd, "list", "--user", "--format=json"])
    if output is None:
        # Try without --user (some systems don't support it)
        output = _run_command([pip_cmd, "list", "--format=json"])

    if output:
        try:
            packages = json_lib.loads(output)
            for pkg in packages:
                result["packages"].append(
                    {
                        "name": pkg.get("name"),
                        "version": pkg.get("version"),
                    }
                )
        except json_lib.JSONDecodeError:
            # Fallback to non-JSON format
            output = _run_command([pip_cmd, "list"])
            if output:
                for line in output.split("\n"):
                    line = line.strip()
                    if not line or line.startswith("Package") or line.startswith("-"):
                        continue
                    parts = line.split()
                    if len(parts) >= 2:
                        result["packages"].append(
                            {
                                "name": parts[0],
                                "version": parts[1],
                            }
                        )

    result["packages"].sort(key=lambda x: x["name"].lower())
    return result


def scan_pipx() -> dict:
    """Scan pipx installed applications.

    Returns:
        Dictionary with 'packages' list
    """
    result = {
        "installed": False,
        "packages": [],
        "errors": [],
    }

    if not _check_command_exists("pipx"):
        return result

    result["installed"] = True

    # Get list of packages in JSON format
    output = _run_command(["pipx", "list", "--json"])
    if output:
        try:
            data = json_lib.loads(output)
            venvs = data.get("venvs", {})
            for name, info in venvs.items():
                metadata = info.get("metadata", {}).get("main_package", {})
                result["packages"].append(
                    {
                        "name": name,
                        "version": metadata.get("package_version"),
                        "python_version": metadata.get("python_version"),
                    }
                )
        except json_lib.JSONDecodeError as e:
            result["errors"].append({"error": f"Failed to parse pipx JSON: {e}"})
    else:
        # Fallback to non-JSON
        output = _run_command(["pipx", "list"])
        if output:
            for line in output.split("\n"):
                line = line.strip()
                if line.startswith("-") or not line:
                    continue
                # Parse "package x.y.z" format
                parts = line.split()
                if len(parts) >= 2:
                    result["packages"].append(
                        {
                            "name": parts[0],
                            "version": parts[1] if parts[1] != "injected" else None,
                        }
                    )

    result["packages"].sort(key=lambda x: x["name"].lower())
    return result


def scan_cargo() -> dict:
    """Scan cargo installed packages.

    Returns:
        Dictionary with 'packages' list
    """
    result = {
        "installed": False,
        "packages": [],
        "errors": [],
    }

    if not _check_command_exists("cargo"):
        return result

    result["installed"] = True

    # cargo install --list shows installed packages
    output = _run_command(["cargo", "install", "--list"])
    if output:
        for line in output.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Package lines don't start with whitespace
            if not line.startswith(" ") and "v" in line:
                # Format: "package-name v1.2.3:"
                parts = line.rstrip(":").split()
                if len(parts) >= 2:
                    name = parts[0]
                    version = parts[1].lstrip("v")
                    result["packages"].append(
                        {
                            "name": name,
                            "version": version,
                        }
                    )

    result["packages"].sort(key=lambda x: x["name"].lower())
    return result


def scan_gem() -> dict:
    """Scan gem installed packages.

    Returns:
        Dictionary with 'packages' list
    """
    result = {
        "installed": False,
        "packages": [],
        "errors": [],
    }

    if not _check_command_exists("gem"):
        return result

    result["installed"] = True

    # Get list of user-installed gems
    output = _run_command(["gem", "list", "--local"])
    if output:
        for line in output.split("\n"):
            line = line.strip()
            if not line or line.startswith("*"):
                continue

            # Format: "package-name (1.2.3, 1.2.2)" or "package-name (1.2.3)"
            if "(" in line and ")" in line:
                paren_start = line.index("(")
                name = line[:paren_start].strip()
                versions_str = line[paren_start + 1 : -1]
                # Take the first (latest) version
                versions = [v.strip() for v in versions_str.split(",")]
                result["packages"].append(
                    {
                        "name": name,
                        "version": versions[0] if versions else None,
                        "all_versions": versions,
                    }
                )

    result["packages"].sort(key=lambda x: x["name"].lower())
    return result


def scan_go() -> dict:
    """Scan Go installed binaries.

    Returns:
        Dictionary with 'packages' list
    """
    result = {
        "installed": False,
        "packages": [],
        "errors": [],
    }

    if not _check_command_exists("go"):
        return result

    result["installed"] = True

    # Check GOPATH/bin or GOBIN for installed binaries
    gopath = _run_command(["go", "env", "GOPATH"])
    gobin = _run_command(["go", "env", "GOBIN"])

    bin_dir = None
    if gobin:
        bin_dir = Path(gobin)
    elif gopath:
        bin_dir = Path(gopath) / "bin"

    if bin_dir and bin_dir.exists():
        for binary in bin_dir.iterdir():
            if binary.is_file() and not binary.name.startswith("."):
                result["packages"].append(
                    {
                        "name": binary.name,
                        "path": str(binary),
                    }
                )

    result["packages"].sort(key=lambda x: x["name"].lower())
    return result


def scan() -> dict:
    """Scan all global package managers.

    Returns:
        Dictionary with results from all package managers
    """
    npm_result = scan_npm_global()
    pip_result = scan_pip()
    pipx_result = scan_pipx()
    cargo_result = scan_cargo()
    gem_result = scan_gem()
    go_result = scan_go()

    return {
        "npm": {
            "installed": npm_result["installed"],
            "packages": npm_result["packages"],
            "count": len(npm_result["packages"]),
            "errors": npm_result["errors"],
        },
        "pip": {
            "installed": pip_result["installed"],
            "packages": pip_result["packages"],
            "count": len(pip_result["packages"]),
            "errors": pip_result["errors"],
        },
        "pipx": {
            "installed": pipx_result["installed"],
            "packages": pipx_result["packages"],
            "count": len(pipx_result["packages"]),
            "errors": pipx_result["errors"],
        },
        "cargo": {
            "installed": cargo_result["installed"],
            "packages": cargo_result["packages"],
            "count": len(cargo_result["packages"]),
            "errors": cargo_result["errors"],
        },
        "gem": {
            "installed": gem_result["installed"],
            "packages": gem_result["packages"],
            "count": len(gem_result["packages"]),
            "errors": gem_result["errors"],
        },
        "go": {
            "installed": go_result["installed"],
            "packages": go_result["packages"],
            "count": len(go_result["packages"]),
            "errors": go_result["errors"],
        },
    }


if __name__ == "__main__":
    import json

    result = scan()
    print(json.dumps(result, indent=2))

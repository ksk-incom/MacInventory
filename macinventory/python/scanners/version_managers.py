"""Scanner for version managers (pyenv, nvm, rbenv, asdf).

Scans for installed version managers and their managed runtime versions.
"""

import os
import subprocess
from pathlib import Path
from typing import Optional


def _run_command(cmd: list[str], timeout: int = 30, env: Optional[dict] = None) -> Optional[str]:
    """Run a command and return its stdout, or None on failure.

    Args:
        cmd: Command and arguments as a list
        timeout: Timeout in seconds
        env: Optional environment variables

    Returns:
        stdout as string, or None if command failed
    """
    try:
        run_env = os.environ.copy()
        if env:
            run_env.update(env)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=run_env,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def _check_command_exists(cmd: str) -> bool:
    """Check if a command exists in PATH."""
    return _run_command(["which", cmd]) is not None


def scan_pyenv() -> dict:
    """Scan pyenv for installed Python versions.

    Returns:
        Dictionary with 'versions' list and current global version
    """
    result = {
        "installed": False,
        "versions": [],
        "global_version": None,
        "errors": [],
    }

    # Check if pyenv exists
    pyenv_root = Path.home() / ".pyenv"
    if not pyenv_root.exists() and not _check_command_exists("pyenv"):
        return result

    result["installed"] = True

    # Get installed versions from directory
    versions_dir = pyenv_root / "versions"
    if versions_dir.exists():
        for version_path in versions_dir.iterdir():
            if version_path.is_dir() and not version_path.name.startswith("."):
                result["versions"].append(version_path.name)
    else:
        # Try pyenv command
        output = _run_command(["pyenv", "versions", "--bare"])
        if output:
            result["versions"] = [v.strip() for v in output.split("\n") if v.strip()]

    # Get global version
    global_file = pyenv_root / "version"
    if global_file.exists():
        try:
            result["global_version"] = global_file.read_text().strip()
        except OSError:
            pass

    result["versions"].sort()
    return result


def scan_nvm() -> dict:
    """Scan nvm for installed Node.js versions.

    Returns:
        Dictionary with 'versions' list and current default version
    """
    result = {
        "installed": False,
        "versions": [],
        "default_version": None,
        "errors": [],
    }

    # Check if nvm exists
    nvm_dir = Path(os.environ.get("NVM_DIR", str(Path.home() / ".nvm")))
    if not nvm_dir.exists():
        return result

    result["installed"] = True

    # Get installed versions from directory
    versions_dir = nvm_dir / "versions" / "node"
    if versions_dir.exists():
        for version_path in versions_dir.iterdir():
            if version_path.is_dir():
                # Remove 'v' prefix if present
                version = version_path.name
                if version.startswith("v"):
                    version = version[1:]
                result["versions"].append(version)

    # Get default version from alias
    alias_dir = nvm_dir / "alias"
    default_file = alias_dir / "default"
    if default_file.exists():
        try:
            result["default_version"] = default_file.read_text().strip()
        except OSError:
            pass

    result["versions"].sort(key=lambda v: [int(x) for x in v.split(".") if x.isdigit()])
    return result


def scan_rbenv() -> dict:
    """Scan rbenv for installed Ruby versions.

    Returns:
        Dictionary with 'versions' list and current global version
    """
    result = {
        "installed": False,
        "versions": [],
        "global_version": None,
        "errors": [],
    }

    # Check if rbenv exists
    rbenv_root = Path.home() / ".rbenv"
    if not rbenv_root.exists() and not _check_command_exists("rbenv"):
        return result

    result["installed"] = True

    # Get installed versions from directory
    versions_dir = rbenv_root / "versions"
    if versions_dir.exists():
        for version_path in versions_dir.iterdir():
            if version_path.is_dir() and not version_path.name.startswith("."):
                result["versions"].append(version_path.name)
    else:
        # Try rbenv command
        output = _run_command(["rbenv", "versions", "--bare"])
        if output:
            result["versions"] = [v.strip() for v in output.split("\n") if v.strip()]

    # Get global version
    global_file = rbenv_root / "version"
    if global_file.exists():
        try:
            result["global_version"] = global_file.read_text().strip()
        except OSError:
            pass

    result["versions"].sort()
    return result


def scan_asdf() -> dict:
    """Scan asdf for installed plugin versions.

    Returns:
        Dictionary with plugins and their installed versions
    """
    result = {
        "installed": False,
        "plugins": {},
        "errors": [],
    }

    # Check if asdf exists
    asdf_dir = Path.home() / ".asdf"
    if not asdf_dir.exists() and not _check_command_exists("asdf"):
        return result

    result["installed"] = True

    # Get installed plugins and their versions
    plugins_dir = asdf_dir / "plugins"
    installs_dir = asdf_dir / "installs"

    if plugins_dir.exists():
        for plugin_path in plugins_dir.iterdir():
            if plugin_path.is_dir():
                plugin_name = plugin_path.name
                versions = []

                # Get versions from installs directory
                plugin_installs = installs_dir / plugin_name
                if plugin_installs.exists():
                    for version_path in plugin_installs.iterdir():
                        if version_path.is_dir():
                            versions.append(version_path.name)

                result["plugins"][plugin_name] = {
                    "versions": sorted(versions),
                    "count": len(versions),
                }

    # Get global tool versions
    tool_versions_file = Path.home() / ".tool-versions"
    if tool_versions_file.exists():
        try:
            tool_versions = {}
            content = tool_versions_file.read_text()
            for line in content.split("\n"):
                line = line.strip()
                if line and not line.startswith("#"):
                    parts = line.split()
                    if len(parts) >= 2:
                        tool_versions[parts[0]] = parts[1]
            result["global_versions"] = tool_versions
        except OSError:
            pass

    return result


def scan_nodenv() -> dict:
    """Scan nodenv for installed Node.js versions.

    Returns:
        Dictionary with 'versions' list and current global version
    """
    result = {
        "installed": False,
        "versions": [],
        "global_version": None,
        "errors": [],
    }

    # Check if nodenv exists
    nodenv_root = Path.home() / ".nodenv"
    if not nodenv_root.exists() and not _check_command_exists("nodenv"):
        return result

    result["installed"] = True

    # Get installed versions from directory
    versions_dir = nodenv_root / "versions"
    if versions_dir.exists():
        for version_path in versions_dir.iterdir():
            if version_path.is_dir() and not version_path.name.startswith("."):
                result["versions"].append(version_path.name)

    # Get global version
    global_file = nodenv_root / "version"
    if global_file.exists():
        try:
            result["global_version"] = global_file.read_text().strip()
        except OSError:
            pass

    result["versions"].sort(key=lambda v: [int(x) for x in v.split(".") if x.isdigit()])
    return result


def scan() -> dict:
    """Scan all version managers.

    Returns:
        Dictionary with results from all version managers
    """
    return {
        "pyenv": scan_pyenv(),
        "nvm": scan_nvm(),
        "rbenv": scan_rbenv(),
        "asdf": scan_asdf(),
        "nodenv": scan_nodenv(),
    }


if __name__ == "__main__":
    import json

    result = scan()
    print(json.dumps(result, indent=2))

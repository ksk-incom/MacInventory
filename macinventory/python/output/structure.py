"""Output directory structure creation.

Creates the consistent output directory structure defined in
MACINVENTORY_IMPLEMENTATION_GUIDE.md Decision 7.

Output Structure:
    ~/mac-inventory/YYYY-MM-DD-HHMMSS/
    ├── Restoration-Guide.md          # Primary human-readable output
    ├── state.yaml                    # Machine-readable inventory
    ├── bundles/                      # Executable installation files
    │   ├── Brewfile                  # brew bundle install
    │   ├── MASApps.txt               # mas install commands
    │   ├── NPMGlobalPackages.txt     # npm install -g
    │   ├── PipPackages.txt           # pip install
    │   ├── CargoPackages.txt         # cargo install
    │   ├── VSCodeExtensions.txt      # code --install-extension
    │   ├── CursorExtensions.txt      # cursor --install-extension
    │   └── PythonVersions.txt        # pyenv install
    └── configs/                      # Backed-up configuration files
        ├── shell/
        ├── git/
        ├── ssh/
        ├── editors/
        └── apps/

From Vision document:
    "Every run should produce the same file structure, enabling:
    - Comparison between captures over time
    - Reliable cloud sync (files in predictable locations)
    - Clear expectations for users
    - Can build automation on top"
"""

import platform
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from utils.path_safety import safe_join


def get_timestamp() -> str:
    """Get a timestamp string for directory naming.

    Returns:
        Timestamp in YYYY-MM-DD-HHMMSS format
    """
    return datetime.now().strftime("%Y-%m-%d-%H%M%S")


def get_default_output_base() -> Path:
    """Get the default base directory for inventory output.

    Returns:
        Path to ~/mac-inventory/
    """
    return Path.home() / "mac-inventory"


def create_output_directory(
    base_dir: Optional[Path] = None,
    timestamp: Optional[str] = None
) -> Path:
    """Create a timestamped output directory with full structure.

    Creates the complete directory hierarchy for inventory output.
    Always creates the same structure to enable comparison and automation.

    Args:
        base_dir: Base directory (default: ~/mac-inventory/)
        timestamp: Timestamp string (default: current time)

    Returns:
        Path to the created output directory (e.g., ~/mac-inventory/2025-12-22-143022/)

    Raises:
        OSError: If directory creation fails
    """
    if base_dir is None:
        base_dir = get_default_output_base()

    if timestamp is None:
        timestamp = get_timestamp()

    output_dir = base_dir / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create bundles directory
    bundles_dir = output_dir / "bundles"
    bundles_dir.mkdir(exist_ok=True)

    # Create configs directory structure
    configs_dir = output_dir / "configs"
    configs_subdirs = [
        "shell",
        "git",
        "ssh",
        "editors",
        "apps",
    ]

    for subdir in configs_subdirs:
        (configs_dir / subdir).mkdir(parents=True, exist_ok=True)

    return output_dir


def get_output_paths(output_dir: Path) -> dict[str, Path]:
    """Get paths to all expected output files.

    Returns a dictionary mapping file types to their expected paths.
    Files may not exist yet - this just returns where they should be.

    Args:
        output_dir: The timestamped output directory

    Returns:
        Dictionary mapping file types to paths
    """
    return {
        # Main files
        "restoration_guide": output_dir / "Restoration-Guide.md",
        "state_file": output_dir / "state.yaml",

        # Bundle files
        "brewfile": output_dir / "bundles" / "Brewfile",
        "mas_apps": output_dir / "bundles" / "MASApps.txt",
        "npm_packages": output_dir / "bundles" / "NPMGlobalPackages.txt",
        "pip_packages": output_dir / "bundles" / "PipPackages.txt",
        "pipx_packages": output_dir / "bundles" / "PipxPackages.txt",
        "cargo_packages": output_dir / "bundles" / "CargoPackages.txt",
        "gem_packages": output_dir / "bundles" / "GemPackages.txt",
        "go_packages": output_dir / "bundles" / "GoPackages.txt",
        "vscode_extensions": output_dir / "bundles" / "VSCodeExtensions.txt",
        "cursor_extensions": output_dir / "bundles" / "CursorExtensions.txt",
        "zed_extensions": output_dir / "bundles" / "ZedExtensions.txt",
        "python_versions": output_dir / "bundles" / "PythonVersions.txt",
        "node_versions": output_dir / "bundles" / "NodeVersions.txt",
        "ruby_versions": output_dir / "bundles" / "RubyVersions.txt",
        "asdf_versions": output_dir / "bundles" / "AsdfVersions.txt",

        # Config directories
        "configs_shell": output_dir / "configs" / "shell",
        "configs_git": output_dir / "configs" / "git",
        "configs_ssh": output_dir / "configs" / "ssh",
        "configs_editors": output_dir / "configs" / "editors",
        "configs_apps": output_dir / "configs" / "apps",
    }


def validate_output_structure(output_dir: Path) -> dict[str, Any]:
    """Validate that an output directory has the expected structure.

    Checks for the presence of expected directories and reports
    which files exist.

    Args:
        output_dir: Path to output directory to validate

    Returns:
        Dictionary with validation results:
        - valid: bool indicating if basic structure is correct
        - directories: dict of directory paths to exists status
        - files: dict of file paths to exists status
        - issues: list of issues found
    """
    result: dict[str, Any] = {
        "valid": True,
        "directories": {},
        "files": {},
        "issues": [],
    }

    # Required directories
    required_dirs = [
        output_dir / "bundles",
        output_dir / "configs",
        output_dir / "configs" / "shell",
        output_dir / "configs" / "git",
        output_dir / "configs" / "ssh",
        output_dir / "configs" / "editors",
        output_dir / "configs" / "apps",
    ]

    for dir_path in required_dirs:
        exists = dir_path.exists() and dir_path.is_dir()
        result["directories"][str(dir_path.relative_to(output_dir))] = exists
        if not exists:
            result["valid"] = False
            result["issues"].append(f"Missing directory: {dir_path.relative_to(output_dir)}")

    # Check for expected files
    expected_files = [
        "Restoration-Guide.md",
        "state.yaml",
        "bundles/Brewfile",
    ]

    for file_rel in expected_files:
        file_path = output_dir / file_rel
        result["files"][file_rel] = file_path.exists()

    return result


def get_system_info() -> dict[str, Any]:
    """Gather system information for the state file.

    Returns:
        Dictionary with system information:
        - hostname: Machine hostname
        - mac_model: Mac model identifier
        - macos_version: macOS version string
        - architecture: CPU architecture (arm64/x86_64)
        - username: Current user
        - capture_timestamp: ISO format timestamp
    """
    info: dict[str, Any] = {
        "hostname": platform.node(),
        "macos_version": platform.mac_ver()[0],
        "architecture": platform.machine(),
        "username": Path.home().name,
        "capture_timestamp": datetime.now().isoformat(),
    }

    # Get Mac model identifier
    try:
        result = subprocess.run(
            ["sysctl", "-n", "hw.model"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            info["mac_model"] = result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    # Get macOS product name (e.g., "macOS Sequoia")
    try:
        result = subprocess.run(
            ["sw_vers", "-productName"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            info["macos_product_name"] = result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    # Get macOS build version
    try:
        result = subprocess.run(
            ["sw_vers", "-buildVersion"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            info["macos_build"] = result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    return info


def cleanup_old_inventories(
    base_dir: Optional[Path] = None,
    keep_count: int = 5
) -> list[Path]:
    """Remove old inventory directories, keeping the most recent ones.

    Args:
        base_dir: Base directory containing inventory folders
        keep_count: Number of most recent directories to keep

    Returns:
        List of paths that were removed
    """
    import shutil

    if base_dir is None:
        base_dir = get_default_output_base()

    if not base_dir.exists():
        return []

    # Get all timestamped directories
    inventory_dirs = []
    for item in base_dir.iterdir():
        if item.is_dir():
            # Check if it looks like a timestamp directory
            name = item.name
            if len(name) == 17 and name[4] == "-" and name[7] == "-" and name[10] == "-":
                inventory_dirs.append(item)

    # Sort by name (which is timestamp) in reverse order
    inventory_dirs.sort(key=lambda p: p.name, reverse=True)

    # Remove old ones
    removed = []
    for dir_to_remove in inventory_dirs[keep_count:]:
        try:
            shutil.rmtree(dir_to_remove)
            removed.append(dir_to_remove)
        except OSError:
            pass  # Best effort

    return removed


class OutputStructure:
    """Manages the output directory structure for an inventory run.

    Provides a convenient interface for creating and accessing
    output directory paths.

    Example:
        >>> output = OutputStructure()
        >>> print(f"Output directory: {output.output_dir}")
        >>> print(f"Brewfile path: {output.paths['brewfile']}")
        >>> output.write_file('brewfile', 'tap "homebrew/cask"\\nbrew "git"')
    """

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        timestamp: Optional[str] = None
    ):
        """Initialize output structure.

        Args:
            base_dir: Base directory for output (default: ~/mac-inventory/)
            timestamp: Timestamp for directory name (default: current time)
        """
        self.base_dir = base_dir or get_default_output_base()
        self.timestamp = timestamp or get_timestamp()
        self.output_dir = create_output_directory(self.base_dir, self.timestamp)
        self.paths = get_output_paths(self.output_dir)
        self.system_info = get_system_info()

    def write_file(self, key: str, content: str) -> Path:
        """Write content to an output file by key.

        Args:
            key: File key from get_output_paths (e.g., 'brewfile', 'state_file')
            content: Content to write

        Returns:
            Path to the written file

        Raises:
            KeyError: If key is not a valid file path key
            OSError: If writing fails
        """
        if key not in self.paths:
            raise KeyError(f"Unknown output file key: {key}")

        path = self.paths[key]

        # Don't write to directory paths
        if key.startswith("configs_"):
            raise KeyError(f"Cannot write to directory path: {key}")

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def get_config_path(self, category: str, filename: str) -> Path:
        """Get the path for a config file backup.

        Args:
            category: Config category (shell, git, ssh, editors, apps)
            filename: Name of the config file

        Returns:
            Full path to where the config should be backed up

        Raises:
            PathTraversalError: If filename contains path traversal sequences

        Example:
            >>> output.get_config_path('shell', 'zshrc')
            PosixPath('/Users/user/mac-inventory/2025-12-22/configs/shell/zshrc')
        """
        category_key = f"configs_{category}"
        if category_key not in self.paths:
            # Fall back to apps for unknown categories
            category_key = "configs_apps"

        # Use safe_join to prevent path traversal attacks
        return safe_join(self.paths[category_key], filename)

    def validate(self) -> dict[str, Any]:
        """Validate the output structure.

        Returns:
            Validation results from validate_output_structure
        """
        return validate_output_structure(self.output_dir)

    def to_dict(self) -> dict[str, Any]:
        """Convert output structure info to dictionary.

        Returns:
            Dictionary with output directory information
        """
        return {
            "base_dir": str(self.base_dir),
            "timestamp": self.timestamp,
            "output_dir": str(self.output_dir),
            "system_info": self.system_info,
            "paths": {k: str(v) for k, v in self.paths.items()},
        }


if __name__ == "__main__":
    import json

    # Demo the output structure
    print("Creating output structure...")
    output = OutputStructure()

    print(f"\nOutput directory: {output.output_dir}")
    print( "\nSystem info:")
    print(json.dumps(output.system_info, indent=2))

    print( "\nOutput paths:")
    for key, path in output.paths.items():
        exists = "✓" if path.exists() else " "
        print(f"  [{exists}] {key}: {path.relative_to(output.output_dir)}")

    print("\nValidation:")
    validation = output.validate()
    print(json.dumps(validation, indent=2))

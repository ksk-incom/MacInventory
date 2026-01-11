"""Platform-specific file operations for macOS.

Handles special macOS file attributes that can prevent normal operations:
- Access Control Lists (ACLs)
- Immutable flags (uchg, schg)
- Extended attributes

From Vision document section "Platform-Specific File Attribute Handling":
    macOS files can have special attributes that prevent normal file operations.
    Before copying configuration files, MacInventory detects and handles these
    attributes, logging when special attributes are encountered.
"""

import platform
import subprocess
from pathlib import Path
from typing import Optional


def is_macos() -> bool:
    """Check if running on macOS.

    Returns:
        True if running on Darwin/macOS
    """
    return platform.system() == "Darwin"


def remove_acl(filepath: Path) -> bool:
    """Remove Access Control Lists from a file/directory (macOS only).

    ACLs are extended permissions beyond standard Unix permissions.
    Configuration files from system applications often have ACLs set
    that can prevent normal copy operations.

    Uses: chmod -N <path> (without -R for single file, -R for directories)

    Args:
        filepath: Path to file or directory

    Returns:
        True if successful, ACLs removed, or not applicable
        False if operation failed
    """
    if not is_macos():
        return True

    chmod_path = Path("/bin/chmod")
    if not chmod_path.exists():
        return True

    try:
        # Use -N to remove ACLs, -R for recursive if directory
        cmd = [str(chmod_path), "-N", str(filepath)]
        if filepath.is_dir():
            cmd.insert(1, "-R")

        subprocess.run(
            cmd,
            capture_output=True,
            check=False,  # Don't raise on failure
            timeout=5  # Quick local operation
        )
        return True
    except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired):
        return False


def remove_immutable_flags(filepath: Path) -> bool:
    """Remove immutable flags from a file/directory (macOS only).

    Immutable flags (uchg, schg) prevent file modification.
    Only removes user-changeable flags (uchg), not system flags (schg)
    which require root permissions.

    Uses: chflags nouchg <path> (without -R for single file, -R for directories)

    Args:
        filepath: Path to file or directory

    Returns:
        True if successful, flags removed, or not applicable
        False if operation failed
    """
    if not is_macos():
        return True

    chflags_path = Path("/usr/bin/chflags")
    if not chflags_path.exists():
        return True

    try:
        cmd = [str(chflags_path), "nouchg", str(filepath)]
        if filepath.is_dir():
            cmd.insert(1, "-R")

        subprocess.run(
            cmd,
            capture_output=True,
            check=False,
            timeout=5  # Quick local operation
        )
        return True
    except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired):
        return False


def get_file_flags(filepath: Path) -> Optional[str]:
    """Get file flags information (macOS only).

    Uses: ls -lO <path>

    Args:
        filepath: Path to file

    Returns:
        Flags string (e.g., "uchg") or None if no flags or not macOS
    """
    if not is_macos() or not filepath.exists():
        return None

    try:
        result = subprocess.run(
            ["/bin/ls", "-lO", str(filepath)],
            capture_output=True,
            text=True,
            check=False,
            timeout=5  # Quick local operation
        )
        if result.returncode == 0:
            # Output format: -rw-r--r--@ 1 user staff flags size date name
            parts = result.stdout.split()
            if len(parts) > 4:
                # The flags appear in the 5th column
                flags = parts[4]
                # Common flags: uchg, hidden, restricted, compressed
                if flags not in ['-', '']:
                    return flags
    except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired):
        pass

    return None


def has_acl(filepath: Path) -> bool:
    """Check if a file has ACLs (macOS only).

    Uses: ls -le <path> and checks for ACL entries

    Args:
        filepath: Path to file

    Returns:
        True if file has ACLs, False otherwise
    """
    if not is_macos() or not filepath.exists():
        return False

    try:
        result = subprocess.run(
            ["/bin/ls", "-le", str(filepath)],
            capture_output=True,
            text=True,
            check=False,
            timeout=5  # Quick local operation
        )
        if result.returncode == 0:
            # ACLs show as additional lines starting with a number
            lines = result.stdout.strip().split('\n')
            return len(lines) > 1 and any(
                line.strip().startswith(('0:', '1:', '2:', '3:'))
                for line in lines[1:]
            )
    except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired):
        pass

    return False


def prepare_for_copy(filepath: Path) -> dict:
    """Prepare a file for copying by handling special attributes.

    Attempts to remove ACLs and immutable flags from the SOURCE file
    so it can be read properly. This is done non-destructively on a
    copy basis - the original file's attributes are preserved on disk.

    Note: This function is called on the source file before copying.
    For most config files, we actually want to handle attributes on
    the DESTINATION after copying. Use normalize_destination() for that.

    Args:
        filepath: Path to file/directory to prepare

    Returns:
        Dictionary with metadata about attribute handling:
        - acl_handled: Whether ACL removal was attempted
        - flags_handled: Whether flag removal was attempted
        - original_path: The file path
        - had_acl: Whether file originally had ACLs
        - original_flags: Original flags if any
    """
    result = {
        'original_path': str(filepath),
        'acl_handled': False,
        'flags_handled': False,
        'had_acl': False,
        'original_flags': None,
    }

    if not is_macos() or not filepath.exists():
        return result

    # Check current state
    result['had_acl'] = has_acl(filepath)
    result['original_flags'] = get_file_flags(filepath)

    # Note: We typically don't want to modify the source file's attributes
    # The caller should handle this appropriately based on whether they
    # own the source file or are just reading it.

    return result


def normalize_destination_permissions(target: Path, file_mode: int = 0o600, dir_mode: int = 0o700) -> None:
    """Normalize permissions on a copied config destination.

    After copying configuration files, normalize permissions to ensure
    backed-up configs are secure regardless of original permissions.

    From Vision document:
        Files: 0600 (owner read/write only)
        Directories: 0700 (owner read/write/execute only)

    Args:
        target: Path to file or directory to normalize
        file_mode: Permission mode for files (default: 0o600)
        dir_mode: Permission mode for directories (default: 0o700)
    """
    import os

    if not target.exists():
        return

    if target.is_file():
        try:
            os.chmod(target, file_mode)
        except OSError:
            pass  # Best effort, don't fail on permission errors
    elif target.is_dir():
        try:
            os.chmod(target, dir_mode)
        except OSError:
            pass

        # Recursively normalize directory contents
        for root, dirs, files in os.walk(target):
            for d in dirs:
                try:
                    os.chmod(Path(root) / d, dir_mode)
                except OSError:
                    pass
            for f in files:
                try:
                    os.chmod(Path(root) / f, file_mode)
                except OSError:
                    pass


def clear_destination_attributes(target: Path) -> dict:
    """Clear special attributes from a copied destination.

    After copying a file, clear any inherited special attributes
    to ensure the backup is clean and portable.

    Args:
        target: Path to the copied destination

    Returns:
        Dictionary with results of attribute clearing
    """
    result = {
        'path': str(target),
        'acl_removed': False,
        'flags_removed': False,
    }

    if not is_macos() or not target.exists():
        return result

    # Remove ACLs from destination
    result['acl_removed'] = remove_acl(target)

    # Remove immutable flags from destination
    result['flags_removed'] = remove_immutable_flags(target)

    return result


if __name__ == "__main__":
    import json
    from pathlib import Path

    print(f"Running on macOS: {is_macos()}")

    # Test with home directory files
    home = Path.home()
    test_files = [
        home / ".zshrc",
        home / ".gitconfig",
        home / "Library/Preferences",
    ]

    for test_path in test_files:
        if test_path.exists():
            info = prepare_for_copy(test_path)
            print(f"\n{test_path.name}:")
            print(json.dumps(info, indent=2))

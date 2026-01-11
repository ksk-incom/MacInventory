"""Binary plist conversion utilities for macOS.

Handles conversion of macOS binary property list (plist) files to
human-readable XML format for backup and inspection.

From Vision document:
    "Configuration files stored in binary plist format may need to be
    converted using 'plutil -convert xml1' for readable backups."

macOS plist files can be in three formats:
- XML (human-readable)
- Binary (more compact, faster to read/write)
- JSON (supported but rarely used for config files)
"""

import plistlib
import subprocess
from pathlib import Path
from typing import Any, Optional


class PlistError(Exception):
    """Raised when plist operations fail."""
    pass


def is_binary_plist(file_path: Path) -> bool:
    """Check if a file is a binary plist.

    Binary plists start with the magic bytes 'bplist'.

    Args:
        file_path: Path to the file to check

    Returns:
        True if file is a binary plist, False otherwise
    """
    try:
        with open(file_path, 'rb') as f:
            magic = f.read(6)
            return magic == b'bplist'
    except (OSError, IOError):
        return False


def is_xml_plist(file_path: Path) -> bool:
    """Check if a file is an XML plist.

    XML plists typically start with '<?xml' or '<!DOCTYPE plist'.

    Args:
        file_path: Path to the file to check

    Returns:
        True if file appears to be an XML plist, False otherwise
    """
    try:
        with open(file_path, 'rb') as f:
            # Read first 100 bytes for magic detection
            header = f.read(100)
            # Check for XML declaration or DOCTYPE
            return (
                header.startswith(b'<?xml') or
                b'<!DOCTYPE plist' in header or
                b'<plist' in header
            )
    except (OSError, IOError):
        return False


def is_plist(file_path: Path) -> bool:
    """Check if a file is a plist (binary or XML).

    Args:
        file_path: Path to the file to check

    Returns:
        True if file is a plist, False otherwise
    """
    return is_binary_plist(file_path) or is_xml_plist(file_path)


def get_plist_format(file_path: Path) -> Optional[str]:
    """Determine the format of a plist file.

    Args:
        file_path: Path to the plist file

    Returns:
        'binary', 'xml', or None if not a plist
    """
    if is_binary_plist(file_path):
        return 'binary'
    elif is_xml_plist(file_path):
        return 'xml'
    return None


def convert_to_xml_plutil(
    source: Path,
    dest: Optional[Path] = None
) -> tuple[bool, str]:
    """Convert a binary plist to XML using plutil command.

    This method uses the macOS plutil command which is more reliable
    than Python's plistlib for certain edge cases.

    Args:
        source: Path to the source plist file
        dest: Optional destination path (converts in-place if None)

    Returns:
        Tuple of (success, message)
    """
    if dest is None:
        # Convert in-place
        cmd = ['/usr/bin/plutil', '-convert', 'xml1', str(source)]
    else:
        # Convert to destination
        dest.parent.mkdir(parents=True, exist_ok=True)
        # First copy, then convert
        import shutil
        shutil.copy2(source, dest)
        cmd = ['/usr/bin/plutil', '-convert', 'xml1', str(dest)]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            return True, "Converted successfully"
        else:
            error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
            return False, f"plutil error: {error_msg}"

    except subprocess.TimeoutExpired:
        return False, "Conversion timed out"
    except FileNotFoundError:
        return False, "plutil command not found (not on macOS?)"
    except Exception as e:
        return False, f"Unexpected error: {e}"


def convert_to_xml_python(
    source: Path,
    dest: Optional[Path] = None
) -> tuple[bool, str]:
    """Convert a plist to XML using Python's plistlib.

    This is a fallback method when plutil is not available.
    Works on any platform but may not handle all plist edge cases.

    Args:
        source: Path to the source plist file
        dest: Optional destination path (returns content if None)

    Returns:
        Tuple of (success, message or error)
    """
    try:
        # Read the plist (works with both binary and XML)
        with open(source, 'rb') as f:
            data = plistlib.load(f)

        # Write as XML
        output_path = dest or source
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'wb') as f:
            plistlib.dump(data, f, fmt=plistlib.FMT_XML)

        return True, "Converted successfully"

    except plistlib.InvalidFileException as e:
        return False, f"Invalid plist: {e}"
    except Exception as e:
        return False, f"Conversion error: {e}"


def convert_to_xml(
    source: Path,
    dest: Optional[Path] = None,
    use_plutil: bool = True
) -> tuple[bool, str]:
    """Convert a plist file to XML format.

    Attempts conversion using plutil first (more reliable on macOS),
    falling back to Python's plistlib if needed.

    Args:
        source: Path to the source plist file
        dest: Optional destination path (in-place if None)
        use_plutil: Try plutil first if available

    Returns:
        Tuple of (success, message)
    """
    # Check if already XML
    if is_xml_plist(source):
        if dest and dest != source:
            import shutil
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
        return True, "Already XML format"

    # Check if it's a plist at all
    if not is_binary_plist(source):
        return False, "Not a valid plist file"

    # Try plutil first on macOS
    if use_plutil:
        success, msg = convert_to_xml_plutil(source, dest)
        if success:
            return success, msg
        # Fall back to Python if plutil fails

    # Use Python plistlib
    return convert_to_xml_python(source, dest)


def read_plist(file_path: Path) -> dict[str, Any]:
    """Read a plist file and return its contents as a dictionary.

    Handles both binary and XML plist formats.

    Args:
        file_path: Path to the plist file

    Returns:
        Dictionary with plist contents

    Raises:
        PlistError: If file cannot be read or parsed
    """
    try:
        with open(file_path, 'rb') as f:
            return plistlib.load(f)
    except plistlib.InvalidFileException as e:
        raise PlistError(f"Invalid plist format: {e}")
    except Exception as e:
        raise PlistError(f"Could not read plist: {e}")


def read_plist_safe(file_path: Path) -> tuple[Optional[dict], Optional[str]]:
    """Safely read a plist file, returning error instead of raising.

    Args:
        file_path: Path to the plist file

    Returns:
        Tuple of (data, error_message) - data is None if error
    """
    try:
        data = read_plist(file_path)
        return data, None
    except PlistError as e:
        return None, str(e)
    except Exception as e:
        return None, f"Unexpected error: {e}"


def write_plist_xml(data: dict[str, Any], file_path: Path) -> tuple[bool, str]:
    """Write data to a plist file in XML format.

    Args:
        data: Dictionary to write
        file_path: Destination path

    Returns:
        Tuple of (success, message)
    """
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'wb') as f:
            plistlib.dump(data, f, fmt=plistlib.FMT_XML)
        return True, "Written successfully"
    except Exception as e:
        return False, f"Write error: {e}"


class PlistConverter:
    """Batch plist conversion utility.

    Handles conversion of multiple plist files with tracking and
    error handling.

    Example:
        >>> converter = PlistConverter()
        >>> converter.add_file(Path("~/Library/Preferences/com.app.plist"))
        >>> converter.add_directory(Path("~/Library/Preferences"))
        >>> results = converter.convert_all(output_dir=Path("/tmp/plists"))
    """

    def __init__(self):
        """Initialize the converter."""
        self.files: list[Path] = []
        self.results: list[dict[str, Any]] = []

    def add_file(self, file_path: Path) -> bool:
        """Add a file to convert.

        Args:
            file_path: Path to plist file

        Returns:
            True if file was added (is a valid plist)
        """
        path = Path(file_path).expanduser()
        if path.exists() and is_plist(path):
            self.files.append(path)
            return True
        return False

    def add_directory(self, dir_path: Path, pattern: str = "*.plist") -> int:
        """Add all plist files from a directory.

        Args:
            dir_path: Directory to scan
            pattern: Glob pattern for files (default: *.plist)

        Returns:
            Number of files added
        """
        dir_path = Path(dir_path).expanduser()
        count = 0

        if dir_path.exists():
            for file_path in dir_path.glob(pattern):
                if self.add_file(file_path):
                    count += 1

        return count

    def convert_all(
        self,
        output_dir: Optional[Path] = None,
        preserve_structure: bool = True
    ) -> list[dict[str, Any]]:
        """Convert all added files.

        Args:
            output_dir: Directory for converted files (in-place if None)
            preserve_structure: If True, preserve relative paths in output

        Returns:
            List of result dictionaries
        """
        self.results = []

        for source in self.files:
            result: dict[str, Any] = {
                'source': str(source),
                'original_format': get_plist_format(source),
            }

            if output_dir:
                if preserve_structure:
                    # Try to preserve relative path structure
                    try:
                        rel_path = source.relative_to(Path.home())
                        dest = output_dir / rel_path
                    except ValueError:
                        dest = output_dir / source.name
                else:
                    dest = output_dir / source.name

                result['dest'] = str(dest)
            else:
                dest = None
                result['dest'] = str(source)

            success, message = convert_to_xml(source, dest)
            result['success'] = success
            result['message'] = message

            self.results.append(result)

        return self.results

    def get_summary(self) -> dict[str, Any]:
        """Get conversion summary.

        Returns:
            Dictionary with summary statistics
        """
        total = len(self.results)
        success = sum(1 for r in self.results if r.get('success'))
        binary_converted = sum(
            1 for r in self.results
            if r.get('success') and r.get('original_format') == 'binary'
        )

        return {
            'total_files': total,
            'successful': success,
            'failed': total - success,
            'binary_converted': binary_converted,
            'already_xml': sum(
                1 for r in self.results
                if r.get('original_format') == 'xml'
            ),
        }


def backup_plist_as_xml(
    source: Path,
    dest: Path,
    normalize_permissions: bool = True
) -> dict[str, Any]:
    """Backup a plist file, converting to XML if needed.

    High-level function for backing up plist files in a readable format.

    Args:
        source: Source plist file
        dest: Destination path
        normalize_permissions: Whether to set secure permissions

    Returns:
        Dictionary with backup results
    """
    result: dict[str, Any] = {
        'source': str(source),
        'dest': str(dest),
        'status': 'success',
        'original_format': None,
        'converted': False,
    }

    if not source.exists():
        result['status'] = 'skipped'
        result['reason'] = 'Source file does not exist'
        return result

    result['original_format'] = get_plist_format(source)

    if result['original_format'] is None:
        result['status'] = 'skipped'
        result['reason'] = 'Not a valid plist file'
        return result

    # Convert to XML (handles both binary and already-XML)
    success, message = convert_to_xml(source, dest)

    if success:
        result['converted'] = result['original_format'] == 'binary'
        result['message'] = message

        # Normalize permissions if requested
        if normalize_permissions:
            import os
            try:
                os.chmod(dest, 0o600)
            except OSError:
                pass
    else:
        result['status'] = 'error'
        result['error'] = message

    return result


if __name__ == "__main__":
    # Demo the plist utilities
    home = Path.home()
    prefs_dir = home / "Library" / "Preferences"

    print("Scanning for plist files in ~/Library/Preferences...")

    if prefs_dir.exists():
        converter = PlistConverter()
        count = converter.add_directory(prefs_dir)
        print(f"Found {count} plist files")

        # Check format breakdown
        formats = {'binary': 0, 'xml': 0}
        for f in converter.files[:20]:  # Check first 20
            fmt = get_plist_format(f)
            if fmt:
                formats[fmt] += 1

        print( "Format breakdown (first 20):")
        print(f"  Binary: {formats['binary']}")
        print(f"  XML: {formats['xml']}")

        # Test reading a common plist
        test_plist = prefs_dir / "com.apple.finder.plist"
        if test_plist.exists():
            print(f"\nReading {test_plist.name}...")
            data, error = read_plist_safe(test_plist)
            if data:
                print(f"  Keys: {list(data.keys())[:5]}...")
            else:
                print(f"  Error: {error}")
    else:
        print("~/Library/Preferences not found (not on macOS?)")

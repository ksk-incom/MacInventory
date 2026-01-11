"""Cloud storage service detection for macOS.

Detects common cloud storage services and their sync folder locations:
- OneDrive (Microsoft)
- iCloud Drive (Apple)
- Dropbox
- Google Drive

Usage:
    from utils.storage_detection import detect_all_cloud_storage

    detected = detect_all_cloud_storage()
    for name, path in detected.items():
        print(f"{name}: {path}")
"""

from pathlib import Path
from typing import Dict, List, Optional
import base64
import binascii


def detect_onedrive() -> Optional[Path]:
    """Detect OneDrive sync folder location.

    OneDrive creates folders in ~/Library/CloudStorage/ with names like:
    - OneDrive-Personal
    - OneDrive-CompanyName

    Returns:
        Path to OneDrive folder if found, None otherwise.
    """
    cloud_storage = Path.home() / "Library/CloudStorage"
    if cloud_storage.exists():
        # Match OneDrive-* pattern (handles personal and business accounts)
        matches = sorted(cloud_storage.glob("OneDrive-*"))
        if matches:
            # Return first match (most common case is single account)
            return matches[0]
    return None


def detect_all_onedrive() -> List[Path]:
    """Detect all OneDrive sync folders (for multiple accounts).

    Returns:
        List of all OneDrive folder paths found.
    """
    cloud_storage = Path.home() / "Library/CloudStorage"
    if cloud_storage.exists():
        return sorted(cloud_storage.glob("OneDrive-*"))
    return []


def detect_icloud() -> Optional[Path]:
    """Detect iCloud Drive location.

    iCloud Drive is always at a fixed path on macOS.

    Returns:
        Path to iCloud Drive if it exists, None otherwise.
    """
    icloud_path = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs"
    return icloud_path if icloud_path.exists() else None


def detect_dropbox() -> Optional[Path]:
    """Detect Dropbox sync folder location.

    Dropbox stores its sync folder path in ~/.dropbox/host.db
    The second line contains a base64-encoded absolute path.

    Falls back to common locations if config file is missing or invalid.

    Returns:
        Path to Dropbox folder if found, None otherwise.
    """
    # Try to read from Dropbox config file
    host_db = Path.home() / ".dropbox/host.db"
    if host_db.exists():
        try:
            lines = host_db.read_text().strip().split('\n')
            if len(lines) >= 2:
                # Second line is base64-encoded path
                decoded_path = base64.b64decode(lines[1]).decode('utf-8')
                dropbox_path = Path(decoded_path)
                if dropbox_path.exists():
                    return dropbox_path
        except (UnicodeDecodeError, binascii.Error, IndexError):
            # Config file is corrupted or in unexpected format
            pass

    # Fallback to common locations
    fallback_locations = [
        Path.home() / "Dropbox",
        Path.home() / "Library/CloudStorage/Dropbox",
    ]

    for fallback in fallback_locations:
        if fallback.exists():
            return fallback

    return None


def detect_google_drive() -> Optional[Path]:
    """Detect Google Drive sync folder location.

    Google Drive creates folders in ~/Library/CloudStorage/ with names like:
    - GoogleDrive-user@gmail.com
    - GoogleDrive-user@company.com

    Returns:
        Path to Google Drive folder if found, None otherwise.
    """
    cloud_storage = Path.home() / "Library/CloudStorage"
    if cloud_storage.exists():
        matches = sorted(cloud_storage.glob("GoogleDrive-*"))
        if matches:
            return matches[0]
    return None


def detect_all_google_drive() -> List[Path]:
    """Detect all Google Drive sync folders (for multiple accounts).

    Returns:
        List of all Google Drive folder paths found.
    """
    cloud_storage = Path.home() / "Library/CloudStorage"
    if cloud_storage.exists():
        return sorted(cloud_storage.glob("GoogleDrive-*"))
    return []


def detect_all_cloud_storage() -> Dict[str, Path]:
    """Detect all available cloud storage services.

    Checks for OneDrive, iCloud, Dropbox, and Google Drive installations.

    Returns:
        Dictionary mapping service name to sync folder path.
        Only includes services that are detected.

    Example:
        >>> detected = detect_all_cloud_storage()
        >>> detected
        {'OneDrive': PosixPath('/Users/me/Library/CloudStorage/OneDrive-Personal'),
         'iCloud': PosixPath('/Users/me/Library/Mobile Documents/com~apple~CloudDocs')}
    """
    detected: Dict[str, Path] = {}

    detectors = [
        ('OneDrive', detect_onedrive),
        ('iCloud', detect_icloud),
        ('Dropbox', detect_dropbox),
        ('Google Drive', detect_google_drive),
    ]

    for name, detector in detectors:
        path = detector()
        if path:
            detected[name] = path

    return detected


def get_cloud_storage_display_name(path: Path) -> str:
    """Get a human-readable display name for a cloud storage path.

    Extracts account info from folder names like 'OneDrive-CompanyName'.

    Args:
        path: Path to cloud storage folder.

    Returns:
        Human-readable name like 'OneDrive (CompanyName)' or 'iCloud Drive'.
    """
    name = path.name

    if name.startswith("OneDrive-"):
        account = name.replace("OneDrive-", "")
        return f"OneDrive ({account})"
    elif name.startswith("GoogleDrive-"):
        account = name.replace("GoogleDrive-", "")
        return f"Google Drive ({account})"
    elif "CloudDocs" in str(path):
        return "iCloud Drive"
    elif "Dropbox" in name:
        return "Dropbox"
    else:
        return name


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Detect cloud storage services on macOS"
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON for machine parsing'
    )
    args = parser.parse_args()

    detected = detect_all_cloud_storage()

    if args.json:
        # JSON output for machine parsing
        result = {
            name: str(path)
            for name, path in detected.items()
        }
        print(json.dumps(result, indent=2))
    else:
        # Human-readable text output (default)
        print("Detecting cloud storage services...\n")

        if detected:
            print("Found cloud storage services:")
            for name, path in detected.items():
                display_name = get_cloud_storage_display_name(path)
                print(f"  {display_name}: {path}")
        else:
            print("No cloud storage services detected.")

        # Also show multiple accounts if present
        print("\nChecking for multiple accounts:")

        all_onedrive = detect_all_onedrive()
        if len(all_onedrive) > 1:
            print("  Multiple OneDrive accounts:")
            for p in all_onedrive:
                print(f"    - {get_cloud_storage_display_name(p)}")

        all_gdrive = detect_all_google_drive()
        if len(all_gdrive) > 1:
            print("  Multiple Google Drive accounts:")
            for p in all_gdrive:
                print(f"    - {get_cloud_storage_display_name(p)}")

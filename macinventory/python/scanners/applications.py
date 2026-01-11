"""Scanner for installed applications on macOS.

Scans /Applications and ~/Applications directories to discover installed apps,
extracting bundle IDs and version information from Info.plist files.
"""

import plistlib
import subprocess
from pathlib import Path
from typing import Optional

# Cache for brew cask list to avoid repeated subprocess calls
_CASK_LIST_CACHE: Optional[list[str]] = None


def _get_bundle_info(app_path: Path) -> Optional[dict]:
    """Extract bundle info from an app's Info.plist.

    Handles both XML and binary plist formats. For binary plists,
    uses plutil to convert to XML first.

    Args:
        app_path: Path to the .app bundle

    Returns:
        Dictionary with bundle_id, version, and name, or None if extraction fails
    """
    info_plist = app_path / "Contents" / "Info.plist"
    if not info_plist.exists():
        return None

    try:
        # Try reading directly (works for XML plists and modern binary plists)
        with open(info_plist, "rb") as f:
            plist = plistlib.load(f)

        return {
            "bundle_id": plist.get("CFBundleIdentifier"),
            "version": plist.get("CFBundleShortVersionString")
            or plist.get("CFBundleVersion"),
            "name": plist.get("CFBundleName") or plist.get("CFBundleDisplayName"),
            "executable": plist.get("CFBundleExecutable"),
        }
    except plistlib.InvalidFileException:
        # Binary plist that plistlib can't read - use plutil to convert
        try:
            # Convert to XML using plutil and read from stdout
            result = subprocess.run(
                ["plutil", "-convert", "xml1", "-o", "-", str(info_plist)],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                plist = plistlib.loads(result.stdout)
                return {
                    "bundle_id": plist.get("CFBundleIdentifier"),
                    "version": plist.get("CFBundleShortVersionString")
                    or plist.get("CFBundleVersion"),
                    "name": plist.get("CFBundleName") or plist.get("CFBundleDisplayName"),
                    "executable": plist.get("CFBundleExecutable"),
                }
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
        return None
    except (PermissionError, OSError):
        return None


def _get_cask_list() -> list[str]:
    """Get list of installed Homebrew casks (cached).

    Returns:
        List of cask names, or empty list if brew not installed or fails
    """
    global _CASK_LIST_CACHE

    if _CASK_LIST_CACHE is not None:
        return _CASK_LIST_CACHE

    try:
        result = subprocess.run(
            ["brew", "list", "--cask"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            _CASK_LIST_CACHE = result.stdout.strip().split("\n")
        else:
            _CASK_LIST_CACHE = []
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        _CASK_LIST_CACHE = []

    return _CASK_LIST_CACHE


def _get_install_method(app_path: Path, bundle_id: Optional[str]) -> str:
    """Determine how an application was installed.

    Args:
        app_path: Path to the .app bundle
        bundle_id: The app's bundle identifier

    Returns:
        Install method: 'mas', 'cask', 'system', or 'unknown'
    """
    # Check for Mac App Store receipt
    receipt_path = app_path / "Contents" / "_MASReceipt" / "receipt"
    if receipt_path.exists():
        return "mas"

    # Check if app is in system location (pre-installed)
    app_name = app_path.name
    system_apps = {
        "Safari.app",
        "Mail.app",
        "Calendar.app",
        "Contacts.app",
        "Notes.app",
        "Reminders.app",
        "Photos.app",
        "Messages.app",
        "FaceTime.app",
        "Music.app",
        "Podcasts.app",
        "TV.app",
        "News.app",
        "Stocks.app",
        "Books.app",
        "Maps.app",
        "Preview.app",
        "TextEdit.app",
        "Calculator.app",
        "Dictionary.app",
        "Finder.app",
        "System Preferences.app",
        "System Settings.app",
        "App Store.app",
        "Automator.app",
        "Console.app",
        "Activity Monitor.app",
        "Disk Utility.app",
        "Keychain Access.app",
        "Terminal.app",
        "Migration Assistant.app",
        "Screenshot.app",
        "Font Book.app",
        "Script Editor.app",
        "Siri.app",
        "Time Machine.app",
        "VoiceOver Utility.app",
    }
    if app_name in system_apps:
        return "system"

    # Check if installed via Homebrew Cask (using cached list)
    if bundle_id:
        cask_list = _get_cask_list()
        if cask_list:
            # Check if any cask name matches part of the app name
            app_lower = app_name.lower().replace(".app", "").replace(" ", "-")
            for cask in cask_list:
                if cask and (cask.lower() in app_lower or app_lower in cask.lower()):
                    return "cask"

    return "unknown"


def scan() -> dict:
    """Scan for installed applications.

    Scans /Applications and ~/Applications for .app bundles and extracts
    bundle IDs, versions, and installation methods.

    Returns:
        Dictionary with 'applications' list and 'errors' list
    """
    applications = []
    errors = []

    # Directories to scan
    scan_dirs = [
        Path("/Applications"),
        Path.home() / "Applications",
    ]

    for scan_dir in scan_dirs:
        if not scan_dir.exists():
            continue

        try:
            # Get all .app bundles (non-recursive for top level)
            for app_path in scan_dir.glob("*.app"):
                if not app_path.is_dir():
                    continue

                bundle_info = _get_bundle_info(app_path)
                if bundle_info is None:
                    errors.append(
                        {
                            "path": str(app_path),
                            "error": "Could not read Info.plist",
                        }
                    )
                    # Still include the app with minimal info
                    applications.append(
                        {
                            "name": app_path.stem,
                            "path": str(app_path),
                            "bundle_id": None,
                            "version": None,
                            "install_method": "unknown",
                            "location": "user" if "Users" in str(app_path) else "system",
                        }
                    )
                    continue

                install_method = _get_install_method(app_path, bundle_info.get("bundle_id"))

                applications.append(
                    {
                        "name": bundle_info.get("name") or app_path.stem,
                        "path": str(app_path),
                        "bundle_id": bundle_info.get("bundle_id"),
                        "version": bundle_info.get("version"),
                        "install_method": install_method,
                        "location": "user" if "Users" in str(app_path) else "system",
                    }
                )

            # Also check for apps in subdirectories (some installers create folders)
            for subdir in scan_dir.iterdir():
                if subdir.is_dir() and not subdir.name.endswith(".app"):
                    for app_path in subdir.glob("*.app"):
                        if not app_path.is_dir():
                            continue

                        bundle_info = _get_bundle_info(app_path)
                        if bundle_info is None:
                            continue

                        install_method = _get_install_method(
                            app_path, bundle_info.get("bundle_id")
                        )

                        applications.append(
                            {
                                "name": bundle_info.get("name") or app_path.stem,
                                "path": str(app_path),
                                "bundle_id": bundle_info.get("bundle_id"),
                                "version": bundle_info.get("version"),
                                "install_method": install_method,
                                "location": "user" if "Users" in str(app_path) else "system",
                            }
                        )

        except PermissionError as e:
            errors.append({"path": str(scan_dir), "error": str(e)})

    # Sort applications by name
    applications.sort(key=lambda x: x["name"].lower())

    return {
        "applications": applications,
        "count": len(applications),
        "errors": errors,
    }


if __name__ == "__main__":
    import json

    result = scan()
    print(json.dumps(result, indent=2))

"""Scanner for code editor extensions (VS Code, Cursor, Zed).

Scans for installed extensions and user settings for popular code editors.
Supports VS Code profiles - scans extensions for each profile separately.
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


def _read_json_file(path: Path) -> Optional[dict]:
    """Read a JSON file and return its contents."""
    if not path.exists():
        return None
    try:
        content = path.read_text()
        # Handle JSON with comments (common in VS Code settings)
        # Simple approach: remove single-line comments
        lines = []
        for line in content.split("\n"):
            stripped = line.strip()
            if not stripped.startswith("//"):
                # Also handle trailing comments (not perfect but handles common cases)
                comment_idx = line.find("//")
                if comment_idx > 0 and '"' not in line[comment_idx:]:
                    line = line[:comment_idx]
                lines.append(line)
        clean_content = "\n".join(lines)
        return json_lib.loads(clean_content)
    except (OSError, json_lib.JSONDecodeError):
        return None


def _get_vscode_user_path(cli_cmd: str) -> Optional[Path]:
    """Get the User directory path for a VS Code-style editor.

    Args:
        cli_cmd: The CLI command (code, code-insiders, cursor)

    Returns:
        Path to the User directory, or None if unknown
    """
    base_path = Path.home() / "Library/Application Support"

    paths = {
        "code": base_path / "Code/User",
        "code-insiders": base_path / "Code - Insiders/User",
        "cursor": base_path / "Cursor/User",
    }

    return paths.get(cli_cmd)


def _get_editor_profiles(cli_cmd: str) -> list[dict]:
    """Get profiles from VS Code storage.json.

    Args:
        cli_cmd: The CLI command (code, code-insiders, cursor)

    Returns:
        List of profile dictionaries with 'name' and 'id' keys
    """
    user_path = _get_vscode_user_path(cli_cmd)
    if not user_path:
        return []

    storage_file = user_path / "globalStorage/storage.json"
    if not storage_file.exists():
        return []

    try:
        content = storage_file.read_text()
        data = json_lib.loads(content)

        profiles = []
        user_data_profiles = data.get("userDataProfiles", [])
        for profile in user_data_profiles:
            name = profile.get("name")
            location = profile.get("location")
            if name:
                profiles.append({
                    "name": name,
                    "id": location,
                })

        return profiles
    except (OSError, json_lib.JSONDecodeError):
        return []


def _scan_extensions_for_profile(cli_cmd: str, profile_name: Optional[str] = None) -> list[dict]:
    """Scan extensions for a specific profile.

    Args:
        cli_cmd: The CLI command (code, code-insiders, cursor)
        profile_name: Profile name, or None/empty for default profile

    Returns:
        List of extension dictionaries with 'id' and 'version' keys
    """
    if not _check_command_exists(cli_cmd):
        return []

    # Build command
    if profile_name and profile_name != "Default":
        cmd = [cli_cmd, "--profile", profile_name, "--list-extensions", "--show-versions"]
    else:
        cmd = [cli_cmd, "--list-extensions", "--show-versions"]

    output = _run_command(cmd, timeout=30)
    if not output:
        return []

    extensions = []
    for line in output.split("\n"):
        line = line.strip()
        if not line:
            continue

        if "@" in line:
            # Format: "publisher.extension@version"
            at_idx = line.rfind("@")
            extension_id = line[:at_idx]
            version = line[at_idx + 1:]
            extensions.append({
                "id": extension_id,
                "version": version,
            })
        else:
            extensions.append({
                "id": line,
                "version": None,
            })

    return extensions


def _scan_vscode_style_editor(
    name: str,
    cli_cmd: str,
    app_paths: list[Path],
) -> dict:
    """Scan a VS Code-style editor with profile support.

    Args:
        name: Display name of the editor
        cli_cmd: CLI command to use
        app_paths: List of possible app bundle paths

    Returns:
        Dictionary with editor info including profiles and extensions
    """
    result = {
        "installed": False,
        "cli_available": False,
        "profiles": [],
        "total_extensions": 0,
        "settings_path": None,
        "keybindings_path": None,
        "snippets_path": None,
        "errors": [],
    }

    # Check if app is installed
    app_installed = any(p.exists() for p in app_paths)
    cli_available = _check_command_exists(cli_cmd)

    if not app_installed and not cli_available:
        return result

    result["installed"] = True
    result["cli_available"] = cli_available

    # Get settings paths
    user_path = _get_vscode_user_path(cli_cmd)
    if user_path and user_path.exists():
        settings_file = user_path / "settings.json"
        if settings_file.exists():
            result["settings_path"] = str(settings_file)

        keybindings_file = user_path / "keybindings.json"
        if keybindings_file.exists():
            result["keybindings_path"] = str(keybindings_file)

        snippets_dir = user_path / "snippets"
        if snippets_dir.exists():
            result["snippets_path"] = str(snippets_dir)

    if not cli_available:
        result["errors"].append(f"{name} app installed but CLI '{cli_cmd}' not in PATH")
        return result

    # Scan Default profile first
    default_extensions = _scan_extensions_for_profile(cli_cmd, None)
    default_extensions.sort(key=lambda x: x["id"].lower())

    result["profiles"].append({
        "name": "Default",
        "id": None,
        "extensions": default_extensions,
        "extensions_count": len(default_extensions),
    })
    result["total_extensions"] = len(default_extensions)

    # Get additional profiles from storage.json
    stored_profiles = _get_editor_profiles(cli_cmd)

    for profile in stored_profiles:
        profile_name = profile.get("name")
        profile_id = profile.get("id")

        if not profile_name:
            continue

        profile_extensions = _scan_extensions_for_profile(cli_cmd, profile_name)
        profile_extensions.sort(key=lambda x: x["id"].lower())

        result["profiles"].append({
            "name": profile_name,
            "id": profile_id,
            "extensions": profile_extensions,
            "extensions_count": len(profile_extensions),
        })
        result["total_extensions"] += len(profile_extensions)

    return result


def scan_vscode() -> dict:
    """Scan VS Code for installed extensions and settings.

    Scans all profiles and returns extensions per profile.

    Returns:
        Dictionary with profiles, extensions, settings info, and paths
    """
    app_paths = [
        Path("/Applications/Visual Studio Code.app"),
        Path.home() / "Applications/Visual Studio Code.app",
    ]

    return _scan_vscode_style_editor("VS Code", "code", app_paths)


def scan_vscode_insiders() -> dict:
    """Scan VS Code Insiders for installed extensions and settings.

    Scans all profiles and returns extensions per profile.

    Returns:
        Dictionary with profiles, extensions, settings info, and paths
    """
    app_paths = [
        Path("/Applications/Visual Studio Code - Insiders.app"),
        Path.home() / "Applications/Visual Studio Code - Insiders.app",
    ]

    return _scan_vscode_style_editor("VS Code Insiders", "code-insiders", app_paths)


def scan_cursor() -> dict:
    """Scan Cursor for installed extensions and settings.

    Scans all profiles and returns extensions per profile.

    Returns:
        Dictionary with profiles, extensions, settings info, and paths
    """
    app_paths = [
        Path("/Applications/Cursor.app"),
        Path.home() / "Applications/Cursor.app",
    ]

    return _scan_vscode_style_editor("Cursor", "cursor", app_paths)


def scan_zed() -> dict:
    """Scan Zed for extensions and settings.

    Returns:
        Dictionary with extensions, themes, and settings info
    """
    result = {
        "installed": False,
        "extensions": [],
        "themes": [],
        "settings_path": None,
        "keymap_path": None,
        "errors": [],
    }

    # Check if Zed is installed
    app_path = Path("/Applications/Zed.app")
    user_app_path = Path.home() / "Applications/Zed.app"

    if not app_path.exists() and not user_app_path.exists():
        return result

    result["installed"] = True

    # Zed config is in ~/.config/zed/
    config_dir = Path.home() / ".config/zed"
    if config_dir.exists():
        settings_file = config_dir / "settings.json"
        if settings_file.exists():
            result["settings_path"] = str(settings_file)

            # Parse settings to find installed themes
            settings = _read_json_file(settings_file)
            if settings:
                theme = settings.get("theme")
                if theme:
                    result["themes"].append(theme)

        keymap_file = config_dir / "keymap.json"
        if keymap_file.exists():
            result["keymap_path"] = str(keymap_file)

        # Check extensions directory
        extensions_dir = config_dir / "extensions"
        if extensions_dir.exists():
            for ext_dir in extensions_dir.iterdir():
                if ext_dir.is_dir() and not ext_dir.name.startswith("."):
                    result["extensions"].append({
                        "id": ext_dir.name,
                        "path": str(ext_dir),
                    })

    result["extensions"].sort(key=lambda x: x["id"].lower())
    return result


def scan_sublime() -> dict:
    """Scan Sublime Text for packages and settings.

    Returns:
        Dictionary with packages, settings info, and paths
    """
    result = {
        "installed": False,
        "packages": [],
        "settings_path": None,
        "keymap_path": None,
        "errors": [],
    }

    # Check if Sublime Text is installed
    app_paths = [
        Path("/Applications/Sublime Text.app"),
        Path("/Applications/Sublime Text 4.app"),
        Path("/Applications/Sublime Text 3.app"),
    ]
    installed = any(p.exists() for p in app_paths)

    if not installed:
        return result

    result["installed"] = True

    # Sublime config is in ~/Library/Application Support/Sublime Text/
    for version in ["", " 4", " 3"]:
        config_dir = Path.home() / f"Library/Application Support/Sublime Text{version}"
        if config_dir.exists():
            # User settings
            user_dir = config_dir / "Packages/User"
            if user_dir.exists():
                settings_file = user_dir / "Preferences.sublime-settings"
                if settings_file.exists():
                    result["settings_path"] = str(settings_file)

                # Check for keymap file
                keymap_file = user_dir / "Default (OSX).sublime-keymap"
                if keymap_file.exists():
                    result["keymap_path"] = str(keymap_file)

                # Check for installed packages
                packages_dir = config_dir / "Installed Packages"
                if packages_dir.exists():
                    for pkg in packages_dir.glob("*.sublime-package"):
                        result["packages"].append({
                            "name": pkg.stem,
                            "path": str(pkg),
                        })

                # Also check Package Control settings
                pc_settings = user_dir / "Package Control.sublime-settings"
                if pc_settings.exists():
                    pc_data = _read_json_file(pc_settings)
                    if pc_data and "installed_packages" in pc_data:
                        for pkg in pc_data["installed_packages"]:
                            if not any(p["name"] == pkg for p in result["packages"]):
                                result["packages"].append({
                                    "name": pkg,
                                    "source": "package_control",
                                })

            break

    result["packages"].sort(key=lambda x: x["name"].lower())
    return result


def scan_jetbrains() -> dict:
    """Scan JetBrains IDEs for installed instances.

    Returns:
        Dictionary with installed JetBrains IDEs and their paths
    """
    result = {
        "ides": [],
        "errors": [],
    }

    jetbrains_apps = [
        ("IntelliJ IDEA.app", "intellij"),
        ("IntelliJ IDEA CE.app", "intellij-ce"),
        ("PyCharm.app", "pycharm"),
        ("PyCharm CE.app", "pycharm-ce"),
        ("WebStorm.app", "webstorm"),
        ("GoLand.app", "goland"),
        ("CLion.app", "clion"),
        ("Rider.app", "rider"),
        ("RubyMine.app", "rubymine"),
        ("DataGrip.app", "datagrip"),
        ("PhpStorm.app", "phpstorm"),
        ("AppCode.app", "appcode"),
        ("Android Studio.app", "android-studio"),
    ]

    apps_dir = Path("/Applications")
    for app_name, ide_id in jetbrains_apps:
        app_path = apps_dir / app_name
        if app_path.exists():
            result["ides"].append({
                "id": ide_id,
                "name": app_name.replace(".app", ""),
                "path": str(app_path),
            })

    return result


def scan() -> dict:
    """Scan all code editors for extensions and settings.

    Returns:
        Dictionary with results from all editors
    """
    vscode_result = scan_vscode()
    vscode_insiders_result = scan_vscode_insiders()
    cursor_result = scan_cursor()
    zed_result = scan_zed()
    sublime_result = scan_sublime()
    jetbrains_result = scan_jetbrains()

    return {
        "vscode": {
            "installed": vscode_result["installed"],
            "cli_available": vscode_result.get("cli_available", False),
            "profiles": vscode_result.get("profiles", []),
            "profiles_count": len(vscode_result.get("profiles", [])),
            "total_extensions": vscode_result.get("total_extensions", 0),
            "settings_path": vscode_result.get("settings_path"),
            "keybindings_path": vscode_result.get("keybindings_path"),
            "snippets_path": vscode_result.get("snippets_path"),
            "errors": vscode_result.get("errors", []),
        },
        "vscode_insiders": {
            "installed": vscode_insiders_result["installed"],
            "cli_available": vscode_insiders_result.get("cli_available", False),
            "profiles": vscode_insiders_result.get("profiles", []),
            "profiles_count": len(vscode_insiders_result.get("profiles", [])),
            "total_extensions": vscode_insiders_result.get("total_extensions", 0),
            "settings_path": vscode_insiders_result.get("settings_path"),
            "keybindings_path": vscode_insiders_result.get("keybindings_path"),
            "snippets_path": vscode_insiders_result.get("snippets_path"),
            "errors": vscode_insiders_result.get("errors", []),
        },
        "cursor": {
            "installed": cursor_result["installed"],
            "cli_available": cursor_result.get("cli_available", False),
            "profiles": cursor_result.get("profiles", []),
            "profiles_count": len(cursor_result.get("profiles", [])),
            "total_extensions": cursor_result.get("total_extensions", 0),
            "settings_path": cursor_result.get("settings_path"),
            "keybindings_path": cursor_result.get("keybindings_path"),
            "snippets_path": cursor_result.get("snippets_path"),
            "errors": cursor_result.get("errors", []),
        },
        "zed": {
            "installed": zed_result["installed"],
            "extensions": zed_result["extensions"],
            "extensions_count": len(zed_result["extensions"]),
            "themes": zed_result["themes"],
            "settings_path": zed_result["settings_path"],
            "keymap_path": zed_result["keymap_path"],
            "errors": zed_result["errors"],
        },
        "sublime": {
            "installed": sublime_result["installed"],
            "packages": sublime_result["packages"],
            "packages_count": len(sublime_result["packages"]),
            "settings_path": sublime_result["settings_path"],
            "keymap_path": sublime_result.get("keymap_path"),
            "errors": sublime_result["errors"],
        },
        "jetbrains": {
            "ides": jetbrains_result["ides"],
            "ides_count": len(jetbrains_result["ides"]),
            "errors": jetbrains_result["errors"],
        },
    }


if __name__ == "__main__":
    import json

    result = scan()
    print(json.dumps(result, indent=2))

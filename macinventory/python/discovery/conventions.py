"""Tier 2 Discovery: Convention-Based Path Discovery.

Checks standard macOS locations for application settings when
an app is not found in the hints database.

This is the second discovery tier:
- Fast (only filesystem checks, no network)
- Free (no API calls)
- Medium confidence (conventions are common but not universal)

macOS Settings Patterns Checked:
1. ~/.config/appname/ (XDG-style)
2. ~/.appname/ (Traditional dotfile directory)
3. ~/Library/Application Support/AppName/
4. ~/Library/Preferences/*.plist
5. ~/Library/Containers/ (Sandboxed apps)
6. ~/Library/Group Containers/ (App Groups)
"""

import os
import re
from pathlib import Path
from typing import Optional


def generate_name_variations(app_name: str) -> list[str]:
    """Generate common variations of an application name.

    macOS apps may store configs under various name formats.
    This generates likely variations to check.

    Args:
        app_name: The application name (e.g., "Visual Studio Code")

    Returns:
        List of name variations to check (e.g., ["visual-studio-code", "visualstudiocode", "vscode", "Code"])

    Examples:
        >>> generate_name_variations("Visual Studio Code")
        ['visual-studio-code', 'visualstudiocode', 'visual_studio_code', 'vscode', 'Code']
        >>> generate_name_variations("Docker Desktop")
        ['docker-desktop', 'dockerdesktop', 'docker_desktop', 'docker', 'Desktop']
    """
    variations = []

    # Remove .app suffix if present
    name = app_name.removesuffix('.app').strip()

    # Original name (for Library/Application Support which often uses original case)
    if name not in variations:
        variations.append(name)

    # Lowercase with hyphens (most common for dotfiles)
    hyphenated = re.sub(r'[^a-zA-Z0-9]', '-', name).lower()
    hyphenated = re.sub(r'-+', '-', hyphenated).strip('-')
    if hyphenated and hyphenated not in variations:
        variations.append(hyphenated)

    # Lowercase without separators
    no_sep = re.sub(r'[^a-zA-Z0-9]', '', name).lower()
    if no_sep and no_sep not in variations:
        variations.append(no_sep)

    # Lowercase with underscores
    underscored = re.sub(r'[^a-zA-Z0-9]', '_', name).lower()
    underscored = re.sub(r'_+', '_', underscored).strip('_')
    if underscored and underscored not in variations:
        variations.append(underscored)

    # First word only (common for multi-word apps like "Docker Desktop" -> "docker")
    first_word = name.split()[0].lower() if name.split() else None
    if first_word and len(first_word) > 2 and first_word not in variations:
        variations.append(first_word)

    # Last word only (useful for "Visual Studio Code" -> "Code")
    words = name.split()
    if len(words) > 1:
        last_word = words[-1]
        if last_word and len(last_word) > 2 and last_word not in variations:
            variations.append(last_word)

    # CamelCase to lowercase (e.g., "VSCode" -> "vscode")
    if name != name.lower():
        lower = name.lower()
        if lower not in variations:
            variations.append(lower)

    return variations


def generate_bundle_id_variations(bundle_id: str) -> list[str]:
    """Generate path variations from a bundle identifier.

    Bundle IDs like "com.microsoft.VSCode" can map to paths like:
    - Library/Application Support/com.microsoft.VSCode/
    - Library/Preferences/com.microsoft.VSCode.plist

    Args:
        bundle_id: The bundle identifier (e.g., "com.microsoft.VSCode")

    Returns:
        List of path-friendly variations derived from the bundle ID
    """
    if not bundle_id:
        return []

    variations = [bundle_id]  # Full bundle ID

    # Last component (e.g., "VSCode" from "com.microsoft.VSCode")
    last = bundle_id.split('.')[-1]
    if last and last.lower() not in [v.lower() for v in variations]:
        variations.append(last)
        variations.append(last.lower())

    # Second-to-last + last (e.g., "microsoft.VSCode")
    parts = bundle_id.split('.')
    if len(parts) >= 2:
        suffix = '.'.join(parts[-2:])
        if suffix not in variations:
            variations.append(suffix)

    return variations


def _normalize_path_for_dedup(path: Path) -> str:
    """Normalize a path for deduplication on case-insensitive filesystems.

    On macOS HFS+/APFS (case-insensitive by default), /Users/.Docker and
    /Users/.docker are the same path. We use resolve() and lowercase to
    deduplicate.

    Args:
        path: Path to normalize

    Returns:
        Lowercase resolved path string for deduplication
    """
    try:
        # resolve() canonicalizes the path and follows symlinks
        return str(path.resolve()).lower()
    except OSError:
        # Path doesn't exist, just lowercase it
        return str(path).lower()


def discover_from_conventions(
    app_name: str,
    bundle_id: Optional[str] = None,
    check_exists: bool = True
) -> dict:
    """Check standard macOS locations for app settings.

    Searches common macOS configuration patterns to find where
    an application might store its settings.

    Args:
        app_name: Application name (e.g., "Visual Studio Code")
        bundle_id: Optional bundle identifier (e.g., "com.microsoft.VSCode")
        check_exists: If True, only return paths that exist on filesystem

    Returns:
        Dictionary with discovery results:
        {
            'app_name': str,
            'bundle_id': str or None,
            'configuration_files': list[str],  # Relative to $HOME
            'xdg_configuration_files': list[str],  # Relative to $XDG_CONFIG_HOME
            'found_paths': list[str],  # Absolute paths (for validation)
            'confidence': 'high' | 'medium' | 'low',
            'source': 'conventions'
        }
    """
    home = Path.home()
    xdg_config_home = Path(os.environ.get('XDG_CONFIG_HOME', home / '.config'))

    name_variations = generate_name_variations(app_name)
    bundle_variations = generate_bundle_id_variations(bundle_id) if bundle_id else []

    # Paths relative to $HOME (configuration_files)
    # Use directory paths only (trailing slash) - we'll handle files separately
    home_relative_candidates = []

    for name in name_variations:
        # Pattern 2: ~/.appname/ (Traditional dotfile directory)
        # Only add directory version - avoids duplication with file version
        home_relative_candidates.append(f".{name}/")

        # Pattern 3: ~/Library/Application Support/AppName/
        home_relative_candidates.append(f"Library/Application Support/{name}/")

    # Bundle ID specific paths
    for bid in bundle_variations:
        # Pattern 3: ~/Library/Application Support/bundle.id/
        home_relative_candidates.append(f"Library/Application Support/{bid}/")

        # Pattern 4: ~/Library/Preferences/*.plist
        home_relative_candidates.append(f"Library/Preferences/{bid}.plist")

        # Pattern 5: ~/Library/Containers/ (Sandboxed apps)
        home_relative_candidates.append(f"Library/Containers/{bid}/")
        home_relative_candidates.append(f"Library/Containers/{bid}/Data/Library/Preferences/")
        home_relative_candidates.append(f"Library/Containers/{bid}/Data/Library/Application Support/")

        # Pattern 6: ~/Library/Group Containers/ (App Groups)
        # Group containers often have prefixes like "group." or team IDs
        home_relative_candidates.append(f"Library/Group Containers/{bid}/")
        home_relative_candidates.append(f"Library/Group Containers/group.{bid}/")

    # Paths relative to $XDG_CONFIG_HOME (xdg_configuration_files)
    xdg_relative_candidates = []

    for name in name_variations:
        # Pattern 1: ~/.config/appname/ (XDG-style)
        xdg_relative_candidates.append(f"{name}/")

    # Remove duplicates while preserving order (case-insensitive for macOS)
    seen_home = set()
    unique_home = []
    for path in home_relative_candidates:
        key = path.lower()
        if key not in seen_home:
            seen_home.add(key)
            unique_home.append(path)
    home_relative_candidates = unique_home

    seen_xdg = set()
    unique_xdg = []
    for path in xdg_relative_candidates:
        key = path.lower()
        if key not in seen_xdg:
            seen_xdg.add(key)
            unique_xdg.append(path)
    xdg_relative_candidates = unique_xdg

    # Check which paths actually exist (if requested)
    if check_exists:
        found_config_files = []
        found_xdg_files = []
        found_absolute_paths = []
        # Track resolved paths to avoid duplicates (case-insensitive)
        seen_resolved = set()

        for path in home_relative_candidates:
            full_path = home / path
            if full_path.exists():
                # Use resolved lowercase path as dedup key
                resolved_key = _normalize_path_for_dedup(full_path)
                if resolved_key not in seen_resolved:
                    seen_resolved.add(resolved_key)
                    # Normalize: remove trailing slash for files, keep for directories
                    normalized = path.rstrip('/') if full_path.is_file() else path.rstrip('/')
                    found_config_files.append(normalized)
                    found_absolute_paths.append(str(full_path.resolve()))

        for path in xdg_relative_candidates:
            full_path = xdg_config_home / path
            if full_path.exists():
                resolved_key = _normalize_path_for_dedup(full_path)
                if resolved_key not in seen_resolved:
                    seen_resolved.add(resolved_key)
                    normalized = path.rstrip('/') if full_path.is_file() else path.rstrip('/')
                    found_xdg_files.append(normalized)
                    found_absolute_paths.append(str(full_path.resolve()))
    else:
        found_config_files = home_relative_candidates
        found_xdg_files = xdg_relative_candidates
        found_absolute_paths = []

    # Determine confidence based on what was found
    total_found = len(found_config_files) + len(found_xdg_files)
    if total_found == 0:
        confidence = 'low'
    elif total_found == 1:
        confidence = 'medium'
    else:
        confidence = 'high'

    return {
        'app_name': app_name,
        'bundle_id': bundle_id,
        'configuration_files': found_config_files,
        'xdg_configuration_files': found_xdg_files,
        'found_paths': found_absolute_paths,
        'checked_paths': {
            'home_relative': home_relative_candidates,
            'xdg_relative': xdg_relative_candidates
        },
        'confidence': confidence,
        'source': 'conventions'
    }


def discover_common_patterns(app_name: str, bundle_id: Optional[str] = None) -> list[str]:
    """Get a list of common paths to check for an app (for LLM fallback).

    This returns ALL candidate paths that would typically be checked,
    useful for telling the LLM which paths have already been checked.
    Paths are deduplicated (case-insensitive for macOS).

    Args:
        app_name: Application name
        bundle_id: Optional bundle identifier

    Returns:
        List of absolute paths that would be checked by convention discovery
    """
    result = discover_from_conventions(app_name, bundle_id, check_exists=False)
    home = Path.home()
    xdg_config_home = Path(os.environ.get('XDG_CONFIG_HOME', home / '.config'))

    # Use case-insensitive deduplication for macOS
    seen = set()
    paths = []

    for path in result.get('checked_paths', {}).get('home_relative', []):
        full_path = str(home / path)
        key = full_path.lower()
        if key not in seen:
            seen.add(key)
            paths.append(full_path)

    for path in result.get('checked_paths', {}).get('xdg_relative', []):
        full_path = str(xdg_config_home / path)
        key = full_path.lower()
        if key not in seen:
            seen.add(key)
            paths.append(full_path)

    return paths


def check_known_patterns(app_name: str, bundle_id: Optional[str] = None) -> dict:
    """Quick check for whether an app follows known patterns.

    This is a lighter-weight check that just determines IF settings exist,
    without building the full discovery result.

    Args:
        app_name: Application name
        bundle_id: Optional bundle identifier

    Returns:
        Dictionary with:
        {
            'has_settings': bool,
            'primary_location': str or None,  # First found path
            'pattern_type': str or None  # 'xdg', 'dotfile', 'library', 'plist', 'container'
        }
    """
    home = Path.home()
    xdg_config_home = Path(os.environ.get('XDG_CONFIG_HOME', home / '.config'))

    name_variations = generate_name_variations(app_name)

    # Check patterns in order of preference
    pattern_checks = []

    for name in name_variations[:3]:  # Limit to top 3 variations for speed
        # XDG style (most modern)
        pattern_checks.append((xdg_config_home / name, 'xdg'))

        # Dotfile directory
        pattern_checks.append((home / f".{name}", 'dotfile'))

        # Library/Application Support
        pattern_checks.append((home / "Library/Application Support" / name, 'library'))

    # Bundle ID specific
    if bundle_id:
        pattern_checks.append((home / f"Library/Preferences/{bundle_id}.plist", 'plist'))
        pattern_checks.append((home / f"Library/Containers/{bundle_id}", 'container'))
        pattern_checks.append((home / f"Library/Application Support/{bundle_id}", 'library'))

    for path, pattern_type in pattern_checks:
        if path.exists():
            return {
                'has_settings': True,
                'primary_location': str(path),
                'pattern_type': pattern_type
            }

    return {
        'has_settings': False,
        'primary_location': None,
        'pattern_type': None
    }

#!/usr/bin/env python3
"""Validate hints database entries for MacInventory.

Usage:
    python validate-hints.py                    # Validate entire database
    python validate-hints.py app-name           # Validate single app
    python validate-hints.py --check-paths      # Also verify paths exist
    python validate-hints.py --verbose          # Show detailed output
"""

import sys
import os
from pathlib import Path
from typing import List

# Try to import yaml, provide helpful error if missing
try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Install with: pip install pyyaml")
    sys.exit(1)

VALID_INSTALL_METHODS = {
    'cask', 'formula', 'mas', 'dmg', 'system',
    'npm', 'pip', 'cargo', 'unknown'
}


def validate_entry(name: str, config: dict) -> List[str]:
    """Validate a single hints entry. Returns list of errors."""
    errors = []

    # Check required fields
    if 'bundle_id' not in config:
        errors.append(f"{name}: Missing 'bundle_id' (use null for CLI tools)")

    # Check install_method
    method = config.get('install_method', '')
    if method not in VALID_INSTALL_METHODS:
        errors.append(f"{name}: Invalid install_method '{method}'. "
                      f"Valid: {', '.join(sorted(VALID_INSTALL_METHODS))}")

    # Check at least one config location
    has_configs = (
        config.get('configuration_files') or
        config.get('xdg_configuration_files')
    )
    if not has_configs:
        errors.append(f"{name}: Must have configuration_files or xdg_configuration_files")

    # Validate configuration_files paths
    for path in config.get('configuration_files', []):
        if path.startswith('/'):
            errors.append(f"{name}: Absolute path not allowed in configuration_files: {path}")
        if '..' in path:
            errors.append(f"{name}: Path traversal (..) not allowed: {path}")

    # Validate xdg_configuration_files paths
    for path in config.get('xdg_configuration_files', []):
        if path.startswith('/'):
            errors.append(f"{name}: Absolute path not allowed in xdg_configuration_files: {path}")
        if '..' in path:
            errors.append(f"{name}: Path traversal (..) not allowed: {path}")

    # Validate exclude_files if present
    for path in config.get('exclude_files', []):
        if path.startswith('/'):
            errors.append(f"{name}: Absolute path not allowed in exclude_files: {path}")

    # Validate extensions_cmd if present (should be a string)
    extensions_cmd = config.get('extensions_cmd')
    if extensions_cmd is not None and not isinstance(extensions_cmd, str):
        errors.append(f"{name}: extensions_cmd must be a string")

    # Validate notes if present (should be a string)
    notes = config.get('notes')
    if notes is not None and not isinstance(notes, str):
        errors.append(f"{name}: notes must be a string")

    return errors


def check_paths_exist(name: str, config: dict) -> List[str]:
    """Check if configuration paths actually exist on this system."""
    warnings = []
    home = Path.home()
    xdg_config = Path(os.environ.get('XDG_CONFIG_HOME', home / '.config'))

    # Check configuration_files (relative to $HOME)
    for path in config.get('configuration_files', []):
        full_path = home / path
        if not full_path.exists():
            warnings.append(f"{name}: Path not found (may be OK if app not installed): {path}")

    # Check xdg_configuration_files (relative to $XDG_CONFIG_HOME)
    for path in config.get('xdg_configuration_files', []):
        full_path = xdg_config / path
        if not full_path.exists():
            warnings.append(f"{name}: XDG path not found (may be OK if app not installed): {path}")

    return warnings


def validate_yaml_structure(hints: dict) -> List[str]:
    """Validate overall YAML structure."""
    errors = []

    if not isinstance(hints, dict):
        errors.append("Root must be a dictionary of app entries")
        return errors

    for name, config in hints.items():
        if not isinstance(name, str):
            errors.append(f"App name must be a string, got: {type(name)}")
        if not isinstance(config, dict):
            errors.append(f"{name}: App config must be a dictionary, got: {type(config)}")

    return errors


def find_hints_database() -> Path:
    """Find the hints database relative to script location."""
    script_dir = Path(__file__).parent.resolve()

    # Try different relative paths
    possible_paths = [
        script_dir.parent.parent.parent / 'data' / 'app-hints.yaml',
        script_dir / '..' / '..' / '..' / 'data' / 'app-hints.yaml',
    ]

    for path in possible_paths:
        resolved = path.resolve()
        if resolved.exists():
            return resolved

    # Also check if running from plugin root
    cwd = Path.cwd()
    cwd_path = cwd / 'data' / 'app-hints.yaml'
    if cwd_path.exists():
        return cwd_path

    macinventory_path = cwd / 'macinventory' / 'data' / 'app-hints.yaml'
    if macinventory_path.exists():
        return macinventory_path

    return possible_paths[0].resolve()


def print_summary(errors: List[str], warnings: List[str], total: int, verbose: bool):
    """Print validation summary."""
    if errors:
        print("\n" + "=" * 60)
        print("ERRORS:")
        print("=" * 60)
        for error in errors:
            print(f"  ✗ {error}")

    if warnings and verbose:
        print("\n" + "-" * 60)
        print("WARNINGS (paths not found on this system):")
        print("-" * 60)
        for warning in warnings:
            print(f"  ⚠ {warning}")

    print("\n" + "=" * 60)
    if not errors:
        print(f"✓ Validated {total} entries successfully")
        if warnings:
            print(f"  ({len(warnings)} path warnings - apps may not be installed)")
    else:
        print(f"✗ Found {len(errors)} error(s) in {total} entries")


def main():
    # Parse arguments
    args = sys.argv[1:]
    check_paths = '--check-paths' in args
    verbose = '--verbose' in args or '-v' in args

    # Remove flags from args
    args = [a for a in args if not a.startswith('-')]
    app_filter = args[0] if args else None

    # Find hints database
    hints_path = find_hints_database()

    if not hints_path.exists():
        print(f"Error: Hints database not found at {hints_path}")
        print("\nExpected location (installed plugin):")
        print("  ~/.claude/plugins/macinventory@MacInventory/skills/macos-discovery/scripts/validate-hints.py")
        print("  ~/.claude/plugins/macinventory@MacInventory/data/app-hints.yaml")
        print("\nOr for development:")
        print("  macinventory/skills/macos-discovery/scripts/validate-hints.py")
        print("  macinventory/data/app-hints.yaml")
        sys.exit(1)

    if verbose:
        print(f"Loading hints from: {hints_path}")

    # Load and parse YAML
    try:
        with open(hints_path) as f:
            hints = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"Error: Invalid YAML syntax in {hints_path}")
        print(f"  {e}")
        sys.exit(1)

    # Validate YAML structure
    structure_errors = validate_yaml_structure(hints)
    if structure_errors:
        print("YAML Structure Errors:")
        for error in structure_errors:
            print(f"  ✗ {error}")
        sys.exit(1)

    # Filter to specific app if provided
    if app_filter:
        if app_filter not in hints:
            print(f"Error: App '{app_filter}' not found in hints database")
            print(f"\nAvailable apps: {', '.join(sorted(hints.keys()))}")
            sys.exit(1)
        hints = {app_filter: hints[app_filter]}

    all_errors = []
    all_warnings = []

    # Validate each entry
    for name, config in hints.items():
        errors = validate_entry(name, config)
        all_errors.extend(errors)

        if check_paths:
            warnings = check_paths_exist(name, config)
            all_warnings.extend(warnings)

    # Print results
    print_summary(all_errors, all_warnings, len(hints), verbose)

    # Exit with appropriate code
    sys.exit(1 if all_errors else 0)


if __name__ == '__main__':
    main()

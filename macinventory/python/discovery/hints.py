"""Tier 1 Discovery: Hints Database Loader.

Provides fast lookup of application settings from a curated YAML database.
This is the primary discovery method - instant lookup, free, highest confidence.

The hints database uses the convention:
    - configuration_files: Paths relative to $HOME
    - xdg_configuration_files: Paths relative to $XDG_CONFIG_HOME

Security constraints:
    - All paths must be home-relative (no absolute paths)
    - No directory traversal allowed (..)
    - XDG_CONFIG_HOME must be within home directory
"""

import os
from pathlib import Path
from typing import Any, Optional


class PathSecurityError(ValueError):
    """Raised when a path violates security constraints."""
    pass


def validate_path_security(path: str, context: str = "configuration") -> None:
    """Validate that a path meets security constraints.

    Raises PathSecurityError if:
    - Path is absolute (starts with /)
    - Path attempts directory traversal (contains ..)

    Args:
        path: The path string to validate
        context: Description for error messages (e.g., "appname configuration_files")

    Raises:
        PathSecurityError: If path violates security constraints
    """
    if path.startswith("/"):
        raise PathSecurityError(
            f"Absolute paths not allowed in {context}: {path}"
        )

    if ".." in path:
        raise PathSecurityError(
            f"Directory traversal not allowed in {context}: {path}"
        )


def validate_xdg_config_home() -> Path:
    """Validate XDG_CONFIG_HOME is within home directory.

    Returns the validated path, or default ~/.config if not set.

    Returns:
        Path to XDG_CONFIG_HOME (validated to be within $HOME)

    Raises:
        PathSecurityError: If XDG_CONFIG_HOME points outside home directory
    """
    home = Path.home()
    xdg_config = os.environ.get('XDG_CONFIG_HOME')

    if xdg_config is None:
        return home / '.config'

    xdg_path = Path(xdg_config).expanduser().resolve()

    # Ensure XDG_CONFIG_HOME is within home directory
    try:
        xdg_path.relative_to(home)
    except ValueError:
        raise PathSecurityError(
            f"$XDG_CONFIG_HOME must be within home directory: {xdg_path}"
        )

    return xdg_path


def get_xdg_config_home() -> Path:
    """Get XDG_CONFIG_HOME path without security validation.

    Use this when you need the path for discovery (not backup).
    For backup operations, use validate_xdg_config_home() instead.

    Returns:
        Path to XDG_CONFIG_HOME (default: ~/.config)
    """
    home = Path.home()
    xdg_config = os.environ.get('XDG_CONFIG_HOME')

    if xdg_config is None:
        return home / '.config'

    return Path(xdg_config).expanduser()


def load_hints_database(hints_path: Path) -> dict[str, Any]:
    """Load and validate the app-hints.yaml database.

    Loads the YAML file and validates all paths for security constraints.
    Invalid paths will raise PathSecurityError to prevent loading unsafe configs.

    Args:
        hints_path: Path to the app-hints.yaml file

    Returns:
        Dictionary mapping app names to their configuration

    Raises:
        FileNotFoundError: If hints file doesn't exist
        PathSecurityError: If any path violates security constraints
        yaml.YAMLError: If YAML is malformed
    """
    # Import yaml here to make it optional at module level
    import yaml

    with open(hints_path) as f:
        hints = yaml.safe_load(f)

    if hints is None:
        return {}

    # Validate all paths in the database for security
    for app_name, config in hints.items():
        if config is None:
            continue

        for path in config.get('configuration_files', []) or []:
            validate_path_security(path, f"{app_name} configuration_files")

        for path in config.get('xdg_configuration_files', []) or []:
            validate_path_security(path, f"{app_name} xdg_configuration_files")

    return hints


def resolve_app_paths(app_config: dict[str, Any], check_exists: bool = True) -> list[Path]:
    """Resolve all configuration paths to absolute paths.

    Handles both configuration_files (relative to $HOME) and
    xdg_configuration_files (relative to $XDG_CONFIG_HOME).

    Args:
        app_config: Application configuration from hints database
        check_exists: If True, only return paths that exist on filesystem

    Returns:
        List of resolved absolute paths
    """
    paths = []
    home = Path.home()
    xdg_config_home = get_xdg_config_home()

    # Regular configuration files (relative to $HOME)
    for path in app_config.get('configuration_files', []) or []:
        resolved = home / path
        if not check_exists or resolved.exists():
            paths.append(resolved)

    # XDG configuration files (relative to $XDG_CONFIG_HOME)
    for path in app_config.get('xdg_configuration_files', []) or []:
        resolved = xdg_config_home / path
        if not check_exists or resolved.exists():
            paths.append(resolved)

    return paths


def get_app_settings(
    hints_db: dict[str, Any],
    app_name: str,
    bundle_id: Optional[str] = None
) -> Optional[dict[str, Any]]:
    """Look up an application in the hints database.

    Tries multiple matching strategies:
    1. Exact match on lowercased app name
    2. Match on bundle_id if provided
    3. Fuzzy match on name variations

    Args:
        hints_db: The loaded hints database
        app_name: Application name to look up
        bundle_id: Optional bundle identifier for matching

    Returns:
        Application config dict if found, None otherwise
    """
    # Normalize the app name for lookup
    normalized_name = app_name.lower().replace(' ', '-').replace('_', '-')

    # Try exact match first
    if normalized_name in hints_db:
        result = dict(hints_db[normalized_name])
        result['_hints_key'] = normalized_name
        return result

    # Try without common suffixes
    for suffix in ['.app', '-app', ' app']:
        stripped = normalized_name.removesuffix(suffix)
        if stripped != normalized_name and stripped in hints_db:
            result = dict(hints_db[stripped])
            result['_hints_key'] = stripped
            return result

    # Try bundle_id match if provided
    if bundle_id:
        for name, config in hints_db.items():
            if config and config.get('bundle_id') == bundle_id:
                result = dict(config)
                result['_hints_key'] = name
                return result

    # Try partial bundle_id match (e.g., "com.microsoft.VSCode" -> "vscode")
    if bundle_id:
        bundle_suffix = bundle_id.split('.')[-1].lower()
        if bundle_suffix in hints_db:
            result = dict(hints_db[bundle_suffix])
            result['_hints_key'] = bundle_suffix
            return result

    return None


def get_default_hints_path() -> Path:
    """Get the default path to app-hints.yaml relative to this module.

    Returns:
        Path to the default app-hints.yaml file
    """
    # Navigate from discovery/ up to python/, then to data/
    module_dir = Path(__file__).parent
    return module_dir.parent.parent / 'data' / 'app-hints.yaml'


class HintsDatabase:
    """Convenience class for working with the hints database.

    Provides caching and helper methods for common operations with
    the app-hints.yaml database. Handles lazy loading and path resolution.

    Example - Basic Lookup:
        >>> from discovery.hints import HintsDatabase
        >>>
        >>> # Initialize with default path
        >>> db = HintsDatabase()
        >>>
        >>> # Look up a known application
        >>> config = db.lookup("vscode")
        >>> if config:
        ...     print(f"Install method: {config['install_method']}")
        ...     print(f"Config files: {config.get('configuration_files', [])}")
        ...
        >>> # Resolve paths to absolute locations
        >>> paths = db.resolve_paths(config, check_exists=True)
        >>> for path in paths:
        ...     print(f"Found: {path}")

    Example - Bundle ID Lookup:
        >>> db = HintsDatabase()
        >>>
        >>> # Look up by bundle identifier
        >>> config = db.lookup("VS Code", bundle_id="com.microsoft.VSCode")
        >>> if config:
        ...     paths = db.resolve_paths(config)
        ...     print(f"Found {len(paths)} configuration paths")

    Example - Exploring the Database:
        >>> db = HintsDatabase()
        >>>
        >>> # List all applications in the database
        >>> apps = db.list_apps()
        >>> print(f"Total apps in database: {len(apps)}")
        >>>
        >>> # Get apps by install method
        >>> cask_apps = db.get_apps_by_install_method('cask')
        >>> mas_apps = db.get_apps_by_install_method('mas')
        >>> print(f"Homebrew casks: {len(cask_apps)}")
        >>> print(f"Mac App Store: {len(mas_apps)}")

    Example - Custom Database Path:
        >>> from pathlib import Path
        >>>
        >>> # Use a custom hints database
        >>> custom_path = Path("/path/to/custom-hints.yaml")
        >>> db = HintsDatabase(hints_path=custom_path)
        >>>
        >>> # Reload database after updates
        >>> db.reload()

    Example - Integration with Discovery:
        >>> from discovery.hints import HintsDatabase
        >>> from discovery.conventions import discover_from_conventions
        >>>
        >>> db = HintsDatabase()
        >>>
        >>> # Try hints database first
        >>> app_name = "Docker Desktop"
        >>> config = db.lookup(app_name)
        >>>
        >>> if config:
        ...     # Found in hints database (Tier 1)
        ...     paths = db.resolve_paths(config, check_exists=True)
        ...     source = "hints"
        ... else:
        ...     # Fall back to conventions (Tier 2)
        ...     result = discover_from_conventions(app_name)
        ...     paths = result.get('found_paths', [])
        ...     source = "conventions"
        ...
        >>> print(f"Found via {source}: {len(paths)} paths")
    """

    def __init__(self, hints_path: Optional[Path] = None):
        """Initialize the hints database.

        Args:
            hints_path: Path to app-hints.yaml (uses default if not specified)
        """
        self.hints_path = hints_path or get_default_hints_path()
        self._database: Optional[dict[str, Any]] = None

    @property
    def database(self) -> dict[str, Any]:
        """Lazy-load and cache the database."""
        if self._database is None:
            self._database = load_hints_database(self.hints_path)
        return self._database

    def reload(self) -> None:
        """Force reload of the database from disk."""
        self._database = None

    def lookup(
        self,
        app_name: str,
        bundle_id: Optional[str] = None
    ) -> Optional[dict[str, Any]]:
        """Look up an application in the database.

        Args:
            app_name: Application name to look up
            bundle_id: Optional bundle identifier

        Returns:
            Application config if found, None otherwise
        """
        return get_app_settings(self.database, app_name, bundle_id)

    def resolve_paths(
        self,
        app_config: dict[str, Any],
        check_exists: bool = True
    ) -> list[Path]:
        """Resolve configuration paths for an application.

        Args:
            app_config: Application config from lookup()
            check_exists: Only return paths that exist

        Returns:
            List of resolved absolute paths
        """
        return resolve_app_paths(app_config, check_exists)

    def list_apps(self) -> list[str]:
        """List all applications in the database.

        Returns:
            List of application names
        """
        return list(self.database.keys())

    def get_apps_by_install_method(self, method: str) -> list[str]:
        """Get all apps with a specific install method.

        Args:
            method: Install method (cask, formula, mas, dmg, system)

        Returns:
            List of application names with that install method
        """
        return [
            name for name, config in self.database.items()
            if config and config.get('install_method') == method
        ]

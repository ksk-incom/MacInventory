"""Discovery Result Merging and Validation.

Combines results from multiple discovery tiers:
    Tier 1: Hints database (highest priority)
    Tier 2: Convention-based discovery
    Tier 3: LLM fallback results (when provided)

Also provides:
    - Filesystem validation for discovered paths
    - List of undiscovered apps for LLM fallback
    - Confidence scoring based on discovery source
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class DiscoveryResult:
    """Result of discovering an application's settings.

    Attributes:
        app_name: Application name as discovered
        bundle_id: Bundle identifier if known
        canonical_key: Hints database key for consistent folder naming (e.g., "vscode" not "code")
        configuration_files: Paths relative to $HOME
        xdg_configuration_files: Paths relative to $XDG_CONFIG_HOME
        resolved_paths: Absolute paths that exist on filesystem (legacy, for backward compat)
        source: Discovery tier that found this ('hints', 'conventions', 'llm')
        confidence: Confidence level ('high', 'medium', 'low')
        install_method: How the app is installed (cask, formula, mas, etc.)
        extensions_cmd: Command to list extensions (if applicable)
        exclude_files: Files/patterns to exclude from backup
        notes: Special restoration instructions
        needs_llm_discovery: Whether LLM fallback should be tried

        # Phase 6.5: Tier-specific paths for separate backup folders
        hints_paths: Absolute paths from Tier 1 (App Hints Database) - trusted, no filtering
        conventions_paths: Absolute paths from Tier 2 (Convention Discovery) - filtered
        llm_paths: Absolute paths from Tier 3 (LLM Research) - filtered
        found_in_hints: Whether app was found in hints database (prevents Tier 3)
    """
    app_name: str
    bundle_id: Optional[str] = None
    canonical_key: Optional[str] = None
    configuration_files: list[str] = field(default_factory=list)
    xdg_configuration_files: list[str] = field(default_factory=list)
    resolved_paths: list[Path] = field(default_factory=list)
    source: str = 'unknown'
    confidence: str = 'low'
    install_method: Optional[str] = None
    extensions_cmd: Optional[str] = None
    exclude_files: list[str] = field(default_factory=list)
    notes: Optional[str] = None
    needs_llm_discovery: bool = False

    # Phase 6.5: Tier-specific paths
    hints_paths: list[Path] = field(default_factory=list)
    conventions_paths: list[Path] = field(default_factory=list)
    llm_paths: list[Path] = field(default_factory=list)
    found_in_hints: bool = False

    def has_settings(self) -> bool:
        """Check if any settings were discovered."""
        return bool(
            self.configuration_files or
            self.xdg_configuration_files or
            self.resolved_paths or
            self.hints_paths or
            self.conventions_paths or
            self.llm_paths
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'app_name': self.app_name,
            'bundle_id': self.bundle_id,
            'canonical_key': self.canonical_key,
            'configuration_files': self.configuration_files,
            'xdg_configuration_files': self.xdg_configuration_files,
            'resolved_paths': [str(p) for p in self.resolved_paths],
            'source': self.source,
            'confidence': self.confidence,
            'install_method': self.install_method,
            'extensions_cmd': self.extensions_cmd,
            'exclude_files': self.exclude_files,
            'notes': self.notes,
            'needs_llm_discovery': self.needs_llm_discovery,
            # Phase 6.5: Tier-specific paths
            'hints_paths': [str(p) for p in self.hints_paths],
            'conventions_paths': [str(p) for p in self.conventions_paths],
            'llm_paths': [str(p) for p in self.llm_paths],
            'found_in_hints': self.found_in_hints
        }


def _normalize_path_for_dedup(path: Path) -> str:
    """Normalize a path for deduplication on case-insensitive filesystems.

    On macOS HFS+/APFS (case-insensitive by default), paths like
    /Users/.Docker and /Users/.docker are the same. We use resolve()
    and lowercase to deduplicate.

    Args:
        path: Path to normalize

    Returns:
        Lowercase resolved path string for deduplication
    """
    try:
        return str(path.resolve()).lower()
    except OSError:
        return str(path).lower()


def validate_paths(
    configuration_files: list[str],
    xdg_configuration_files: list[str]
) -> tuple[list[Path], list[str]]:
    """Validate discovered paths exist on the filesystem.

    Deduplicates paths that resolve to the same location (case-insensitive
    on macOS).

    Args:
        configuration_files: Paths relative to $HOME
        xdg_configuration_files: Paths relative to $XDG_CONFIG_HOME

    Returns:
        Tuple of (valid_paths, invalid_paths):
        - valid_paths: List of unique absolute Path objects that exist
        - invalid_paths: List of path strings that don't exist
    """
    home = Path.home()
    xdg_config_home = Path(os.environ.get('XDG_CONFIG_HOME', home / '.config'))

    valid_paths = []
    invalid_paths = []
    # Track resolved paths to avoid duplicates (case-insensitive)
    seen_resolved = set()

    for path_str in configuration_files:
        full_path = home / path_str
        if full_path.exists():
            resolved_key = _normalize_path_for_dedup(full_path)
            if resolved_key not in seen_resolved:
                seen_resolved.add(resolved_key)
                valid_paths.append(full_path.resolve())
        else:
            invalid_paths.append(path_str)

    for path_str in xdg_configuration_files:
        full_path = xdg_config_home / path_str
        if full_path.exists():
            resolved_key = _normalize_path_for_dedup(full_path)
            if resolved_key not in seen_resolved:
                seen_resolved.add(resolved_key)
                valid_paths.append(full_path.resolve())
        else:
            invalid_paths.append(path_str)

    return valid_paths, invalid_paths


def _normalize_config_path(path: str) -> str:
    """Normalize a config path for case-insensitive deduplication.

    Removes trailing slashes and lowercases for macOS compatibility.

    Args:
        path: Configuration file path (relative)

    Returns:
        Normalized lowercase path without trailing slash
    """
    return path.rstrip('/').lower()


def merge_discovery_results(
    hints_result: Optional[dict[str, Any]],
    conventions_result: Optional[dict[str, Any]],
    llm_result: Optional[dict[str, Any]] = None,
    app_name: str = '',
    bundle_id: Optional[str] = None
) -> DiscoveryResult:
    """Merge results from multiple discovery tiers.

    Priority order:
    1. Hints database (highest confidence, curated)
    2. Convention-based discovery (medium confidence)
    3. LLM fallback results (variable confidence)

    The merge strategy is:
    - Use hints data if available (it's curated and most reliable)
    - Supplement with convention discoveries not already in hints
    - Add LLM discoveries as last resort

    Paths are deduplicated case-insensitively for macOS compatibility.

    Phase 6.5 Enhancement:
    - Paths are now stored separately by discovery tier (hints_paths, conventions_paths, llm_paths)
    - If found in hints, LLM discovery is prevented (found_in_hints=True)
    - Convention/LLM paths are filtered to only include config files

    Args:
        hints_result: Result from hints database lookup (or None)
        conventions_result: Result from convention discovery (or None)
        llm_result: Result from LLM discovery (or None)
        app_name: Application name for the result
        bundle_id: Bundle identifier if known

    Returns:
        Merged DiscoveryResult with all discovered paths
    """
    from .config_filter import ConfigFilter

    result = DiscoveryResult(
        app_name=app_name,
        bundle_id=bundle_id
    )

    # Use dicts for case-insensitive deduplication while preserving original case
    # Key: normalized (lowercase, no trailing slash), Value: original path
    config_files_map: dict[str, str] = {}
    xdg_files_map: dict[str, str] = {}

    # Phase 6.5: Track paths by tier (normalized key -> Path)
    hints_paths_map: dict[str, Path] = {}
    conventions_paths_map: dict[str, Path] = {}
    llm_paths_map: dict[str, Path] = {}

    # Initialize config filter for Tier 2/3
    config_filter = ConfigFilter()

    home = Path.home()
    xdg_config_home = Path(os.environ.get('XDG_CONFIG_HOME', home / '.config'))

    def add_config_path(path: str) -> None:
        """Add a config path with case-insensitive deduplication."""
        key = _normalize_config_path(path)
        if key not in config_files_map:
            # Store without trailing slash for consistency
            config_files_map[key] = path.rstrip('/')

    def add_xdg_path(path: str) -> None:
        """Add an XDG config path with case-insensitive deduplication."""
        key = _normalize_config_path(path)
        if key not in xdg_files_map:
            xdg_files_map[key] = path.rstrip('/')

    def resolve_and_add_tier_path(
        relative_path: str,
        tier_map: dict[str, Path],
        is_xdg: bool = False,
        apply_filter: bool = False
    ) -> None:
        """Resolve a relative path and add to tier-specific map.

        Args:
            relative_path: Path relative to home or XDG config
            tier_map: The tier-specific path map to add to
            is_xdg: If True, path is relative to XDG_CONFIG_HOME
            apply_filter: If True, apply config file filtering (for Tier 2/3)
        """
        base = xdg_config_home if is_xdg else home
        full_path = base / relative_path

        if not full_path.exists():
            return

        resolved = full_path.resolve()
        key = _normalize_path_for_dedup(resolved)

        # Skip if already in this tier's map
        if key in tier_map:
            return

        # Apply filtering for Tier 2/3
        if apply_filter:
            if resolved.is_file():
                is_valid, _ = config_filter.is_config_file(resolved)
                if not is_valid:
                    return
            elif resolved.is_dir():
                # For directories, we'll filter contents during backup
                is_valid, _ = config_filter.is_config_directory(resolved)
                if not is_valid:
                    return

        tier_map[key] = resolved

    # Process hints result (highest priority) - NO filtering applied
    if hints_result:
        result.source = 'hints'
        result.confidence = 'high'
        result.found_in_hints = True  # Phase 6.5: Mark as found in hints
        result.canonical_key = hints_result.get('_hints_key')  # For consistent folder naming

        for path in hints_result.get('configuration_files', []) or []:
            add_config_path(path)
            resolve_and_add_tier_path(path, hints_paths_map, is_xdg=False, apply_filter=False)

        for path in hints_result.get('xdg_configuration_files', []) or []:
            add_xdg_path(path)
            resolve_and_add_tier_path(path, hints_paths_map, is_xdg=True, apply_filter=False)

        result.install_method = hints_result.get('install_method')
        result.extensions_cmd = hints_result.get('extensions_cmd')
        result.exclude_files = hints_result.get('exclude_files', []) or []
        result.notes = hints_result.get('notes')

        if hints_result.get('bundle_id'):
            result.bundle_id = hints_result.get('bundle_id')

    # Process conventions result (supplement hints) - filtering applied
    if conventions_result:
        for path in conventions_result.get('configuration_files', []) or []:
            add_config_path(path)
            # Only add to conventions_paths if not already in hints
            full_path = home / path
            if full_path.exists():
                key = _normalize_path_for_dedup(full_path.resolve())
                if key not in hints_paths_map:
                    resolve_and_add_tier_path(path, conventions_paths_map, is_xdg=False, apply_filter=True)

        for path in conventions_result.get('xdg_configuration_files', []) or []:
            add_xdg_path(path)
            full_path = xdg_config_home / path
            if full_path.exists():
                key = _normalize_path_for_dedup(full_path.resolve())
                if key not in hints_paths_map:
                    resolve_and_add_tier_path(path, conventions_paths_map, is_xdg=True, apply_filter=True)

        # Update source and confidence if no hints were found
        if not hints_result:
            result.source = 'conventions'
            result.confidence = conventions_result.get('confidence', 'medium')

        if conventions_result.get('bundle_id') and not result.bundle_id:
            result.bundle_id = conventions_result.get('bundle_id')

    # Process LLM result (supplement both) - filtering applied
    # Phase 6.5: Only process LLM if NOT found in hints
    if llm_result and not result.found_in_hints:
        for path in llm_result.get('configuration_files', []) or []:
            add_config_path(path)
            full_path = home / path
            if full_path.exists():
                key = _normalize_path_for_dedup(full_path.resolve())
                if key not in hints_paths_map and key not in conventions_paths_map:
                    resolve_and_add_tier_path(path, llm_paths_map, is_xdg=False, apply_filter=True)

        for path in llm_result.get('xdg_configuration_files', []) or []:
            add_xdg_path(path)
            full_path = xdg_config_home / path
            if full_path.exists():
                key = _normalize_path_for_dedup(full_path.resolve())
                if key not in hints_paths_map and key not in conventions_paths_map:
                    resolve_and_add_tier_path(path, llm_paths_map, is_xdg=True, apply_filter=True)

        # Update source if this is the only source
        if not hints_result and not conventions_result:
            result.source = 'llm'
            result.confidence = llm_result.get('confidence', 'low')

        if llm_result.get('install_method') and not result.install_method:
            result.install_method = llm_result.get('install_method')

        if llm_result.get('notes') and not result.notes:
            result.notes = llm_result.get('notes')

    # Convert maps back to sorted lists (use original case values)
    result.configuration_files = sorted(config_files_map.values())
    result.xdg_configuration_files = sorted(xdg_files_map.values())

    # Validate paths and store resolved versions (legacy field for backward compat)
    valid_paths, _ = validate_paths(
        result.configuration_files,
        result.xdg_configuration_files
    )
    result.resolved_paths = valid_paths

    # Phase 6.5: Store tier-specific paths
    result.hints_paths = sorted(hints_paths_map.values(), key=str)
    result.conventions_paths = sorted(conventions_paths_map.values(), key=str)
    result.llm_paths = sorted(llm_paths_map.values(), key=str)

    # Determine if LLM discovery is needed
    # Phase 6.5: If found in hints, NEVER need LLM discovery
    if result.found_in_hints:
        result.needs_llm_discovery = False
    else:
        result.needs_llm_discovery = not result.has_settings()

    return result


def discover_app(
    app_name: str,
    bundle_id: Optional[str],
    hints_db: dict[str, Any],
    skip_conventions: bool = False
) -> DiscoveryResult:
    """Run full discovery pipeline for an application.

    This is the main entry point for discovering an app's settings.
    It runs through tiers 1 and 2, and flags apps that need tier 3.

    Args:
        app_name: Application name
        bundle_id: Bundle identifier (if known)
        hints_db: The loaded hints database
        skip_conventions: Skip convention-based discovery (for known apps)

    Returns:
        DiscoveryResult with merged findings from all tiers
    """
    from .hints import get_app_settings
    from .conventions import discover_from_conventions

    # Tier 1: Hints database
    hints_result = get_app_settings(hints_db, app_name, bundle_id)

    # Tier 2: Convention-based discovery (unless skipped)
    conventions_result = None
    if not skip_conventions:
        conventions_result = discover_from_conventions(app_name, bundle_id)

    # Merge results
    return merge_discovery_results(
        hints_result=hints_result,
        conventions_result=conventions_result,
        llm_result=None,  # LLM is handled separately
        app_name=app_name,
        bundle_id=bundle_id
    )


def discover_all_apps(
    apps: list[dict[str, Any]],
    hints_db: dict[str, Any],
    skip_system_apps: bool = True
) -> tuple[list[DiscoveryResult], list[dict[str, Any]]]:
    """Discover settings for multiple applications.

    Runs the discovery pipeline for all provided apps and separates
    them into discovered and undiscovered lists.

    Args:
        apps: List of app dicts with 'name' and optional 'bundle_id' keys
        hints_db: The loaded hints database
        skip_system_apps: Skip apps that are likely system apps

    Returns:
        Tuple of (discovered_apps, undiscovered_apps):
        - discovered_apps: List of DiscoveryResult objects
        - undiscovered_apps: List of app dicts that need LLM discovery
    """
    discovered = []
    undiscovered = []

    # System app patterns to skip
    system_patterns = [
        'com.apple.',
        'Apple ',
        'System ',
    ]

    for app in apps:
        app_name = app.get('name', '')
        bundle_id = app.get('bundle_id')

        # Skip system apps if requested
        if skip_system_apps:
            if bundle_id and any(bundle_id.startswith(p) for p in system_patterns):
                continue
            if any(app_name.startswith(p) for p in system_patterns):
                continue

        result = discover_app(app_name, bundle_id, hints_db)

        if result.has_settings():
            discovered.append(result)
        else:
            # Add to undiscovered list for LLM fallback
            result.needs_llm_discovery = True
            discovered.append(result)
            undiscovered.append({
                'name': app_name,
                'bundle_id': bundle_id,
                'checked_paths': get_checked_paths(app_name, bundle_id)
            })

    return discovered, undiscovered


def get_checked_paths(app_name: str, bundle_id: Optional[str] = None) -> list[str]:
    """Get list of paths that were already checked for an app.

    Useful for LLM fallback to know what NOT to check again.

    Args:
        app_name: Application name
        bundle_id: Bundle identifier

    Returns:
        List of absolute path strings that were checked
    """
    from .conventions import discover_common_patterns
    return discover_common_patterns(app_name, bundle_id)


def build_undiscovered_apps_report(
    undiscovered: list[dict[str, Any]],
    include_checked_paths: bool = True
) -> dict[str, Any]:
    """Build a report of apps that need LLM discovery.

    This report is used by the slash command to spawn app-discovery agents.

    Args:
        undiscovered: List of undiscovered app dicts from discover_all_apps
        include_checked_paths: Include paths already checked (for LLM context)

    Returns:
        Report dict with:
        {
            'count': int,
            'apps': list of app details,
            'summary': str
        }
    """
    apps_for_report = []

    for app in undiscovered:
        app_entry = {
            'name': app.get('name', ''),
            'bundle_id': app.get('bundle_id')
        }

        if include_checked_paths:
            app_entry['checked_paths'] = app.get('checked_paths', [])

        apps_for_report.append(app_entry)

    return {
        'count': len(undiscovered),
        'apps': apps_for_report,
        'summary': f"{len(undiscovered)} application(s) need LLM-based discovery"
    }


def filter_by_importance(
    undiscovered: list[dict[str, Any]],
    max_apps: int = 20
) -> list[dict[str, Any]]:
    """Filter undiscovered apps to those worth researching.

    Some apps (like system utilities) aren't worth LLM discovery.
    This filter prioritizes developer tools and productivity apps.

    Args:
        undiscovered: List of undiscovered app dicts
        max_apps: Maximum number of apps to return

    Returns:
        Filtered list of apps, sorted by likely importance
    """
    # Keywords indicating developer/productivity apps worth researching
    important_keywords = [
        'code', 'studio', 'editor', 'ide', 'terminal', 'iterm',
        'docker', 'postgres', 'mysql', 'redis', 'mongo',
        'slack', 'notion', 'obsidian', 'craft', 'bear',
        'alfred', 'raycast', 'keyboard', 'karabiner',
        'git', 'github', 'tower', 'fork', 'sourcetree',
        'postman', 'insomnia', 'charles', 'proxyman',
        'figma', 'sketch', 'affinity',
        'zoom', 'teams', 'webex',
        '1password', 'bitwarden', 'keychain',
        'homebrew', 'brew',
    ]

    # Patterns to skip (likely not useful to research)
    skip_patterns = [
        'helper', 'agent', 'daemon', 'service', 'updater',
        'crash', 'diagnostic', 'feedback', 'analytics',
        'install', 'uninstall', 'setup', 'wizard',
    ]

    def importance_score(app: dict) -> int:
        """Score an app by likely importance for research."""
        name = app.get('name', '').lower()

        # Skip if matches skip patterns
        for pattern in skip_patterns:
            if pattern in name:
                return -1

        # Score based on important keywords
        score = 0
        for keyword in important_keywords:
            if keyword in name:
                score += 10

        # Bonus for having a bundle_id (more likely to be a real app)
        if app.get('bundle_id'):
            score += 5

        return score

    # Score and filter apps
    scored_apps = [(app, importance_score(app)) for app in undiscovered]
    scored_apps = [(app, score) for app, score in scored_apps if score >= 0]

    # Sort by score descending
    scored_apps.sort(key=lambda x: x[1], reverse=True)

    # Return top apps
    return [app for app, _ in scored_apps[:max_apps]]


class DiscoveryPipeline:
    """Orchestrates the full discovery process for multiple apps.

    This is the main entry point for discovering configuration locations
    for multiple applications. It runs the three-tier discovery system
    (hints → conventions → LLM fallback) and manages results.

    Example - Basic Usage:
        >>> from pathlib import Path
        >>> from discovery.hints import load_hints_database
        >>> from discovery.merge import DiscoveryPipeline
        >>>
        >>> # Load the hints database
        >>> hints_path = Path('data/app-hints.yaml')
        >>> hints_db = load_hints_database(hints_path)
        >>>
        >>> # Create pipeline
        >>> pipeline = DiscoveryPipeline(hints_db)
        >>>
        >>> # Discover settings for multiple apps
        >>> apps = [
        ...     {'name': 'Visual Studio Code', 'bundle_id': 'com.microsoft.VSCode'},
        ...     {'name': 'Docker', 'bundle_id': 'com.docker.docker'},
        ...     {'name': 'UnknownApp', 'bundle_id': 'com.example.unknown'}
        ... ]
        >>> results = pipeline.discover_all(apps)
        >>>
        >>> # Check what was found
        >>> for result in results:
        ...     if result.has_settings():
        ...         print(f"{result.app_name}: {len(result.resolved_paths)} paths")
        ...     else:
        ...         print(f"{result.app_name}: No settings found")

    Example - Complete Workflow with LLM Fallback:
        >>> from discovery.hints import HintsDatabase
        >>> from discovery.merge import DiscoveryPipeline
        >>>
        >>> # Initialize with convenience class
        >>> db = HintsDatabase()  # Uses default path
        >>> pipeline = DiscoveryPipeline(db.database)
        >>>
        >>> # Run discovery
        >>> apps = [
        ...     {'name': 'VS Code', 'bundle_id': 'com.microsoft.VSCode'},
        ...     {'name': 'Warp', 'bundle_id': 'dev.warp.Warp-Stable'},
        ...     {'name': 'NicheDevTool', 'bundle_id': 'com.niche.tool'}
        ... ]
        >>> results = pipeline.discover_all(apps, skip_system_apps=True)
        >>>
        >>> # Get apps that need LLM discovery
        >>> undiscovered = pipeline.get_undiscovered_for_llm(
        ...     max_apps=20,
        ...     filter_important=True
        ... )
        >>>
        >>> # Simulate LLM discovery for unknown apps
        >>> for app in undiscovered:
        ...     # In real usage, this would be results from app-discovery agent
        ...     llm_result = {
        ...         'configuration_files': ['.nichetool/config.json'],
        ...         'xdg_configuration_files': ['nichetool/settings.yaml'],
        ...         'confidence': 'medium',
        ...         'notes': 'Settings stored in XDG-compliant location'
        ...     }
        ...     updated = pipeline.add_llm_result(app['name'], llm_result)
        ...     if updated:
        ...         print(f"Updated {app['name']} with LLM results")
        >>>
        >>> # Get final statistics
        >>> stats = pipeline.get_statistics()
        >>> print(f"Total apps: {stats['total_apps']}")
        >>> print(f"With settings: {stats['with_settings']}")
        >>> print(f"By source: {stats['by_source']}")

    Example - Integration with Scanner Output:
        >>> from discovery.hints import HintsDatabase
        >>> from discovery.merge import DiscoveryPipeline
        >>> # from scanners.applications import scan  # Hypothetical scanner
        >>>
        >>> # Typical scanner output format
        >>> scanned_apps = [
        ...     {
        ...         'name': 'Visual Studio Code',
        ...         'bundle_id': 'com.microsoft.VSCode',
        ...         'path': '/Applications/Visual Studio Code.app',
        ...         'version': '1.85.0'
        ...     },
        ...     {
        ...         'name': 'Docker Desktop',
        ...         'bundle_id': 'com.docker.docker',
        ...         'path': '/Applications/Docker.app'
        ...     }
        ... ]
        >>>
        >>> # Run discovery pipeline
        >>> db = HintsDatabase()
        >>> pipeline = DiscoveryPipeline(db.database)
        >>> results = pipeline.discover_all(scanned_apps)
        >>>
        >>> # Export results for guide generation
        >>> all_results = pipeline.get_all_results()
        >>> # This JSON output can be consumed by the guide-generator agent
        >>> import json
        >>> output = {
        ...     'discovery_results': all_results,
        ...     'statistics': pipeline.get_statistics(),
        ...     'undiscovered_report': pipeline.get_undiscovered_report()
        ... }
        >>> print(json.dumps(output, indent=2))

    Example - Error Handling and Validation:
        >>> from discovery.hints import HintsDatabase, PathSecurityError
        >>> from discovery.merge import DiscoveryPipeline
        >>>
        >>> try:
        ...     db = HintsDatabase()
        ...     pipeline = DiscoveryPipeline(db.database)
        ...
        ...     apps = [{'name': 'TestApp', 'bundle_id': 'com.test.app'}]
        ...     results = pipeline.discover_all(apps)
        ...
        ...     # Validate discovered paths
        ...     for result in results:
        ...         if result.resolved_paths:
        ...             print(f"{result.app_name}:")
        ...             for path in result.resolved_paths:
        ...                 if path.exists():
        ...                     print(f"  ✓ {path}")
        ...                 else:
        ...                     print(f"  ✗ {path} (not found)")
        ...
        ... except PathSecurityError as e:
        ...     print(f"Security validation failed: {e}")
        ... except FileNotFoundError as e:
        ...     print(f"Hints database not found: {e}")
        ... except Exception as e:
        ...     print(f"Discovery failed: {e}")

    Attributes:
        hints_db: The loaded app-hints.yaml database
        _results: Internal list of DiscoveryResult objects
        _undiscovered: Internal list of apps needing LLM discovery
    """

    def __init__(self, hints_db: dict[str, Any]):
        """Initialize the pipeline with a hints database.

        Args:
            hints_db: The loaded app-hints.yaml database
        """
        self.hints_db = hints_db
        self._results: list[DiscoveryResult] = []
        self._undiscovered: list[dict[str, Any]] = []

    def discover_all(
        self,
        apps: list[dict[str, Any]],
        skip_system_apps: bool = True
    ) -> list[DiscoveryResult]:
        """Run discovery for all applications.

        Args:
            apps: List of app dicts with 'name' and optional 'bundle_id'
            skip_system_apps: Skip system apps

        Returns:
            List of DiscoveryResult objects
        """
        self._results, self._undiscovered = discover_all_apps(
            apps, self.hints_db, skip_system_apps
        )
        return self._results

    def get_undiscovered_for_llm(
        self,
        max_apps: int = 20,
        filter_important: bool = True
    ) -> list[dict[str, Any]]:
        """Get apps that need LLM-based discovery.

        Args:
            max_apps: Maximum number of apps to return
            filter_important: Filter to likely-important apps

        Returns:
            List of app dicts for LLM discovery
        """
        if filter_important:
            return filter_by_importance(self._undiscovered, max_apps)
        return self._undiscovered[:max_apps]

    def get_undiscovered_report(self) -> dict[str, Any]:
        """Get a report of undiscovered apps for the slash command.

        Returns:
            Report dict for use in inventory.md
        """
        return build_undiscovered_apps_report(self._undiscovered)

    def add_llm_result(
        self,
        app_name: str,
        llm_result: dict[str, Any]
    ) -> Optional[DiscoveryResult]:
        """Add LLM discovery result for an app.

        Finds the existing result and updates it with LLM findings.

        Args:
            app_name: Application name
            llm_result: Result from LLM discovery agent

        Returns:
            Updated DiscoveryResult or None if app not found
        """
        for i, result in enumerate(self._results):
            if result.app_name.lower() == app_name.lower():
                # Re-merge with LLM result
                updated = merge_discovery_results(
                    hints_result=None,  # Already incorporated
                    conventions_result=None,  # Already incorporated
                    llm_result=llm_result,
                    app_name=result.app_name,
                    bundle_id=result.bundle_id
                )

                # Preserve existing data
                updated.configuration_files = list(set(
                    result.configuration_files + updated.configuration_files
                ))
                updated.xdg_configuration_files = list(set(
                    result.xdg_configuration_files + updated.xdg_configuration_files
                ))
                updated.resolved_paths = list(set(
                    result.resolved_paths + updated.resolved_paths
                ))

                if result.install_method:
                    updated.install_method = result.install_method
                if result.extensions_cmd:
                    updated.extensions_cmd = result.extensions_cmd
                if result.notes:
                    updated.notes = result.notes

                updated.needs_llm_discovery = False
                self._results[i] = updated
                return updated

        return None

    def get_all_results(self) -> list[dict[str, Any]]:
        """Get all results as dictionaries for JSON output.

        Returns:
            List of result dicts
        """
        return [r.to_dict() for r in self._results]

    def get_statistics(self) -> dict[str, Any]:
        """Get discovery statistics.

        Returns:
            Statistics dict with counts by source, confidence, etc.
        """
        by_source = {'hints': 0, 'conventions': 0, 'llm': 0, 'unknown': 0}
        by_confidence = {'high': 0, 'medium': 0, 'low': 0}
        total_with_settings = 0
        total_needs_llm = 0

        for result in self._results:
            by_source[result.source] = by_source.get(result.source, 0) + 1
            by_confidence[result.confidence] = by_confidence.get(result.confidence, 0) + 1

            if result.has_settings():
                total_with_settings += 1
            if result.needs_llm_discovery:
                total_needs_llm += 1

        return {
            'total_apps': len(self._results),
            'with_settings': total_with_settings,
            'needs_llm_discovery': total_needs_llm,
            'by_source': by_source,
            'by_confidence': by_confidence
        }

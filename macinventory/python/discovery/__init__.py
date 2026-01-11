"""Discovery modules for finding application settings locations.

Implements a three-tier discovery system:
    Tier 1 (hints): Curated YAML database lookup
    Tier 2 (conventions): Check standard macOS paths
    Tier 3 (LLM): Fallback for unknown applications

Modules:
    hints: Load and parse app-hints.yaml database
    conventions: Convention-based path discovery
    merge: Result merging from multiple sources

Usage:
    from macinventory.python.discovery import DiscoveryPipeline, HintsDatabase

    # Load hints database
    db = HintsDatabase()

    # Run discovery for all apps
    pipeline = DiscoveryPipeline(db.database)
    results = pipeline.discover_all(apps)

    # Get apps that need LLM discovery
    undiscovered = pipeline.get_undiscovered_for_llm()
"""

from .hints import (
    HintsDatabase,
    PathSecurityError,
    get_app_settings,
    get_default_hints_path,
    get_xdg_config_home,
    load_hints_database,
    resolve_app_paths,
    validate_path_security,
    validate_xdg_config_home,
)
from .conventions import (
    check_known_patterns,
    discover_common_patterns,
    discover_from_conventions,
    generate_bundle_id_variations,
    generate_name_variations,
)
from .merge import (
    DiscoveryPipeline,
    DiscoveryResult,
    build_undiscovered_apps_report,
    discover_all_apps,
    discover_app,
    filter_by_importance,
    get_checked_paths,
    merge_discovery_results,
    validate_paths,
)

__all__ = [
    # hints.py
    'HintsDatabase',
    'PathSecurityError',
    'get_app_settings',
    'get_default_hints_path',
    'get_xdg_config_home',
    'load_hints_database',
    'resolve_app_paths',
    'validate_path_security',
    'validate_xdg_config_home',
    # conventions.py
    'check_known_patterns',
    'discover_common_patterns',
    'discover_from_conventions',
    'generate_bundle_id_variations',
    'generate_name_variations',
    # merge.py
    'DiscoveryPipeline',
    'DiscoveryResult',
    'build_undiscovered_apps_report',
    'discover_all_apps',
    'discover_app',
    'filter_by_importance',
    'get_checked_paths',
    'merge_discovery_results',
    'validate_paths',
]

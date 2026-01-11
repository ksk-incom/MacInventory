#!/usr/bin/env python3
"""MacInventory main entry point.

Single entry point for the MacInventory Python backend, designed to be called
from the Claude Code plugin via the /inventory slash command.

Usage:
    python3 main.py /path/to/config.json

The config.json file should contain:
    {
        "output_dir": "~/mac-inventory/2025-12-22-143022",
        "include_secrets": false,
        "cloud_destination": "OneDrive"  // optional
    }

This script:
    1. Reads configuration from JSON file
    2. Runs all scanners (applications, homebrew, version managers, etc.)
    3. Runs discovery pipeline (hints + conventions)
    4. Backs up configuration files with security filtering
    5. Generates bundle files (Brewfile, extensions, etc.)
    6. Generates state.yaml
    7. Outputs JSON for the guide-generator agent

From MACINVENTORY_IMPLEMENTATION_GUIDE.md:
    "The user never runs the Python script directly. The slash command:
    1. Gathers user preferences via AskUserQuestion
    2. Writes a config.json file to the output directory
    3. Runs the Python script which reads that config file"
"""

import json
import sys
from pathlib import Path
from typing import Any

# Allow running as script from any location (development repo or installed plugin)
# Instead of trying to use macinventory.python.* package structure, we add the
# python/ directory directly to sys.path and use absolute imports from there.
_script_dir = Path(__file__).resolve().parent  # macinventory/python/ or .../1.0.0/python/
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))


def run_inventory(config: dict[str, Any]) -> dict[str, Any]:
    """Run the complete inventory process.

    Args:
        config: Configuration dictionary with:
            - output_dir: Where to write output
            - include_secrets: Whether to include secrets in backups
            - cloud_destination: Optional cloud sync destination

    Returns:
        Complete results dictionary for guide generator
    """
    from output.structure import OutputStructure
    from output.bundles import generate_all_bundles
    from output.state import generate_state
    from scanners import applications, homebrew, version_managers, global_packages, editors, configs
    from discovery.hints import HintsDatabase
    from discovery.merge import DiscoveryPipeline
    from backup.config_backup import ConfigBackup
    from utils.path_safety import sanitize_path_component

    # Parse output directory
    output_base = Path(config.get("output_dir", "~/mac-inventory")).expanduser()
    include_secrets = config.get("include_secrets", False)
    cloud_destination = config.get("cloud_destination")

    # Create output structure
    output = OutputStructure(base_dir=output_base.parent, timestamp=output_base.name)

    results: dict[str, Any] = {
        "status": "success",
        "output_dir": str(output.output_dir),
        "system_info": output.system_info,
        "errors": [],
        "warnings": [],
    }

    # =================================================================
    # Phase 1: Run All Scanners
    # =================================================================
    print("Scanning applications...", flush=True)
    scan_results: dict[str, Any] = {}

    try:
        scan_results["applications"] = applications.scan()
    except Exception as e:
        scan_results["applications"] = {"applications": [], "count": 0, "errors": [str(e)]}
        results["errors"].append(f"Applications scan failed: {e}")

    print("Scanning Homebrew packages...", flush=True)
    try:
        scan_results["homebrew"] = homebrew.scan()
    except Exception as e:
        scan_results["homebrew"] = {"formulae": [], "casks": [], "taps": [], "errors": [str(e)]}
        results["errors"].append(f"Homebrew scan failed: {e}")

    print("Scanning Mac App Store...", flush=True)
    try:
        scan_results["mas"] = homebrew.scan_mas()
    except Exception as e:
        scan_results["mas"] = {"apps": [], "errors": [str(e)]}
        results["errors"].append(f"MAS scan failed: {e}")

    print("Scanning version managers...", flush=True)
    try:
        scan_results["version_managers"] = version_managers.scan()
    except Exception as e:
        scan_results["version_managers"] = {}
        results["errors"].append(f"Version managers scan failed: {e}")

    print("Scanning global packages...", flush=True)
    try:
        scan_results["global_packages"] = global_packages.scan()
    except Exception as e:
        scan_results["global_packages"] = {}
        results["errors"].append(f"Global packages scan failed: {e}")

    print("Scanning editors...", flush=True)
    try:
        scan_results["editors"] = editors.scan()
    except Exception as e:
        scan_results["editors"] = {}
        results["errors"].append(f"Editors scan failed: {e}")

    print("Scanning configurations...", flush=True)
    try:
        scan_results["configs"] = configs.scan()
    except Exception as e:
        scan_results["configs"] = {"shell": {}, "git": {}, "ssh": {}}
        results["errors"].append(f"Configs scan failed: {e}")

    results["scan_results"] = scan_results

    # =================================================================
    # Phase 2: Run Discovery Pipeline
    # =================================================================
    print("Running discovery pipeline...", flush=True)
    discovery_results = []
    discovery_stats = {}
    undiscovered_report = {"count": 0, "apps": []}

    # Load hints database outside try block so it's available for framework backup
    hints_db = HintsDatabase()

    try:

        # Build app list from scan results
        # Scanner returns single "applications" list with "location" field ("system" or "user")
        apps_for_discovery = []
        for app in scan_results.get("applications", {}).get("applications", []):
            apps_for_discovery.append({
                "name": app.get("name", ""),
                "bundle_id": app.get("bundle_id"),
                "location": app.get("location"),
            })

        # Run discovery
        pipeline = DiscoveryPipeline(hints_db.database)
        pipeline.discover_all(apps_for_discovery, skip_system_apps=True)

        discovery_results = pipeline.get_all_results()
        discovery_stats = pipeline.get_statistics()
        undiscovered_report = pipeline.get_undiscovered_report()

    except Exception as e:
        results["errors"].append(f"Discovery pipeline failed: {e}")

    results["discovery"] = {
        "results": discovery_results,
        "statistics": discovery_stats,
        "undiscovered_report": undiscovered_report,
    }

    # =================================================================
    # Phase 3: Backup Configurations
    # =================================================================
    print("Backing up configurations...", flush=True)
    backup_results: dict[str, Any] = {"summary": {}, "results": []}

    try:
        configs_dir = output.output_dir / "configs"
        backup = ConfigBackup(
            output_dir=configs_dir,
            include_secrets=include_secrets,
        )

        # Backup shell configs
        # Scanner returns "configs" (list of dicts with "path" key), not "files"
        shell_configs = scan_results.get("configs", {}).get("shell", {}).get("configs", [])
        for shell_config in shell_configs:
            source = Path(shell_config.get("path", ""))
            if source.exists():
                backup.backup_file(source, f"shell/{source.name.lstrip('.')}")

        # Backup git config
        git_config = Path.home() / ".gitconfig"
        if git_config.exists():
            backup.backup_file(git_config, "git/gitconfig")

        global_gitignore = Path.home() / ".gitignore_global"
        if global_gitignore.exists():
            backup.backup_file(global_gitignore, "git/gitignore_global")

        # Backup SSH config (not keys!)
        ssh_config = Path.home() / ".ssh/config"
        if ssh_config.exists():
            backup.backup_file(ssh_config, "ssh/config")

        # Backup editor settings from scanner data
        # Uses Tier 1 folder since these are known, trusted paths from the scanner
        editors_data = scan_results.get("editors", {})
        tier_folder = "Tier 1 - App Hints Database"

        # VS Code family (vscode, vscode_insiders, cursor)
        # Uses: settings_path, keybindings_path, snippets_path
        for editor_key in ["vscode", "vscode_insiders", "cursor"]:
            editor = editors_data.get(editor_key, {})
            if editor.get("installed"):
                # Backup settings.json
                settings_path = editor.get("settings_path")
                if settings_path:
                    source = Path(settings_path).expanduser()
                    if source.exists():
                        backup.backup_file(source, f"editors/{editor_key}/{tier_folder}/settings.json")

                # Backup keybindings.json
                keybindings_path = editor.get("keybindings_path")
                if keybindings_path:
                    source = Path(keybindings_path).expanduser()
                    if source.exists():
                        backup.backup_file(source, f"editors/{editor_key}/{tier_folder}/keybindings.json")

                # Backup snippets directory
                snippets_path = editor.get("snippets_path")
                if snippets_path:
                    source = Path(snippets_path).expanduser()
                    if source.exists() and source.is_dir():
                        backup.backup_directory(source, f"editors/{editor_key}/{tier_folder}/snippets")

        # Zed editor
        # Uses: settings_path, keymap_path (not keybindings_path)
        zed = editors_data.get("zed", {})
        if zed.get("installed"):
            settings_path = zed.get("settings_path")
            if settings_path:
                source = Path(settings_path).expanduser()
                if source.exists():
                    backup.backup_file(source, f"editors/zed/{tier_folder}/settings.json")

            keymap_path = zed.get("keymap_path")
            if keymap_path:
                source = Path(keymap_path).expanduser()
                if source.exists():
                    backup.backup_file(source, f"editors/zed/{tier_folder}/keymap.json")

        # Sublime Text
        # Uses: settings_path, keymap_path (not keybindings_path)
        sublime = editors_data.get("sublime", {})
        if sublime.get("installed"):
            settings_path = sublime.get("settings_path")
            if settings_path:
                source = Path(settings_path).expanduser()
                if source.exists():
                    backup.backup_file(source, f"editors/sublime/{tier_folder}/settings.json")

            keymap_path = sublime.get("keymap_path")
            if keymap_path:
                source = Path(keymap_path).expanduser()
                if source.exists():
                    backup.backup_file(source, f"editors/sublime/{tier_folder}/keymap.json")

        # =================================================================
        # Phase 3.5: Backup Shell Framework Configurations
        # =================================================================
        print("Backing up shell framework configurations...", flush=True)
        shell_data = scan_results.get("configs", {}).get("shell", {})
        detected_frameworks = shell_data.get("frameworks", [])

        # Backward compat: handle legacy single "framework" field
        legacy_framework = shell_data.get("framework")
        if legacy_framework and not detected_frameworks:
            detected_frameworks = [legacy_framework]

        results["framework_backups"] = []
        for framework in detected_frameworks:
            framework_name = framework.get("name", "").lower()
            if not framework_name:
                continue

            # Look up framework in hints database
            framework_hints = hints_db.lookup(framework_name)

            if framework_hints:
                fw_tier_folder = "Tier 1 - App Hints Database"
                base_dest = f"shell/frameworks/{framework_name}/{fw_tier_folder}"
                exclude_patterns = framework_hints.get("exclude_files", []) or []

                # Backup configuration_files (relative to $HOME)
                for config_path in framework_hints.get("configuration_files", []) or []:
                    source = Path.home() / config_path
                    if source.exists():
                        backup.backup_path(
                            source,
                            f"{base_dest}/{source.name}",
                            discovery_tier="hints",
                            exclude_patterns=exclude_patterns
                        )

                # Backup xdg_configuration_files (relative to ~/.config)
                xdg_config = Path.home() / ".config"
                for config_path in framework_hints.get("xdg_configuration_files", []) or []:
                    source = xdg_config / config_path
                    if source.exists():
                        backup.backup_path(
                            source,
                            f"{base_dest}/{source.name}",
                            discovery_tier="hints",
                            exclude_patterns=exclude_patterns
                        )

                results["framework_backups"].append({
                    "name": framework_name,
                    "status": "backed_up",
                    "source": "hints"
                })
            else:
                # Framework not in hints database - log warning
                results["warnings"].append(
                    f"Shell framework '{framework_name}' not found in hints database - skipping backup"
                )
                results["framework_backups"].append({
                    "name": framework_name,
                    "status": "no_hints_entry",
                    "detected_path": framework.get("path")
                })

        # Phase 6.5: Backup settings from discovery results by tier
        # Each tier gets its own subfolder for clear separation
        # Editors with explicit backup are handled above, skip Tier 1 for them
        EDITOR_KEYS_WITH_EXPLICIT_BACKUP = {"vscode", "vscode_insiders", "cursor", "zed", "sublime"}

        # Known code/text editors for category classification
        # Using explicit allowlist instead of keyword matching to avoid false positives
        KNOWN_EDITORS = {
            # VS Code family
            "vscode", "vscode-insiders", "code", "code-insiders", "cursor",
            # Zed
            "zed",
            # Sublime Text
            "sublime", "sublime-text", "sublime-text-3", "sublime-text-4",
            # JetBrains IDEs
            "intellij", "intellij-idea", "intellij-ce", "intellij-idea-ce",
            "pycharm", "pycharm-ce",
            "webstorm", "goland", "clion", "rider", "rubymine",
            "datagrip", "phpstorm", "appcode", "android-studio",
            # Terminal editors
            "vim", "neovim", "nvim", "emacs",
            # Native macOS editors
            "textmate", "bbedit", "nova", "coteditor",
            # Other popular editors
            "atom", "brackets", "helix", "ultraedit",
        }

        for dr in discovery_results:
            # Use canonical_key from hints database for consistent folder naming
            # Falls back to slugified app_name for apps not in hints
            canonical_key = dr.get("canonical_key")
            if canonical_key:
                folder_key = canonical_key
            else:
                folder_key = dr.get("app_name", "unknown").lower().replace(" ", "-")

            # Sanitize folder_key to prevent path traversal attacks
            folder_key = sanitize_path_component(folder_key)

            # Determine base category using explicit allowlist
            if folder_key in KNOWN_EDITORS:
                category = "editors"
            else:
                category = "apps"

            # Skip Tier 1 for editors with explicit backup (already handled in lines 217-239)
            # But still process Tier 2 and Tier 3 for completeness
            skip_tier1 = folder_key in EDITOR_KEYS_WITH_EXPLICIT_BACKUP

            # Tier 1: App Hints Database - trusted, but use app-specific exclude_files
            exclude_patterns = dr.get("exclude_files", [])
            if not skip_tier1:
                for path_str in dr.get("hints_paths", []):
                    path = Path(path_str)
                    if path.exists():
                        tier_folder = "Tier 1 - App Hints Database"
                        rel_path = f"{category}/{folder_key}/{tier_folder}/{path.name}"
                        backup.backup_path(path, rel_path, discovery_tier="hints", exclude_patterns=exclude_patterns)

            # Tier 2: App Conventions - filtered by ConfigFilter
            for path_str in dr.get("conventions_paths", []):
                path = Path(path_str)
                if path.exists():
                    tier_folder = "Tier 2 - App Conventions"
                    rel_path = f"{category}/{folder_key}/{tier_folder}/{path.name}"
                    backup.backup_path(path, rel_path, discovery_tier="conventions")

            # Tier 3: LLM Research - filtered by ConfigFilter
            for path_str in dr.get("llm_paths", []):
                path = Path(path_str)
                if path.exists():
                    tier_folder = "Tier 3 - LLM Research"
                    rel_path = f"{category}/{folder_key}/{tier_folder}/{path.name}"
                    backup.backup_path(path, rel_path, discovery_tier="llm")

        backup_results = {
            "summary": backup.get_summary(),
            "results": backup.results,
        }

    except Exception as e:
        results["errors"].append(f"Config backup failed: {e}")

    results["backup"] = backup_results

    # =================================================================
    # Phase 4: Generate Bundle Files
    # =================================================================
    print("Generating bundle files...", flush=True)
    try:
        bundles_result = generate_all_bundles(output.output_dir, scan_results)
        results["bundles"] = bundles_result
    except Exception as e:
        results["bundles"] = {"files": [], "errors": [str(e)]}
        results["errors"].append(f"Bundle generation failed: {e}")

    # =================================================================
    # Phase 5: Generate State File
    # =================================================================
    print("Generating state file...", flush=True)
    try:
        state = generate_state(
            output_dir=output.output_dir,
            system_info=output.system_info,
            scan_results=scan_results,
            discovery_results=discovery_results,
            discovery_stats=discovery_stats,
            backup_results=backup_results,
            cloud_destination=cloud_destination,
        )
        results["state_summary"] = state.get("summary", {})
    except Exception as e:
        results["errors"].append(f"State generation failed: {e}")

    # =================================================================
    # Final Status
    # =================================================================
    if results["errors"]:
        results["status"] = "partial" if results.get("bundles", {}).get("files") else "error"

    results["output_structure"] = output.to_dict()

    return results


def main() -> None:
    """Main entry point for MacInventory."""
    # Check arguments
    if len(sys.argv) < 2:
        print(json.dumps({
            "status": "error",
            "error": "Usage: python3 main.py /path/to/config.json"
        }))
        sys.exit(1)

    config_path = Path(sys.argv[1]).expanduser()

    # Read config file
    try:
        with open(config_path) as f:
            config = json.load(f)
    except FileNotFoundError:
        print(json.dumps({
            "status": "error",
            "error": f"Config file not found: {config_path}"
        }))
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(json.dumps({
            "status": "error",
            "error": f"Invalid JSON in config file: {e}"
        }))
        sys.exit(1)

    # Run inventory
    try:
        results = run_inventory(config)
        print(json.dumps(results, indent=2, default=str))
    except Exception as e:
        print(json.dumps({
            "status": "error",
            "error": f"Inventory failed: {e}",
            "exception_type": type(e).__name__,
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()

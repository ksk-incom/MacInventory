"""State file generation for machine-readable inventory.

Generates state.yaml - a comprehensive machine-readable inventory file
that serves as the definitive record of the captured environment.

From Vision document - State File:
    "Machine-readable inventory for programmatic access:
    - System information (Mac model, macOS version, architecture)
    - Count summaries (applications, packages, extensions, configs)
    - Discovery statistics (how each item was found)
    - Cloud sync information
    - Capture timestamp and version"

The state.yaml file is designed to:
    1. Be consumed by the guide-generator agent for documentation
    2. Enable comparison between captures over time
    3. Support programmatic access for automation
    4. Provide complete inventory metadata
"""

import yaml
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


# MacInventory version
MACINVENTORY_VERSION = "1.0.0"


def _count_items(data: Any, key: str = "count") -> int:
    """Safely count items in nested data structures.

    Args:
        data: Data structure to count items in
        key: Key to look for count in (default: 'count')

    Returns:
        Count of items, 0 if not found
    """
    if isinstance(data, dict):
        if key in data:
            return data[key]
        if "packages" in data:
            return len(data["packages"])
        if "apps" in data:
            return len(data["apps"])
        if "extensions" in data:
            return len(data["extensions"])
    if isinstance(data, list):
        return len(data)
    return 0


def build_system_section(system_info: dict[str, Any]) -> dict[str, Any]:
    """Build the system information section for state.yaml.

    Args:
        system_info: System information from structure.get_system_info()

    Returns:
        Formatted system section
    """
    return {
        "hostname": system_info.get("hostname", "unknown"),
        "mac_model": system_info.get("mac_model"),
        "macos": {
            "version": system_info.get("macos_version"),
            "product_name": system_info.get("macos_product_name"),
            "build": system_info.get("macos_build"),
        },
        "architecture": system_info.get("architecture"),
        "username": system_info.get("username"),
    }


def build_applications_section(
    apps_data: dict[str, Any],
    homebrew_data: dict[str, Any],
    mas_data: dict[str, Any]
) -> dict[str, Any]:
    """Build the applications section for state.yaml.

    Args:
        apps_data: Results from applications.scan()
        homebrew_data: Results from homebrew.scan()
        mas_data: Results from homebrew.scan_mas()

    Returns:
        Formatted applications section with counts
    """
    # Scanner returns single "applications" list with "location" field
    all_apps = apps_data.get("applications", [])
    system_apps = [a for a in all_apps if a.get("location") == "system"]
    user_apps = [a for a in all_apps if a.get("location") == "user"]
    homebrew_casks = homebrew_data.get("casks", [])
    mas_apps = mas_data.get("apps", [])

    return {
        "total": len(all_apps),
        "by_source": {
            "system_applications": len(system_apps),
            "user_applications": len(user_apps),
            "homebrew_casks": len(homebrew_casks),
            "mac_app_store": len(mas_apps),
        },
        "details": {
            "system_apps": [
                {
                    "name": app.get("name"),
                    "bundle_id": app.get("bundle_id"),
                    "version": app.get("version"),
                }
                for app in system_apps
            ],
            "user_apps": [
                {
                    "name": app.get("name"),
                    "bundle_id": app.get("bundle_id"),
                    "version": app.get("version"),
                }
                for app in user_apps
            ],
        },
    }


def build_homebrew_section(homebrew_data: dict[str, Any]) -> dict[str, Any]:
    """Build the Homebrew section for state.yaml.

    Args:
        homebrew_data: Results from homebrew.scan()

    Returns:
        Formatted Homebrew section
    """
    formulae = homebrew_data.get("formulae", [])
    casks = homebrew_data.get("casks", [])
    taps = homebrew_data.get("taps", [])

    return {
        "installed": bool(formulae or casks),
        "formulae_count": len(formulae),
        "casks_count": len(casks),
        "taps_count": len(taps),
        "taps": taps,
        "formulae": [
            {"name": f.get("name"), "version": f.get("version")}
            for f in formulae
        ],
        "casks": [
            {"name": c.get("name"), "version": c.get("version")}
            for c in casks
        ],
    }


def build_mas_section(mas_data: dict[str, Any]) -> dict[str, Any]:
    """Build the Mac App Store section for state.yaml.

    Args:
        mas_data: Results from homebrew.scan_mas()

    Returns:
        Formatted MAS section
    """
    apps = mas_data.get("apps", [])

    return {
        "installed": bool(apps),
        "count": len(apps),
        "apps": [
            {
                "id": app.get("id"),
                "name": app.get("name"),
                "version": app.get("version"),
            }
            for app in apps
        ],
    }


def build_global_packages_section(packages_data: dict[str, Any]) -> dict[str, Any]:
    """Build the global packages section for state.yaml.

    Args:
        packages_data: Results from global_packages.scan()

    Returns:
        Formatted global packages section
    """
    section: dict[str, Any] = {}

    package_managers = ["npm", "pip", "pipx", "cargo", "gem", "go"]

    for pm in package_managers:
        pm_data = packages_data.get(pm, {})
        if pm_data.get("installed"):
            packages = pm_data.get("packages", [])
            section[pm] = {
                "installed": True,
                "count": len(packages),
                "packages": [
                    {
                        "name": pkg.get("name"),
                        "version": pkg.get("version"),
                    }
                    for pkg in packages
                ],
            }
        else:
            section[pm] = {"installed": False, "count": 0}

    return section


def build_version_managers_section(vm_data: dict[str, Any]) -> dict[str, Any]:
    """Build the version managers section for state.yaml.

    Args:
        vm_data: Results from version_managers.scan()

    Returns:
        Formatted version managers section
    """
    section: dict[str, Any] = {}

    # pyenv
    pyenv = vm_data.get("pyenv", {})
    if pyenv.get("installed"):
        section["pyenv"] = {
            "installed": True,
            "versions": pyenv.get("versions", []),
            "global_version": pyenv.get("global_version"),
            "count": len(pyenv.get("versions", [])),
        }
    else:
        section["pyenv"] = {"installed": False}

    # nvm
    nvm = vm_data.get("nvm", {})
    if nvm.get("installed"):
        section["nvm"] = {
            "installed": True,
            "versions": nvm.get("versions", []),
            "default_version": nvm.get("default_version"),
            "count": len(nvm.get("versions", [])),
        }
    else:
        section["nvm"] = {"installed": False}

    # rbenv
    rbenv = vm_data.get("rbenv", {})
    if rbenv.get("installed"):
        section["rbenv"] = {
            "installed": True,
            "versions": rbenv.get("versions", []),
            "global_version": rbenv.get("global_version"),
            "count": len(rbenv.get("versions", [])),
        }
    else:
        section["rbenv"] = {"installed": False}

    # nodenv
    nodenv = vm_data.get("nodenv", {})
    if nodenv.get("installed"):
        section["nodenv"] = {
            "installed": True,
            "versions": nodenv.get("versions", []),
            "global_version": nodenv.get("global_version"),
            "count": len(nodenv.get("versions", [])),
        }
    else:
        section["nodenv"] = {"installed": False}

    # asdf
    asdf = vm_data.get("asdf", {})
    if asdf.get("installed"):
        plugins = asdf.get("plugins", {})
        section["asdf"] = {
            "installed": True,
            "plugins": plugins,
            "global_versions": asdf.get("global_versions", {}),
            "plugins_count": len(plugins),
        }
    else:
        section["asdf"] = {"installed": False}

    return section


def build_editors_section(editors_data: dict[str, Any]) -> dict[str, Any]:
    """Build the editors section for state.yaml.

    Args:
        editors_data: Results from editors.scan()

    Returns:
        Formatted editors section
    """
    section: dict[str, Any] = {}

    # VS Code family editors
    for editor_key in ["vscode", "vscode_insiders", "cursor"]:
        editor = editors_data.get(editor_key, {})
        if editor.get("installed"):
            profiles = editor.get("profiles", [])
            total_extensions = sum(
                len(p.get("extensions", [])) for p in profiles
            )
            section[editor_key] = {
                "installed": True,
                "cli_available": editor.get("cli_available", False),
                "profiles_count": len(profiles),
                "total_extensions": total_extensions,
                "settings_path": editor.get("settings_path"),
                "profiles": [
                    {
                        "name": p.get("name"),
                        "extensions_count": len(p.get("extensions", [])),
                        "extensions": [
                            {"id": e.get("id"), "version": e.get("version")}
                            for e in p.get("extensions", [])
                        ],
                    }
                    for p in profiles
                ],
            }
        else:
            section[editor_key] = {"installed": False}

    # Zed
    zed = editors_data.get("zed", {})
    if zed.get("installed"):
        extensions = zed.get("extensions", [])
        section["zed"] = {
            "installed": True,
            "extensions_count": len(extensions),
            "extensions": [{"id": e.get("id")} for e in extensions],
            "themes": zed.get("themes", []),
            "settings_path": zed.get("settings_path"),
        }
    else:
        section["zed"] = {"installed": False}

    # Sublime Text
    sublime = editors_data.get("sublime", {})
    if sublime.get("installed"):
        packages = sublime.get("packages", [])
        section["sublime"] = {
            "installed": True,
            "packages_count": len(packages),
            "packages": [{"name": p.get("name")} for p in packages],
            "settings_path": sublime.get("settings_path"),
        }
    else:
        section["sublime"] = {"installed": False}

    # JetBrains
    jetbrains = editors_data.get("jetbrains", {})
    ides = jetbrains.get("ides", [])
    if ides:
        section["jetbrains"] = {
            "installed": True,
            "ides_count": len(ides),
            "ides": [{"id": ide.get("id"), "name": ide.get("name")} for ide in ides],
        }
    else:
        section["jetbrains"] = {"installed": False}

    return section


def build_configs_section(
    configs_data: dict[str, Any],
    backup_results: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    """Build the configurations section for state.yaml.

    Args:
        configs_data: Results from configs.scan()
        backup_results: Results from config backup operation

    Returns:
        Formatted configurations section
    """
    shell = configs_data.get("shell", {})
    git = configs_data.get("git", {})
    ssh = configs_data.get("ssh", {})

    # Scanner returns "configs" list with config file dicts, not "files" list of strings
    shell_configs = shell.get("configs", [])

    # Git user info is nested under "user" dict, and "installed" instead of "config_exists"
    git_user = git.get("user") or {}

    # Find global gitignore from git configs list
    global_gitignore = next(
        (c.get("path") for c in git.get("configs", [])
         if "gitignore" in c.get("name", "").lower()),
        None
    )

    section: dict[str, Any] = {
        "shell": {
            "files": [c.get("name") for c in shell_configs],
            "count": len(shell_configs),
            "current_shell": shell.get("current_shell"),
            "frameworks": shell.get("frameworks", []),
            # Backward compat
            "framework": shell.get("framework"),
        },
        "git": {
            "config_exists": git.get("installed", False),
            "version": git.get("version"),
            "global_gitignore": global_gitignore,
            "user_name": git_user.get("name"),
            "user_email": git_user.get("email"),
            "aliases_count": len(git.get("aliases", [])),
        },
        "ssh": {
            "config_exists": ssh.get("config_exists", False),
            "hosts_count": len(ssh.get("hosts", [])),
        },
    }

    # Add backup statistics if available
    if backup_results:
        summary = backup_results.get("summary", {})
        section["backup"] = {
            "total_operations": summary.get("total_operations", 0),
            "success": summary.get("success", 0),
            "skipped": summary.get("skipped", 0),
            "errors": summary.get("errors", 0),
            "secrets_filtered": not summary.get("include_secrets", True),
        }

    return section


def build_discovery_section(
    discovery_results: Optional[list[dict[str, Any]]] = None,
    discovery_stats: Optional[dict[str, Any]] = None,
    backup_results: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    """Build the discovery statistics section for state.yaml.

    Args:
        discovery_results: List of discovery result dicts
        discovery_stats: Statistics from DiscoveryPipeline.get_statistics()
        backup_results: Results from backup operations (for tier filtering stats)

    Returns:
        Formatted discovery section
    """
    section: dict[str, Any] = {}

    if discovery_stats:
        section.update({
            "total_apps_processed": discovery_stats.get("total_apps", 0),
            "apps_with_settings": discovery_stats.get("with_settings", 0),
            "apps_needs_llm_discovery": discovery_stats.get("needs_llm_discovery", 0),
            "by_source": discovery_stats.get("by_source", {}),
            "by_confidence": discovery_stats.get("by_confidence", {}),
        })
    elif discovery_results:
        # Build from raw results
        by_source: dict[str, int] = {}
        by_confidence: dict[str, int] = {}
        with_settings = 0

        for result in discovery_results:
            source = result.get("source", "unknown")
            confidence = result.get("confidence", "low")
            by_source[source] = by_source.get(source, 0) + 1
            by_confidence[confidence] = by_confidence.get(confidence, 0) + 1

            if result.get("resolved_paths") or result.get("hints_paths") or result.get("conventions_paths"):
                with_settings += 1

        section.update({
            "total_apps_processed": len(discovery_results),
            "apps_with_settings": with_settings,
            "by_source": by_source,
            "by_confidence": by_confidence,
        })

    # Phase 6.5: Add tier-based statistics from discovery results
    if discovery_results:
        tier_stats = {
            "hints": {
                "apps_count": 0,
                "paths_count": 0,
            },
            "conventions": {
                "apps_count": 0,
                "paths_count": 0,
            },
            "llm": {
                "apps_count": 0,
                "paths_count": 0,
            }
        }

        for result in discovery_results:
            hints_paths = result.get("hints_paths", [])
            conventions_paths = result.get("conventions_paths", [])
            llm_paths = result.get("llm_paths", [])

            if hints_paths:
                tier_stats["hints"]["apps_count"] += 1
                tier_stats["hints"]["paths_count"] += len(hints_paths)

            if conventions_paths:
                tier_stats["conventions"]["apps_count"] += 1
                tier_stats["conventions"]["paths_count"] += len(conventions_paths)

            if llm_paths:
                tier_stats["llm"]["apps_count"] += 1
                tier_stats["llm"]["paths_count"] += len(llm_paths)

        section["by_tier"] = tier_stats

    # Phase 6.5: Add backup filtering statistics
    if backup_results:
        backup_items = backup_results.get("results", [])
        tier_backup_stats = {
            "hints": {"files_backed_up": 0},
            "conventions": {"files_backed_up": 0, "files_filtered": 0},
            "llm": {"files_backed_up": 0, "files_filtered": 0},
        }

        for item in backup_items:
            tier = item.get("discovery_tier", "unknown")
            if tier in tier_backup_stats:
                if item.get("status") == "success":
                    tier_backup_stats[tier]["files_backed_up"] += 1
                elif item.get("tier_filtered"):
                    if "files_filtered" in tier_backup_stats[tier]:
                        tier_backup_stats[tier]["files_filtered"] += 1

                # Also count filtered files from directory backups
                if "tier_filtered" in item and isinstance(item["tier_filtered"], int):
                    if "files_filtered" in tier_backup_stats[tier]:
                        tier_backup_stats[tier]["files_filtered"] += item["tier_filtered"]

        if "by_tier" in section:
            for tier in tier_backup_stats:
                if tier in section["by_tier"]:
                    section["by_tier"][tier].update(tier_backup_stats[tier])
        else:
            section["by_tier"] = tier_backup_stats

    return section


def build_summary_section(
    apps_data: dict[str, Any],
    homebrew_data: dict[str, Any],
    mas_data: dict[str, Any],
    global_packages: dict[str, Any],
    editors_data: dict[str, Any],
    version_managers: dict[str, Any],
) -> dict[str, Any]:
    """Build the summary counts section for state.yaml.

    Args:
        apps_data: Applications scan data
        homebrew_data: Homebrew scan data
        mas_data: Mac App Store scan data
        global_packages: Global packages scan data
        editors_data: Editors scan data
        version_managers: Version managers scan data

    Returns:
        Formatted summary section with total counts
    """
    # Count applications - scanner returns single "applications" list
    total_apps = len(apps_data.get("applications", []))

    # Count Homebrew packages
    homebrew_count = (
        len(homebrew_data.get("formulae", [])) +
        len(homebrew_data.get("casks", []))
    )

    # Count MAS apps
    mas_count = len(mas_data.get("apps", []))

    # Count global packages
    global_count = 0
    for pm in ["npm", "pip", "pipx", "cargo", "gem", "go"]:
        pm_data = global_packages.get(pm, {})
        if pm_data.get("installed"):
            global_count += len(pm_data.get("packages", []))

    # Count editor extensions
    extensions_count = 0
    for editor_key in ["vscode", "vscode_insiders", "cursor"]:
        editor = editors_data.get(editor_key, {})
        if editor.get("installed"):
            for profile in editor.get("profiles", []):
                extensions_count += len(profile.get("extensions", []))

    zed = editors_data.get("zed", {})
    if zed.get("installed"):
        extensions_count += len(zed.get("extensions", []))

    sublime = editors_data.get("sublime", {})
    if sublime.get("installed"):
        extensions_count += len(sublime.get("packages", []))

    # Count version manager versions
    versions_count = 0
    for vm_key in ["pyenv", "nvm", "rbenv", "nodenv"]:
        vm = version_managers.get(vm_key, {})
        if vm.get("installed"):
            versions_count += len(vm.get("versions", []))

    asdf = version_managers.get("asdf", {})
    if asdf.get("installed"):
        for plugin_data in asdf.get("plugins", {}).values():
            versions_count += len(plugin_data.get("versions", []))

    return {
        "total_applications": total_apps,
        "homebrew_packages": homebrew_count,
        "mac_app_store_apps": mas_count,
        "global_packages": global_count,
        "editor_extensions": extensions_count,
        "runtime_versions": versions_count,
        "total_items": (
            total_apps + homebrew_count + mas_count +
            global_count + extensions_count + versions_count
        ),
    }


def generate_state(
    output_dir: Path,
    system_info: dict[str, Any],
    scan_results: dict[str, Any],
    discovery_results: Optional[list[dict[str, Any]]] = None,
    discovery_stats: Optional[dict[str, Any]] = None,
    backup_results: Optional[dict[str, Any]] = None,
    cloud_destination: Optional[str] = None,
) -> dict[str, Any]:
    """Generate the complete state.yaml file.

    Args:
        output_dir: Output directory path
        system_info: System information
        scan_results: Combined results from all scanners
        discovery_results: List of discovery result dicts
        discovery_stats: Discovery statistics
        backup_results: Config backup results
        cloud_destination: Cloud sync destination (if any)

    Returns:
        The complete state dictionary (also written to file)
    """
    # Extract individual scanner results
    apps_data = scan_results.get("applications", {})
    homebrew_data = scan_results.get("homebrew", {})
    mas_data = scan_results.get("mas", {})
    global_packages = scan_results.get("global_packages", {})
    version_managers = scan_results.get("version_managers", {})
    editors_data = scan_results.get("editors", {})
    configs_data = scan_results.get("configs", {})

    # Build state structure
    state: dict[str, Any] = {
        "macinventory": {
            "version": MACINVENTORY_VERSION,
            "capture_timestamp": datetime.now().isoformat(),
            "output_directory": str(output_dir),
            "cloud_destination": cloud_destination,
        },
        "system": build_system_section(system_info),
        "summary": build_summary_section(
            apps_data, homebrew_data, mas_data,
            global_packages, editors_data, version_managers
        ),
        "applications": build_applications_section(apps_data, homebrew_data, mas_data),
        "homebrew": build_homebrew_section(homebrew_data),
        "mac_app_store": build_mas_section(mas_data),
        "global_packages": build_global_packages_section(global_packages),
        "version_managers": build_version_managers_section(version_managers),
        "editors": build_editors_section(editors_data),
        "configurations": build_configs_section(configs_data, backup_results),
    }

    # Add discovery section if available
    # Phase 6.5: Pass backup_results for tier filtering statistics
    if discovery_results or discovery_stats:
        state["discovery"] = build_discovery_section(discovery_results, discovery_stats, backup_results)

    # Write to file
    state_path = output_dir / "state.yaml"
    with open(state_path, "w") as f:
        yaml.dump(state, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    return state


def load_state(state_path: Path) -> dict[str, Any]:
    """Load a state.yaml file.

    Args:
        state_path: Path to state.yaml file

    Returns:
        Parsed state dictionary

    Raises:
        FileNotFoundError: If file doesn't exist
        yaml.YAMLError: If file is invalid YAML
    """
    with open(state_path) as f:
        return yaml.safe_load(f)


def compare_states(
    state1: dict[str, Any],
    state2: dict[str, Any]
) -> dict[str, Any]:
    """Compare two state files to find differences.

    Args:
        state1: First state (typically older)
        state2: Second state (typically newer)

    Returns:
        Dictionary with comparison results
    """
    comparison: dict[str, Any] = {
        "timestamp1": state1.get("macinventory", {}).get("capture_timestamp"),
        "timestamp2": state2.get("macinventory", {}).get("capture_timestamp"),
        "summary_diff": {},
        "added": {},
        "removed": {},
    }

    # Compare summary counts
    summary1 = state1.get("summary", {})
    summary2 = state2.get("summary", {})

    for key in summary2:
        val1 = summary1.get(key, 0)
        val2 = summary2.get(key, 0)
        if val1 != val2:
            comparison["summary_diff"][key] = {
                "before": val1,
                "after": val2,
                "change": val2 - val1,
            }

    # Compare Homebrew packages
    brew1 = set(f["name"] for f in state1.get("homebrew", {}).get("formulae", []))
    brew2 = set(f["name"] for f in state2.get("homebrew", {}).get("formulae", []))
    comparison["added"]["homebrew_formulae"] = list(brew2 - brew1)
    comparison["removed"]["homebrew_formulae"] = list(brew1 - brew2)

    cask1 = set(c["name"] for c in state1.get("homebrew", {}).get("casks", []))
    cask2 = set(c["name"] for c in state2.get("homebrew", {}).get("casks", []))
    comparison["added"]["homebrew_casks"] = list(cask2 - cask1)
    comparison["removed"]["homebrew_casks"] = list(cask1 - cask2)

    return comparison


if __name__ == "__main__":
    import json
    import tempfile

    # Demo state generation with mock data
    mock_system = {
        "hostname": "MacBook-Pro.local",
        "mac_model": "MacBookPro18,3",
        "macos_version": "14.2.1",
        "macos_product_name": "macOS Sonoma",
        "architecture": "arm64",
        "username": "developer",
    }

    # Mock data structure matching actual scanner output format
    mock_results = {
        "applications": {
            "applications": [
                {"name": "Safari", "bundle_id": "com.apple.Safari", "version": "17.2", "location": "system"},
                {"name": "VS Code", "bundle_id": "com.microsoft.VSCode", "version": "1.85.0", "location": "user"},
            ],
            "count": 2,
            "errors": [],
        },
        "homebrew": {
            "formulae": [
                {"name": "git", "version": "2.43.0"},
                {"name": "python@3.12", "version": "3.12.1"},
            ],
            "casks": [
                {"name": "docker", "version": "4.26.1"},
            ],
            "taps": ["homebrew/cask"],
        },
        "mas": {"apps": []},
        "global_packages": {
            "npm": {
                "installed": True,
                "packages": [{"name": "typescript", "version": "5.3.3"}],
            },
            "pip": {"installed": False},
            "pipx": {"installed": False},
            "cargo": {"installed": False},
            "gem": {"installed": False},
            "go": {"installed": False},
        },
        "version_managers": {
            "pyenv": {"installed": True, "versions": ["3.11.7", "3.12.1"], "global_version": "3.12.1"},
            "nvm": {"installed": False},
            "rbenv": {"installed": False},
            "nodenv": {"installed": False},
            "asdf": {"installed": False},
        },
        "editors": {
            "vscode": {
                "installed": True,
                "cli_available": True,
                "profiles": [
                    {
                        "name": "Default",
                        "extensions": [
                            {"id": "ms-python.python", "version": "2024.0.1"},
                        ],
                    }
                ],
                "settings_path": "~/Library/Application Support/Code/User/settings.json",
            },
            "vscode_insiders": {"installed": False},
            "cursor": {"installed": False},
            "zed": {"installed": False},
            "sublime": {"installed": False},
            "jetbrains": {"ides": []},
        },
        "configs": {
            "shell": {
                "current_shell": "zsh",
                "configs": [
                    {"name": ".zshrc", "path": "/Users/developer/.zshrc", "shell": "zsh"},
                    {"name": ".zprofile", "path": "/Users/developer/.zprofile", "shell": "zsh"},
                ],
                "configs_count": 2,
                "framework": None,
            },
            "git": {
                "installed": True,
                "version": "2.43.0",
                "configs": [{"name": ".gitconfig", "path": "/Users/developer/.gitconfig"}],
                "user": {"name": "Developer", "email": "dev@example.com"},
                "aliases": [],
            },
            "ssh": {"config_exists": True, "hosts": ["github.com"]},
        },
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        output_dir.mkdir(exist_ok=True)

        state = generate_state(
            output_dir=output_dir,
            system_info=mock_system,
            scan_results=mock_results,
        )

        print("=== Generated State Summary ===")
        print(json.dumps(state.get("summary", {}), indent=2))

        print("\n=== State File Written ===")
        state_path = output_dir / "state.yaml"
        print(state_path.read_text()[:2000])

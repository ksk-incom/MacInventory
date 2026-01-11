---
name: macos-discovery
description: This skill should be used when the user asks to "add app to hints database", "research app settings", "find application preferences", "discover config paths", "macOS config discovery", "where does [app] store settings", or needs to understand where macOS applications store their settings and configuration files.
version: 1.0.0
---

# macOS Application Configuration Discovery

This skill provides knowledge and methodology for discovering where macOS applications store their configuration files, preferences, and settings. It enables effective contribution to MacInventory's hints database.

## Overview

macOS applications store their configuration in predictable locations based on app type, development era, and sandboxing status. Understanding these patterns enables systematic discovery of config paths for any application.

### The Three-Tier Discovery System

MacInventory uses a three-tier approach to find application configurations:

1. **Tier 1 - Hints Database**: Curated YAML entries with verified config paths (highest trust)
2. **Tier 2 - Conventions**: Automatic scanning of standard macOS locations
3. **Tier 3 - LLM Research**: Web search and intelligent discovery for unknown apps

This skill supports all three tiers by providing the knowledge needed to research and document application configurations.

## Standard macOS Configuration Locations

### Primary Locations (Check First)

| Location                         | Purpose           | Typical Contents           |
|----------------------------------|-------------------|----------------------------|
| `~/Library/Application Support/` | Modern app data   | Databases, caches, configs |
| `~/Library/Preferences/`         | Preference plists | `.plist` settings files    |
| `~/.config/`                     | XDG standard      | CLI tool configs           |
| `~/Library/Containers/`          | Sandboxed apps    | App-specific storage       |

### Secondary Locations (App-Specific)

| Location                             | Purpose         | Example Apps               |
|--------------------------------------|-----------------|----------------------------|
| `~/.appname/`                        | Dotfile configs | CLI tools, dev tools       |
| `~/Library/Group Containers/`        | Shared app data | iCloud-enabled apps        |
| `~/Library/Caches/`                  | Cache data      | All apps (usually exclude) |
| `~/Library/Saved Application State/` | Window states   | GUI apps                   |

### Environment-Specific Paths

For detailed information on each location and its typical contents, see `references/common-paths.md`.

## App-Hints.yaml Entry Format

To add an application to the hints database, create a YAML entry with this structure:

```yaml
app-name:
  bundle_id: com.developer.AppName  # Required (null for CLI tools)
  install_method: cask              # Required: cask | formula | mas | dmg | system
  configuration_files:              # Paths relative to $HOME (no ~/ prefix)
    - Library/Application Support/AppName/
    - Library/Preferences/com.developer.AppName.plist
  xdg_configuration_files:          # Paths relative to ~/.config (optional)
    - appname/config.yaml
  exclude_files:                    # Files/dirs to skip during backup
    - "*.log"
    - "Cache/"
    - "*.tmp"
  notes: |
    Optional notes about the app's config behavior,
    special considerations, or discovery methodology.
```

### Field Descriptions

- **bundle_id** (required): macOS bundle identifier - get with `osascript -e 'id of app "AppName"'`. Use `null` for CLI tools.
- **install_method** (required): How the app is installed - `cask` | `formula` | `mas` | `dmg` | `system`
- **configuration_files**: Paths relative to `$HOME` (no `~/` prefix). For files like `~/Library/...`
- **xdg_configuration_files**: Paths relative to `$XDG_CONFIG_HOME` (default `~/.config/`). For files like `~/.config/appname/`
- **exclude_files**: Glob patterns for files/dirs to skip during backup
- **notes**: Optional context about the app or special handling needed

**IMPORTANT**: Paths are RELATIVE - use `Library/Application Support/App/` not `~/Library/Application Support/App/`

For a complete template with all optional fields, see `examples/hints-entry-template.yaml`.

## Discovery Methodology

### Quick Discovery Checklist

When researching where an app stores its configuration:

1. **Check standard locations first** - Most apps use conventional paths
2. **Search for the app's bundle ID** - Find with: `osascript -e 'id of app "AppName"'`
3. **Look in Application Support** - Most modern apps: `ls ~/Library/Application\ Support/ | grep -i appname`
4. **Check Preferences** - Traditional plist: `ls ~/Library/Preferences/ | grep -i appname`
5. **Try XDG config** - CLI tools: `ls ~/.config/ | grep -i appname`
6. **Check for dotfiles** - Some tools: `ls -la ~/ | grep -i appname`

### Research Resources

When standard locations don't yield results:

- **Official documentation**: Check the app's docs/FAQ for "where are settings stored"
- **GitHub repository**: For open source apps, check README and code
- **Stack Overflow**: Search "[AppName] config file location mac"
- **Reddit/Forums**: Community discussions often reveal hidden paths

For detailed research methodology, see `references/research-methodology.md`.

## Configuration File Patterns

Different types of apps follow different configuration patterns:

### GUI Applications

Modern macOS GUI apps typically use:

- `~/Library/Application Support/AppName/` for data and complex configs
- `~/Library/Preferences/com.developer.AppName.plist` for simple preferences
- Sandboxed apps: `~/Library/Containers/com.developer.AppName/`

### CLI Tools

Command-line tools commonly use:

- `~/.config/toolname/` (XDG standard)
- `~/.toolname` or `~/.toolnamerc` (traditional dotfiles)
- `~/.toolname/config.yaml` or similar

### Development Tools

IDEs and dev tools often have complex configurations:

- Settings, keybindings, snippets (usually JSON or XML)
- Extensions/plugins directory
- Project-specific vs global settings

For comprehensive patterns by app category, see `references/settings-patterns.md`.

## What to Exclude from Backup

Not everything in an app's directory should be backed up. Exclude:

### Always Exclude

- **Caches**: `Cache/`, `Caches/`, `*.cache`
- **Logs**: `*.log`, `Logs/`, `log/`
- **Temporary files**: `*.tmp`, `temp/`, `Temp/`
- **Generated data**: `GPUCache/`, `Code Cache/`
- **Large databases**: `*.sqlite` (unless settings), `*.db`

### Usually Exclude

- **Updates**: `Updates/`, `*.download`
- **App backups**: `Backups/`, `backup/`
- **Media caches**: `MediaCache/`, `ImageCache/`

### Never Backup

- **SSH keys**: `id_rsa`, `id_ed25519`, etc.
- **Certificates**: `*.pem`, `*.key` (non-config)
- **OAuth tokens**: If stored in plaintext files

## Validation Process

Before adding an entry to the hints database:

1. **Verify paths exist**: Use Glob to confirm each path is present on the system
2. **Check file contents**: Ensure files are configuration, not caches/data
3. **Test exclude patterns**: Verify patterns correctly filter non-config files
4. **Validate YAML syntax**: Use the validate-hints.py script

```bash
# Validate hints database (use installed plugin path)
PLUGIN_PATH=~/.claude/plugins/macinventory@MacInventory
python3 $PLUGIN_PATH/skills/macos-discovery/scripts/validate-hints.py \
    $PLUGIN_PATH/data/app-hints.yaml
```

## Utility Scripts

This skill includes utility scripts in `scripts/`:

- **validate-hints.py**: Validate app-hints.yaml entries for correctness
- **test-security-patterns.py**: Test security pattern matching

## Additional Resources

### Reference Files

For detailed information beyond this overview:

- **`references/common-paths.md`** - Complete guide to macOS config locations
- **`references/settings-patterns.md`** - Config patterns by application type
- **`references/research-methodology.md`** - How to research unknown apps

### Examples

- **`examples/hints-entry-template.yaml`** - Complete template for new entries

## Integration with MacInventory

This skill supports:

1. **Adding apps to hints database** - Research and create YAML entries
2. **Tier 3 discovery** - Used by app-discovery agent for unknown apps
3. **Validation** - Verify discovered paths are actual configurations
4. **Documentation** - Understanding macOS config conventions

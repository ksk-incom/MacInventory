# Application Research Methodology

This reference provides a systematic approach to researching where unknown applications store their configuration files on macOS.

## Research Process Overview

```
1. Check Standard Locations (5 min)
   ↓
2. Find Bundle Identifier
   ↓
3. Web Search Research (if needed)
   ↓
4. File System Exploration
   ↓
5. Validate Discoveries
   ↓
6. Create Hints Entry
```

---

## Step 1: Check Standard Locations First

Before researching online, check the most common locations. Many apps will be found here.

### Quick Check Commands

```bash
# Set the app name (case-insensitive search)
APP="appname"

# Check Application Support
ls ~/Library/Application\ Support/ | grep -i "$APP"

# Check Preferences
ls ~/Library/Preferences/ | grep -i "$APP"

# Check XDG config
ls ~/.config/ | grep -i "$APP"

# Check Containers (sandboxed apps)
ls ~/Library/Containers/ | grep -i "$APP"

# Check Group Containers
ls ~/Library/Group\ Containers/ | grep -i "$APP"

# Check home directory dotfiles
ls -la ~/ | grep -i "$APP"
```

### Comprehensive Search Script

```bash
#!/bin/bash
APP="${1:-appname}"

echo "=== Searching for: $APP ==="

echo -e "\n--- Application Support ---"
find ~/Library/Application\ Support -maxdepth 1 -iname "*$APP*" 2>/dev/null

echo -e "\n--- Preferences ---"
find ~/Library/Preferences -maxdepth 1 -iname "*$APP*" 2>/dev/null

echo -e "\n--- XDG Config ---"
find ~/.config -maxdepth 1 -iname "*$APP*" 2>/dev/null

echo -e "\n--- Containers ---"
find ~/Library/Containers -maxdepth 1 -iname "*$APP*" 2>/dev/null

echo -e "\n--- Group Containers ---"
find ~/Library/Group\ Containers -maxdepth 1 -iname "*$APP*" 2>/dev/null

echo -e "\n--- Home Dotfiles ---"
ls -la ~/ 2>/dev/null | grep -i "$APP"

echo -e "\n--- Deep Search (slower) ---"
find ~/Library -maxdepth 3 -iname "*$APP*" 2>/dev/null | head -20
```

---

## Step 2: Find the Bundle Identifier

The bundle identifier is critical for finding configs, especially in Preferences and Containers.

### Getting Bundle ID

```bash
# Method 1: From app bundle
osascript -e 'id of app "AppName"'

# Method 2: Using mdls
mdls -name kMDItemCFBundleIdentifier "/Applications/AppName.app"

# Method 3: Reading Info.plist directly
defaults read "/Applications/AppName.app/Contents/Info" CFBundleIdentifier

# Method 4: Using plutil
plutil -p "/Applications/AppName.app/Contents/Info.plist" | grep CFBundleIdentifier
```

### Using Bundle ID

Once you have the bundle ID (e.g., `com.example.AppName`):

```bash
BUNDLE_ID="com.example.AppName"

# Check Preferences
ls ~/Library/Preferences/$BUNDLE_ID.plist

# Check Containers
ls -la ~/Library/Containers/$BUNDLE_ID/

# Check Application Support variations
ls ~/Library/Application\ Support/$BUNDLE_ID/
```

---

## Step 3: Web Search Research

When standard locations don't yield results, research online.

### Effective Search Queries

**Primary queries** (try these first):

- `"AppName" config file location mac`
- `"AppName" preferences path macos`
- `where does "AppName" store settings mac`
- `"AppName" configuration directory`

**Developer-focused queries**:

- `"AppName" dotfiles`
- `site:github.com "AppName" config`
- `"AppName" XDG_CONFIG_HOME`

**Troubleshooting queries**:

- `"AppName" reset settings mac`
- `"AppName" backup settings`
- `"AppName" export settings`

### Valuable Sources

**Tier 1 - Most Reliable**:

1. **Official documentation** - App's website, docs, FAQ
2. **GitHub repository** - README, issues, source code
3. **App's support forums** - Official community

**Tier 2 - Generally Reliable**:
4. **Stack Overflow** - Technical Q&A
5. **Ask Different (Apple SE)** - macOS-specific
6. **Super User** - General power user Q&A

**Tier 3 - Use with Verification**:
7. **Reddit** (r/macapps, r/mac, app-specific subs)
8. **Blog posts** - May be outdated
9. **Forum discussions** - Verify independently

### What to Look For

In documentation or discussions:

- Explicit path mentions (e.g., "Settings are stored in ~/.config/app/")
- Instructions for backup/export
- Reset/clean install instructions
- Migration guides

In source code (GitHub):

- Look for `XDG_CONFIG_HOME`, `Application Support`, `Preferences`
- Check config loading code
- Look at README for setup instructions

---

## Step 4: File System Exploration

When web research is inconclusive, explore the file system directly.

### Monitoring File Activity

**Using fs_usage** (requires elevated privileges):

```bash
# Monitor file access by app name
sudo fs_usage -w -f filesystem AppName 2>&1 | grep -E "(open|write|create)"

# Filter for config-like paths
sudo fs_usage -w -f filesystem AppName 2>&1 | grep -E "(Library|\.config|Preferences)"
```

**Using opensnoop** (if available):

```bash
sudo opensnoop -n AppName
```

**Using dtrace** (advanced):

```bash
sudo dtrace -n 'syscall::open*:entry /execname == "AppName"/ { printf("%s %s\n", execname, copyinstr(arg0)); }'
```

### Timestamp-Based Discovery

After changing settings in an app, find recently modified files:

```bash
# Find files modified in last 5 minutes in Library
find ~/Library -mmin -5 -type f 2>/dev/null | grep -v Cache

# Find files modified in last 5 minutes in .config
find ~/.config -mmin -5 -type f 2>/dev/null
```

### Process Inspection

Check what files an app has open:

```bash
# Find the process ID
pgrep -f "AppName"

# List open files for that PID
lsof -p <PID> | grep -E "(Library|\.config|home)"
```

---

## Step 5: Validate Discoveries

Before adding to hints database, validate findings.

### Path Validation

```bash
# Check path exists
test -e "/path/to/config" && echo "EXISTS" || echo "NOT FOUND"

# Check path type
file "/path/to/config"

# Check if readable
test -r "/path/to/config" && echo "READABLE" || echo "NOT READABLE"
```

### Content Validation

```bash
# For directories - list contents
ls -la "/path/to/config/"

# For plist files - verify and show contents
plutil -lint "/path/to/file.plist" && plutil -p "/path/to/file.plist"

# For JSON files
python3 -m json.tool "/path/to/file.json" | head -20

# For YAML files
python3 -c "import yaml; print(yaml.safe_load(open('/path/to/file.yaml')))" | head -20
```

### Distinguish Config from Cache

Signs of **configuration** (include in backup):

- Human-readable format (JSON, YAML, TOML, plist)
- Small file size (usually <1MB)
- Contains settings, preferences, keybindings
- Named `settings`, `config`, `preferences`, etc.

Signs of **cache/data** (exclude from backup):

- Binary format
- Large file size (>10MB)
- Named `cache`, `index`, `temp`
- Located in `Cache/`, `Caches/` directories
- Contains session/history data

---

## Step 6: Create Hints Entry

Once validated, create the hints database entry.

### Entry Checklist

Before finalizing:

- [ ] App name key is lowercase-hyphenated (e.g., `my-app-name`)
- [ ] `bundle_id` obtained via osascript (null for CLI tools)
- [ ] `install_method` specified (cask | formula | mas | dmg | system)
- [ ] All paths verified to exist
- [ ] Paths are RELATIVE (no `~/` prefix)
- [ ] HOME paths in `configuration_files` (relative to $HOME)
- [ ] XDG paths in `xdg_configuration_files` (relative to ~/.config)
- [ ] `exclude_files` cover caches and logs
- [ ] Notes document discovery method
- [ ] YAML syntax is valid

### Entry Template

```yaml
app-name:
  bundle_id: com.developer.AppName  # null for CLI tools
  install_method: cask              # cask | formula | mas | dmg | system
  configuration_files:              # Paths relative to $HOME (no ~/ prefix)
    - Library/Application Support/AppName/
    - Library/Preferences/com.developer.AppName.plist
  xdg_configuration_files:          # Paths relative to ~/.config (optional)
    - appname/config.yaml
  exclude_files:
    - "*.log"
    - "Cache/"
    - "*.tmp"
    - "Logs/"
  notes: |
    Discovery: Found via [method]
    Config files: [list key files]
    Verified: [date]
    Source: [link if from web research]
```

### Validate Entry

```bash
# Run hints validator (use installed plugin path)
PLUGIN_PATH=~/.claude/plugins/macinventory@MacInventory
python3 $PLUGIN_PATH/skills/macos-discovery/scripts/validate-hints.py \
    $PLUGIN_PATH/data/app-hints.yaml
```

---

## Research Examples

### Example 1: Well-Documented App (Obsidian)

**Search**: "Obsidian config location mac"

**Result**: Official docs say `~/Library/Application Support/obsidian/`

**Get Bundle ID**:

```bash
osascript -e 'id of app "Obsidian"'
# md.obsidian
```

**Validation**:

```bash
ls ~/Library/Application\ Support/obsidian/
# obsidian.json, themes/, plugins/, etc.
```

**Entry**:

```yaml
obsidian:
  bundle_id: md.obsidian
  install_method: cask
  configuration_files:
    - Library/Application Support/obsidian/
  exclude_files:
    - "Cache/"
  notes: Documented in official docs. Contains app settings and vault list.
```

### Example 2: CLI Tool (starship)

**Search**: "starship prompt config location"

**Result**: GitHub README says `~/.config/starship.toml`

**Bundle ID**: None (CLI tool installed via Homebrew)

**Install method**: `formula` (installed via `brew install starship`)

**Validation**:

```bash
cat ~/.config/starship.toml
# Shows prompt configuration
```

**Entry**:

```yaml
starship:
  bundle_id: null
  install_method: formula
  xdg_configuration_files:
    - starship.toml
  notes: Single TOML config file. Documented in GitHub README.
```

### Example 3: Less-Documented App

**Search**: Limited results

**Approach**:

1. Get bundle ID: `osascript -e 'id of app "MysteryApp"'` → `com.mystery.app`
2. Determine install method: `brew list --cask | grep -i mystery` → Found as cask
3. Check standard locations:
   - `ls ~/Library/Preferences/com.mystery.app.plist` → Found!
   - `ls ~/Library/Application Support/MysteryApp/` → Found!
4. Change setting in app, check modified files
5. Validate both locations contain config data

**Entry**:

```yaml
mystery-app:
  bundle_id: com.mystery.app
  install_method: cask
  configuration_files:
    - Library/Application Support/MysteryApp/
    - Library/Preferences/com.mystery.app.plist
  exclude_files:
    - "Cache/"
  notes: |
    Discovered via bundle ID search and timestamp monitoring.
    Main settings in Application Support, preferences in plist.
```

---

## Troubleshooting

### "Can't Find Any Config"

1. **Verify app is installed** and has been run at least once
2. **Check for unusual naming** (company name vs app name)
3. **Look for sandboxed version** in Containers
4. **Check if cloud-synced** (some apps store everything in cloud)
5. **Monitor file system** while changing settings

### "Multiple Possible Locations"

Include all verified locations in the entry. Apps often use multiple locations for different purposes:

- Preferences plist for simple settings
- Application Support for complex data
- XDG config for cross-platform compatibility

### "Config Contains Secrets"

1. Add file to exclude_patterns if it's entirely secrets
2. Note in entry that security filtering should handle it
3. Consider if the file is essential for restoration

### "Very Large Config Directory"

1. Investigate subdirectories to find actual config files
2. Create specific path to config subdirectory, not entire app folder
3. Add aggressive exclude patterns for non-config data

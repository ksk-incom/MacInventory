# MacInventory

**Never lose your Mac setup again.**

[![macOS](https://img.shields.io/badge/macOS-956D51?style=for-the-badge&logo=apple&logoColor=white)](https://www.apple.com/macos/) [![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/) [![Claude Code](https://img.shields.io/badge/Claude_Code-Plugin-D97706?style=for-the-badge&logo=claude&logoColor=white)](https://claude.ai/code) [![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

<p align="center">
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-features">Features</a> •
  <a href="#-installation">Installation</a>
</p>

---

## Why MacInventory?

Ever had that sinking feeling when your Mac dies and you realize you don't remember half of what you had installed? Or spent hours manually recreating your dev environment on a new machine?

**MacInventory is your insurance policy.** One command captures everything - apps, packages, configs, extensions - and creates restoration scripts that actually work.

| Without MacInventory                    | With MacInventory                     |
|-----------------------------------------|---------------------------------------|
| 😰 "What Homebrew packages did I have?" | ✅ `brew bundle --file=Brewfile`       |
| 😰 "Where were my VS Code settings?"    | ✅ All configs backed up automatically |
| 😰 "What was my shell configuration?"   | ✅ `.zshrc`, `.bashrc`, aliases saved  |
| 😰 "How did I set up that app?"         | ✅ Professional Restoration Guide      |

---

## ⚡ Quick Start

```bash
# 1. Start up your Claude Code
claude

# 2. Install the plugin (one-time)
/plugin marketplace add ksk-incom/MacInventory
/plugin install macinventory@MacInventory

# 3. Run the inventory
/macinventory:inventory
```

That's it. Follow the prompts, and in minutes you'll have a complete snapshot of your Mac.

---

## ✨ What It Does

MacInventory solves a common problem: documenting your Mac's computing environment for hardware failures, migrations, or fresh starts. It automatically:

- 📱 Scans installed applications (system and user)
- 🍺 Catalogs Homebrew packages, casks, and taps
- 🛒 Lists Mac App Store apps
- 🔄 Detects version managers (pyenv, nvm, rbenv, asdf)
- 📦 Inventories global packages (npm, pip, pipx, cargo, gem)
- ✏️ Captures editor extensions (VS Code, Cursor, Zed, Sublime)
- 🔐 Backs up configuration files with secret filtering
- 📋 Generates restoration bundles (Brewfile, package lists)
- 💾 Creates a comprehensive `state.yaml` snapshot
- 📖 Optionally generates a professional Restoration Guide

---

## 📥 Installation

### From Claude Code

```bash
# Add the marketplace (one-time)
/plugin marketplace add ksk-incom/MacInventory

# Install the plugin
/plugin install macinventory@MacInventory
```

### For Development

```bash
# Clone the repository
git clone https://github.com/ksk-incom/MacInventory.git

# Test locally without installing
claude --plugin-dir ./macinventory
```

---

## 🚀 Usage

Run the inventory command in Claude Code:

```
/macinventory:inventory
```

You'll be guided through options:

1. **Security Settings** - Whether to include files that may contain secrets
2. **Guide Generation** - Whether to create a Restoration-Guide.md
3. **Cloud Backup** - Optionally copy output to OneDrive, iCloud, Dropbox, or Google Drive

---

## 📂 Output Structure

After running, you'll have a timestamped directory with everything you need:

```
~/mac-inventory/2025-12-24-183045/
├── 📄 state.yaml              # Complete system state snapshot
├── 📖 Restoration-Guide.md    # Step-by-step restoration guide
├── 📦 bundles/                # Ready-to-use restoration files
│   ├── Brewfile               # → brew bundle --file=Brewfile
│   ├── MASApps.txt            # Mac App Store apps
│   ├── *Packages.txt          # npm, pip, pipx, cargo, gem, go
│   └── *Extensions.txt        # VS Code, Cursor, Zed extensions
└── ⚙️ configs/                # Backed-up configuration files
    ├── shell/                 # .zshrc, .bashrc, aliases
    ├── git/                   # .gitconfig, .gitignore_global
    ├── ssh/                   # SSH config (not keys!)
    └── apps/                  # Per-app configs organized by tier
```

---

## 🎯 Features

### Three-Tier Discovery

MacInventory uses a smart tiered approach to discover application configurations:

| Tier  | Source            | Trust Level | What It Does                           |
|:-----:|-------------------|-------------|----------------------------------------|
| **1** | Curated Database  | ✅ High     | Uses exact paths from `app-hints.yaml` |
| **2** | MacOS Conventions | ⚠️ Medium   | Scans standard config locations        |
| **3** | AI Research       | ⚠️ Medium   | Web search for unknown apps            |

<details>
<summary><strong>How the discovery flow works</strong> (<span style="color: #3776AB;">click to expand</span>)</summary>

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        APPLICATION DISCOVERED                               │
│                              (e.g., "iTerm")                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  TIER 1: Hints Database                                          ✓ TRUSTED  │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Check app-hints.yaml for curated config paths                              │
│                                                                             │
│  Found?  ──YES──►  Use exact paths from database                            │
│    │               • No filtering applied (trusted source)                  │
│    │               • Backed up to: configs/apps/[app]/Tier 1 - App Hints/   │
│    │                                                                        │
│    │                                                                        │
└────┼────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  TIER 2: macOS Conventions                                      ◐ FILTERED  │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Scan standard macOS config locations:                                      │
│    • ~/.config/[app-name]/                                                  │
│    • ~/Library/Application Support/[app-name]/                              │
│    • ~/Library/Preferences/[bundle-id].plist                                │
│                                                                             │
│  Found?  ──YES──►  Filter through config-patterns.yaml                      │
│    │               • Only safe extensions (.json, .yaml, .plist, etc.)      │
│    │               • Exclude caches, logs, databases                        │
│    │               • Backed up to: configs/apps/[app]/Tier 2 - Conventions/ │
│    NO                                                                       │
│    │                                                                        │
└────┼────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  TIER 3: LLM Research                                           ◐ FILTERED  │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Agent uses web search to discover config paths                             │
│    • Searches documentation, forums, GitHub                                 │
│    • Validates discovered paths exist on system                             │
│    • Learns new apps for future runs                                        │
│                                                                             │
│  Found?  ──YES──►  Filter through config-patterns.yaml                      │
│    │               • Same safety filtering as Tier 2                        │
│    │               • Backed up to: configs/apps/[app]/Tier 3 - LLM Research/│
│    NO                                                                       │
│    │                                                                        │
└────┼────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  UNDISCOVERED                                                               │
│  ─────────────────────────────────────────────────────────────────────────  │
│  App added to undiscovered_report.yaml for manual review                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

</details>

<details>
<summary><strong>Example: How iTerm2 is discovered</strong> (<span style="color: #3776AB;">click to expand</span>)</summary>

#### Example: How "iTerm2" is Discovered

```yaml
# Tier 1: Found in app-hints.yaml
iterm2:
  bundle_id: com.googlecode.iterm2
  install_method: homebrew_cask
  configuration_files:
    - ~/Library/Preferences/com.googlecode.iterm2.plist
    - ~/Library/Application Support/iTerm2/DynamicProfiles/
  notes: "Terminal emulator with extensive customization"
```

Because iTerm2 is in the hints database, MacInventory:

1. Uses the exact paths specified (no guessing)
2. Backs up without filtering (trusted source)
3. Organizes files under `Tier 1 - App Hints Database/`

**For unknown apps**, MacInventory:

1. Scans standard macOS locations (Tier 2)
2. Uses AI to research config paths (Tier 3)
3. Filters results to only include safe file types

</details>

<details>
<summary><strong>Filtering details</strong> (<span style="color: #3776AB;">click to expand</span>)</summary>

Tier 2 and 3 discoveries are filtered by `config-patterns.yaml`:

| ✅ Included                | ❌ Excluded                 |
|---------------------------|----------------------------|
| `.json`, `.yaml`, `.toml` | `.db`, `.sqlite`, `.realm` |
| `.plist`, `.conf`, `.ini` | `.log`, `.cache`, `Cache/` |
| `.sh`, `.zsh`, `.bash`    | `.dmg`, `.app`, `.pkg`     |
| `.xml`, `.cfg`            | `node_modules/`, `.git/`   |

Maximum file size: **10 MB** (larger files are likely not configs)

</details>

### Security First

- Secret filtering enabled by default (API keys, tokens, passwords)
- SSH keys explicitly excluded
- Secure permissions on backed-up files (0600/0700)
- Home-relative paths only

### Restoration Bundles

Generate files ready for system restoration:

```bash
# Restore Homebrew packages
brew bundle --file=Brewfile

# Restore npm globals
xargs npm install -g < NPMGlobalPackages.txt

# Restore pip packages
pip install -r PipPackages.txt

# Restore VS Code extensions
while IFS= read -r ext; do code --install-extension "$ext"; done < VSCodeExtensions.txt
```

---

## 📋 Requirements

| Requirement  |   Status    | Notes                       |
|--------------|:-----------:|-----------------------------|
| macOS        |  Required   | Any recent version          |
| Python 3.12+ |  Required   | `python3 --version`         |
| PyYAML       |  Required   | `pip3 install pyyaml`       |
| Homebrew     | Recommended | Enables package scanning    |
| mas-cli      |  Optional   | Enhances App Store metadata |

---

## 🧩 Plugin Components

| Component                     | Description                                        |
|-------------------------------|----------------------------------------------------|
| `/macinventory:inventory`     | Main command - runs the full inventory process     |
| `app-discovery` agent         | Researches unknown app config paths via web search |
| `config-validator` agent      | Validates backed-up configs for quality            |
| `guide-generator` agent       | Creates professional restoration documentation     |
| `prerequisites-checker` agent | Validates system prerequisites before inventory    |
| `verification` agent          | Final quality check on all output                  |
| `macos-discovery` skill       | Knowledge base for researching macOS app settings  |

---

## 🛡️ Privacy

- All data stays on your machine (unless you choose cloud backup)
- No telemetry or external connections (except optional LLM research)
- Secret filtering removes sensitive content from backups
- You control what gets included via command prompts

---

## 🔧 Troubleshooting

<details>
<summary><strong>Missing Python/PyYAML</strong></summary>

```bash
pip3 install pyyaml
```

</details>

<details>
<summary><strong>Homebrew Not Found</strong></summary>

The inventory continues without Homebrew data. Install it:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

</details>

<details>
<summary><strong>mas-cli Not Found</strong></summary>

Mac App Store apps still appear, but with limited metadata. Install mas:

```bash
brew install mas
```

</details>

<details>
<summary><strong>Permission Errors</strong></summary>

Some system files may be inaccessible. The plugin gracefully skips these and continues with accessible files.

</details>

---

## 🔍 Using the macOS Discovery Skill

The `macos-discovery` skill helps you research where macOS applications store their configuration files. Use it to add apps to the hints database.

**Quick examples:**

- `"Add Obsidian to the hints database"`
- `"Where does TablePlus store its settings?"`
- `"Research config paths for Raycast"`

<details>
<summary><strong>📖 Full skill documentation</strong> (<span style="color: #3776AB;">click to expand</span>)</summary>

### When to Use This Skill

- **Adding a specific app**: You want to ensure a particular application's settings are backed up
- **Processing undiscovered apps**: After `/inventory`, you see apps in `undiscovered_report.yaml` that you want to track
- **Bulk discovery**: You want to add all undiscovered apps from a previous inventory run
- **Understanding config locations**: You're curious where an app stores its settings

### How to Invoke the Skill

The skill activates when you ask Claude about app configuration discovery. Use phrases like:

- "Add [AppName] to the hints database"
- "Where does [AppName] store its settings?"
- "Research app settings for [AppName]"
- "Find configuration paths for [AppName]"

### Examples

#### Add a Single Application

```
Add Obsidian to the hints database
```

Claude will:

1. Get the bundle ID (`osascript -e 'id of app "Obsidian"'`)
2. Check standard macOS config locations
3. Search for documentation if needed
4. Validate discovered paths exist on your system
5. Create a properly formatted YAML entry

#### Research an Unknown App

```
Where does TablePlus store its configuration on macOS?
```

Claude will research the app and show you exactly which files contain settings vs cache/data.

#### Process Undiscovered Apps from Inventory

After running `/inventory`, if you have undiscovered apps:

```
Read the undiscovered_report.yaml from my last inventory and add all those apps
to the hints database. For each app, research the config locations and create
valid hints entries.
```

### Optimized Prompt for Bulk Discovery

Use this prompt to systematically process all undiscovered apps from your latest inventory:

```
I just ran /inventory and have undiscovered apps. Please:

1. Read ~/mac-inventory/[latest-folder]/undiscovered_report.yaml
2. For each app listed:
   - Get its bundle ID using osascript
   - Determine the install method (cask, formula, mas, dmg)
   - Check these locations for config files:
     * ~/Library/Application Support/[AppName]/
     * ~/Library/Preferences/[bundle_id].plist
     * ~/.config/[appname]/
     * ~/Library/Containers/[bundle_id]/ (if sandboxed)
   - Search web for "[AppName] config location mac" if standard locations are empty
   - Validate all discovered paths actually exist
3. Create valid app-hints.yaml entries for each app
4. Compile all entries into a single YAML block I can add to my hints database
5. Run the validate-hints.py script to verify the entries

Focus only on configuration files (settings, preferences, keybindings).
Exclude caches, logs, and databases. Use relative paths (no ~/ prefix).
```

### Entry Format Quick Reference

```yaml
app-name:                              # Lowercase, hyphenated
  bundle_id: com.developer.AppName     # From: osascript -e 'id of app "AppName"'
  install_method: cask                 # cask | formula | mas | dmg | system
  configuration_files:                 # Paths relative to $HOME (no ~/ prefix)
    - Library/Application Support/AppName/settings.json
    - Library/Preferences/com.developer.AppName.plist
  xdg_configuration_files:             # Paths relative to ~/.config (optional)
    - appname/config.yaml
  exclude_files:                       # Patterns to skip
    - "*.log"
    - "Cache/"
  notes: "Optional notes about the app"
```

**Key rules**:

- Paths are RELATIVE (use `Library/...` not `~/Library/...`)
- `configuration_files` = relative to `$HOME`
- `xdg_configuration_files` = relative to `~/.config`
- Use `null` for `bundle_id` on CLI tools

### Standard macOS Config Locations

The skill knows these common patterns:

| Location                         | Used By                    | Example                 |
|----------------------------------|----------------------------|-------------------------|
| `~/Library/Application Support/` | Modern GUI apps            | Slack, VS Code, Discord |
| `~/Library/Preferences/*.plist`  | Native macOS apps          | iTerm2, Terminal        |
| `~/.config/`                     | CLI tools, cross-platform  | neovim, starship, git   |
| `~/Library/Containers/`          | Sandboxed (App Store) apps | Notes, 1Password        |
| `~/.appname/`                    | Traditional dotfiles       | Docker, Warp            |

### Validation

After creating entries, validate them:

```bash
# Set your plugin path (adjust if using a different marketplace)
PLUGIN_PATH=~/.claude/plugins/macinventory@MacInventory

# Validate entire database
python3 $PLUGIN_PATH/skills/macos-discovery/scripts/validate-hints.py \
    $PLUGIN_PATH/data/app-hints.yaml

# Validate and check paths exist
python3 $PLUGIN_PATH/skills/macos-discovery/scripts/validate-hints.py \
    $PLUGIN_PATH/data/app-hints.yaml --check-paths --verbose
```

> **For developers**: If working from the source repository, use `macinventory/` as the path instead.

</details>

---

<p align="center">
  Made with ❤️ for the Mac community
</p>

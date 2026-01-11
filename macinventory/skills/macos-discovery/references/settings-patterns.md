# Application Settings Patterns

This reference documents configuration file patterns organized by application category. Use this to quickly identify where specific types of apps store their settings.

## CLI Tools

### Shell Configuration

**Bash**:

```
~/.bashrc
~/.bash_profile
~/.bash_aliases
~/.bash_history (usually exclude)
```

**Zsh**:

```
~/.zshrc
~/.zprofile
~/.zshenv
~/.zsh_history (usually exclude)
~/.oh-my-zsh/ (if using Oh My Zsh)
```

**Fish**:

```
~/.config/fish/config.fish
~/.config/fish/functions/
~/.config/fish/conf.d/
```

### Git Tools

**Git**:

```
~/.gitconfig
~/.config/git/config
~/.config/git/ignore
~/.gitignore_global
~/.git-credentials (SENSITIVE - often exclude)
```

**GitHub CLI**:

```
~/.config/gh/config.yml
~/.config/gh/hosts.yml (SENSITIVE)
```

### Package Managers

**Homebrew**:

- No config files (uses command-line)
- Generate with: `brew bundle dump`

**npm**:

```
~/.npmrc (may contain tokens - check for secrets)
```

**pip**:

```
~/.config/pip/pip.conf
~/.pip/pip.conf (legacy)
```

**Cargo (Rust)**:

```
~/.cargo/config.toml
~/.cargo/credentials.toml (SENSITIVE)
```

### Cloud & Infrastructure Tools

**AWS CLI**:

```
~/.aws/config
~/.aws/credentials (SENSITIVE - usually exclude)
```

**Google Cloud**:

```
~/.config/gcloud/configurations/
~/.config/gcloud/credentials.db (SENSITIVE)
```

**Kubernetes**:

```
~/.kube/config (may contain tokens - check carefully)
```

**Docker**:

```
~/.docker/config.json (may contain auth - check)
```

**Terraform**:

```
~/.terraformrc
~/.terraform.d/credentials.tfrc.json (SENSITIVE)
```

---

## Code Editors & IDEs

### VS Code / Cursor / VSCodium

**Settings Location**:

```
~/Library/Application Support/Code/User/settings.json
~/Library/Application Support/Code/User/keybindings.json
~/Library/Application Support/Code/User/snippets/
~/Library/Application Support/Code/User/tasks.json
```

**Exclude**:

```
Cache/
CachedData/
CachedExtensions/
CachedExtensionVSIXs/
logs/
*.log
workspaceStorage/
globalStorage/ (large, often not needed)
```

### JetBrains IDEs (IntelliJ, PyCharm, WebStorm, etc.)

**Settings Location**:

```
~/Library/Application Support/JetBrains/<IDE><version>/
  - options/           # Settings
  - keymaps/          # Keyboard shortcuts
  - codestyles/       # Code formatting
  - templates/        # Live templates
  - colors/           # Color schemes
```

**Exclude**:

```
system/
log/
index/
LocalHistory/
```

### Sublime Text

**Settings Location**:

```
~/Library/Application Support/Sublime Text/Packages/User/
  - Preferences.sublime-settings
  - Default (OSX).sublime-keymap
  - *.sublime-snippet
```

### Vim / Neovim

**Vim**:

```
~/.vimrc
~/.vim/
```

**Neovim**:

```
~/.config/nvim/init.vim
~/.config/nvim/init.lua
~/.config/nvim/lua/
~/.local/share/nvim/ (plugins - may be large)
```

### Zed

```
~/.config/zed/settings.json
~/.config/zed/keymap.json
~/.config/zed/themes/
```

---

## Browsers

### Chrome / Chromium-based

**Config Location**:

```
~/Library/Application Support/Google/Chrome/Default/
  - Preferences (JSON - main settings)
  - Bookmarks (JSON)
  - Extensions/ (installed extensions)
```

**Exclude**:

```
Cache/
Code Cache/
GPUCache/
*.log
Sessions/
History (SQLite, large)
```

### Firefox

**Config Location**:

```
~/Library/Application Support/Firefox/Profiles/*.default-release/
  - prefs.js
  - user.js (if exists)
  - bookmarkbackups/
  - extensions/
```

**Exclude**:

```
cache2/
thumbnails/
storage/
*.sqlite (most are cache)
```

### Safari

```
~/Library/Safari/Bookmarks.plist
~/Library/Safari/History.plist (may want to exclude)
~/Library/Preferences/com.apple.Safari.plist
```

### Arc

```
~/Library/Application Support/Arc/User Data/Default/
  - Preferences
  - Bookmarks
```

---

## Communication Apps

### Slack

```
~/Library/Application Support/Slack/
  - storage/ (contains settings)
```

**Exclude**:

```
Cache/
Code Cache/
GPUCache/
logs/
```

### Discord

```
~/Library/Application Support/discord/
  - Local Storage/
```

**Exclude**:

```
Cache/
Code Cache/
GPUCache/
```

### Microsoft Teams

```
~/Library/Application Support/Microsoft/Teams/
```

**Exclude**:

```
Cache/
Logs/
media-stack/
```

---

## Productivity Apps

### Alfred

```
~/Library/Application Support/Alfred/
  - Alfred.alfredpreferences/ (main settings bundle)
  - Preferences.plist
```

### Raycast

```
~/Library/Application Support/com.raycast.macos/
```

### 1Password

```
~/Library/Group Containers/2BUA8C4S2C.com.1password/
```

**Note**: Most 1Password data is encrypted or synced. Local config limited.

### Things 3

```
~/Library/Group Containers/JLMPQHK86H.com.culturedcode.ThingsMac/
```

### Notion

```
~/Library/Application Support/Notion/
```

---

## Development Databases

### TablePlus

```
~/Library/Application Support/com.tinyapp.TablePlus/
```

### Sequel Pro / Ace

```
~/Library/Application Support/Sequel Pro/
~/Library/Application Support/Sequel Ace/
```

### DBeaver

```
~/Library/DBeaverData/workspace6/General/
```

---

## Media & Design Tools

### Figma

```
~/Library/Application Support/Figma/
```

### Sketch

```
~/Library/Application Support/com.bohemiancoding.sketch3/
```

### Adobe Creative Cloud

Adobe apps are complex - each app has its own settings:

```
~/Library/Preferences/Adobe*/
~/Library/Application Support/Adobe/
```

**Note**: Adobe licensing and sync add complexity. Focus on specific app prefs.

---

## File Formats by Pattern

### Plist Files (Property Lists)

**Format**: Binary or XML
**Extension**: `.plist`
**Location**: Typically `~/Library/Preferences/`

**Handling**:

```bash
# Convert binary to XML for backup
plutil -convert xml1 file.plist -o file.xml.plist

# Validate syntax
plutil -lint file.plist
```

### JSON Configuration

**Common files**: `settings.json`, `config.json`, `preferences.json`
**Location**: Varies by app

**Handling**:

```bash
# Validate JSON
python3 -m json.tool file.json > /dev/null
```

### YAML Configuration

**Common files**: `config.yaml`, `settings.yml`
**Location**: Typically `~/.config/`

**Handling**:

```bash
# Validate YAML
python3 -c "import yaml; yaml.safe_load(open('file.yaml'))"
```

### TOML Configuration

**Common files**: `config.toml`, `pyproject.toml`
**Location**: Project roots or `~/.config/`

### INI / Config Files

**Common files**: `.ini`, `.conf`, `.cfg`
**Format**: Sections in brackets, key=value pairs

---

## Security Considerations by App Type

### High Security Risk (Usually Exclude)

- Cloud credentials (AWS, GCP, Azure)
- API tokens stored in plaintext
- OAuth tokens
- SSH private keys
- Database connection strings

### Medium Risk (Review Before Including)

- Shell history files
- Browser session data
- App-specific auth tokens
- Git credentials

### Low Risk (Generally Safe)

- Editor settings and keybindings
- Color schemes and themes
- UI preferences
- Workspace layouts

---

## Common Exclude Patterns by Type

### Cache Patterns

```yaml
exclude_patterns:
  - "Cache/"
  - "Caches/"
  - "cache/"
  - "*.cache"
  - "CachedData/"
  - "CachedExtensions/"
  - "GPUCache/"
  - "Code Cache/"
  - "ShaderCache/"
```

### Log Patterns

```yaml
exclude_patterns:
  - "*.log"
  - "Logs/"
  - "logs/"
  - "log/"
```

### Temporary File Patterns

```yaml
exclude_patterns:
  - "*.tmp"
  - "*.temp"
  - "temp/"
  - "Temp/"
  - ".tmp/"
```

### Generated/Large Data Patterns

```yaml
exclude_patterns:
  - "*.sqlite"
  - "*.db"
  - "IndexedDB/"
  - "Local Storage/"
  - "Session Storage/"
  - "Service Worker/"
  - "File System/"
```

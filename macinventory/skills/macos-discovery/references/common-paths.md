# Common macOS Configuration Paths

This reference provides a comprehensive guide to where macOS applications store their configuration files, preferences, and settings.

## Primary Configuration Locations

### ~/Library/Application Support/

**Purpose**: Modern application data storage

**Path Pattern**: `~/Library/Application Support/AppName/` or `~/Library/Application Support/com.developer.AppName/`

**Typical Contents**:

- Configuration files (JSON, YAML, XML, TOML)
- User databases (SQLite for settings)
- Extensions and plugins
- Themes and customizations
- License files

**Examples**:

```
~/Library/Application Support/Slack/
~/Library/Application Support/Code/ (VS Code)
~/Library/Application Support/Firefox/Profiles/
~/Library/Application Support/Google/Chrome/Default/
```

**Discovery Command**:

```bash
ls ~/Library/Application\ Support/ | grep -i "appname"
```

**Notes**:

- Most common location for modern apps
- May contain both config and cache data (filter carefully)
- Directory name may be app name, bundle ID, or company name

---

### ~/Library/Preferences/

**Purpose**: Traditional macOS preferences (property list files)

**Path Pattern**: `~/Library/Preferences/com.developer.AppName.plist`

**Typical Contents**:

- Single `.plist` file per app
- User preferences and settings
- Window positions and states
- Simple configuration values

**Examples**:

```
~/Library/Preferences/com.apple.Terminal.plist
~/Library/Preferences/com.googlecode.iterm2.plist
~/Library/Preferences/com.microsoft.VSCode.plist
```

**Discovery Commands**:

```bash
# Find by app name
ls ~/Library/Preferences/ | grep -i "appname"

# Read plist contents
defaults read com.developer.AppName

# Get app's bundle identifier
osascript -e 'id of app "AppName"'
```

**Notes**:

- Can be binary or XML format (use `plutil -convert xml1` for backup)
- Changes may require app restart to take effect
- Some apps use CFPreferences API which may store in different locations

---

### ~/.config/

**Purpose**: XDG Base Directory standard config location

**Path Pattern**: `~/.config/appname/` or `~/.config/appname.conf`

**Typical Contents**:

- Cross-platform tool configurations
- Usually YAML, TOML, JSON, or INI format
- May have multiple config files for different aspects

**Examples**:

```
~/.config/git/config
~/.config/nvim/init.vim
~/.config/fish/config.fish
~/.config/karabiner/karabiner.json
~/.config/starship.toml
```

**Discovery Command**:

```bash
ls ~/.config/ | grep -i "appname"
```

**Notes**:

- Standard location for CLI tools and cross-platform apps
- Often respects XDG_CONFIG_HOME environment variable
- Increasingly popular with modern CLI tools

---

### ~/Library/Containers/

**Purpose**: Sandboxed app storage (Mac App Store apps)

**Path Pattern**: `~/Library/Containers/com.developer.AppName/Data/`

**Typical Contents**:

- Complete app sandbox including:
  - `Library/Application Support/`
  - `Library/Preferences/`
  - `Library/Caches/`
  - `Documents/`

**Examples**:

```
~/Library/Containers/com.apple.Notes/
~/Library/Containers/com.agilebits.onepassword7/
~/Library/Containers/com.tapbots.Tweetbot3/
```

**Discovery Command**:

```bash
ls ~/Library/Containers/ | grep -i "appname"
```

**Notes**:

- Contains entire sandboxed file system for the app
- Structure mirrors standard Library locations
- Be selective - don't backup entire container (usually huge)
- Look in `Data/Library/Application Support/` and `Data/Library/Preferences/`

---

### ~/Library/Group Containers/

**Purpose**: Shared storage for app suites/extensions

**Path Pattern**: `~/Library/Group Containers/group.com.developer.AppName/`

**Typical Contents**:

- Shared settings between main app and extensions
- iCloud sync data
- Cross-app shared preferences

**Examples**:

```
~/Library/Group Containers/group.com.apple.notes/
~/Library/Group Containers/group.com.culturedcode.ThingsMac/
~/Library/Group Containers/UBF8T346G9.Office/ (Microsoft Office)
```

**Discovery Command**:

```bash
ls ~/Library/Group\ Containers/ | grep -i "appname"
```

**Notes**:

- Used by apps with share extensions, widgets, or iCloud sync
- May contain sync metadata that's not useful for backup
- Often paired with regular Containers entry

---

## Traditional Dotfile Locations

### Home Directory Dotfiles

**Purpose**: Traditional Unix-style configuration

**Path Patterns**:

- `~/.appname/` (directory)
- `~/.appname` (file)
- `~/.appnamerc` (rc file)

**Examples**:

```
~/.ssh/config
~/.gitconfig
~/.zshrc
~/.npmrc
~/.aws/credentials
~/.docker/config.json
```

**Discovery Command**:

```bash
ls -la ~/ | grep -E "^\.|/\."
```

**Notes**:

- Oldest configuration convention
- Many CLI tools still use this pattern
- Often contains sensitive data (be careful with backups)

---

## Secondary Locations

### ~/Library/Saved Application State/

**Purpose**: Window positions and restoration state

**Path Pattern**: `~/Library/Saved Application State/com.developer.AppName.savedState/`

**Typical Contents**:

- Window positions and sizes
- Scroll positions
- Open documents state

**Notes**:

- Usually NOT useful for backup (system regenerates)
- May contain useful state for specific workflows
- Generally exclude from config backups

---

### ~/Library/Caches/

**Purpose**: Cached data (not configuration)

**Path Pattern**: `~/Library/Caches/com.developer.AppName/`

**Notes**:

- **Almost never backup** - caches are regenerated
- Exclude patterns should always include cache directories
- Can grow very large (gigabytes)

---

### ~/Library/Logs/

**Purpose**: Application logs

**Path Pattern**: `~/Library/Logs/AppName/`

**Notes**:

- **Never backup** as configuration
- Useful for debugging, not restoration
- Exclude `*.log` files in backup patterns

---

## Application-Specific Patterns

### Browsers

```
# Chrome
~/Library/Application Support/Google/Chrome/Default/Preferences
~/Library/Application Support/Google/Chrome/Default/Bookmarks
~/Library/Application Support/Google/Chrome/Local State

# Firefox
~/Library/Application Support/Firefox/Profiles/*.default-release/prefs.js
~/Library/Application Support/Firefox/profiles.ini

# Safari
~/Library/Safari/Bookmarks.plist
~/Library/Preferences/com.apple.Safari.plist
```

### Code Editors

```
# VS Code
~/Library/Application Support/Code/User/settings.json
~/Library/Application Support/Code/User/keybindings.json
~/Library/Application Support/Code/User/snippets/

# Cursor
~/Library/Application Support/Cursor/User/settings.json

# Sublime Text
~/Library/Application Support/Sublime Text/Packages/User/

# Zed
~/.config/zed/settings.json
```

### Terminal Emulators

```
# iTerm2
~/Library/Preferences/com.googlecode.iterm2.plist
~/Library/Application Support/iTerm2/DynamicProfiles/

# Warp
~/.warp/

# Alacritty
~/.config/alacritty/alacritty.yml
```

### Development Tools

```
# Git
~/.gitconfig
~/.config/git/config
~/.git-credentials (SENSITIVE)

# Docker
~/.docker/config.json

# Homebrew
~/.Brewfile (if created)
```

### Version Managers

```
# pyenv
~/.pyenv/version
~/.python-version

# nvm
~/.nvmrc
~/.nvm/alias/default

# rbenv
~/.rbenv/version
~/.ruby-version

# asdf
~/.tool-versions
~/.asdfrc
```

---

## Path Discovery Techniques

### Finding App's Bundle ID

```bash
# Using osascript
osascript -e 'id of app "AppName"'

# Using mdls
mdls -name kMDItemCFBundleIdentifier "/Applications/AppName.app"

# Using defaults
defaults read "/Applications/AppName.app/Contents/Info" CFBundleIdentifier
```

### Searching All Locations

```bash
# Comprehensive search for app configs
for dir in \
    ~/Library/Application\ Support \
    ~/Library/Preferences \
    ~/Library/Containers \
    ~/Library/Group\ Containers \
    ~/.config \
    ~; do
    find "$dir" -maxdepth 2 -iname "*appname*" 2>/dev/null
done
```

### Monitoring File System Activity

```bash
# Watch what files an app touches (requires SIP disabled or specific entitlements)
sudo fs_usage -w -f filesystem AppName 2>&1 | grep -E "(open|write)"

# Alternative: Use opensnoop (if available)
sudo opensnoop -n AppName
```

---

## Best Practices for Path Discovery

1. **Start with standard locations** - Check Application Support, Preferences, and .config first
2. **Find bundle ID early** - Makes searching much easier
3. **Check multiple locations** - Many apps use several config locations
4. **Validate paths exist** - Use Glob to verify before adding to hints
5. **Document discovery method** - Note in hints entry how path was found
6. **Test backup/restore** - Verify configs actually work when restored

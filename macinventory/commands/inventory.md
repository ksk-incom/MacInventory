---
description: Generate comprehensive Mac environment inventory and restoration guide
argument-hint: [You'll be guided through the process with questions]
allowed-tools: Bash, Write, Read, Edit, Glob, AskUserQuestion, Task, WebFetch, TodoWrite
---

# MacInventory - Environment Documentation Generator

Generate a comprehensive inventory of the Mac computing environment including applications, packages, configurations, and optionally create a professional restoration guide.

## Workflow

### Phase 0: Runtime Notice and Confirmation

**First, use AskUserQuestion to display the runtime notice and get user confirmation:**

- Header: "Welcome"
- Question: "This inventory command takes 10-15 minutes depending on your setup and includes: scanning apps/packages/configs, agent-based research for unknown apps, validation, and optional guide generation. Ready to start?"
- Options:
  - "Yes, start inventory" - Begin the full inventory process
  - "Cancel" - Abort the inventory

**If the user selects "Cancel":** Stop immediately and confirm the inventory was cancelled.

**If the user selects "Yes, start inventory":** Create the todo list and proceed to Phase 1.

## REQUIRED: Create Todo List

**IMMEDIATELY after the user confirms, you MUST use the TodoWrite tool to create a todo list with all phases.** This is mandatory - do not skip this step.

Create these todos (mark the first one as `in_progress`, the rest as `pending`):

| # | Content                                           | Active Form                 |
|---|---------------------------------------------------|-----------------------------|
| 1 | Discover plugin location and check for updates    | Discovering plugin location |
| 2 | Check prerequisites                               | Checking prerequisites      |
| 3 | Gather user preferences                           | Gathering user preferences  |
| 4 | Create output directory and configuration         | Creating output directory   |
| 5 | Execute inventory scan                            | Running inventory scan      |
| 6 | Post-process: validate configs and generate guide | Post-processing inventory   |
| 7 | Sync to cloud storage (if selected)               | Syncing to cloud storage    |
| 8 | Report final results                              | Reporting results           |

**Update the todo list as you complete each phase:**

- Mark current phase as `in_progress` when starting it
- Mark phase as `completed` when done
- If a phase is skipped (e.g., cloud sync not selected), mark it `completed` with a note

### Phase 1: Discover Plugin Location & Check Updates

Before running any Python scripts, discover the plugin's installation path and check for updates.

#### Step 1a: Get Plugin Path and Installed Version

**Method 1: Check installed_plugins.json (for installed plugins)**

Run this bash command to get the install path and version:

```bash
python3 -c "
import json, os
try:
    with open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')) as f:
        plugins = json.load(f)['plugins']
    for key, value in plugins.items():
        if 'macinventory' in key.lower():
            data = value[0]
            print(f\"{data['installPath']}|{data.get('version', 'unknown')}\")
            break
except: pass
"
```

Output format: `/path/to/plugin|1.1.10`

Parse the output to extract:

- **PLUGIN_ROOT**: The path before the `|`
- **INSTALLED_VERSION**: The version after the `|`

If this returns a valid path (non-empty), proceed to Step 1b.

**Method 2: Glob fallback (for development mode)**

If Method 1 returns empty or the path doesn't exist, use Glob to search:

```
Pattern: **/macinventory/python/main.py
```

Then extract PLUGIN_ROOT by removing `/python/main.py` from the found path.

**Note:** In development mode (Method 2), skip the update check and proceed directly to Phase 2.

**Store PLUGIN_ROOT** for use in subsequent phases. If neither method finds the plugin, report error: "MacInventory plugin files not found. Please reinstall the plugin."

#### Step 1b: Check for Updates (installed plugins only)

Use WebFetch to get the latest version from GitHub:

- URL: `https://raw.githubusercontent.com/ksk-incom/MacInventory/main/VERSION`
- Prompt: "Return only the version number from this file, nothing else"

The response will be a version string like `1.1.12`.

**Compare versions:**

If WebFetch fails (network error, timeout, etc.):

- Log: "Could not check for updates (network unavailable)"
- Continue to Phase 2

If WebFetch succeeds:

- Parse the remote version (trim whitespace)
- Compare with INSTALLED_VERSION

**If remote version > installed version:**

Use AskUserQuestion:

- Header: "Update Available"
- Question: "MacInventory v{REMOTE_VERSION} is available (you have v{INSTALLED_VERSION}). Would you like to update?"
- Options:
  - "Update now" - Run update and stop
  - "Continue with current version" - Proceed with inventory

**If user selects "Update now":**

Run the update script:

```bash
bash [PLUGIN_ROOT]/scripts/update-plugin.sh
```

(Replace `[PLUGIN_ROOT]` with the path discovered in Step 1a)

After the script completes, inform the user:

"Update complete! Please restart Claude Code for the changes to take effect, then run /inventory again."

Then STOP the inventory process.

**If user selects "Continue with current version":**

- Proceed to Phase 2

**If versions are equal or installed is newer:**

- Proceed to Phase 2 (no prompt needed)

### Phase 2: Prerequisites Check

Before starting, validate the system environment using the prerequisites-checker agent:

Use the Task tool to spawn the prerequisites-checker agent:

- subagent_type: `macinventory:prerequisites-checker`
- prompt: `Check all prerequisites for MacInventory and report status. Plugin root: [PLUGIN_ROOT]`

(Replace `[PLUGIN_ROOT]` with the actual path discovered in Phase 1)

The agent will return a clean summary of available and missing tools.

**If all tools are available:** Proceed to Phase 3.

**If any tools are missing (required OR optional):**

Use AskUserQuestion to offer installation:

- Header: "Missing Tools"
- Question: "Some tools are missing. Would you like me to install them?"
- Options:
  - "Yes, install missing tools" (Recommended) - Claude will attempt to install all missing tools
  - "No, continue without them" - Proceed with limitations (only if required tools are present)
  - "Cancel inventory" - Stop the inventory process

**If user selects "Yes, install missing tools":**

Install each missing tool using the appropriate command:

| Tool     | Installation Command                                                                              |
|----------|---------------------------------------------------------------------------------------------------|
| PyYAML   | `pip3 install pyyaml`                                                                             |
| Homebrew | `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"` |
| mas      | `brew install mas` (requires Homebrew)                                                            |

After installation attempts, re-run the prerequisites-checker agent to verify:

- If all required tools are now available, proceed to Phase 3
- If required tools are still missing, stop and report the failure with manual installation instructions

**If user selects "No, continue without them":**

- If required tools (Python, PyYAML) are missing: Stop and report that these are required
- If only optional tools are missing: Note the limitations and proceed to Phase 3
  - Without Homebrew: Package detection will be limited
  - Without mas: Mac App Store apps won't be catalogued

**If user selects "Cancel inventory":** Stop immediately and confirm the inventory was cancelled.

### Phase 3: Gather User Preferences

#### Step 3a: Detect Cloud Storage (before asking questions)

**Run the cloud storage detection FIRST**, so all questions can be asked in a single prompt:

```bash
python3 [PLUGIN_ROOT]/python/utils/storage_detection.py --json
```

(Replace `[PLUGIN_ROOT]` with the path discovered in Phase 1)

The output is a JSON object mapping service names to their FULL PATHS, e.g.:

```json
{"OneDrive": "/Users/username/Library/CloudStorage/OneDrive-AccountName"}
```

Store the detected services for use in the questions below.

#### Step 3b: Ask All Questions in a Single Prompt

Use **ONE AskUserQuestion call** with all questions. The AskUserQuestion tool supports up to 4 questions in a single call.

**Question 1 - Security Settings:**

- Header: "Security"
- Question: "Should the backup include files that may contain secrets (API keys, tokens)?"
- Options:
  - "No, filter secrets" (Recommended) - Safer, redacts sensitive content
  - "Yes, include everything" - Full backup including sensitive files

**Question 2 - Guide Generation:**

- Header: "Restoration Guide"
- Question: "Generate an easy to follow Restoration-Guide.md after inventory?"
- Options:
  - "Yes, generate guide" (Recommended) - Creates step-by-step restoration documentation
  - "No, just inventory" - Only collect inventory data

**Question 3 - Cloud Backup Destination (only if cloud storage was detected):**

- Header: "Cloud Backup"
- Question: "Copy inventory output to cloud storage for safekeeping?"
- Options (dynamically generated from detected services):
  - "[Service Name] ([path])" - For each detected service
  - "Skip cloud backup" - Keep only in local output directory

**CRITICAL**: When the user selects a cloud service, save the FULL PATH from the detection output (e.g., `/Users/username/Library/CloudStorage/OneDrive-AccountName`) to config.json, NOT just the service name.

**If no cloud storage was detected:** Only ask Questions 1 and 2 (omit Question 3 entirely).

### Phase 4: Create Output Directory and Configuration

After collecting preferences, create a timestamped output directory and configuration file:

```bash
# Generate timestamp for unique directory name
TIMESTAMP=$(date +%Y-%m-%d-%H%M%S)
OUTPUT_DIR=~/mac-inventory/$TIMESTAMP

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Create config file in the output directory
cat > "$OUTPUT_DIR/config.json" << 'EOF'
{
  "output_dir": "$OUTPUT_DIR",
  "include_secrets": [true/false based on security choice],
  "cloud_destination": "[full path to cloud storage or null if skipped]",
  "generate_guide": [true/false based on guide generation choice]
}
EOF
```

**IMPORTANT**: The `cloud_destination` field must contain the FULL PATH to the cloud storage directory (e.g., `/Users/username/Library/CloudStorage/OneDrive-AccountName/`), NOT just the service name. Use `null` (without quotes) if the user skipped cloud backup. The `generate_guide` field tracks whether to generate the Restoration-Guide.md.

### Phase 5: Execute Inventory

Run the Python backend to perform the inventory:

```bash
python3 -u [PLUGIN_ROOT]/python/main.py "$OUTPUT_DIR/config.json"
```

(Replace `[PLUGIN_ROOT]` with the path discovered in Phase 1)

Monitor the output and report progress to the user:

- Applications scanned
- Homebrew packages detected
- Mac App Store apps found
- Global packages catalogued (npm, pip, etc.)
- Editor extensions captured
- Configuration files backed up

### Phase 6: Post-Processing

After the inventory completes, perform these sub-agent orchestrations:

#### 6a: Check for Unknown Apps

Read the `undiscovered_report.yaml` file (if present) to check for apps without known config paths:

```bash
cat [output_dir]/undiscovered_report.yaml 2>/dev/null || echo "No undiscovered apps report"
```

If unknown apps exist, ask the user:

- Header: "Unknown Apps"
- Question: "Found X apps without known config paths. Research them using web search?"
- Options:
  - "Yes, research configs" (Recommended) - Use LLM to find config locations
  - "Skip research" - Leave unknown apps undocumented

#### 6b: Parallel App Discovery (if user approved research)

For unknown apps, spawn `app-discovery` agents IN PARALLEL using batches of 5:

**Example with 12 unknown apps:**

1. **First batch** - Spawn 5 agents in parallel using multiple Task tool calls in a SINGLE message:

   Use the Task tool 5 times with these prompts:
   - Task #1: `subagent_type='app-discovery'`, `prompt='Research config paths for Obsidian (bundle_id: md.obsidian). Return YAML entry for app-hints.yaml.'`
   - Task #2: `subagent_type='app-discovery'`, `prompt='Research config paths for Arc (bundle_id: company.thebrowser.Browser). Return YAML entry for app-hints.yaml.'`
   - Task #3: `subagent_type='app-discovery'`, `prompt='Research config paths for Linear. Return YAML entry for app-hints.yaml.'`
   - Task #4: `subagent_type='app-discovery'`, `prompt='Research config paths for Raycast. Return YAML entry for app-hints.yaml.'`
   - Task #5: `subagent_type='app-discovery'`, `prompt='Research config paths for Warp. Return YAML entry for app-hints.yaml.'`

2. **Wait** for all 5 agents to complete and collect results

3. **Second batch** - Repeat with next 5 apps (agents 6-10)

4. **Final batch** - Process remaining 2 apps (agents 11-12)

5. **Merge results** - Collect all discovered YAML entries from all batches

**CRITICAL**: Parallel spawning requires using multiple Task tool invocations in a SINGLE message. Do not send separate messages for each agent.

#### 6c: Config Validation

After inventory and any app research, spawn the `config-validator` agent:

```
"Validate the backed up configs at [output_dir]/configs/ for quality and security. Check for leaked secrets, invalid file formats, and completeness. Plugin root: [PLUGIN_ROOT]"
```

(Replace `[PLUGIN_ROOT]` with the path discovered in Phase 1)

#### 6d: Guide Generation (if requested)

If the user requested guide generation, spawn the `guide-generator` agent:

```
"Generate a comprehensive Restoration-Guide.md for the Mac inventory at [output_dir]. Read state.yaml and the backed-up configs to create professional restoration documentation."
```

#### 6e: Final Verification

After all processing, spawn the `verification` agent:

```
"Verify the inventory output at [output_dir] including state.yaml, Brewfile, and all generated files for completeness and quality."
```

### Phase 7: Cloud Sync (if selected)

Read the `cloud_destination` from config.json to determine if cloud backup was requested:

```bash
# Read cloud destination from config.json
CLOUD_PATH=$(python3 -c "import json; c=json.load(open('[output_dir]/config.json')); print(c.get('cloud_destination') or '')")

if [ -n "$CLOUD_PATH" ]; then
    # Extract timestamp from output directory to mirror local structure
    # Local: ~/mac-inventory/YYYY-MM-DD-HHMMSS/
    # Cloud: [cloud_path]/mac-inventory/YYYY-MM-DD-HHMMSS/
    TIMESTAMP=$(basename [output_dir])
    CLOUD_DEST="$CLOUD_PATH/mac-inventory/$TIMESTAMP"
    mkdir -p "$CLOUD_DEST"

    # Copy all output files
    cp -R [output_dir]/* "$CLOUD_DEST/"

    echo "Inventory backed up to: $CLOUD_DEST"
else
    echo "Cloud backup skipped (not selected)"
fi
```

Report the cloud backup location to the user.

### Phase 8: Report Results

Provide a comprehensive summary to the user:

**Inventory Summary:**

- Total applications discovered
- Homebrew packages (formulae + casks)
- Mac App Store apps
- Global packages by manager
- Editor extensions
- Configuration files backed up
- Unknown apps researched (if applicable)

**Output Files Created:**

- `state.yaml` - Complete system state snapshot
- `bundles/Brewfile` - Homebrew restoration file
- `bundles/` - Package lists for npm, pip, etc.
- `configs/` - Backed up configuration files
- `Restoration-Guide.md` - (if requested) Step-by-step restoration guide
- `undiscovered_report.yaml` - Apps without known config paths (if any)

**Validation Results:**

- Config validation: PASS/FAIL with details
- Output verification: PASS/FAIL with details

**Cloud Backup:**

- Location: [cloud path if selected]
- Status: Synced/Not selected

**Next Steps:**

- Review the Restoration-Guide.md for accuracy
- Store the output safely (cloud backup recommended)
- Test restoration commands on a fresh system when ready

## Error Handling

**If prerequisites fail:**

1. Report missing tools clearly
2. Provide installation commands:
   - Python: Should be pre-installed on macOS
   - PyYAML: `pip3 install pyyaml`
   - Homebrew: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
   - mas: `brew install mas`

**If the Python backend fails:**

1. Check if Python 3 is available: `python3 --version`
2. Check if PyYAML is installed: `python3 -c "import yaml"`
3. Verify the config file was created correctly
4. Report the specific error and suggest fixes

**If an agent fails:**

1. Report which agent failed and why
2. The inventory data is still valid even if agents fail
3. User can manually run agents later
4. Continue with remaining agents if possible

**If parallel spawning fails:**

1. Fall back to sequential agent spawning
2. Report the degraded performance mode
3. Complete all research even if slower

## Important Notes

- The inventory process reads system information but makes no changes
- Configuration backups include home-relative paths only (no system files)
- SSH keys are explicitly excluded from backup for security
- Secret filtering is enabled by default (API keys, tokens, passwords redacted)
- Output files have secure permissions (0600 for files, 0700 for directories)
- Cloud storage detection supports OneDrive, iCloud, Dropbox, and Google Drive
- Parallel agent spawning requires using multiple Task tool calls in a single message

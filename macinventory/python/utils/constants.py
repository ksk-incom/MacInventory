"""Centralized constants for MacInventory.

Provides standardized timeout values and other constants used throughout
the codebase. Centralizing these values makes them easier to tune and
ensures consistency.

From REVIEW-FINDINGS.md Issue #7:
    "Hardcoded Timeouts - Add configurable timeout constants and
    ensure ALL subprocess calls have timeouts."
"""

# =============================================================================
# SUBPROCESS TIMEOUTS (in seconds)
# =============================================================================

# Quick local system queries that should complete almost instantly
# Used for: ls, chmod, chflags, plutil, sysctl, sw_vers
TIMEOUT_SYSTEM_QUICK = 5

# Prerequisite and version checks
# Used for: python3 --version, brew --version, mas version
TIMEOUT_PREREQUISITE = 10

# Package manager queries and editor commands
# Used for: git config, rbenv versions, editor --list-extensions
TIMEOUT_PACKAGE_QUERY = 30

# Longer operations that may involve network or large data
# Used for: brew list, npm list, pip list, cargo install --list
TIMEOUT_PACKAGE_LIST = 60

# =============================================================================
# FILE SIZE LIMITS
# =============================================================================

# Maximum file size for config backup (10MB)
MAX_CONFIG_FILE_SIZE = 10 * 1024 * 1024

# Warning threshold for large files (3MB)
WARN_FILE_SIZE = 3 * 1024 * 1024

# =============================================================================
# PERMISSION MODES
# =============================================================================

# Default file permissions for backed-up configs (owner read/write only)
FILE_MODE = 0o600

# Default directory permissions (owner read/write/execute only)
DIR_MODE = 0o700

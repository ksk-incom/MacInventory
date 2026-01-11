"""Security filtering for configuration backups.

Provides secret filtering and exclusion rules using security-patterns.yaml.
Filters sensitive data (API keys, tokens, passwords) while preserving file structure.

Key Design Principle (from Vision document):
    "Filtering should preserve structure (don't break configs)"

    The patterns replace only the secret VALUE, not the entire line:
    - Shell files remain valid (export API_KEY=<REDACTED>)
    - JSON files remain parseable ("token": "<REDACTED>")
    - YAML files maintain structure (api_key: <REDACTED>)
"""

import fnmatch
import re
from pathlib import Path
from typing import Any, Optional

# Default maximum file size for config files (10MB)
DEFAULT_MAX_FILE_SIZE_MB = 10


class SecurityError(Exception):
    """Raised when a security violation is detected."""
    pass


def get_default_patterns_path() -> Path:
    """Get the default path to security-patterns.yaml.

    Returns:
        Path to the default security-patterns.yaml file
    """
    # Navigate from backup/ up to python/, then to data/
    module_dir = Path(__file__).parent
    return module_dir.parent.parent / 'data' / 'security-patterns.yaml'


def load_security_patterns(patterns_path: Optional[Path] = None) -> dict[str, Any]:
    """Load the security patterns from YAML file.

    Args:
        patterns_path: Path to security-patterns.yaml (uses default if not specified)

    Returns:
        Dictionary containing filter_patterns, exclude_files, exclude_directories, etc.

    Raises:
        FileNotFoundError: If patterns file doesn't exist
        yaml.YAMLError: If YAML is malformed
    """
    import yaml

    path = patterns_path or get_default_patterns_path()

    with open(path) as f:
        patterns = yaml.safe_load(f)

    return patterns or {}


class SecretFilter:
    """Filters secrets from configuration file content.

    Uses regex patterns to identify and redact sensitive values while
    preserving the overall structure of configuration files.

    Example:
        >>> filter = SecretFilter()
        >>> content = "API_KEY=sk-ant-1234567890abcdef"
        >>> filtered, changes = filter.filter_content(content)
        >>> print(filtered)
        API_KEY=<REDACTED_ANTHROPIC_KEY>
        >>> print(changes)
        [{'pattern': 'anthropic_key', 'original': 'sk-ant-...', 'line': 1}]
    """

    def __init__(self, patterns_path: Optional[Path] = None):
        """Initialize the secret filter.

        Args:
            patterns_path: Path to security-patterns.yaml
        """
        self.patterns_path = patterns_path
        self._patterns: Optional[dict[str, Any]] = None
        self._compiled_patterns: Optional[list[tuple[str, re.Pattern, str]]] = None

    @property
    def patterns(self) -> dict[str, Any]:
        """Lazy-load security patterns."""
        if self._patterns is None:
            self._patterns = load_security_patterns(self.patterns_path)
        return self._patterns

    @property
    def compiled_patterns(self) -> list[tuple[str, re.Pattern, str]]:
        """Get compiled regex patterns.

        Returns:
            List of (name, compiled_pattern, replacement) tuples
        """
        if self._compiled_patterns is None:
            self._compiled_patterns = []
            for pattern_def in self.patterns.get('filter_patterns', []):
                try:
                    compiled = re.compile(pattern_def['pattern'])
                    self._compiled_patterns.append((
                        pattern_def['name'],
                        compiled,
                        pattern_def['replacement']
                    ))
                except re.error as e:
                    # Log but don't fail on invalid regex
                    import sys
                    print(f"Warning: Invalid regex in {pattern_def['name']}: {e}",
                          file=sys.stderr)
        return self._compiled_patterns

    def filter_content(
        self,
        content: str,
        filename: Optional[str] = None
    ) -> tuple[str, list[dict[str, Any]]]:
        """Filter secrets from content.

        Applies all filter patterns to redact sensitive values.

        Args:
            content: The file content to filter
            filename: Optional filename for context in change tracking

        Returns:
            Tuple of (filtered_content, list of changes made)
            Each change dict has: pattern, original (truncated), line_number
        """
        changes: list[dict[str, Any]] = []
        filtered = content

        for name, pattern, replacement in self.compiled_patterns:
            # Track positions of matches for change logging
            for match in pattern.finditer(filtered):
                # Calculate line number
                line_num = filtered[:match.start()].count('\n') + 1
                # Truncate original for security (don't log full secrets)
                original = match.group()
                truncated = self._truncate_secret(original)
                changes.append({
                    'pattern': name,
                    'original': truncated,
                    'line': line_num,
                    'filename': filename,
                })

            # Apply the replacement
            filtered = pattern.sub(replacement, filtered)

        return filtered, changes

    def filter_file(
        self,
        file_path: Path,
        output_path: Optional[Path] = None
    ) -> tuple[bool, list[dict[str, Any]]]:
        """Filter secrets from a file.

        Args:
            file_path: Path to the file to filter
            output_path: Optional output path (if None, returns filtered content only)

        Returns:
            Tuple of (success, list of changes made)
        """
        try:
            content = file_path.read_text(encoding='utf-8', errors='replace')
            filtered, changes = self.filter_content(content, str(file_path))

            if output_path:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(filtered, encoding='utf-8')

            return True, changes
        except Exception as e:
            return False, [{'error': str(e), 'filename': str(file_path)}]

    def _truncate_secret(self, value: str, max_len: int = 20) -> str:
        """Truncate a secret value for safe logging.

        Args:
            value: The secret value to truncate
            max_len: Maximum length to show

        Returns:
            Truncated value with ellipsis
        """
        if len(value) <= max_len:
            return value[:4] + '...' if len(value) > 8 else '...'
        return value[:8] + '...' + value[-4:]


class ExclusionChecker:
    """Checks files and directories against exclusion rules.

    Uses patterns from security-patterns.yaml to determine if a file
    or directory should be excluded from backup.

    Example:
        >>> checker = ExclusionChecker()
        >>> checker.should_exclude_file(Path("~/.ssh/id_rsa"))
        (True, "Matches exclude_files: id_rsa")
        >>> checker.should_exclude_directory(Path("~/.cache"))
        (True, "Matches exclude_directories: .cache/")
    """

    def __init__(self, patterns_path: Optional[Path] = None):
        """Initialize the exclusion checker.

        Args:
            patterns_path: Path to security-patterns.yaml
        """
        self.patterns_path = patterns_path
        self._patterns: Optional[dict[str, Any]] = None

    @property
    def patterns(self) -> dict[str, Any]:
        """Lazy-load security patterns."""
        if self._patterns is None:
            self._patterns = load_security_patterns(self.patterns_path)
        return self._patterns

    @property
    def exclude_files(self) -> list[str]:
        """Get file exclusion patterns."""
        return self.patterns.get('exclude_files', [])

    @property
    def exclude_directories(self) -> list[str]:
        """Get directory exclusion patterns."""
        return self.patterns.get('exclude_directories', [])

    @property
    def exclude_apps(self) -> list[str]:
        """Get app exclusion list."""
        return self.patterns.get('exclude_apps', [])

    @property
    def exclude_by_pattern(self) -> list[str]:
        """Get glob patterns for path-based exclusion."""
        return self.patterns.get('exclude_by_pattern', [])

    @property
    def exclude_by_extension(self) -> list[str]:
        """Get file extension exclusion patterns."""
        return self.patterns.get('exclude_by_extension', [])

    @property
    def max_file_size_mb(self) -> float:
        """Get maximum file size in MB."""
        size_config = self.patterns.get('exclude_by_size', {})
        return size_config.get('max_file_size_mb', DEFAULT_MAX_FILE_SIZE_MB)

    def should_exclude_file(self, file_path: Path) -> tuple[bool, Optional[str]]:
        """Check if a file should be excluded from backup.

        Checks against:
        - exclude_files patterns
        - exclude_by_extension patterns
        - exclude_by_pattern glob patterns
        - file size limits

        Args:
            file_path: Path to the file to check

        Returns:
            Tuple of (should_exclude, reason if excluded)
        """
        filename = file_path.name
        path_str = str(file_path)

        # Check exclude_files patterns
        for pattern in self.exclude_files:
            if fnmatch.fnmatch(filename, pattern):
                return True, f"Matches exclude_files: {pattern}"
            # Also check full path for patterns like ".aws/credentials"
            if '/' in pattern and fnmatch.fnmatch(path_str, f"*{pattern}*"):
                return True, f"Matches exclude_files: {pattern}"

        # Check exclude_by_extension
        for ext_pattern in self.exclude_by_extension:
            if fnmatch.fnmatch(filename, ext_pattern):
                return True, f"Matches exclude_by_extension: {ext_pattern}"

        # Check exclude_by_pattern (glob patterns)
        for glob_pattern in self.exclude_by_pattern:
            if fnmatch.fnmatch(path_str, glob_pattern):
                return True, f"Matches exclude_by_pattern: {glob_pattern}"

        # Check file size
        if file_path.exists() and file_path.is_file():
            try:
                size_mb = file_path.stat().st_size / (1024 * 1024)
                if size_mb > self.max_file_size_mb:
                    return True, f"File too large: {size_mb:.1f}MB > {self.max_file_size_mb}MB"
            except OSError:
                pass  # Can't check size, don't exclude based on it

        return False, None

    def should_exclude_directory(self, dir_path: Path) -> tuple[bool, Optional[str]]:
        """Check if a directory should be excluded from backup.

        Checks against:
        - exclude_directories patterns
        - exclude_by_pattern glob patterns

        Args:
            dir_path: Path to the directory to check

        Returns:
            Tuple of (should_exclude, reason if excluded)
        """
        dirname = dir_path.name
        path_str = str(dir_path)

        # Check exclude_directories patterns
        for pattern in self.exclude_directories:
            # Normalize pattern (remove trailing slash for comparison)
            clean_pattern = pattern.rstrip('/')
            if fnmatch.fnmatch(dirname, clean_pattern):
                return True, f"Matches exclude_directories: {pattern}"
            # Check with wildcards
            if fnmatch.fnmatch(dirname, clean_pattern.replace('*', '')):
                if '*' in clean_pattern:
                    return True, f"Matches exclude_directories: {pattern}"

        # Check exclude_by_pattern
        for glob_pattern in self.exclude_by_pattern:
            if fnmatch.fnmatch(path_str, glob_pattern):
                return True, f"Matches exclude_by_pattern: {glob_pattern}"
            # Also check with trailing slash
            if fnmatch.fnmatch(path_str + '/', glob_pattern):
                return True, f"Matches exclude_by_pattern: {glob_pattern}"

        return False, None

    def should_exclude_app(self, app_name: str) -> tuple[bool, Optional[str]]:
        """Check if an application should be excluded.

        Args:
            app_name: Name of the application

        Returns:
            Tuple of (should_exclude, reason if excluded)
        """
        for excluded_app in self.exclude_apps:
            if app_name.lower() == excluded_app.lower():
                return True, f"Application in exclude_apps: {excluded_app}"
        return False, None

    def is_path_in_excluded_directory(self, file_path: Path) -> tuple[bool, Optional[str]]:
        """Check if a file is within an excluded directory.

        Walks up the path hierarchy to check if any parent directory
        should be excluded.

        Args:
            file_path: Path to check

        Returns:
            Tuple of (is_excluded, reason if excluded)
        """
        # Check each parent directory
        current = file_path if file_path.is_dir() else file_path.parent

        while current != current.parent:  # Stop at root
            excluded, reason = self.should_exclude_directory(current)
            if excluded:
                return True, f"Parent directory excluded: {reason}"
            current = current.parent

        return False, None


def is_pure_config(
    path: Path,
    max_size_mb: float = DEFAULT_MAX_FILE_SIZE_MB
) -> tuple[bool, str]:
    """Check if a path represents pure configuration.

    Validates that a file is a legitimate configuration file:
    - Not a cache/log/runtime file
    - Not too large
    - Not a binary/compiled file

    Args:
        path: Path to check
        max_size_mb: Maximum size in MB for config files

    Returns:
        Tuple of (is_valid, reason)
    """
    path_str = str(path).lower()

    # Check cache patterns (case-insensitive)
    cache_patterns = [
        '/cache/', '/caches/', '/.cache/',
        '/logs/', '/log/',
        '/crashpad/', '/crashreporter/',
        '/temp/', '/tmp/',
    ]
    for pattern in cache_patterns:
        if pattern in path_str:
            return False, f"Matches excluded pattern: {pattern}"

    # Check file size
    if path.is_file():
        try:
            size_mb = path.stat().st_size / (1024 * 1024)
            if size_mb > max_size_mb:
                return False, f"File too large: {size_mb:.1f}MB > {max_size_mb}MB"
        except OSError as e:
            return False, f"Cannot check size: {e}"

    # Check extension
    excluded_extensions = {
        '.sqlite', '.sqlite3', '.db',
        '.dylib', '.so', '.dll', '.exe',
        '.sqlite-wal', '.sqlite-shm',
    }
    if path.suffix.lower() in excluded_extensions:
        return False, f"Excluded extension: {path.suffix}"

    return True, "OK"


class SecurityManager:
    """Combined security manager for filtering and exclusion.

    Provides a unified interface for all security operations during backup.

    Example:
        >>> manager = SecurityManager()
        >>>
        >>> # Check if file should be backed up
        >>> if manager.can_backup(Path("~/.gitconfig")):
        ...     content = file_path.read_text()
        ...     filtered = manager.filter_content(content)
        ...     # Write filtered content to backup
    """

    def __init__(self, patterns_path: Optional[Path] = None):
        """Initialize the security manager.

        Args:
            patterns_path: Path to security-patterns.yaml
        """
        self.filter = SecretFilter(patterns_path)
        self.exclusions = ExclusionChecker(patterns_path)

    def can_backup(self, path: Path) -> tuple[bool, Optional[str]]:
        """Check if a path can be backed up.

        Combines all exclusion checks and pure config validation.

        Args:
            path: Path to check

        Returns:
            Tuple of (can_backup, reason if not)
        """
        # Check if it's a pure config
        is_config, reason = is_pure_config(path, self.exclusions.max_file_size_mb)
        if not is_config:
            return False, reason

        # Check file exclusions
        if path.is_file():
            excluded, reason = self.exclusions.should_exclude_file(path)
            if excluded:
                return False, reason

        # Check directory exclusions
        if path.is_dir():
            excluded, reason = self.exclusions.should_exclude_directory(path)
            if excluded:
                return False, reason

        # Check if in excluded parent directory
        excluded, reason = self.exclusions.is_path_in_excluded_directory(path)
        if excluded:
            return False, reason

        return True, None

    def filter_content(
        self,
        content: str,
        filename: Optional[str] = None
    ) -> tuple[str, list[dict[str, Any]]]:
        """Filter secrets from content.

        Args:
            content: Content to filter
            filename: Optional filename for context

        Returns:
            Tuple of (filtered_content, changes)
        """
        return self.filter.filter_content(content, filename)

    def process_file(
        self,
        source: Path,
        dest: Path,
        include_secrets: bool = False
    ) -> dict[str, Any]:
        """Process a file for backup with optional secret filtering.

        Args:
            source: Source file path
            dest: Destination file path
            include_secrets: If True, skip secret filtering

        Returns:
            Dict with status, changes, and any errors
        """
        result: dict[str, Any] = {
            'source': str(source),
            'dest': str(dest),
            'status': 'success',
            'filtered': not include_secrets,
            'changes': [],
            'errors': [],
        }

        # Check if file can be backed up
        can_backup, reason = self.can_backup(source)
        if not can_backup:
            result['status'] = 'skipped'
            result['reason'] = reason
            return result

        try:
            # Read content
            content = source.read_text(encoding='utf-8', errors='replace')

            # Filter if needed
            if include_secrets:
                filtered_content = content
            else:
                filtered_content, changes = self.filter.filter_content(
                    content, str(source)
                )
                result['changes'] = changes

            # Write to destination
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(filtered_content, encoding='utf-8')

        except Exception as e:
            result['status'] = 'error'
            result['errors'].append(str(e))

        return result


if __name__ == "__main__":
    import json

    # Demo the security module
    manager = SecurityManager()

    print("Security Patterns Loaded:")
    print(f"  Filter patterns: {len(manager.filter.compiled_patterns)}")
    print(f"  Exclude files: {len(manager.exclusions.exclude_files)}")
    print(f"  Exclude directories: {len(manager.exclusions.exclude_directories)}")
    print(f"  Exclude apps: {len(manager.exclusions.exclude_apps)}")
    print(f"  Max file size: {manager.exclusions.max_file_size_mb}MB")

    # Test filtering
    test_content = """
# Example config
API_KEY=sk-ant-1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef
DATABASE_URL=postgresql://user:secretpassword@localhost:5432/db
GITHUB_TOKEN=ghp_12345678901234567890123456789012345678
NORMAL_VALUE=not_a_secret
"""

    filtered, changes = manager.filter_content(test_content, "test.env")

    print("\nFiltered Content:")
    print(filtered)
    print("\nChanges Made:")
    print(json.dumps(changes, indent=2))

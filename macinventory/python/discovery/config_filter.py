"""Configuration file filtering for Tier 2/3 discovery.

Provides include-list based filtering to ensure only actual
configuration files are backed up from convention and LLM discoveries.

This module implements the guardrails defined in Phase 6.5 to prevent
backing up binaries, caches, logs, and other non-configuration files
that may be discovered by convention-based or LLM-based discovery.

Tier 1 (Hints Database) paths are NOT filtered - they are curated
and trusted. Only Tier 2 (Conventions) and Tier 3 (LLM) use this filter.
"""

import fnmatch
import os
from pathlib import Path
from typing import Any, Optional

import yaml


def _default_patterns_path() -> Path:
    """Get the default path to config-patterns.yaml."""
    # Go from discovery/ up to python/, then to data/
    module_dir = Path(__file__).parent
    return module_dir.parent.parent / "data" / "config-patterns.yaml"


class ConfigFilter:
    """Filters discovered paths to only include configuration files.

    Uses an include-list approach defined in config-patterns.yaml to
    determine which files should be backed up from Tier 2/3 discoveries.

    Example:
        >>> filter = ConfigFilter()
        >>> is_valid, reason = filter.is_config_file(Path("~/.docker/config.json"))
        >>> print(f"Valid: {is_valid}, Reason: {reason}")
        Valid: True, Reason: Safe extension: .json

        >>> paths = [Path("~/.docker/config.json"), Path("~/.docker/bin/docker")]
        >>> valid, rejected = filter.filter_paths(paths)
        >>> print(f"Valid: {len(valid)}, Rejected: {len(rejected)}")
        Valid: 1, Rejected: 1
    """

    def __init__(self, patterns_path: Optional[Path] = None):
        """Load config patterns from YAML file.

        Args:
            patterns_path: Path to config-patterns.yaml. If None, uses default.
        """
        self.patterns_path = patterns_path or _default_patterns_path()
        self._patterns: dict[str, Any] = {}
        self._load_patterns()

        # Pre-compute flattened extension lists for performance
        self._safe_extensions: set[str] = set()
        self._hard_exclude_extensions: set[str] = set()
        self._safe_filenames: set[str] = set()
        self._safe_directories: set[str] = set()
        self._hard_exclude_patterns: list[str] = []
        self._max_file_size: int = 1048576  # 1MB default

        self._build_lookup_sets()

    def _load_patterns(self) -> None:
        """Load patterns from YAML file."""
        try:
            if self.patterns_path.exists():
                with open(self.patterns_path, 'r') as f:
                    self._patterns = yaml.safe_load(f) or {}
            else:
                # Use minimal defaults if file doesn't exist
                self._patterns = {
                    'safe_extensions': {
                        'text_configs': ['.json', '.yaml', '.yml', '.toml', '.plist']
                    },
                    'hard_exclude_extensions': ['.dylib', '.so', '.sqlite', '.db'],
                    'hard_exclude_patterns': ['**/Cache/**', '**/Logs/**'],
                    'size_limits': {'max_file_size_bytes': 1048576}
                }
        except (yaml.YAMLError, OSError):
            # Fail gracefully with minimal defaults
            self._patterns = {}

    def _build_lookup_sets(self) -> None:
        """Build lookup sets from patterns for efficient checking."""
        # Flatten safe_extensions (which is a nested dict)
        safe_ext = self._patterns.get('safe_extensions', {})
        if isinstance(safe_ext, dict):
            for category_extensions in safe_ext.values():
                if isinstance(category_extensions, list):
                    for ext in category_extensions:
                        # Normalize: ensure starts with dot, lowercase
                        ext = ext.lower()
                        if not ext.startswith('.'):
                            ext = '.' + ext
                        self._safe_extensions.add(ext)

        # Hard exclude extensions (flat list)
        for ext in self._patterns.get('hard_exclude_extensions', []):
            ext = ext.lower()
            if not ext.startswith('.'):
                ext = '.' + ext
            self._hard_exclude_extensions.add(ext)

        # Safe filenames (case-insensitive)
        for name in self._patterns.get('safe_filenames', []):
            self._safe_filenames.add(name.lower())

        # Safe directories (case-insensitive)
        for name in self._patterns.get('safe_directories', []):
            self._safe_directories.add(name.lower())

        # Hard exclude patterns (for fnmatch)
        self._hard_exclude_patterns = self._patterns.get('hard_exclude_patterns', [])

        # Size limits
        size_limits = self._patterns.get('size_limits', {})
        self._max_file_size = size_limits.get('max_file_size_bytes', 1048576)

    def _matches_exclude_pattern(self, path: Path) -> Optional[str]:
        """Check if path matches any hard exclude pattern.

        Args:
            path: Path to check

        Returns:
            The matched pattern string, or None if no match
        """
        path_str = str(path)

        for pattern in self._hard_exclude_patterns:
            if fnmatch.fnmatch(path_str, pattern):
                return pattern
            # Also check with forward slashes normalized
            if fnmatch.fnmatch(path_str.replace('\\', '/'), pattern):
                return pattern

        return None

    def _is_in_excluded_directory(self, path: Path) -> Optional[str]:
        """Check if path is inside an excluded directory pattern.

        Args:
            path: Path to check

        Returns:
            The directory name that matched, or None
        """
        # Check each part of the path against exclude patterns
        parts = path.parts

        # Common excluded directory names
        excluded_dirs = {
            'cache', 'caches', 'cacheddata',
            'log', 'logs',
            'build', 'buildx',
            'node_modules', '.git',
            'bin', 'obj',
            '__pycache__',
            'blob_storage', 'indexeddb', 'webstorage',
            'workspacestorage', 'globalstorage',
            'local storage', 'session storage',
            'gpucache', 'shadercache',
            'crashpad', 'crashreporter',
            'models', 'mutagen', 'contexts', 'cloud',
            'desktop-build', 'refs', 'activity'
        }

        for part in parts:
            if part.lower() in excluded_dirs:
                return part

        return None

    def is_config_file(self, path: Path) -> tuple[bool, str]:
        """Check if a file is a valid configuration file.

        Applies the include-list rules to determine if a file should
        be backed up from Tier 2/3 discovery.

        Args:
            path: Absolute path to the file

        Returns:
            (is_valid, reason) tuple:
            - is_valid: True if file should be backed up
            - reason: Human-readable explanation
        """
        path = Path(path)

        # Check if file exists
        if not path.exists():
            return False, "File does not exist"

        if not path.is_file():
            return False, "Not a file"

        filename = path.name.lower()
        suffix = path.suffix.lower()

        # 1. Check hard exclude patterns first (highest priority)
        exclude_pattern = self._matches_exclude_pattern(path)
        if exclude_pattern:
            return False, f"Matches exclude pattern: {exclude_pattern}"

        # 2. Check if in excluded directory
        excluded_dir = self._is_in_excluded_directory(path)
        if excluded_dir:
            return False, f"Inside excluded directory: {excluded_dir}"

        # 3. Check hard exclude extensions
        if suffix in self._hard_exclude_extensions:
            return False, f"Excluded extension: {suffix}"

        # 4. Check file size
        try:
            file_size = path.stat().st_size
            if file_size > self._max_file_size:
                size_mb = file_size / (1024 * 1024)
                return False, f"File too large: {size_mb:.2f}MB (max: {self._max_file_size / (1024 * 1024):.0f}MB)"
        except OSError:
            pass  # Continue if we can't get size

        # 5. Check if filename is in safe list
        if filename in self._safe_filenames:
            return True, f"Safe filename: {filename}"

        # 6. Check if extension is in safe list
        if suffix in self._safe_extensions:
            return True, f"Safe extension: {suffix}"

        # 7. Check for dotfile patterns (files starting with .)
        if filename.startswith('.') and not filename.startswith('..'):
            # Dotfiles with safe extensions
            if suffix in self._safe_extensions:
                return True, f"Dotfile with safe extension: {suffix}"

            # Common dotfile config patterns
            dotfile_patterns = [
                'rc', 'config', 'conf', 'profile', 'login', 'logout',
                'history', 'aliases', 'exports', 'functions'
            ]
            for pattern in dotfile_patterns:
                if pattern in filename:
                    return True, f"Dotfile config pattern: {filename}"

        # Default: reject unknown files
        return False, f"Unknown file type: {filename}"

    def is_config_directory(self, path: Path) -> tuple[bool, str]:
        """Check if a directory likely contains configs.

        Args:
            path: Path to the directory

        Returns:
            (is_valid, reason) tuple
        """
        path = Path(path)

        if not path.exists():
            return False, "Directory does not exist"

        if not path.is_dir():
            return False, "Not a directory"

        dirname = path.name.lower()

        # Check if in excluded patterns
        exclude_pattern = self._matches_exclude_pattern(path)
        if exclude_pattern:
            return False, f"Matches exclude pattern: {exclude_pattern}"

        # Check if directory name is excluded
        excluded_dir = self._is_in_excluded_directory(path)
        if excluded_dir:
            return False, f"Excluded directory type: {excluded_dir}"

        # Check if directory name is in safe list
        if dirname in self._safe_directories:
            return True, f"Safe directory: {dirname}"

        # Default: allow but note it's not explicitly safe
        return True, f"Allowed directory (not explicitly safe): {dirname}"

    def should_recurse_directory(self, path: Path) -> bool:
        """Check if we should recurse into this directory for configs.

        Args:
            path: Path to directory

        Returns:
            True if we should look inside this directory
        """
        is_valid, _ = self.is_config_directory(path)
        return is_valid

    def filter_paths(
        self,
        paths: list[Path],
        include_directories: bool = False
    ) -> tuple[list[Path], list[dict[str, Any]]]:
        """Filter a list of paths, returning valid configs and rejection reasons.

        Args:
            paths: List of paths to filter
            include_directories: If True, also process directories

        Returns:
            Tuple of (valid_paths, rejected_info):
            - valid_paths: List of paths that passed filtering
            - rejected_info: List of dicts with path and rejection reason
        """
        valid_paths: list[Path] = []
        rejected: list[dict[str, Any]] = []

        for path in paths:
            path = Path(path)

            if path.is_file():
                is_valid, reason = self.is_config_file(path)
                if is_valid:
                    valid_paths.append(path)
                else:
                    rejected.append({
                        'path': str(path),
                        'reason': reason,
                        'type': 'file'
                    })
            elif path.is_dir() and include_directories:
                is_valid, reason = self.is_config_directory(path)
                if is_valid:
                    valid_paths.append(path)
                else:
                    rejected.append({
                        'path': str(path),
                        'reason': reason,
                        'type': 'directory'
                    })

        return valid_paths, rejected

    def filter_directory_contents(
        self,
        directory: Path,
        recursive: bool = True
    ) -> tuple[list[Path], list[dict[str, Any]]]:
        """Filter all files in a directory.

        Args:
            directory: Directory to scan
            recursive: If True, recurse into subdirectories

        Returns:
            Tuple of (valid_paths, rejected_info)
        """
        directory = Path(directory)
        if not directory.is_dir():
            return [], [{'path': str(directory), 'reason': 'Not a directory', 'type': 'error'}]

        all_files: list[Path] = []

        if recursive:
            for root, dirs, files in os.walk(directory):
                root_path = Path(root)

                # Filter out excluded directories from traversal
                dirs[:] = [d for d in dirs if self.should_recurse_directory(root_path / d)]

                for file in files:
                    all_files.append(root_path / file)
        else:
            all_files = [f for f in directory.iterdir() if f.is_file()]

        return self.filter_paths(all_files)

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about loaded patterns.

        Returns:
            Dict with pattern counts
        """
        return {
            'safe_extensions_count': len(self._safe_extensions),
            'safe_filenames_count': len(self._safe_filenames),
            'safe_directories_count': len(self._safe_directories),
            'hard_exclude_extensions_count': len(self._hard_exclude_extensions),
            'hard_exclude_patterns_count': len(self._hard_exclude_patterns),
            'max_file_size_mb': self._max_file_size / (1024 * 1024),
            'patterns_file': str(self.patterns_path),
            'patterns_file_exists': self.patterns_path.exists()
        }


# Convenience function for simple filtering
def filter_config_paths(
    paths: list[Path],
    patterns_path: Optional[Path] = None
) -> tuple[list[Path], list[dict[str, Any]]]:
    """Filter paths using default ConfigFilter.

    Args:
        paths: List of paths to filter
        patterns_path: Optional custom patterns file

    Returns:
        Tuple of (valid_paths, rejected_info)
    """
    config_filter = ConfigFilter(patterns_path)
    return config_filter.filter_paths(paths)


if __name__ == "__main__":
    import json

    # Demo the filter
    filter = ConfigFilter()

    print("ConfigFilter Statistics:")
    print(json.dumps(filter.get_statistics(), indent=2))

    # Test some paths
    test_paths = [
        Path.home() / ".gitconfig",
        Path.home() / ".docker" / "config.json",
        Path.home() / ".docker" / "daemon.json",
        Path.home() / ".docker" / "bin" / "docker",
        Path.home() / "Library" / "Caches" / "test.json",
    ]

    print("\nTest Results:")
    for path in test_paths:
        if path.exists():
            is_valid, reason = filter.is_config_file(path)
            status = "VALID" if is_valid else "REJECT"
            print(f"  [{status}] {path.name}: {reason}")
        else:
            print(f"  [SKIP] {path} (does not exist)")

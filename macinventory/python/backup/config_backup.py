"""Safe configuration backup with error handling.

Implements the config backup system from MACINVENTORY_IMPLEMENTATION_GUIDE.md.
Provides safe copying of configuration files with:
- Security filtering (secrets redacted by default)
- Permission normalization (files 0600, directories 0700)
- macOS attribute handling (ACLs, immutable flags)
- Graceful error handling (partial results over failure)

From Vision document:
    "Users should always get something useful, never a complete failure."
"""

import fnmatch
import os
import shutil
from pathlib import Path
from typing import Any, Optional

from .security import SecurityManager
from utils.plist import backup_plist_as_xml, is_binary_plist
from utils.path_safety import safe_join, PathTraversalError


# Default permission modes (from Vision document)
FILE_MODE = 0o600  # rw-------
DIR_MODE = 0o700   # rwx------


def normalize_permissions(target: Path) -> None:
    """Normalize permissions on copied config files/directories.

    From Vision document - Permission Normalization:
        Files: 0600 (owner read/write only)
        Directories: 0700 (owner read/write/execute only)

    Args:
        target: Path to file or directory to normalize
    """
    if not target.exists():
        return

    try:
        if target.is_file():
            os.chmod(target, FILE_MODE)
        elif target.is_dir():
            os.chmod(target, DIR_MODE)
            # Recursively normalize directory contents
            for root, dirs, files in os.walk(target):
                for d in dirs:
                    try:
                        os.chmod(Path(root) / d, DIR_MODE)
                    except OSError:
                        pass  # Best effort
                for f in files:
                    try:
                        os.chmod(Path(root) / f, FILE_MODE)
                    except OSError:
                        pass
    except OSError:
        pass  # Best effort, don't fail on permission errors


def copy_file_safe(
    src: Path,
    dst: Path,
    normalize: bool = True,
    handle_attributes: bool = True
) -> dict[str, Any]:
    """Safely copy a single file with optional permission normalization.

    Args:
        src: Source file path
        dst: Destination file path
        normalize: Whether to normalize permissions after copy
        handle_attributes: Whether to handle macOS attributes

    Returns:
        Dictionary with copy results:
        - status: 'success', 'error', or 'skipped'
        - source: Source path
        - dest: Destination path
        - error: Error message if failed
        - attributes: Attribute handling results
    """
    result: dict[str, Any] = {
        'status': 'success',
        'source': str(src),
        'dest': str(dst),
    }

    # Handle macOS attributes on source
    if handle_attributes:
        try:
            from utils.file_ops import prepare_for_copy, clear_destination_attributes
            result['source_attributes'] = prepare_for_copy(src)
        except ImportError:
            pass  # file_ops not available, continue without

    try:
        # Create parent directories
        dst.parent.mkdir(parents=True, exist_ok=True)

        # Copy file with metadata
        shutil.copy2(src, dst)

        # Clear attributes on destination (macOS)
        if handle_attributes:
            try:
                from utils.file_ops import clear_destination_attributes
                result['dest_attributes'] = clear_destination_attributes(dst)
            except ImportError:
                pass

        # Normalize permissions
        if normalize:
            normalize_permissions(dst)

    except OSError as e:
        result['status'] = 'error'
        result['error'] = str(e)
    except Exception as e:
        result['status'] = 'error'
        result['error'] = f"Unexpected error: {e}"

    return result


def copy_directory_safe(
    src: Path,
    dst: Path,
    normalize: bool = True,
    handle_attributes: bool = True
) -> dict[str, Any]:
    """Safely copy a directory with optional permission normalization.

    Args:
        src: Source directory path
        dst: Destination directory path
        normalize: Whether to normalize permissions after copy
        handle_attributes: Whether to handle macOS attributes

    Returns:
        Dictionary with copy results
    """
    result: dict[str, Any] = {
        'status': 'success',
        'source': str(src),
        'dest': str(dst),
        'files_copied': 0,
        'dirs_copied': 0,
        'errors': [],
    }

    try:
        # Create destination
        dst.parent.mkdir(parents=True, exist_ok=True)

        # Copy directory tree
        if dst.exists():
            # Merge with existing
            for item in src.iterdir():
                item_dst = dst / item.name
                if item.is_file():
                    copy_result = copy_file_safe(item, item_dst, normalize=False)
                    if copy_result['status'] == 'success':
                        result['files_copied'] += 1
                    else:
                        result['errors'].append(copy_result)
                elif item.is_dir():
                    sub_result = copy_directory_safe(item, item_dst, normalize=False)
                    result['files_copied'] += sub_result.get('files_copied', 0)
                    result['dirs_copied'] += sub_result.get('dirs_copied', 0) + 1
                    result['errors'].extend(sub_result.get('errors', []))
        else:
            shutil.copytree(src, dst, dirs_exist_ok=True)
            # Count copied items
            for root, dirs, files in os.walk(dst):
                result['files_copied'] += len(files)
                result['dirs_copied'] += len(dirs)

        # Clear macOS attributes on destination
        if handle_attributes:
            try:
                from utils.file_ops import clear_destination_attributes
                clear_destination_attributes(dst)
            except ImportError:
                pass

        # Normalize permissions (this handles the whole tree)
        if normalize:
            normalize_permissions(dst)

        if result['errors']:
            result['status'] = 'partial'

    except OSError as e:
        result['status'] = 'error'
        result['errors'].append({'error': str(e)})
    except Exception as e:
        result['status'] = 'error'
        result['errors'].append({'error': f"Unexpected error: {e}"})

    return result


class ConfigBackup:
    """Manages configuration file backups with security filtering.

    Provides a high-level interface for backing up configuration files
    with automatic secret filtering and permission normalization.

    Example:
        >>> backup = ConfigBackup(output_dir=Path("~/mac-inventory/backup"))
        >>> result = backup.backup_file(Path("~/.gitconfig"), "git/gitconfig")
        >>> print(f"Backed up with {len(result['changes'])} secrets filtered")
    """

    def __init__(
        self,
        output_dir: Path,
        include_secrets: bool = False,
        normalize_permissions: bool = True,
        security_manager: Optional[SecurityManager] = None
    ):
        """Initialize the config backup.

        Args:
            output_dir: Base directory for backups
            include_secrets: If True, don't filter secrets
            normalize_permissions: If True, normalize file permissions
            security_manager: Optional custom SecurityManager instance
        """
        self.output_dir = Path(output_dir)
        self.include_secrets = include_secrets
        self.normalize = normalize_permissions
        self.security = security_manager or SecurityManager()

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Track backup results
        self.results: list[dict[str, Any]] = []

    def backup_file(
        self,
        source: Path,
        relative_dest: str,
        filter_secrets: Optional[bool] = None,
        discovery_tier: str = "unknown",
        exclude_patterns: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """Backup a single configuration file.

        Args:
            source: Source file path
            relative_dest: Destination path relative to output_dir
            filter_secrets: Override include_secrets setting
            discovery_tier: Discovery tier ('hints', 'conventions', 'llm', 'unknown')
                           Tier 2/3 files are validated with ConfigFilter
            exclude_patterns: App-specific patterns to exclude (from hints exclude_files)

        Returns:
            Dictionary with backup results
        """
        source = Path(source).expanduser()

        # Validate path to prevent directory traversal attacks
        try:
            dest = safe_join(self.output_dir, relative_dest)
        except PathTraversalError as e:
            return {
                'source': str(source),
                'dest': None,
                'relative_dest': relative_dest,
                'status': 'error',
                'errors': [str(e)],
                'discovery_tier': discovery_tier,
            }

        result: dict[str, Any] = {
            'source': str(source),
            'dest': str(dest),
            'relative_dest': relative_dest,
            'status': 'success',
            'filtered': False,
            'changes': [],
            'errors': [],
            'discovery_tier': discovery_tier,
            'plist_converted': False,
            'original_format': None,
        }

        # Check if file exists
        if not source.exists():
            result['status'] = 'skipped'
            result['reason'] = 'Source file does not exist'
            self.results.append(result)
            return result

        # Phase 6.5: Apply ConfigFilter for Tier 2/3 discoveries
        if discovery_tier in ('conventions', 'llm'):
            from discovery.config_filter import ConfigFilter
            config_filter = ConfigFilter()
            is_valid, filter_reason = config_filter.is_config_file(source)
            if not is_valid:
                result['status'] = 'skipped'
                result['reason'] = f'Config filter: {filter_reason}'
                result['tier_filtered'] = True
                self.results.append(result)
                return result

        # Check if file can be backed up
        can_backup, reason = self.security.can_backup(source)
        if not can_backup:
            result['status'] = 'skipped'
            result['reason'] = reason
            self.results.append(result)
            return result

        # Determine whether to filter
        should_filter = not self.include_secrets
        if filter_secrets is not None:
            should_filter = filter_secrets

        try:
            # Create destination directory
            dest.parent.mkdir(parents=True, exist_ok=True)

            if source.is_file():
                # Handle binary plist files - convert to XML for readable backup
                if source.suffix.lower() == '.plist' and is_binary_plist(source):
                    plist_result = backup_plist_as_xml(source, dest, normalize_permissions=False)

                    if plist_result['status'] != 'success':
                        result['status'] = plist_result['status']
                        result['reason'] = plist_result.get('reason') or plist_result.get('error')
                    else:
                        result['plist_converted'] = True
                        result['original_format'] = plist_result.get('original_format')

                        # Apply secret filtering to the converted XML if needed
                        if should_filter:
                            content = dest.read_text(encoding='utf-8')
                            filtered_content, changes = self.security.filter.filter_content(content, str(source))
                            dest.write_text(filtered_content, encoding='utf-8')
                            result['filtered'] = True
                            result['changes'] = changes

                        # Normalize permissions
                        if self.normalize:
                            normalize_permissions(dest)

                elif should_filter:
                    # Filter and copy
                    process_result = self.security.process_file(
                        source, dest, include_secrets=False
                    )
                    result['filtered'] = True
                    result['changes'] = process_result.get('changes', [])
                    if process_result.get('status') == 'error':
                        result['status'] = 'error'
                        result['errors'] = process_result.get('errors', [])

                    # Normalize permissions if needed (filtering doesn't do this)
                    if self.normalize and result['status'] == 'success':
                        normalize_permissions(dest)

                else:
                    # Direct copy without filtering
                    copy_result = copy_file_safe(source, dest, normalize=self.normalize)
                    if copy_result['status'] != 'success':
                        result['status'] = copy_result['status']
                        result['errors'].append(copy_result.get('error', 'Copy failed'))

        except Exception as e:
            result['status'] = 'error'
            result['errors'].append(str(e))

        self.results.append(result)
        return result

    def backup_directory(
        self,
        source: Path,
        relative_dest: str,
        filter_secrets: Optional[bool] = None,
        discovery_tier: str = "unknown",
        exclude_patterns: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """Backup a configuration directory.

        Args:
            source: Source directory path
            relative_dest: Destination path relative to output_dir
            filter_secrets: Override include_secrets setting
            discovery_tier: Discovery tier ('hints', 'conventions', 'llm', 'unknown')
                           Tier 2/3 files inside the directory are validated with ConfigFilter
            exclude_patterns: App-specific patterns to exclude (from hints exclude_files)

        Returns:
            Dictionary with backup results
        """
        source = Path(source).expanduser()

        # Validate path to prevent directory traversal attacks
        try:
            dest = safe_join(self.output_dir, relative_dest)
        except PathTraversalError as e:
            return {
                'source': str(source),
                'dest': None,
                'relative_dest': relative_dest,
                'status': 'error',
                'errors': [str(e)],
                'discovery_tier': discovery_tier,
            }

        result: dict[str, Any] = {
            'source': str(source),
            'dest': str(dest),
            'relative_dest': relative_dest,
            'status': 'success',
            'files_processed': 0,
            'files_filtered': 0,
            'files_skipped': 0,
            'tier_filtered': 0,  # Phase 6.5: Files filtered by ConfigFilter
            'total_changes': [],
            'errors': [],
            'discovery_tier': discovery_tier,
        }

        # Check if directory exists
        if not source.exists():
            result['status'] = 'skipped'
            result['reason'] = 'Source directory does not exist'
            self.results.append(result)
            return result

        # Phase 6.5: Apply ConfigFilter to directory for Tier 2/3
        config_filter = None
        if discovery_tier in ('conventions', 'llm'):
            from discovery.config_filter import ConfigFilter
            config_filter = ConfigFilter()
            is_valid, filter_reason = config_filter.is_config_directory(source)
            if not is_valid:
                result['status'] = 'skipped'
                result['reason'] = f'Config filter: {filter_reason}'
                result['tier_filtered'] = True
                self.results.append(result)
                return result

        # Check if directory can be backed up
        can_backup, reason = self.security.can_backup(source)
        if not can_backup:
            result['status'] = 'skipped'
            result['reason'] = reason
            self.results.append(result)
            return result

        # Determine whether to filter
        should_filter = not self.include_secrets
        if filter_secrets is not None:
            should_filter = filter_secrets

        try:
            # Walk the source directory
            for root, dirs, files in os.walk(source):
                root_path = Path(root)
                # Filter out excluded directories (use root_path, not source, for nested dirs)
                dirs[:] = [d for d in dirs if not self._should_skip_dir(root_path / d)]

                # Apply app-specific exclude_patterns to directories
                if exclude_patterns:
                    dirs[:] = [d for d in dirs if not self._matches_exclude_pattern(d, exclude_patterns)]

                # Phase 6.5: Also filter directories using ConfigFilter for Tier 2/3
                if config_filter:
                    dirs[:] = [d for d in dirs if config_filter.should_recurse_directory(Path(root) / d)]

                rel_root = Path(root).relative_to(source)
                dest_root = dest / rel_root

                for filename in files:
                    src_file = Path(root) / filename
                    dst_file = dest_root / filename

                    # Apply app-specific exclude_patterns to files
                    if exclude_patterns and self._matches_exclude_pattern(filename, exclude_patterns):
                        result['files_skipped'] += 1
                        continue

                    # Phase 6.5: Apply ConfigFilter to files for Tier 2/3
                    if config_filter:
                        is_valid, filter_reason = config_filter.is_config_file(src_file)
                        if not is_valid:
                            result['tier_filtered'] += 1
                            continue

                    # Check if file can be backed up
                    can_backup_file, skip_reason = self.security.can_backup(src_file)
                    if not can_backup_file:
                        result['files_skipped'] += 1
                        continue

                    try:
                        dest_root.mkdir(parents=True, exist_ok=True)

                        # Handle binary plist files - convert to XML for readable backup
                        if src_file.suffix.lower() == '.plist' and is_binary_plist(src_file):
                            plist_result = backup_plist_as_xml(src_file, dst_file, normalize_permissions=False)

                            if plist_result['status'] == 'success':
                                # Apply secret filtering to the converted XML if needed
                                if should_filter:
                                    content = dst_file.read_text(encoding='utf-8')
                                    filtered_content, changes = self.security.filter.filter_content(content, str(src_file))
                                    dst_file.write_text(filtered_content, encoding='utf-8')
                                    if changes:
                                        result['files_filtered'] += 1
                                        result['total_changes'].extend(changes)
                            else:
                                result['errors'].append({
                                    'file': str(src_file),
                                    'error': plist_result.get('error') or plist_result.get('reason', 'Plist conversion failed')
                                })
                        elif should_filter:
                            # Filter and copy
                            process_result = self.security.process_file(
                                src_file, dst_file, include_secrets=False
                            )
                            if process_result.get('changes'):
                                result['files_filtered'] += 1
                                result['total_changes'].extend(process_result['changes'])
                            if process_result.get('status') == 'error':
                                result['errors'].extend(process_result.get('errors', []))
                        else:
                            # Direct copy
                            copy_file_safe(src_file, dst_file, normalize=False)

                        result['files_processed'] += 1

                    except Exception as e:
                        result['errors'].append({
                            'file': str(src_file),
                            'error': str(e)
                        })

            # Normalize permissions for entire destination tree
            if self.normalize:
                normalize_permissions(dest)

            if result['errors']:
                result['status'] = 'partial'

        except Exception as e:
            result['status'] = 'error'
            result['errors'].append(str(e))

        self.results.append(result)
        return result

    def backup_path(
        self,
        source: Path,
        relative_dest: str,
        filter_secrets: Optional[bool] = None,
        discovery_tier: str = "unknown",
        exclude_patterns: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """Backup a file or directory automatically.

        Args:
            source: Source path (file or directory)
            relative_dest: Destination path relative to output_dir
            filter_secrets: Override include_secrets setting
            discovery_tier: Discovery tier ('hints', 'conventions', 'llm', 'unknown')
                           Tier 2/3 paths are validated with ConfigFilter
            exclude_patterns: App-specific patterns to exclude (from hints exclude_files)

        Returns:
            Dictionary with backup results
        """
        source = Path(source).expanduser()

        if source.is_dir():
            return self.backup_directory(source, relative_dest, filter_secrets, discovery_tier, exclude_patterns)
        else:
            return self.backup_file(source, relative_dest, filter_secrets, discovery_tier, exclude_patterns)

    def _should_skip_dir(self, dir_path: Path) -> bool:
        """Check if a directory should be skipped during backup.

        Args:
            dir_path: Directory path to check

        Returns:
            True if directory should be skipped
        """
        excluded, _ = self.security.exclusions.should_exclude_directory(dir_path)
        return excluded

    def _matches_exclude_pattern(self, name: str, patterns: list[str]) -> bool:
        """Check if a file/directory name matches any exclude pattern.

        Args:
            name: File or directory name to check
            patterns: List of patterns from app-hints.yaml exclude_files

        Returns:
            True if name matches any pattern
        """
        for pattern in patterns:
            # Normalize pattern (remove trailing slash for directory patterns)
            clean_pattern = pattern.rstrip('/')
            if fnmatch.fnmatch(name, clean_pattern):
                return True
            # Also check case-insensitive for macOS
            if fnmatch.fnmatch(name.lower(), clean_pattern.lower()):
                return True
        return False

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of all backup operations.

        Returns:
            Dictionary with summary statistics
        """
        total = len(self.results)
        success = sum(1 for r in self.results if r['status'] == 'success')
        partial = sum(1 for r in self.results if r['status'] == 'partial')
        skipped = sum(1 for r in self.results if r['status'] == 'skipped')
        errors = sum(1 for r in self.results if r['status'] == 'error')

        return {
            'total_operations': total,
            'success': success,
            'partial': partial,
            'skipped': skipped,
            'errors': errors,
            'include_secrets': self.include_secrets,
            'output_dir': str(self.output_dir),
        }


def backup_all_configs(
    configs: list[dict[str, Any]],
    output_dir: Path,
    include_secrets: bool = False
) -> dict[str, Any]:
    """Backup all configuration files from a list.

    High-level function for backing up multiple configs at once.

    Args:
        configs: List of config dicts with 'source' and 'dest' keys
        output_dir: Base output directory
        include_secrets: Whether to include secrets

    Returns:
        Dictionary with overall results

    Example:
        >>> configs = [
        ...     {'source': '~/.gitconfig', 'dest': 'git/gitconfig'},
        ...     {'source': '~/.zshrc', 'dest': 'shell/zshrc'},
        ... ]
        >>> result = backup_all_configs(configs, Path("~/backup"))
    """
    backup = ConfigBackup(
        output_dir=output_dir,
        include_secrets=include_secrets
    )

    for config in configs:
        source = Path(config['source']).expanduser()
        dest = config['dest']
        backup.backup_path(source, dest)

    return {
        'summary': backup.get_summary(),
        'results': backup.results,
    }


if __name__ == "__main__":
    import json
    import tempfile

    # Demo the backup system
    with tempfile.TemporaryDirectory() as tmpdir:
        backup = ConfigBackup(
            output_dir=Path(tmpdir),
            include_secrets=False
        )

        # Backup some test files
        test_configs = [
            (Path.home() / ".gitconfig", "git/gitconfig"),
            (Path.home() / ".zshrc", "shell/zshrc"),
        ]

        for source, dest in test_configs:
            if source.exists():
                result = backup.backup_file(source, dest)
                print(f"\n{source.name}:")
                print(f"  Status: {result['status']}")
                print(f"  Filtered: {result['filtered']}")
                print(f"  Changes: {len(result['changes'])}")

        print("\nSummary:")
        print(json.dumps(backup.get_summary(), indent=2))

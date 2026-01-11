"""Backup modules for safely copying configuration files.

Modules:
    config_backup: Safe config file copying with error handling
    security: Secret filtering using security-patterns.yaml
"""

from .security import (
    SecurityManager,
    SecretFilter,
    ExclusionChecker,
    load_security_patterns,
    is_pure_config,
    SecurityError,
)

from .config_backup import (
    ConfigBackup,
    backup_all_configs,
    copy_file_safe,
    copy_directory_safe,
    normalize_permissions,
    FILE_MODE,
    DIR_MODE,
)

__all__ = [
    # security
    'SecurityManager',
    'SecretFilter',
    'ExclusionChecker',
    'load_security_patterns',
    'is_pure_config',
    'SecurityError',
    # config_backup
    'ConfigBackup',
    'backup_all_configs',
    'copy_file_safe',
    'copy_directory_safe',
    'normalize_permissions',
    'FILE_MODE',
    'DIR_MODE',
]

"""Utility modules for common operations.

Modules:
    plist: Binary plist conversion to XML
    file_ops: Platform-specific file operations (ACLs, flags)
    storage_detection: Cloud storage service detection (OneDrive, iCloud, Dropbox, Google Drive)
    subprocess_utils: Safe command execution (planned)
"""

from .plist import (
    is_plist,
    is_binary_plist,
    is_xml_plist,
    get_plist_format,
    convert_to_xml,
    read_plist,
    read_plist_safe,
    backup_plist_as_xml,
    PlistConverter,
    PlistError,
)

from .file_ops import (
    is_macos,
    remove_acl,
    remove_immutable_flags,
    prepare_for_copy,
    normalize_destination_permissions,
    clear_destination_attributes,
)

from .storage_detection import (
    detect_onedrive,
    detect_all_onedrive,
    detect_icloud,
    detect_dropbox,
    detect_google_drive,
    detect_all_google_drive,
    detect_all_cloud_storage,
    get_cloud_storage_display_name,
)

__all__ = [
    # plist
    'is_plist',
    'is_binary_plist',
    'is_xml_plist',
    'get_plist_format',
    'convert_to_xml',
    'read_plist',
    'read_plist_safe',
    'backup_plist_as_xml',
    'PlistConverter',
    'PlistError',
    # file_ops
    'is_macos',
    'remove_acl',
    'remove_immutable_flags',
    'prepare_for_copy',
    'normalize_destination_permissions',
    'clear_destination_attributes',
    # storage_detection
    'detect_onedrive',
    'detect_all_onedrive',
    'detect_icloud',
    'detect_dropbox',
    'detect_google_drive',
    'detect_all_google_drive',
    'detect_all_cloud_storage',
    'get_cloud_storage_display_name',
]

"""Path safety utilities to prevent directory traversal attacks.

Provides validation and safe path operations to ensure files are only
written within intended directories, preventing path traversal attacks
where malicious paths like "../../../etc/passwd" could escape the output directory.

From REVIEW-FINDINGS.md Issue #2:
    "A crafted relative_dest like ../../etc/passwd could write outside
    the intended directory."
"""

from pathlib import Path
from typing import Union


class PathTraversalError(ValueError):
    """Raised when path traversal is detected.

    This exception indicates an attempt to access a path outside the
    allowed base directory, which could be a security issue.
    """
    pass


def validate_relative_path(rel_path: Union[str, Path]) -> bool:
    """Check if a path is safe (no traversal sequences).

    A path is considered safe if:
    - It is not an absolute path
    - It does not contain ".." components

    Args:
        rel_path: The relative path to validate

    Returns:
        True if the path is safe, False otherwise

    Examples:
        >>> validate_relative_path("subdir/file.txt")
        True
        >>> validate_relative_path("../etc/passwd")
        False
        >>> validate_relative_path("/etc/passwd")
        False
    """
    path = Path(rel_path)

    # Reject absolute paths
    if path.is_absolute():
        return False

    # Reject paths with parent directory references
    if ".." in path.parts:
        return False

    return True


def safe_join(base: Path, relative: Union[str, Path]) -> Path:
    """Join paths with traversal protection.

    Safely joins a base directory with a relative path, ensuring the
    resulting path stays within the base directory. This prevents
    directory traversal attacks.

    Args:
        base: The base directory (must exist or be creatable)
        relative: The relative path to join

    Returns:
        The resolved, safe destination path

    Raises:
        PathTraversalError: If the resolved path escapes base directory

    Examples:
        >>> base = Path("/tmp/output")
        >>> safe_join(base, "configs/app.json")
        PosixPath('/tmp/output/configs/app.json')

        >>> safe_join(base, "../etc/passwd")
        Traceback (most recent call last):
            ...
        PathTraversalError: Invalid relative path: ../etc/passwd
    """
    # First check for obvious traversal patterns
    if not validate_relative_path(relative):
        raise PathTraversalError(f"Invalid relative path: {relative}")

    # Resolve both paths to catch edge cases
    base_resolved = base.resolve()
    dest = (base / relative).resolve()

    # Verify the destination is still within the base directory
    # Using is_relative_to() for Python 3.9+ compatibility
    try:
        dest.relative_to(base_resolved)
    except ValueError:
        raise PathTraversalError(
            f"Path traversal detected: {relative} escapes {base}"
        )

    return dest


def sanitize_path_component(name: str) -> str:
    """Sanitize a single path component (filename or directory name).

    Removes or replaces characters that could be used for path traversal
    or are otherwise unsafe in filenames.

    Args:
        name: The path component to sanitize

    Returns:
        A sanitized version of the name safe for use in paths

    Examples:
        >>> sanitize_path_component("My App")
        'my-app'
        >>> sanitize_path_component("../etc")
        'etc'
        >>> sanitize_path_component("app/config")
        'app-config'
    """
    # Remove parent directory references
    sanitized = name.replace("..", "")

    # Replace path separators with hyphens
    sanitized = sanitized.replace("/", "-").replace("\\", "-")

    # Convert to lowercase and replace spaces
    sanitized = sanitized.lower().replace(" ", "-")

    # Remove any leading/trailing hyphens or dots
    sanitized = sanitized.strip("-.")

    # If empty after sanitization, use a default
    if not sanitized:
        sanitized = "unnamed"

    return sanitized


if __name__ == "__main__":
    # Demo the path safety utilities
    import tempfile

    print("Path Safety Utilities Demo")
    print("=" * 50)

    # Test validate_relative_path
    test_paths = [
        "subdir/file.txt",
        "../etc/passwd",
        "../../etc/shadow",
        "/etc/passwd",
        "normal.txt",
        "a/b/c/d.txt",
    ]

    print("\nvalidate_relative_path() tests:")
    for path in test_paths:
        result = validate_relative_path(path)
        status = "SAFE" if result else "BLOCKED"
        print(f"  {path:30} -> {status}")

    # Test safe_join
    print("\nsafe_join() tests:")
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        print(f"  Base directory: {base}")

        safe_tests = ["configs/app.json", "shell/zshrc", "a/b/c.txt"]
        for rel in safe_tests:
            try:
                result = safe_join(base, rel)
                print(f"  safe_join(base, '{rel}') -> {result}")
            except PathTraversalError as e:
                print(f"  safe_join(base, '{rel}') -> ERROR: {e}")

        unsafe_tests = ["../etc/passwd", "../../root", "/etc/passwd"]
        for rel in unsafe_tests:
            try:
                result = safe_join(base, rel)
                print(f"  safe_join(base, '{rel}') -> {result}")
            except PathTraversalError as e:
                print(f"  safe_join(base, '{rel}') -> BLOCKED: {e}")

    # Test sanitize_path_component
    print("\nsanitize_path_component() tests:")
    test_names = [
        "My App",
        "../etc",
        "app/config",
        "Visual Studio Code",
        "...",
        "",
    ]
    for name in test_names:
        result = sanitize_path_component(name)
        print(f"  {name!r:30} -> {result!r}")

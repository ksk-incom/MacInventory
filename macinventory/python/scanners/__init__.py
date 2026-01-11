"""Scanner modules for discovering installed software and configurations.

Modules:
    applications: Scan /Applications and ~/Applications
    homebrew: Scan brew list, cask list, tap, and mas list
    version_managers: Scan pyenv, nvm, rbenv, asdf
    global_packages: Scan npm -g, pip, cargo, gem
    editors: Scan VS Code, Cursor, Zed extensions
    configs: Scan shell configs, git config
"""

from . import applications
from . import homebrew
from . import version_managers
from . import global_packages
from . import editors
from . import configs

__all__ = [
    "applications",
    "homebrew",
    "version_managers",
    "global_packages",
    "editors",
    "configs",
]

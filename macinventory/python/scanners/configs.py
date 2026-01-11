"""Scanner for shell configurations and git config.

Scans for shell dotfiles (zsh, bash, fish) and git configuration.
"""

import subprocess
from pathlib import Path
from typing import Optional


def _run_command(cmd: list[str], timeout: int = 30) -> Optional[str]:
    """Run a command and return its stdout, or None on failure.

    Args:
        cmd: Command and arguments as a list
        timeout: Timeout in seconds

    Returns:
        stdout as string, or None if command failed
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def scan_shell() -> dict:
    """Scan for shell configuration files.

    Returns:
        Dictionary with found shell config files and current shell info
    """
    result = {
        "current_shell": None,
        "configs": [],
        "frameworks": [],
        "errors": [],
    }

    home = Path.home()
    import os

    # Detect current shell from environment variable
    shell_env = os.environ.get("SHELL", "")
    if shell_env:
        result["current_shell"] = shell_env.split("/")[-1]

    # ZSH configuration files
    zsh_files = [
        (".zshrc", "ZSH run commands - main config file"),
        (".zprofile", "ZSH profile - login shell config"),
        (".zshenv", "ZSH environment - always sourced"),
        (".zlogin", "ZSH login - sourced after zprofile"),
        (".zlogout", "ZSH logout - sourced on logout"),
        (".zsh_history", "ZSH command history"),
    ]

    for filename, description in zsh_files:
        filepath = home / filename
        if filepath.exists():
            try:
                stat = filepath.stat()
                result["configs"].append(
                    {
                        "name": filename,
                        "path": str(filepath),
                        "shell": "zsh",
                        "description": description,
                        "size": stat.st_size,
                    }
                )
            except OSError:
                result["configs"].append(
                    {
                        "name": filename,
                        "path": str(filepath),
                        "shell": "zsh",
                        "description": description,
                    }
                )

    # Detect Oh My Zsh
    omz_dir = home / ".oh-my-zsh"
    if omz_dir.exists():
        framework_info: dict[str, str | list[str]] = {
            "name": "oh-my-zsh",
            "path": str(omz_dir),
        }
        # Check custom plugins/themes
        custom_dir = omz_dir / "custom"
        if custom_dir.exists():
            custom_plugins = list((custom_dir / "plugins").glob("*")) if (custom_dir / "plugins").exists() else []
            custom_themes = list((custom_dir / "themes").glob("*")) if (custom_dir / "themes").exists() else []
            framework_info["custom_plugins"] = [p.name for p in custom_plugins if p.is_dir()]
            framework_info["custom_themes"] = [t.name for t in custom_themes if t.is_file()]
        result["frameworks"].append(framework_info)

    # Detect Prezto (independent of Oh My Zsh)
    prezto_dir = home / ".zprezto"
    if prezto_dir.exists():
        result["frameworks"].append({
            "name": "prezto",
            "path": str(prezto_dir),
        })

    # Detect Zinit (check both legacy and XDG locations)
    zinit_locations = [
        home / ".zinit",
        home / ".local/share/zinit",
    ]
    for zinit_dir in zinit_locations:
        if zinit_dir.exists():
            result["frameworks"].append({
                "name": "zinit",
                "path": str(zinit_dir),
            })
            break  # Only add once

    # Detect Powerlevel10k (p10k)
    p10k_config = home / ".p10k.zsh"
    if p10k_config.exists():
        result["frameworks"].append({
            "name": "p10k",
            "path": str(p10k_config),
        })

    # Detect Fisher (Fish plugin manager)
    fisher_plugins = home / ".config/fish/fish_plugins"
    if fisher_plugins.exists():
        result["frameworks"].append({
            "name": "fisher",
            "path": str(fisher_plugins),
        })

    # Detect Oh My Fish
    omf_dir = home / ".config/omf"
    if omf_dir.exists():
        result["frameworks"].append({
            "name": "oh-my-fish",
            "path": str(omf_dir),
        })

    # Bash configuration files
    bash_files = [
        (".bashrc", "Bash run commands - interactive non-login shells"),
        (".bash_profile", "Bash profile - login shells"),
        (".bash_login", "Bash login - login shells (fallback)"),
        (".bash_logout", "Bash logout - sourced on logout"),
        (".profile", "Bourne shell profile - fallback for bash"),
        (".bash_history", "Bash command history"),
    ]

    for filename, description in bash_files:
        filepath = home / filename
        if filepath.exists():
            try:
                stat = filepath.stat()
                result["configs"].append(
                    {
                        "name": filename,
                        "path": str(filepath),
                        "shell": "bash",
                        "description": description,
                        "size": stat.st_size,
                    }
                )
            except OSError:
                result["configs"].append(
                    {
                        "name": filename,
                        "path": str(filepath),
                        "shell": "bash",
                        "description": description,
                    }
                )

    # Fish configuration
    fish_config_dir = home / ".config/fish"
    if fish_config_dir.exists():
        fish_files = [
            (fish_config_dir / "config.fish", "Fish main config"),
            (fish_config_dir / "fish_variables", "Fish universal variables"),
        ]

        for filepath, description in fish_files:
            if filepath.exists():
                try:
                    stat = filepath.stat()
                    result["configs"].append(
                        {
                            "name": filepath.name,
                            "path": str(filepath),
                            "shell": "fish",
                            "description": description,
                            "size": stat.st_size,
                        }
                    )
                except OSError:
                    result["configs"].append(
                        {
                            "name": filepath.name,
                            "path": str(filepath),
                            "shell": "fish",
                            "description": description,
                        }
                    )

        # Fish functions directory
        functions_dir = fish_config_dir / "functions"
        if functions_dir.exists():
            functions = list(functions_dir.glob("*.fish"))
            if functions:
                result["configs"].append(
                    {
                        "name": "functions/",
                        "path": str(functions_dir),
                        "shell": "fish",
                        "description": f"Fish functions directory ({len(functions)} functions)",
                        "count": len(functions),
                    }
                )

    # Common shell utilities (starship, etc.)
    starship_config = home / ".config/starship.toml"
    if starship_config.exists():
        # Keep in configs for backward compatibility
        result["configs"].append(
            {
                "name": "starship.toml",
                "path": str(starship_config),
                "shell": "all",
                "description": "Starship prompt configuration",
            }
        )
        # Also add to frameworks for proper backup via hints
        result["frameworks"].append({
            "name": "starship",
            "path": str(starship_config),
        })

    return result


def scan_git() -> dict:
    """Scan for git configuration.

    Returns:
        Dictionary with git config files and settings
    """
    result = {
        "installed": False,
        "configs": [],
        "user": None,
        "aliases": [],
        "errors": [],
    }

    # Check if git is installed
    version = _run_command(["git", "--version"])
    if version is None:
        return result

    result["installed"] = True
    result["version"] = version.replace("git version ", "")

    home = Path.home()

    # Git config files
    git_files = [
        (home / ".gitconfig", "Global git configuration"),
        (home / ".gitignore_global", "Global gitignore patterns"),
        (home / ".gitattributes_global", "Global gitattributes"),
        (home / ".git-credentials", "Git credentials (WARNING: may contain tokens)"),
    ]

    # XDG config location
    xdg_config = home / ".config/git"
    if xdg_config.exists():
        git_files.extend(
            [
                (xdg_config / "config", "XDG git configuration"),
                (xdg_config / "ignore", "XDG global gitignore"),
                (xdg_config / "attributes", "XDG global gitattributes"),
            ]
        )

    for filepath, description in git_files:
        if filepath.exists():
            try:
                stat = filepath.stat()
                config_entry = {
                    "name": filepath.name,
                    "path": str(filepath),
                    "description": description,
                    "size": stat.st_size,
                }
                # Mark sensitive files
                if "credentials" in filepath.name.lower():
                    config_entry["sensitive"] = True
                result["configs"].append(config_entry)
            except OSError:
                result["configs"].append(
                    {
                        "name": filepath.name,
                        "path": str(filepath),
                        "description": description,
                    }
                )

    # Get user info from git config
    user_name = _run_command(["git", "config", "--global", "user.name"])
    user_email = _run_command(["git", "config", "--global", "user.email"])
    if user_name or user_email:
        result["user"] = {
            "name": user_name,
            "email": user_email,
        }

    # Get aliases
    aliases_output = _run_command(["git", "config", "--global", "--get-regexp", "^alias\\."])
    if aliases_output:
        for line in aliases_output.split("\n"):
            if line.strip():
                parts = line.split(" ", 1)
                if len(parts) >= 2:
                    alias_name = parts[0].replace("alias.", "")
                    alias_value = parts[1]
                    result["aliases"].append(
                        {
                            "name": alias_name,
                            "command": alias_value,
                        }
                    )

    return result


def scan_ssh() -> dict:
    """Scan for SSH configuration (not private keys).

    Returns:
        Dictionary with SSH config info
    """
    result = {
        "config_exists": False,
        "config_path": None,
        "hosts": [],
        "errors": [],
    }

    ssh_dir = Path.home() / ".ssh"
    if not ssh_dir.exists():
        return result

    # SSH config file
    config_file = ssh_dir / "config"
    if config_file.exists():
        result["config_exists"] = True
        result["config_path"] = str(config_file)

        # Parse hosts from config (just host names, not full config)
        try:
            content = config_file.read_text()
            for line in content.split("\n"):
                line = line.strip()
                if line.lower().startswith("host ") and not line.startswith("Host *"):
                    host = line.split()[1] if len(line.split()) > 1 else None
                    if host and not host.startswith("#"):
                        result["hosts"].append(host)
        except OSError as e:
            result["errors"].append({"error": f"Could not read SSH config: {e}"})

    # Note about keys (we don't backup them, just note they exist)
    key_patterns = ["id_rsa", "id_ed25519", "id_ecdsa", "id_dsa"]
    keys_found = []
    for pattern in key_patterns:
        key_file = ssh_dir / pattern
        if key_file.exists():
            keys_found.append(pattern)

    if keys_found:
        result["keys_present"] = keys_found
        result["key_warning"] = "Private keys found but NOT backed up for security"

    return result


def scan_misc_dotfiles() -> dict:
    """Scan for other common dotfiles.

    Returns:
        Dictionary with misc dotfile info
    """
    result = {
        "files": [],
        "errors": [],
    }

    home = Path.home()

    # Common dotfiles to check
    dotfiles = [
        (".inputrc", "Readline configuration"),
        (".editorconfig", "EditorConfig settings"),
        (".curlrc", "cURL defaults"),
        (".wgetrc", "Wget defaults"),
        (".hushlogin", "Suppress login message"),
        (".npmrc", "NPM configuration (may contain tokens)"),
        (".yarnrc", "Yarn v1 configuration"),
        (".yarnrc.yml", "Yarn v2+ configuration"),
        (".gemrc", "RubyGems configuration"),
        (".pylintrc", "Pylint configuration"),
        (".flake8", "Flake8 configuration"),
        (".prettierrc", "Prettier configuration"),
        (".prettierrc.json", "Prettier configuration (JSON)"),
        (".eslintrc", "ESLint configuration"),
        (".eslintrc.json", "ESLint configuration (JSON)"),
        (".tmux.conf", "Tmux configuration"),
        (".screenrc", "Screen configuration"),
        (".vimrc", "Vim configuration"),
        (".nanorc", "Nano configuration"),
    ]

    for filename, description in dotfiles:
        filepath = home / filename
        if filepath.exists():
            try:
                stat = filepath.stat()
                file_entry = {
                    "name": filename,
                    "path": str(filepath),
                    "description": description,
                    "size": stat.st_size,
                }
                # Mark potentially sensitive files
                if any(x in filename.lower() for x in ["npm", "gem", "pypi"]):
                    file_entry["potentially_sensitive"] = True
                result["files"].append(file_entry)
            except OSError:
                result["files"].append(
                    {
                        "name": filename,
                        "path": str(filepath),
                        "description": description,
                    }
                )

    return result


def scan() -> dict:
    """Scan all shell and system configurations.

    Returns:
        Dictionary with all config scan results
    """
    shell_result = scan_shell()
    git_result = scan_git()
    ssh_result = scan_ssh()
    misc_result = scan_misc_dotfiles()

    return {
        "shell": {
            "current_shell": shell_result["current_shell"],
            "configs": shell_result["configs"],
            "configs_count": len(shell_result["configs"]),
            "frameworks": shell_result.get("frameworks", []),
            # Backward compat: provide first framework as "framework" (or None)
            "framework": shell_result.get("frameworks", [None])[0] if shell_result.get("frameworks") else None,
            "errors": shell_result["errors"],
        },
        "git": {
            "installed": git_result["installed"],
            "version": git_result.get("version"),
            "configs": git_result["configs"],
            "configs_count": len(git_result["configs"]),
            "user": git_result["user"],
            "aliases": git_result["aliases"],
            "aliases_count": len(git_result["aliases"]),
            "errors": git_result["errors"],
        },
        "ssh": {
            "config_exists": ssh_result["config_exists"],
            "config_path": ssh_result["config_path"],
            "hosts": ssh_result["hosts"],
            "hosts_count": len(ssh_result["hosts"]),
            "keys_present": ssh_result.get("keys_present", []),
            "key_warning": ssh_result.get("key_warning"),
            "errors": ssh_result["errors"],
        },
        "misc_dotfiles": {
            "files": misc_result["files"],
            "files_count": len(misc_result["files"]),
            "errors": misc_result["errors"],
        },
    }


if __name__ == "__main__":
    import json

    result = scan()
    print(json.dumps(result, indent=2))

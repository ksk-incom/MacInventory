"""Output generation modules for creating inventory artifacts.

Modules:
    structure: Create output directory structure
    bundles: Generate Brewfile, NPM, pip, cargo bundle files
    state: Generate state.yaml inventory file
"""

from .structure import (
    OutputStructure,
    create_output_directory,
    get_output_paths,
    get_system_info,
    validate_output_structure,
)
from .bundles import (
    generate_brewfile,
    generate_mas_file,
    generate_npm_file,
    generate_pip_file,
    generate_pipx_file,
    generate_cargo_file,
    generate_gem_file,
    generate_go_file,
    generate_vscode_extensions_file,
    generate_cursor_extensions_file,
    generate_zed_extensions_file,
    generate_python_versions_file,
    generate_node_versions_file,
    generate_ruby_versions_file,
    generate_asdf_versions_file,
    generate_all_bundles,
)
from .state import (
    generate_state,
    load_state,
    compare_states,
    MACINVENTORY_VERSION,
)

__all__ = [
    # structure
    "OutputStructure",
    "create_output_directory",
    "get_output_paths",
    "get_system_info",
    "validate_output_structure",
    # bundles
    "generate_brewfile",
    "generate_mas_file",
    "generate_npm_file",
    "generate_pip_file",
    "generate_pipx_file",
    "generate_cargo_file",
    "generate_gem_file",
    "generate_go_file",
    "generate_vscode_extensions_file",
    "generate_cursor_extensions_file",
    "generate_zed_extensions_file",
    "generate_python_versions_file",
    "generate_node_versions_file",
    "generate_ruby_versions_file",
    "generate_asdf_versions_file",
    "generate_all_bundles",
    # state
    "generate_state",
    "load_state",
    "compare_states",
    "MACINVENTORY_VERSION",
]

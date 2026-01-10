# Outstanding Tasks
These are mockups and notes around creating the simulated file system.

### Unless explicitly told to use these files, do not use them or index them.


- [Simulated Filesystem Format](plans\to-do\plan-pseudo-tty-filesystem-formatting\virtualtermnal.md)

- [Fields in FS](plans\to-do\pfs-data-addons\pseudo-filesystem-fields.md)

- [Sample JSON](plans\to-do\pfs-data-addons\file-contents.json)
    - is this still relevant?
    - **Caution: may be obsolete, ask first!**
- [Output](plans\to-do\plan-pseudo-tty-filesystem-formatting\raw-text-output\krafton-jungle.files.txt) from the [standalone file listing script](app\modules\enumerate\list_dockerhub_container_files.py) used for development and testing.
    - standalone script is only meant to be used to generate independant results verifications during development, not for production use.

    ![alttext](imageLink)

These standards MUST be followed for every subtask:

### 1. Module Size Limit
- **Maximum 100 lines of code per file**
- If code exceeds 100 lines, split into submodules
- Each module should have a single, clear responsibility

### 2. Project Structure Alignment
- New code MUST be organized into subfolders matching existing project structure
- Follow the established pattern: `app/core/`, `app/ui/`, `app/modules/`
- UI components go in `app/ui/` with appropriate subfolders (`commands/`, `widgets/`, etc.)

### 3. Textual Documentation Access
- **All agents have access to `textual-mcp`** for Textual framework documentation
- Use `mcp--textual-mcp--search_textual_documentation` to look up Textual patterns
- Use `mcp--textual-mcp--search_textual_code` to find code examples
- Consult documentation before implementing any Textual-specific features

### 4. Clean Code Principles
- Clear, descriptive function and variable names
- Type hints on all function signatures
- Docstrings for all classes and public methods
- Imports organized: stdlib, third-party, local

### 5. No Emoji or "special" characters
- Emojis and similar characters break cross compatibility
# Code Style Guide

## IMPORTANT: Coding Standards for All Tasks

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

---

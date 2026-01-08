"""
Filesystem utilities for organizing tar entries by directory.

Provides directory filtering and ls -la style formatting for the
virtual filesystem browser.

Also includes merge_layer_entries() for Layer Slayer mode to combine
entries from all layers into a single virtual filesystem.
"""

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from src.api.layerslayer.parser import TarEntry

if TYPE_CHECKING:
    from src.api.layerslayer.fetcher import LayerPeekResult


@dataclass
class DirectoryListing:
    """Contents of a single directory."""
    path: str                         # Current path (e.g., "/etc/")
    parent: Optional[str]             # Parent path (None if root)
    entries: list[TarEntry]           # Direct children only


def get_directory_contents(
    all_entries: list[TarEntry],
    current_path: str = "/"
) -> DirectoryListing:
    """
    Filter entries to show only direct children of current_path.
    
    Args:
        all_entries: All tar entries from layer peek
        current_path: Directory to list (e.g., "/" or "/etc/")
    
    Returns:
        DirectoryListing with filtered and sorted entries
    
    Example:
        If current_path is "/etc/" and entries contains:
        - etc/passwd
        - etc/shadow
        - etc/ssl/certs/ca.pem
        - etc/ssl/
        
        Returns only: etc/passwd, etc/shadow, etc/ssl/
        (not the nested certs/ca.pem)
    """
    # Normalize path - ensure it ends with /
    if not current_path.endswith("/"):
        current_path += "/"
    
    # For root, prefix is empty; otherwise strip leading /
    if current_path == "/":
        prefix = ""
    else:
        prefix = current_path.lstrip("/")
    
    children = []
    seen_names = set()
    
    for entry in all_entries:
        name = entry.name
        
        # Skip entries not under current path
        if prefix and not name.startswith(prefix):
            continue
        
        # Get relative path from current directory
        relative = name[len(prefix):]
        if not relative:
            continue  # Skip the directory itself
        
        # Check if direct child (no more slashes except trailing)
        # e.g., "passwd" or "ssl/" but not "ssl/certs"
        relative_stripped = relative.rstrip("/")
        if "/" in relative_stripped:
            continue  # Nested entry, skip it
        
        # Avoid duplicates (directories might appear multiple times)
        base_name = relative_stripped
        if base_name not in seen_names:
            children.append(entry)
            seen_names.add(base_name)
    
    # Sort: directories first, then alphabetically (case-insensitive)
    children.sort(key=lambda e: (
        0 if e.is_dir else 1,  # dirs first
        e.name.lower()
    ))
    
    # Calculate parent path
    parent = None
    if current_path != "/":
        # Split path and remove last component
        parts = current_path.rstrip("/").split("/")
        if len(parts) > 1:
            parent = "/".join(parts[:-1]) + "/"
        else:
            parent = "/"
    
    return DirectoryListing(
        path=current_path,
        parent=parent,
        entries=children
    )


def format_ls_line(entry: TarEntry) -> str:
    """
    Format a single entry as an ls -la style line.
    
    Matches the exact format from the plan:
        drwxr-xr-x 0/0               0 2024-10-21 14:28 etc/
        -rw-r--r-- 0/0           75113 2023-07-12 13:08 mime.types
        lrwxrwxrwx 0/0               0 2024-04-22 13:08 lib -> usr/lib
    
    Format breakdown:
        {perms:10} {uid}/{gid:<4} {size:>15} {mtime:16} {name}
    
    Args:
        entry: TarEntry to format
    
    Returns:
        Formatted line string
    """
    # Get just the filename (last component)
    name = entry.name.rstrip("/").split("/")[-1]
    
    # Add trailing slash for directories
    if entry.is_dir:
        name += "/"
    
    # Add symlink target
    if entry.is_symlink and entry.linkname:
        name += f" -> {entry.linkname}"
    
    # Format uid/gid as "uid/gid"
    uid_gid = f"{entry.uid}/{entry.gid}"
    
    # Format the line with proper alignment
    # perms(10) + space + uid/gid(variable, left-pad to ~5) + size(right-align 15) + space + date(16) + space + name
    return f"{entry.mode:10} {uid_gid:<5} {entry.size:>15} {entry.mtime:16} {name}"


def format_parent_entry() -> str:
    """
    Format the parent directory entry (../).
    
    Returns:
        Formatted line for parent directory navigation
    """
    return "drwxr-xr-x 0/0               0 ----.--.-- --:-- ../"


def get_entry_basename(entry: TarEntry) -> str:
    """
    Get the base filename from a TarEntry.
    
    Args:
        entry: TarEntry to extract name from
    
    Returns:
        Just the filename without path, with trailing / for directories
    """
    name = entry.name.rstrip("/").split("/")[-1]
    if entry.is_dir:
        name += "/"
    return name


# =============================================================================
# Layer Slayer: Merge entries from all layers
# =============================================================================


def merge_layer_entries(layer_results: list["LayerPeekResult"]) -> list[TarEntry]:
    """
    Merge entries from all layers into a single virtual filesystem.
    
    Docker layer behavior:
    - Later layers override earlier layers (same path = replacement)
    - Whiteout files (.wh.filename) delete entries from earlier layers
    - Opaque whiteouts (.wh..wh..opq) hide entire directories
    
    Args:
        layer_results: List of LayerPeekResult in layer order (base layer first)
        
    Returns:
        Merged list of TarEntry representing the final filesystem
    """
    # Use dict to track entries by normalized path (later layers override)
    entries_by_path: dict[str, TarEntry] = {}
    deleted_paths: set[str] = set()
    opaque_dirs: set[str] = set()
    
    for result in layer_results:
        if result.error:
            continue
            
        for entry in result.entries:
            name = entry.name.rstrip("/")
            
            # Handle whiteout files (Docker AUFS/OverlayFS deletion markers)
            if "/.wh." in f"/{name}" or name.startswith(".wh."):
                # Extract the path being deleted
                parts = name.rsplit("/", 1)
                if len(parts) == 2:
                    parent, filename = parts
                    if filename == ".wh..wh..opq":
                        # Opaque whiteout - hide entire parent directory contents
                        opaque_dirs.add(parent)
                    elif filename.startswith(".wh."):
                        # Single file whiteout
                        deleted_file = filename[4:]  # Remove ".wh." prefix
                        deleted_paths.add(f"{parent}/{deleted_file}")
                else:
                    # Whiteout at root level
                    if name == ".wh..wh..opq":
                        opaque_dirs.add("")
                    elif name.startswith(".wh."):
                        deleted_paths.add(name[4:])
                continue  # Don't add whiteout entries to filesystem
            
            # Check if this entry is in an opaque directory
            # (earlier layer contents should be hidden)
            in_opaque = False
            for opaque_dir in opaque_dirs:
                if opaque_dir and name.startswith(f"{opaque_dir}/"):
                    in_opaque = True
                    break
            
            # Later layer entries override earlier ones
            entries_by_path[name] = entry
    
    # Remove deleted entries
    for deleted in deleted_paths:
        entries_by_path.pop(deleted, None)
    
    # Convert back to list and sort
    merged = list(entries_by_path.values())
    merged.sort(key=lambda e: e.name.lower())
    
    return merged

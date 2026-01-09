"""Table formatting utilities for search results."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from app.core.utils.formatters import abbreviate_arch, abbreviate_os, format_date


def format_count(count: Any) -> str:
    """Format large numbers with K/M/B suffix.
    
    Args:
        count: The number to format.
        
    Returns:
        Formatted string with appropriate suffix.
    """
    if count is None:
        return "-"
    # Convert string to int if needed
    if isinstance(count, str):
        try:
            count = int(count)
        except ValueError:
            return count
    if count >= 1_000_000_000:
        return f"{count / 1_000_000_000:.1f}B"
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    if count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)


def format_table_row(result: Dict[str, Any], index: int) -> Tuple[str, ...]:
    """Format a single result as a table row tuple.
    
    Args:
        result: Dictionary containing result data.
        index: Row number (1-based) for label.
        
    Returns:
        Tuple of (label, name, pulls, stars, updated, os, arch, description).
    """
    name = result.get("name", "")
    pull_count = result.get("pull_count", 0) or 0
    star_count = result.get("star_count", 0) or 0
    updated_at = result.get("updated_at", "")
    os_list = result.get("operating_systems", []) or []
    arch_list = result.get("architectures", []) or []
    description = result.get("short_description", "") or ""

    # Format values
    pulls_str = format_count(pull_count)
    stars_str = str(star_count)
    updated_str = format_date(updated_at) if updated_at else "N/A"
    os_str = abbreviate_os(os_list)
    arch_str = abbreviate_arch(arch_list)
    
    # Truncate description if very long (but no-wrap in table)
    max_desc_len = 100
    if len(description) > max_desc_len:
        description = description[:max_desc_len - 3] + "..."

    return (
        str(index),  # Label (1-based)
        name,  # Name
        pulls_str,  # Pulls
        stars_str,  # Stars
        updated_str,  # Updated
        os_str,  # OS
        arch_str,  # Arch
        description,  # Description
    )

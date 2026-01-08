"""
Data formatting utilities for docker-dorker.

Pure functions for formatting search result data for display.
No UI dependencies - can be easily tested and reused.
"""

from datetime import datetime
from typing import Any, Dict, List, Tuple

def format_date(iso_date: str, fmt: str = "%m-%d-%Y") -> str:
    """
    Format ISO date string to display format.

    Args:
        iso_date: ISO 8601 date string (e.g., "2024-01-15T10:30:00Z")
        fmt: Output format string (default: MM-DD-YYYY, US standard)

    Returns:
        Formatted date string or empty string if parsing fails

    Examples:
        >>> format_date("2024-01-15T10:30:00Z")
        '01-15-2024'
    """
    if not iso_date:
        return ""
    try:
        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        return dt.strftime(fmt)
    except (ValueError, TypeError):
        # Fallback: return full date string
        return iso_date if iso_date else ""


def abbreviate_os(os_list: List[str]) -> str:
    """
    Get first OS name.

    Args:
        os_list: List of operating system names

    Returns:
        OS name or empty string

    Examples:
        >>> abbreviate_os(["linux", "windows"])
        'linux'
        >>> abbreviate_os([])
        ''
    """
    if not os_list:
        return ""
    return os_list[0]


def abbreviate_arch(arch_list: List[str]) -> str:
    """
    Get first architecture with common abbreviations.

    Args:
        arch_list: List of architecture names

    Returns:
        Abbreviated architecture name

    Examples:
        >>> abbreviate_arch(["amd64", "arm64"])
        'x64'
        >>> abbreviate_arch(["arm64"])
        'arm'
        >>> abbreviate_arch([])
        'unk'
    """
    if not arch_list:
        return "unk"
    arch = arch_list[0]
    if arch == "amd64":
        return "x64"
    elif arch == "arm64":
        return "arm"
    else:
        return arch


def format_result_row(result: Dict[str, Any], index: int) -> Tuple[str, ...]:
    """
    Format a single search result into a table row tuple.

    Args:
        result: Dictionary containing search result data
        index: Row index number (1-based)

    Returns:
        Tuple of formatted strings for table :
        (idx, name, pulls, stars, updated, os, arch, os_count, arch_count, description)
    """
    return (
        str(index),
        result.get("name", ""),
        str(result.get("pull_count", 0)),
        str(result.get("star_count", 0)),
        format_date(result.get("updated_at", "")),
        abbreviate_os(result.get("operating_systems", [])),
        abbreviate_arch(result.get("architectures", [])),
        str(result.get("os_count", 0)),
        str(result.get("architecture_count", 0)),
        result.get("short_description", ""),
    )

# TODO this logic is fucked and seems like a forbidden "magic numbers"
def empty_row() -> Tuple[str, ...]:
    """
    Create an empty row tuple for table padding.

    Returns:
        Tuple of 10 empty strings matching table width
    """
    return ("", "", "", "", "", "", "", "", "", "")

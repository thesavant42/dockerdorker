"""Formatting utilities for result details."""

from __future__ import annotations

from typing import Any


def format_count(count: int) -> str:
    """Format large numbers with K/M/B suffix.
    
    Args:
        count: The number to format.
        
    Returns:
        Formatted string with appropriate suffix.
    """
    if count >= 1_000_000_000:
        return f"{count / 1_000_000_000:.1f}B"
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    if count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)


def format_date(date_val: Any) -> str:
    """Format a date value for display.
    
    Args:
        date_val: Date value (string or datetime-like).
        
    Returns:
        Formatted date string or 'N/A' if invalid.
    """
    if not date_val or date_val == "N/A":
        return "N/A"
    date_str = str(date_val)
    if "T" in date_str:
        return date_str.split("T")[0]
    return date_str[:10]

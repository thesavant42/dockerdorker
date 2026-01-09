"""Card formatting utilities for search results."""

from __future__ import annotations

from typing import Any, Dict

from rich.console import RenderableType
from rich.text import Text


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


def format_card(result: Dict[str, Any]) -> RenderableType:
    """Format a single result as a Rich Text card.
    
    Args:
        result: Dictionary containing result data with keys:
            - name: Repository name
            - publisher: Publisher/owner name
            - updated_at: Last update timestamp
            - star_count: Number of stars
            - pull_count: Number of pulls
            - short_description: Brief description
            
    Returns:
        Rich Text object formatted as a card.
    """
    name = result.get("name", "unknown")
    publisher = result.get("publisher", "")
    updated_at = result.get("updated_at", "")
    star_count = result.get("star_count", 0) or 0
    pull_count = result.get("pull_count", 0) or 0
    description = result.get("short_description", "") or ""

    # Format display name
    if publisher and publisher != name.split("/")[0]:
        display_name = f"{publisher}/{name}"
    else:
        display_name = name

    # Format date (extract just the date part)
    if updated_at and "T" in str(updated_at):
        date_str = str(updated_at).split("T")[0]
    else:
        date_str = str(updated_at)[:10] if updated_at else "N/A"

    # Format pull count with K/M/B suffix
    pulls_str = format_count(pull_count)

    # Truncate description
    max_desc_len = 35
    if len(description) > max_desc_len:
        description = description[: max_desc_len - 3] + "..."

    # Build the card text
    card = Text()
    card.append(display_name[:25], style="bold cyan")  # Row 1: name
    card.append("\n")
    card.append(f"Updated: {date_str}", style="dim")  # Row 2: date
    card.append("\n")
    card.append(f"* {star_count} ", style="yellow")  # Row 3: stats
    card.append(f"Pulls: {pulls_str}", style="green")
    card.append("\n")
    card.append(description, style="italic dim")  # Row 4: description

    return card

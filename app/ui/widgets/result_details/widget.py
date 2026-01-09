"""Result details widget for the main panel."""

from __future__ import annotations

from typing import Any, Dict, Optional

from rich.console import RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.widgets import Static

from app.ui.widgets.result_details.formatters import format_count, format_date


class ResultDetailsWidget(Static):
    """Displays detailed information about a selected Docker Hub result."""

    DEFAULT_MESSAGE = "Select a search result to view details"

    def __init__(self, **kwargs) -> None:
        """Initialize the result details widget."""
        super().__init__(self.DEFAULT_MESSAGE, **kwargs)
        self._result: Optional[Dict[str, Any]] = None
        self._status_text: str = ""

    def show_result(self, result: Dict[str, Any]) -> None:
        """Display details for the given result.
        
        Args:
            result: Dictionary containing result data.
        """
        self._result = result
        self.update(self._format_details(result))

    def clear_result(self) -> None:
        """Clear the displayed result."""
        self._result = None
        self.update(self.DEFAULT_MESSAGE)

    def set_status(self, text: str) -> None:
        """Update the status text displayed in the panel.
        
        Args:
            text: Status message to display.
        """
        self._status_text = text
        if self._result:
            self.update(self._format_details(self._result))

    def _format_details(self, result: Dict[str, Any]) -> RenderableType:
        """Format result details as a Rich renderable.
        
        Args:
            result: Dictionary containing result data.
            
        Returns:
            Rich Panel with formatted details.
        """
        name = result.get("name", "unknown")
        publisher = result.get("publisher", "")
        updated_at = result.get("updated_at", "N/A")
        created_at = result.get("created_at", "N/A")
        
        # Convert string values to int (API returns strings)
        def to_int(val: Any, default: int = 0) -> int:
            """Convert value to int, handling strings from API."""
            if val is None:
                return default
            if isinstance(val, int):
                return val
            if isinstance(val, str):
                try:
                    # Try to convert string to int (strip whitespace, handle empty)
                    return int(float(val.strip())) if val.strip() else default
                except (ValueError, AttributeError):
                    return default
            if isinstance(val, (float, complex)):
                return int(val)
            return default
        
        star_count = to_int(result.get("star_count"), 0)
        pull_count = to_int(result.get("pull_count"), 0)
        description = result.get("short_description", "") or "No description"
        os_list = result.get("operating_systems", []) or []
        arch_list = result.get("architectures", []) or []

        # Construct slug from publisher/name to avoid API slug issues
        slug = f"{publisher}/{name}" if publisher else name
        display_name = slug
        table = self._build_info_table(
            display_name, slug, publisher, star_count, pull_count,
            created_at, updated_at, os_list, arch_list
        )

        content = Text()
        content.append("Description: ", style="bold")
        content.append(description, style="italic")
        content.append("\n\n")
        content.append_text(self._table_to_text(table))
        
        if self._status_text:
            content.append("\n\n")
            content.append("Status: ", style="bold")
            content.append(self._status_text, style="green")

        return Panel(
            content,
            subtitle=f"[bold]{slug}[/bold]",
            subtitle_align="center",
            border_style="cyan",
        )

    def _build_info_table(
        self, display_name: str, slug: str, publisher: str,
        star_count: int, pull_count: int, created_at: Any,
        updated_at: Any, os_list: list, arch_list: list
    ) -> Table:
        """Build the info table for result details."""
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Field", style="bold")
        table.add_column("Value")

        table.add_row("Repository", Text(display_name, style="bold cyan"))
        table.add_row("Slug", slug)
        table.add_row("Publisher", publisher or "N/A")
        table.add_row("", "")
        table.add_row("Stars", Text(str(star_count), style="yellow"))
        table.add_row("Pulls", Text(format_count(pull_count), style="green"))
        table.add_row("", "")
        table.add_row("Created", format_date(created_at))
        table.add_row("Updated", format_date(updated_at))

        if os_list:
            table.add_row("", "")
            table.add_row("OS", ", ".join(os_list[:5]))
        if arch_list:
            table.add_row("Arch", ", ".join(arch_list[:5]))

        return table

    def _table_to_text(self, table: Table) -> Text:
        """Convert a Rich Table to Text for embedding in Panel."""
        from io import StringIO
        from rich.console import Console

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=60)
        console.print(table)
        return Text.from_ansi(string_io.getvalue())

"""Search results table widget."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from textual.widgets import DataTable

from app.ui.widgets.search_results.formatters import format_table_row

class SearchResultsWidget(DataTable):
    """A DataTable displaying Docker Hub search results with labeled rows."""

    def __init__(self, **kwargs) -> None:
        """Initialize the search results widget."""
        super().__init__(
            show_header=True,
            cursor_type="row",
            zebra_stripes=True,
            **kwargs,
        )
        self._results: List[Dict[str, Any]] = []
        self._current_page = 1
        self._total_pages = 1
        self._query = ""

    def on_mount(self) -> None:
        """Set up the table columns on mount."""
        self.add_column("Name", key="name", width=30)
        self.add_column("Pulls", key="pulls", width=6)
        self.add_column("Stars", key="stars", width=5)
        self.add_column("Updated", key="updated", width=10)
        self.add_column("OS", key="os", width=6)
        self.add_column("Arch", key="arch", width=5)
        self.add_column("Description", key="description", width=30)

    def load_results(
        self,
        results: List[Dict[str, Any]],
        query: str,
        page: int = 1,
        total_pages: int = 1,
    ) -> None:
        """Load search results into the table.
        
        Args:
            results: List of result dictionaries from search.
            query: The search query string.
            page: Current page number.
            total_pages: Total number of pages.
        """
        self._results = results
        self._query = query
        self._current_page = page
        self._total_pages = total_pages
        self._populate_table()

    def _populate_table(self) -> None:
        """Populate the DataTable with search results as rows."""
        self.clear()

        if not self._results:
            return

        for idx, result in enumerate(self._results, start=1):
            row_data = format_table_row(result, idx)
            # Use result index as row key for easy lookup
            self.add_row(
                *row_data[1:],  # Skip label (first element), it's passed separately
                key=str(idx - 1),  # 0-based index for lookup
                label=str(idx),  # 1-based label for display
            )
        
        # Focus the table and update top panel with first row
        if self._results:
            self.focus()
            self.call_later(self._update_top_panel)

    def get_selected_result(self) -> Optional[Dict[str, Any]]:
        """Get the currently selected result data.
        
        Returns:
            The result dictionary for the selected row, or None.
        """
        if not self._results:
            return None

        try:
            # Get row key from cursor coordinate
            row_key, _ = self.coordinate_to_cell_key(self.cursor_coordinate)
            
            # Convert row key to index (row keys are 0-based string indices)
            result_index = int(row_key)
            if 0 <= result_index < len(self._results):
                return self._results[result_index]
        except (ValueError, TypeError, Exception):
            # If coordinate lookup fails, try using row index directly
            try:
                row_index = self.cursor_coordinate.row
                if 0 <= row_index < len(self._results):
                    return self._results[row_index]
            except Exception:
                pass
        
        return None

    @property
    def page_info(self) -> str:
        """Return current page info string: 'Page X/YYY'.""" """Don't think this works? pagination is not relevant"""
        return f"Page {self._current_page:3d}/{self._total_pages:3d}"

    def _update_top_panel(self) -> None:
        """Update top panel with currently selected result."""
        from app.ui.messages import RowHighlighted
        
        if not self._results or self.row_count == 0:
            return
        
        try:
            selected = self.get_selected_result()
            if selected:
                self.post_message(RowHighlighted(result=selected))
        except Exception:
            # Silently fail if we can't get the result
            pass

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Handle row highlight to update top panel."""
        self._update_top_panel()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection (Enter key) to trigger tag enumeration."""
        from app.ui.messages import EnumerateTagsRequested
        
        # Update top panel first
        self._update_top_panel()
        
        # Then trigger tag enumeration
        selected = self.get_selected_result()
        if selected:
            # Extract namespace/repo from slug or name
            slug = selected.get("slug", selected.get("name", ""))
            if "/" in slug:
                parts = slug.split("/", 1)
                namespace = parts[0]
                repo = parts[1] if len(parts) > 1 else ""
                if namespace and repo:
                    self.post_message(EnumerateTagsRequested(namespace=namespace, repo=repo))

    def on_key(self, event) -> None:
        """Handle key presses to update top panel on arrow key movement."""
        # Update top panel after arrow key navigation
        if event.key in ("up", "down", "pageup", "pagedown", "home", "end"):
            # Schedule update after the key event is processed
            self.call_later(self._update_top_panel)

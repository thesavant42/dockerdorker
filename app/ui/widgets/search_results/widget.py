"""Search results grid widget."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from rich.text import Text
from textual.widgets import DataTable

from app.ui.widgets.search_results.formatters import format_card


class SearchResultsWidget(DataTable):
    """A 4-column grid displaying Docker Hub search results as cards."""

    COLUMNS = 4  # Number of cards per row

    def __init__(self, **kwargs) -> None:
        """Initialize the search results widget."""
        super().__init__(
            show_header=False,
            cursor_type="cell",
            zebra_stripes=False,
            **kwargs,
        )
        self._results: List[Dict[str, Any]] = []
        self._current_page = 1
        self._total_pages = 1
        self._query = ""

    def on_mount(self) -> None:
        """Set up the table columns on mount."""
        for i in range(self.COLUMNS):
            self.add_column(f"col{i}", width=None)

    def load_results(
        self,
        results: List[Dict[str, Any]],
        query: str,
        page: int = 1,
        total_pages: int = 1,
    ) -> None:
        """Load search results into the grid.
        
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
        self._populate_grid()

    def _populate_grid(self) -> None:
        """Populate the DataTable with result cards."""
        self.clear()

        if not self._results:
            return

        # Group results into rows of 4
        for i in range(0, len(self._results), self.COLUMNS):
            row_results = self._results[i : i + self.COLUMNS]
            row_cells = []

            for result in row_results:
                card = format_card(result)
                row_cells.append(card)

            # Pad with empty cells if row is incomplete
            while len(row_cells) < self.COLUMNS:
                row_cells.append(Text(""))

            self.add_row(*row_cells, key=f"row_{i}")

    def get_selected_result(self) -> Optional[Dict[str, Any]]:
        """Get the currently selected result data.
        
        Returns:
            The result dictionary for the selected cell, or None.
        """
        if not self._results:
            return None

        coord = self.cursor_coordinate
        result_index = (coord.row * self.COLUMNS) + coord.column

        if 0 <= result_index < len(self._results):
            return self._results[result_index]
        return None

    @property
    def page_info(self) -> str:
        """Return current page info string: 'Page X/YYY'."""
        return f"Page {self._current_page:3d}/{self._total_pages:3d}"

"""Search results grid widget."""

from __future__ import annotations

from math import ceil
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
            self.add_column(f"col{i}", width=25%)

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
        """Populate the DataTable with result cards in column-first order.
        
        Results flow top-to-bottom within each column, then left-to-right:
        Column 1: 1, 2, 3, 4
        Column 2: 5, 6, 7, 8
        Column 3: 9, 10, 11, 12
        Column 4: 13, 14, 15, 16
        
        All columns scroll together as a synchronized slab.
        """
        self.clear()

        if not self._results:
            return

        # Calculate items per column for column-first distribution
        items_per_column = ceil(len(self._results) / self.COLUMNS)
        
        # Build rows by taking one item from each column position
        for row_idx in range(items_per_column):
            row_cells = []
            
            for col_idx in range(self.COLUMNS):
                # Column-first index: col * items_per_column + row
                result_idx = col_idx * items_per_column + row_idx
                
                if result_idx < len(self._results):
                    card = format_card(self._results[result_idx])
                    row_cells.append(card)
                else:
                    row_cells.append(Text(""))
            
            self.add_row(*row_cells, key=f"row_{row_idx}")

    def get_selected_result(self) -> Optional[Dict[str, Any]]:
        """Get the currently selected result data.
        
        Uses column-first indexing to match _populate_grid layout.
        
        Returns:
            The result dictionary for the selected cell, or None.
        """
        if not self._results:
            return None

        coord = self.cursor_coordinate
        items_per_column = ceil(len(self._results) / self.COLUMNS)
        
        # Column-first index calculation
        result_index = coord.column * items_per_column + coord.row

        if 0 <= result_index < len(self._results):
            return self._results[result_index]
        return None

    @property
    def page_info(self) -> str:
        """Return current page info string: 'Page X/YYY'."""
        return f"Page {self._current_page:3d}/{self._total_pages:3d}"

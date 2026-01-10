"""
Search results screen for docker-dorker.

Displays search results in a DataTable with built-in navigation.
"""

from typing import Any, Dict, Optional

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Header, Static, DataTable

from src import keys
from src.utils.formatters import format_result_row


class SearchResultsScreen(Screen):
    """
    Screen showing search results in a DataTable.

    Uses DataTable's built-in navigation (arrows, page-up/down, home/end).
    """

    BINDINGS = [keys.ENTER, keys.BACK]

    # Table column definitions
    COLUMNS = ("#", "Repository Name", "Pulls", "Stars", "Updated", "OS", "Arch", "OS#", "Arch#", "Description")

    def __init__(self, results: Dict[str, Any], query: str):
        """
        Initialize search screen with results.

        Args:
            results: Dictionary with 'total', 'results' list, etc.
            query: Search query string
        """
        super().__init__()
        self.results = results
        self.search_query = query

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()
        yield Static(self._get_info_text(), id="search-info")
        yield DataTable(
            id="results-table",
            cursor_type="row",
            zebra_stripes=True,
        )
        yield Footer()

    def on_mount(self) -> None:
        """Called when screen is mounted - populate DataTable."""
        table = self.query_one("#results-table", DataTable)
        for column in self.COLUMNS:
            table.add_column(column)
        self._populate_results()
        table.focus()

    def _get_info_text(self) -> str:
        """Generate information text."""
        total = self.results.get("total", 0)
        loaded = len(self.results.get("results", []))
        return f"Search: '{self.search_query}' | Showing {loaded} of {total} results"

    def _populate_results(self) -> None:
        """Populate the DataTable with all results."""
        table = self.query_one("#results-table", DataTable)
        table.clear()

        results_list = self.results.get("results", [])
        for row_index, result in enumerate(results_list, start=1):
            row_data = format_result_row(result, row_index)
            table.add_row(*row_data, key=f"row_{row_index}")

    def action_go_back(self) -> None:
        """Go back to the search screen."""
        self.app.pop_screen()

    def _get_selected_repository(self) -> Optional[Dict[str, Any]]:
        """Get the currently selected repository from the table."""
        try:
            table = self.query_one("#results-table", DataTable)
            if table.cursor_row is not None:
                results_list = self.results.get("results", [])
                if 0 <= table.cursor_row < len(results_list):
                    return results_list[table.cursor_row]
            return None
        except Exception:
            return None

    def action_select(self) -> None:
        """Handle Enter key - open Repository Screen."""
        selected = self._get_selected_repository()
        if selected:
            name = selected.get("name") or selected.get("slug", "")
            if "/" in name:
                namespace, repo = name.split("/", 1)
            else:
                namespace = "library"
                repo = name

            from src.screens.repository_screen import RepositoryScreen
            self.app.push_screen(RepositoryScreen(namespace, repo))

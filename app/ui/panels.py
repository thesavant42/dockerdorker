"""Panel widgets for the main application layout."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from app.ui.widgets.pagination import PaginationWidget
from app.ui.widgets.result_details import ResultDetailsWidget
from app.ui.widgets.search_results import SearchResultsWidget


class TopPanel(Static):
    """Top panel widget - contains app title/branding."""

    pass


class LeftPanel(Vertical):
    """Left panel widget - contains search results and pagination."""

    def compose(self) -> ComposeResult:
        """Compose the left panel with pagination and search results."""
        yield PaginationWidget(id="pagination")
        yield SearchResultsWidget(id="search-results")


class RightPanel(Static):
    """Right panel widget - contains result details."""

    def compose(self) -> ComposeResult:
        """Compose the right panel with result details."""
        yield ResultDetailsWidget(id="result-details")

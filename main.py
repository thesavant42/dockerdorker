"""
dockerDorkerUI

A Textual app for exploring Docker Hub repositories.
- Header (docked top)
- Top Panel (title/branding)
- Left Panel (search results table)
- Right Panel (result details)
- Footer (docked bottom)
"""

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import DataTable, Footer, Header

from app.core.api.dockerhub_search import search as dockerhub_search
from app.core.api.dockerhub_v2_api import fetch_all_tags
from app.ui.commands.search_provider import SearchProvider
from app.ui.messages import (
    EnumerateTagsComplete,
    EnumerateTagsError,
    EnumerateTagsRequested,
    RowHighlighted,
    SearchComplete,
    SearchError,
    SearchRequested,
)
from app.ui.panels import LeftPanel, RightPanel, TopPanel
from app.ui.widgets.pagination import PaginationWidget
from app.ui.widgets.result_details import ResultDetailsWidget
from app.ui.widgets.search_results import SearchResultsWidget


class DockerDorkerApp(App):
    """dockerDorker - A Textual app for Docker Hub exploration."""

    CSS_PATH = "app/styles/styles.tcss"
    TITLE = "dockerDorker"
    SUB_TITLE = "by @thesavant42"

    COMMANDS = App.COMMANDS | {SearchProvider}

    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        yield Header(show_clock=True)
        yield TopPanel("dockerDorker", id="top-panel")
        with Horizontal(id="main-content"):
            yield LeftPanel(id="left-panel")
            yield RightPanel(id="right-panel")
        yield Footer()

    def on_mount(self) -> None:
        """Set the Dracula theme when the app mounts."""
        self.theme = "dracula"

    def on_search_requested(self, message: SearchRequested) -> None:
        """Handle search request from command palette."""
        self._set_status(f"Searching for '{message.query}'...")
        self._run_search(message.query)

    @work(exclusive=True, thread=True)
    def _run_search(self, query: str) -> None:
        """Run the search in a background thread.
        
        NOTE: No progress callbacks during pagination - they cause socket corruption.
        Status updates only at start (above) and completion (via message).
        """
        try:
            results = dockerhub_search(query)
            self.call_from_thread(
                self.post_message,
                SearchComplete(
                    query=query,
                    results=results.get("results", []),
                    total=results.get("total", 0),
                    cached=results.get("cached", False),
                ),
            )
        except Exception as e:
            self.call_from_thread(
                self.post_message, SearchError(query=query, error=str(e))
            )

    def on_search_complete(self, message: SearchComplete) -> None:
        """Handle search completion."""
        cached = " (cached)" if message.cached else ""
        self._set_status(f"Found {message.total} results for '{message.query}'{cached}")

        results_widget = self.query_one("#search-results", SearchResultsWidget)
        # Calculate pages based on actual results (no longer 4 columns)
        total_pages = max(1, (len(message.results) + 99) // 100)  # Assume 100 per page
        results_widget.load_results(
            results=message.results,
            query=message.query,
            page=1,
            total_pages=total_pages,
        )

        pagination = self.query_one("#pagination", PaginationWidget)
        pagination.show(1, total_pages)

    def on_search_error(self, message: SearchError) -> None:
        """Handle search errors."""
        self._set_status(f"Search failed: {message.error}")

    def _set_status(self, text: str) -> None:
        """Update status text in subtitle."""
        self.sub_title = text if text else "by @thesavant42"

    def on_row_highlighted(self, message: RowHighlighted) -> None:
        """Handle row highlight to update top panel."""
        details = self.query_one("#result-details", ResultDetailsWidget)
        details.show_result(message.result)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection (Enter key) to trigger tag enumeration."""
        # The widget already posts EnumerateTagsRequested, so we just need to handle it
        pass

    def on_enumerate_tags_requested(self, message: EnumerateTagsRequested) -> None:
        """Handle tag enumeration request."""
        self._set_status(f"Enumerating tags for {message.namespace}/{message.repo}...")
        self._enumerate_tags(message.namespace, message.repo)

    @work(exclusive=True, thread=True)
    def _enumerate_tags(self, namespace: str, repo: str) -> None:
        """Fetch tags in a background thread.
        
        Args:
            namespace: Repository namespace/owner.
            repo: Repository name.
        """
        try:
            tags = fetch_all_tags(namespace, repo)
            self.call_from_thread(
                self.post_message,
                EnumerateTagsComplete(namespace=namespace, repo=repo, tags=tags),
            )
        except Exception as e:
            self.call_from_thread(
                self.post_message,
                EnumerateTagsError(namespace=namespace, repo=repo, error=str(e)),
            )

    def on_enumerate_tags_complete(self, message: EnumerateTagsComplete) -> None:
        """Handle tag enumeration completion."""
        self._set_status(
            f"Found {len(message.tags)} tags for {message.namespace}/{message.repo}"
        )

    def on_enumerate_tags_error(self, message: EnumerateTagsError) -> None:
        """Handle tag enumeration error."""
        self._set_status(
            f"Tag enumeration failed: {message.error}"
        )


if __name__ == "__main__":
    app = DockerDorkerApp()
    app.run()

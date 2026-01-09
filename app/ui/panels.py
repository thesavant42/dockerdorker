"""Panel widgets for the main application layout."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Static, TabbedContent, TabPane

from app.ui.widgets.build_info import BuildInfoWidget
from app.ui.widgets.result_details import ResultDetailsWidget
from app.ui.widgets.search_results import SearchResultsWidget
from app.ui.widgets.tag_selector import TagSelectorWidget


class TopPanel(Static):
    """Top panel widget - contains result details and tag selector."""

    def compose(self) -> ComposeResult:
        """Compose the top panel with result details and tag selector."""
        with Horizontal(id="top-panel-content"):
            yield ResultDetailsWidget(id="result-details")
            with Container(id="tag-selector-container"):
                yield TagSelectorWidget(id="tag-selector")


class LeftPanel(Vertical):
    """Left panel widget - contains search results."""

    def compose(self) -> ComposeResult:
        """Compose the left panel with search results."""
        yield SearchResultsWidget(id="search-results")


class RightPanel(Vertical):
    """Right panel widget - contains tabbed content for build info and filesystem."""

    def compose(self) -> ComposeResult:
        """Compose the right panel with TabbedContent for Build and Files tabs."""
        with TabbedContent():
            with TabPane("Build", id="build-tab"):
                with VerticalScroll(id="build-info-scroll"):
                    yield BuildInfoWidget(id="build-info")
            with TabPane("Files", id="files-tab"):
                yield Static("Select a tag to view filesystem", id="filesystem-placeholder")

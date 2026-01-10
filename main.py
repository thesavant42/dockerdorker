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
from app.core.utils.image_config_formatter import parse_image_config
from app.ui.commands.search_provider import SearchProvider
from app.ui.messages import (
    BuildHistoryFetched,
    EnumerateTagsComplete,
    EnumerateTagsError,
    EnumerateTagsRequested,
    FetchImageConfigComplete,
    FetchImageConfigError,
    LayerPeekComplete,
    LayerPeekError,
    RowHighlighted,
    SearchComplete,
    SearchError,
    SearchRequested,
    TagSelected,
)
from app.ui.panels import LeftPanel, RightPanel, TopPanel
from app.ui.widgets.build_info import BuildInfoWidget
from app.ui.widgets.result_details import ResultDetailsWidget
from app.ui.widgets.search_results import SearchResultsWidget
from app.ui.widgets.tag_selector import TagSelectorWidget


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

    def on_search_error(self, message: SearchError) -> None:
        """Handle search errors."""
        self._set_status(f"Search failed: {message.error}")

    def _set_status(self, text: str) -> None:
        """Update status text in result details panel."""
        # Update the result details widget
        try:
            details = self.query_one("#result-details", ResultDetailsWidget)
            details.set_status(text if text else "")
        except Exception:
            # Silently fail if widget doesn't exist yet
            pass

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
        tag_selector = self.query_one("#tag-selector", TagSelectorWidget)
        tag_selector.load_tags(message.namespace, message.repo, message.tags)

    def on_enumerate_tags_error(self, message: EnumerateTagsError) -> None:
        """Handle tag enumeration error."""
        self._set_status(
            f"Tag enumeration failed: {message.error}"
        )

    def on_tag_selected(self, message: TagSelected) -> None:
        """Handle tag selection."""
        self._set_status(f"Fetching images for {message.tag_name}...")
        self._fetch_image_config(message.namespace, message.repo, message.tag_name)

    @work(exclusive=True, thread=True)
    def _fetch_image_config(self, namespace: str, repo: str, tag_name: str) -> None:
        """Fetch image configs in a background thread.
        
        Args:
            namespace: Repository namespace/owner.
            repo: Repository name.
            tag_name: Tag name to fetch images for.
        """
        from app.core.api.dockerhub_v2_api import fetch_tag_images
        try:
            response = fetch_tag_images(namespace, repo, tag_name)
            # Handle both list and dict responses
            if isinstance(response, dict):
                images = response.get("results", response.get("images", []))
            else:
                images = response if isinstance(response, list) else []
            
            self.call_from_thread(
                self.post_message,
                FetchImageConfigComplete(namespace, repo, tag_name, images)
            )
        except Exception as e:
            self.call_from_thread(
                self.post_message,
                FetchImageConfigError(namespace, repo, tag_name, str(e))
            )

    def on_fetch_image_config_complete(self, message: FetchImageConfigComplete) -> None:
        """Handle image config fetch completion."""
        count = len(message.images)
        self._set_status(f"Loaded {count} image config(s) for {message.tag_name}")
        # Store for next phase (layer peek)
        self._current_images = message.images
        
        # Fetch build history in background
        if message.images:
            first_image = message.images[0]
            if isinstance(first_image, dict):
                self._fetch_build_history(
                    message.namespace, 
                    message.repo, 
                    message.tag_name, 
                    first_image
                )
    
    @work(exclusive=True, thread=True)
    def _fetch_build_history(
        self, namespace: str, repo: str, tag_name: str, image_data: dict
    ) -> None:
        """Fetch build history from registry in background thread."""
        from app.core.utils.image_config_formatter import fetch_image_build_history
        try:
            build_history = fetch_image_build_history(namespace, repo, tag_name)
            self.call_from_thread(
                self.post_message,
                BuildHistoryFetched(namespace, repo, tag_name, image_data, build_history)
            )
        except Exception:
            # On error, post with empty build history
            self.call_from_thread(
                self.post_message,
                BuildHistoryFetched(namespace, repo, tag_name, image_data, [])
            )
    
    def on_build_history_fetched(self, message: BuildHistoryFetched) -> None:
        """Handle build history fetch completion."""
        summary = parse_image_config(message.image_data, build_history=message.build_history)
        build_info = self.query_one("#build-info", BuildInfoWidget)
        build_info.load_config(summary)
        
        # Trigger layer peek for filesystem enumeration
        self._run_layer_peek(message.namespace, message.repo, message.tag_name)

    @work(exclusive=True, thread=True)
    def _run_layer_peek(self, namespace: str, repo: str, tag_name: str) -> None:
        """Peek all layers for filesystem enumeration in background thread."""
        from app.core.api.layerslayer import layerslayer
        from app.core.database import get_database
        from app.modules.enumerate.list_dockerhub_container_files import (
            fetch_pull_token,
            fetch_manifest,
        )
        
        try:
            # Get auth token for registry
            token = fetch_pull_token(namespace, repo)
            if not token:
                self.call_from_thread(
                    self.post_message,
                    LayerPeekError(namespace, repo, tag_name, "Failed to get registry token"),
                )
                return
            
            # Get layers from Registry manifest
            layer_infos = fetch_manifest(namespace, repo, tag_name, token)
            if not layer_infos:
                self.call_from_thread(
                    self.post_message,
                    LayerPeekError(namespace, repo, tag_name, "No layers found in manifest"),
                )
                return
            
            # Convert LayerInfo objects to dicts for layerslayer()
            layers = [{"digest": l.digest, "size": l.size} for l in layer_infos]
            
            # Peek all layers via registry
            db = get_database()
            result = layerslayer(namespace, repo, layers, db=db)
            
            self.call_from_thread(
                self.post_message,
                LayerPeekComplete(namespace, repo, tag_name, result),
            )
        except Exception as e:
            self.call_from_thread(
                self.post_message,
                LayerPeekError(namespace, repo, tag_name, str(e)),
            )

    def on_layer_peek_complete(self, message: LayerPeekComplete) -> None:
        """Handle layer peek completion."""
        result = message.result
        self._set_status(
            f"Found {result.total_entries} files across {result.layers_peeked} layers "
            f"({result.layers_from_cache} cached)"
        )
        # TODO: Display result.all_entries in Files tab

    def on_layer_peek_error(self, message: LayerPeekError) -> None:
        """Handle layer peek error."""
        self._set_status(f"Layer peek failed: {message.error}")

    def on_fetch_image_config_error(self, message: FetchImageConfigError) -> None:
        """Handle image config fetch error."""
        self._set_status(
            f"Image config fetch failed: {message.error}"
        )


if __name__ == "__main__":
    app = DockerDorkerApp()
    app.run()

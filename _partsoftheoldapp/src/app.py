"""
Main Textual application for docker-dorker.
"""

from textual.app import App

from src.screens import SearchResultsScreen, SearchScreen


class DockerDorkerApp(App):
    """
    Main docker-dorker TUI application.

    Handles initial screen setup.
    """

    CSS_PATH = [
        "../styles/app.tcss",
        "../styles/search_screen.tcss",
        "../styles/image_config_screen.tcss",
        "../styles/layer_contents_screen.tcss",
    ]

    def __init__(self, initial_query: str = None):
        """
        Initialize the app.

        Args:
            initial_query: Optional search query to run on startup
        """
        super().__init__()
        self.initial_query = initial_query

    def on_mount(self) -> None:
        """Set up the application on startup."""
        # Always push SearchScreen first as the base screen
        self.push_screen(SearchScreen())
        
        if self.initial_query:
            # If query provided, push SearchResultsScreen on top
            self.perform_search(self.initial_query)

    def perform_search(self, query: str) -> None:
        """
        Execute a search and display results.

        Args:
            query: Search query string
        """
        from src.api import search

        self.notify(f"Searching for: {query}")

        # Perform search (blocks - will add async in future)
        results = search(query)

        self.push_screen(SearchResultsScreen(results, query))
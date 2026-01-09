"""Search command provider for the command palette."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.command import DiscoveryHit, Hit, Hits, Provider

if TYPE_CHECKING:
    from textual.app import App


class SearchProvider(Provider):
    """Provides 'search <query>' command to search Docker Hub."""

    @property
    def _app(self) -> App:
        """Get the app instance."""
        return self.screen.app

    async def discover(self) -> Hits:
        """Show the search command when palette opens."""
        yield DiscoveryHit(
            display="search <query>",
            command=self._no_op,
            help="Search Docker Hub. Example: search nginx",
        )

    async def _no_op(self) -> None:
        """Placeholder - discover hits just show help text."""
        pass

    async def search(self, query: str) -> Hits:
        """Parse and handle search commands.
        
        Args:
            query: The user input from command palette.
            
        Yields:
            Hit objects for matching commands.
        """
        query = query.strip()

        # Check if input starts with 'search '
        if query.lower().startswith("search "):
            search_term = query[7:].strip()  # Remove 'search ' prefix
            if search_term:
                yield Hit(
                    score=100,  # High score to appear at top
                    match_display=f"Search Docker Hub for: {search_term}",
                    command=lambda term=search_term: self._execute_search(term),
                    help=f"Search Docker Hub for '{search_term}'",
                )
        elif query.lower() == "search":
            # User typed just "search" - show hint
            yield Hit(
                score=50,
                match_display="search <query>",
                command=self._no_op,
                help="Type a search term after 'search'. Example: search nginx",
            )

    async def _execute_search(self, search_term: str) -> None:
        """Trigger the search on the app.
        
        Args:
            search_term: The term to search for on Docker Hub.
        """
        from app.ui.messages import SearchRequested

        self._app.post_message(SearchRequested(query=search_term))

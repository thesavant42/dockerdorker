"""Custom messages for the dockerDorker UI."""

from textual.message import Message


class SearchRequested(Message):
    """Posted when user requests a Docker Hub search."""

    def __init__(self, query: str) -> None:
        """Initialize with search query.
        
        Args:
            query: The search term to look for on Docker Hub.
        """
        self.query = query
        super().__init__()


class SearchComplete(Message):
    """Posted when search results are ready."""

    def __init__(
        self, query: str, results: list, total: int, cached: bool
    ) -> None:
        """Initialize with search results.
        
        Args:
            query: The original search term.
            results: List of result dictionaries.
            total: Total number of results found.
            cached: Whether results came from cache.
        """
        self.query = query
        self.results = results
        self.total = total
        self.cached = cached
        super().__init__()


class SearchError(Message):
    """Posted when search fails."""

    def __init__(self, query: str, error: str) -> None:
        """Initialize with error details.
        
        Args:
            query: The search term that failed.
            error: Error message describing the failure.
        """
        self.query = query
        self.error = error
        super().__init__()

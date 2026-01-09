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


class RowHighlighted(Message):
    """Posted when a row is highlighted in search results."""

    def __init__(self, result: dict) -> None:
        """Initialize with highlighted result.
        
        Args:
            result: Dictionary containing result data.
        """
        self.result = result
        super().__init__()


class EnumerateTagsRequested(Message):
    """Posted when user requests tag enumeration."""

    def __init__(self, namespace: str, repo: str) -> None:
        """Initialize with repository info.
        
        Args:
            namespace: Repository namespace/owner.
            repo: Repository name.
        """
        self.namespace = namespace
        self.repo = repo
        super().__init__()


class EnumerateTagsComplete(Message):
    """Posted when tag enumeration completes."""

    def __init__(self, namespace: str, repo: str, tags: list) -> None:
        """Initialize with tag data.
        
        Args:
            namespace: Repository namespace/owner.
            repo: Repository name.
            tags: List of tag dictionaries.
        """
        self.namespace = namespace
        self.repo = repo
        self.tags = tags
        super().__init__()


class EnumerateTagsError(Message):
    """Posted when tag enumeration fails."""

    def __init__(self, namespace: str, repo: str, error: str) -> None:
        """Initialize with error details.
        
        Args:
            namespace: Repository namespace/owner.
            repo: Repository name.
            error: Error message describing the failure.
        """
        self.namespace = namespace
        self.repo = repo
        self.error = error
        super().__init__()
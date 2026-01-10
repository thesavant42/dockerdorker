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


class TagSelected(Message):
    """Posted when a tag is selected from the tag selector."""

    def __init__(self, namespace: str, repo: str, tag_name: str, tag_data: dict) -> None:
        """Initialize with tag selection details.
        
        Args:
            namespace: Repository namespace/owner.
            repo: Repository name.
            tag_name: The selected tag name.
            tag_data: Full tag dictionary from API.
        """
        self.namespace = namespace
        self.repo = repo
        self.tag_name = tag_name
        self.tag_data = tag_data
        super().__init__()


class FetchImageConfigRequested(Message):
    """Posted when image config fetch is requested."""

    def __init__(self, namespace: str, repo: str, tag_name: str) -> None:
        """Initialize with fetch request details.
        
        Args:
            namespace: Repository namespace/owner.
            repo: Repository name.
            tag_name: Tag name to fetch images for.
        """
        self.namespace = namespace
        self.repo = repo
        self.tag_name = tag_name
        super().__init__()


class FetchImageConfigComplete(Message):
    """Posted when image config fetch completes."""

    def __init__(self, namespace: str, repo: str, tag_name: str, images: list[dict]) -> None:
        """Initialize with fetched image configs.
        
        Args:
            namespace: Repository namespace/owner.
            repo: Repository name.
            tag_name: Tag name that was fetched.
            images: List of image config dictionaries.
        """
        self.namespace = namespace
        self.repo = repo
        self.tag_name = tag_name
        self.images = images
        super().__init__()


class FetchImageConfigError(Message):
    """Posted when image config fetch fails."""

    def __init__(self, namespace: str, repo: str, tag_name: str, error: str) -> None:
        """Initialize with error details.
        
        Args:
            namespace: Repository namespace/owner.
            repo: Repository name.
            tag_name: Tag name that failed.
            error: Error message describing the failure.
        """
        self.namespace = namespace
        self.repo = repo
        self.tag_name = tag_name
        self.error = error
        super().__init__()


class BuildHistoryFetched(Message):
    """Posted when build history is fetched from the registry."""

    def __init__(
        self, 
        namespace: str, 
        repo: str, 
        tag_name: str, 
        image_data: dict, 
        build_history: list[dict]
    ) -> None:
        """Initialize with build history data.
        
        Args:
            namespace: Repository namespace/owner.
            repo: Repository name.
            tag_name: Tag name that was fetched.
            image_data: Original image config from Docker Hub API.
            build_history: Build history entries from registry config blob.
        """
        self.namespace = namespace
        self.repo = repo
        self.tag_name = tag_name
        self.image_data = image_data
        self.build_history = build_history
        super().__init__()


class LayerPeekComplete(Message):
    """Posted when layer peek completes."""

    def __init__(
        self,
        namespace: str,
        repo: str,
        tag_name: str,
        result: "LayerSlayerResult",
    ) -> None:
        """Initialize with layer peek results.
        
        Args:
            namespace: Repository namespace/owner.
            repo: Repository name.
            tag_name: Tag name that was peeked.
            result: LayerSlayerResult with all file entries.
        """
        self.namespace = namespace
        self.repo = repo
        self.tag_name = tag_name
        self.result = result
        super().__init__()


class LayerPeekError(Message):
    """Posted when layer peek fails."""

    def __init__(
        self,
        namespace: str,
        repo: str,
        tag_name: str,
        error: str,
    ) -> None:
        """Initialize with error details.
        
        Args:
            namespace: Repository namespace/owner.
            repo: Repository name.
            tag_name: Tag name that failed.
            error: Error message describing the failure.
        """
        self.namespace = namespace
        self.repo = repo
        self.tag_name = tag_name
        self.error = error
        super().__init__()


# --- /ddork command palette messages ---


class ReposRequested(Message):
    """Posted when user requests repository listing for a namespace."""

    def __init__(self, namespace: str) -> None:
        """Initialize with namespace.
        
        Args:
            namespace: Docker Hub namespace to list repos for.
        """
        self.namespace = namespace
        super().__init__()


class TagsRequested(Message):
    """Posted when user requests tag listing for a repository."""

    def __init__(self, namespace: str, repo: str) -> None:
        """Initialize with repository info.
        
        Args:
            namespace: Repository namespace/owner.
            repo: Repository name.
        """
        self.namespace = namespace
        self.repo = repo
        super().__init__()


class ContainersRequested(Message):
    """Posted when user requests container digests for a tag."""

    def __init__(self, namespace: str, repo: str, tag: str) -> None:
        """Initialize with tag info.
        
        Args:
            namespace: Repository namespace/owner.
            repo: Repository name.
            tag: Tag name.
        """
        self.namespace = namespace
        self.repo = repo
        self.tag = tag
        super().__init__()


class LayersRequested(Message):
    """Posted when user requests layer digests from registry."""

    def __init__(self, namespace: str, repo: str, tag: str) -> None:
        """Initialize with tag info.
        
        Args:
            namespace: Repository namespace/owner.
            repo: Repository name.
            tag: Tag name.
        """
        self.namespace = namespace
        self.repo = repo
        self.tag = tag
        super().__init__()


class FilesRequested(Message):
    """Posted when user requests file listing via layer peek."""

    def __init__(self, namespace: str, repo: str, tag: str) -> None:
        """Initialize with tag info.
        
        Args:
            namespace: Repository namespace/owner.
            repo: Repository name.
            tag: Tag name.
        """
        self.namespace = namespace
        self.repo = repo
        self.tag = tag
        super().__init__()


class CarveRequested(Message):
    """Posted when user requests file carving from an image layer."""

    def __init__(self, namespace: str, repo: str, tag: str, filepath: str) -> None:
        """Initialize with carve request details.
        
        Args:
            namespace: Repository namespace/owner.
            repo: Repository name.
            tag: Tag name.
            filepath: Path to file inside container (e.g., '/etc/passwd').
        """
        self.namespace = namespace
        self.repo = repo
        self.tag = tag
        self.filepath = filepath
        super().__init__()


class CarveComplete(Message):
    """Posted when file carving completes successfully."""

    def __init__(
        self, namespace: str, repo: str, tag: str, filepath: str, saved_path: str
    ) -> None:
        """Initialize with carve completion details.
        
        Args:
            namespace: Repository namespace/owner.
            repo: Repository name.
            tag: Tag name.
            filepath: Original path requested.
            saved_path: Local path where file was saved.
        """
        self.namespace = namespace
        self.repo = repo
        self.tag = tag
        self.filepath = filepath
        self.saved_path = saved_path
        super().__init__()


class CarveError(Message):
    """Posted when file carving fails."""

    def __init__(
        self, namespace: str, repo: str, tag: str, filepath: str, error: str
    ) -> None:
        """Initialize with error details.
        
        Args:
            namespace: Repository namespace/owner.
            repo: Repository name.
            tag: Tag name.
            filepath: Path that was requested.
            error: Error message describing the failure.
        """
        self.namespace = namespace
        self.repo = repo
        self.tag = tag
        self.filepath = filepath
        self.error = error
        super().__init__()
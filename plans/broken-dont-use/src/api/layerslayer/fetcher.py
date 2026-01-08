"""
Layerslayer fetcher for docker-dorker.

Uses HTTP Range requests to fetch only the first 8-64KB of a layer blob,
decompress the partial gzip stream, and parse tar headers for a file listing
preview without downloading the full layer.

Key insight: 8KB download → 41 files discovered from a 30MB layer (0.027% of data)

Layer Slayer mode: Peek ALL layers for an image and cache the filesystem metadata.
"""

import zlib
from dataclasses import dataclass, field
from typing import Callable, Generator, Optional, TYPE_CHECKING

import requests

from src.api.layerslayer.parser import TarEntry, parse_tar_header

if TYPE_CHECKING:
    from src.database import Database


@dataclass
class LayerPeekResult:
    """Result of peeking into a layer blob."""
    digest: str
    partial: bool
    bytes_downloaded: int
    bytes_decompressed: int
    entries_found: int
    entries: list[TarEntry]
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "digest": self.digest,
            "partial": self.partial,
            "bytes_downloaded": self.bytes_downloaded,
            "bytes_decompressed": self.bytes_decompressed,
            "entries_found": self.entries_found,
            "entries": [e.to_dict() for e in self.entries],
            "error": self.error,
        }


# Persistent session for registry calls
_session = requests.Session()
_session.headers.update({
    "Accept": "application/vnd.docker.distribution.manifest.v2+json"
})


def _registry_base_url(namespace: str, repo: str) -> str:
    """Get the registry base URL for a repository."""
    return f"https://registry-1.docker.io/v2/{namespace}/{repo}"


def _fetch_pull_token(namespace: str, repo: str) -> Optional[str]:
    """
    Retrieve a Docker Hub pull token (anonymous).
    """
    auth_url = (
        f"https://auth.docker.io/token"
        f"?service=registry.docker.io&scope=repository:{namespace}/{repo}:pull"
    )
    try:
        resp = requests.get(auth_url)
        resp.raise_for_status()
        return resp.json().get("token")
    except requests.RequestException:
        return None


def peek_layer_blob_partial(
    namespace: str,
    repo: str,
    digest: str,
    token: Optional[str] = None,
    initial_bytes: int = 65536,
) -> LayerPeekResult:
    """
    Fetch only first N bytes of a layer using HTTP Range request,
    decompress, and parse tar headers.
    
    Returns partial file listing - enough for a preview.
    
    Args:
        namespace: Docker Hub namespace (e.g., "library" for official images)
        repo: Repository name (e.g., "nginx")
        digest: Layer digest (e.g., "sha256:abc123...")
        token: Optional auth token, will fetch if not provided
        initial_bytes: How many bytes to fetch (default 64KB)
        
    Returns:
        LayerPeekResult with partial file listing
    """
    # Get token if not provided
    if not token:
        token = _fetch_pull_token(namespace, repo)
    
    url = f"{_registry_base_url(namespace, repo)}/blobs/{digest}"
    
    # Build headers with Range request
    headers = {"Range": f"bytes=0-{initial_bytes - 1}"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        resp = _session.get(url, headers=headers, stream=True, timeout=30)
        
        # Handle auth retry
        if resp.status_code == 401:
            token = _fetch_pull_token(namespace, repo)
            if token:
                headers["Authorization"] = f"Bearer {token}"
                resp = _session.get(url, headers=headers, stream=True, timeout=30)
        
        resp.raise_for_status()
        
        # Read the partial data
        compressed_data = resp.raw.read(initial_bytes)
        resp.close()
        
    except requests.RequestException as e:
        return LayerPeekResult(
            digest=digest,
            partial=True,
            bytes_downloaded=0,
            bytes_decompressed=0,
            entries_found=0,
            entries=[],
            error=str(e),
        )
    
    # Verify gzip magic (0x1f 0x8b)
    if len(compressed_data) < 2 or compressed_data[0:2] != b'\x1f\x8b':
        return LayerPeekResult(
            digest=digest,
            partial=True,
            bytes_downloaded=len(compressed_data),
            bytes_decompressed=0,
            entries_found=0,
            entries=[],
            error="Not a gzip file (missing magic bytes)",
        )
    
    # Decompress with zlib (handles partial streams)
    try:
        decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)  # 16 = gzip format
        decompressed = decompressor.decompress(compressed_data)
    except zlib.error as e:
        return LayerPeekResult(
            digest=digest,
            partial=True,
            bytes_downloaded=len(compressed_data),
            bytes_decompressed=0,
            entries_found=0,
            entries=[],
            error=f"Decompression error: {e}",
        )
    
    if len(decompressed) < 512:
        return LayerPeekResult(
            digest=digest,
            partial=True,
            bytes_downloaded=len(compressed_data),
            bytes_decompressed=len(decompressed),
            entries_found=0,
            entries=[],
            error="Not enough decompressed data for tar header",
        )
    
    # Parse tar headers
    entries = []
    offset = 0
    
    while offset + 512 <= len(decompressed):
        entry, next_offset = parse_tar_header(decompressed, offset)
        if entry is None:
            break
        entries.append(entry)
        
        if next_offset <= offset or next_offset > len(decompressed):
            # Next header would be outside our buffer
            break
        offset = next_offset
    
    return LayerPeekResult(
        digest=digest,
        partial=True,
        bytes_downloaded=len(compressed_data),
        bytes_decompressed=len(decompressed),
        entries_found=len(entries),
        entries=entries,
    )


def peek_layer_blob_streaming(
    namespace: str,
    repo: str,
    digest: str,
    token: Optional[str] = None,
    initial_bytes: int = 65536,
) -> Generator[TarEntry, None, LayerPeekResult]:
    """
    Generator version that yields entries as they are parsed.
    
    This allows the UI to display entries progressively as they're discovered.
    
    Usage:
        gen = peek_layer_blob_streaming(namespace, repo, digest)
        for entry in gen:
            display(entry)  # Each entry as it's discovered
        # After exhausting generator, get the final result stats
    
    Yields:
        TarEntry objects as they are parsed
        
    Returns:
        LayerPeekResult with final stats (accessible after generator exhausted)
    """
    # Get token if not provided
    if not token:
        token = _fetch_pull_token(namespace, repo)
    
    url = f"{_registry_base_url(namespace, repo)}/blobs/{digest}"
    
    # Build headers with Range request
    headers = {"Range": f"bytes=0-{initial_bytes - 1}"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    error_msg = None
    compressed_data = b""
    decompressed = b""
    entries = []
    
    try:
        resp = _session.get(url, headers=headers, stream=True, timeout=30)
        
        # Handle auth retry
        if resp.status_code == 401:
            token = _fetch_pull_token(namespace, repo)
            if token:
                headers["Authorization"] = f"Bearer {token}"
                resp = _session.get(url, headers=headers, stream=True, timeout=30)
        
        resp.raise_for_status()
        
        # Read the partial data
        compressed_data = resp.raw.read(initial_bytes)
        resp.close()
        
    except requests.RequestException as e:
        error_msg = str(e)
        return LayerPeekResult(
            digest=digest,
            partial=True,
            bytes_downloaded=0,
            bytes_decompressed=0,
            entries_found=0,
            entries=[],
            error=error_msg,
        )
    
    # Verify gzip magic (0x1f 0x8b)
    if len(compressed_data) < 2 or compressed_data[0:2] != b'\x1f\x8b':
        return LayerPeekResult(
            digest=digest,
            partial=True,
            bytes_downloaded=len(compressed_data),
            bytes_decompressed=0,
            entries_found=0,
            entries=[],
            error="Not a gzip file (missing magic bytes)",
        )
    
    # Decompress with zlib (handles partial streams)
    try:
        decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
        decompressed = decompressor.decompress(compressed_data)
    except zlib.error as e:
        return LayerPeekResult(
            digest=digest,
            partial=True,
            bytes_downloaded=len(compressed_data),
            bytes_decompressed=0,
            entries_found=0,
            entries=[],
            error=f"Decompression error: {e}",
        )
    
    if len(decompressed) < 512:
        return LayerPeekResult(
            digest=digest,
            partial=True,
            bytes_downloaded=len(compressed_data),
            bytes_decompressed=len(decompressed),
            entries_found=0,
            entries=[],
            error="Not enough decompressed data for tar header",
        )
    
    # Parse tar headers and yield entries as we go
    offset = 0
    
    while offset + 512 <= len(decompressed):
        entry, next_offset = parse_tar_header(decompressed, offset)
        if entry is None:
            break
        entries.append(entry)
        yield entry  # Stream the entry to caller
        
        if next_offset <= offset or next_offset > len(decompressed):
            break
        offset = next_offset
    
    # Return final stats
    return LayerPeekResult(
        digest=digest,
        partial=True,
        bytes_downloaded=len(compressed_data),
        bytes_decompressed=len(decompressed),
        entries_found=len(entries),
        entries=entries,
    )


# =============================================================================
# Layer Slayer: Bulk layer peek with caching
# =============================================================================


@dataclass
class LayerSlayerResult:
    """Result of peeking into ALL layers of an image."""
    image_digest: str
    layers_peeked: int
    layers_from_cache: int
    total_bytes_downloaded: int
    total_entries: int
    all_entries: list[TarEntry]  # Merged from all layers
    layer_results: list[LayerPeekResult] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "image_digest": self.image_digest,
            "layers_peeked": self.layers_peeked,
            "layers_from_cache": self.layers_from_cache,
            "total_bytes_downloaded": self.total_bytes_downloaded,
            "total_entries": self.total_entries,
            "all_entries": [e.to_dict() for e in self.all_entries],
            "layer_results": [r.to_dict() for r in self.layer_results],
            "error": self.error,
        }


def _dict_to_tar_entry(d: dict) -> TarEntry:
    """Convert a dictionary back to a TarEntry object."""
    return TarEntry(
        name=d["name"],
        size=d["size"],
        typeflag=d["typeflag"],
        is_dir=d["is_dir"],
        mode=d["mode"],
        uid=d["uid"],
        gid=d["gid"],
        mtime=d["mtime"],
        linkname=d["linkname"],
        is_symlink=d["is_symlink"],
    )


def layerslayer(
    namespace: str,
    repo: str,
    layers: list[dict],
    db: Optional["Database"] = None,
    progress_callback: Optional[Callable[[str, int, int], None]] = None,
) -> LayerSlayerResult:
    """
    Peek ALL layers for an image and merge into virtual filesystem.
    
    - Checks cache first for each layer (if db provided)
    - Fetches uncached layers via peek_layer_blob_partial()
    - Caches new results (if db provided)
    - Returns combined result with total bytes stats
    
    Args:
        namespace: Docker Hub namespace (e.g., "library")
        repo: Repository name (e.g., "nginx")
        layers: List of layer dicts from image_data["layers"]
        db: Optional Database instance for caching
        progress_callback: Optional callback(message, current, total)
        
    Returns:
        LayerSlayerResult with all layer entries and stats
    """
    # Filter to layers with digests only
    layer_digests = [
        layer.get("digest")
        for layer in layers
        if layer.get("digest")
    ]
    
    if not layer_digests:
        return LayerSlayerResult(
            image_digest="",
            layers_peeked=0,
            layers_from_cache=0,
            total_bytes_downloaded=0,
            total_entries=0,
            all_entries=[],
            error="No layers with digests found",
        )
    
    # Get a token for all layer requests (reuse for efficiency)
    token = _fetch_pull_token(namespace, repo)
    
    all_entries: list[TarEntry] = []
    layer_results: list[LayerPeekResult] = []
    total_bytes = 0
    layers_from_cache = 0
    
    for i, digest in enumerate(layer_digests):
        if progress_callback:
            progress_callback(f"Peeking layer {i+1}/{len(layer_digests)}", i, len(layer_digests))
        
        # Check cache first
        if db and db.layer_peek_cached(digest):
            cached = db.get_cached_layer_peek(digest)
            if cached:
                # Reconstruct LayerPeekResult from cache
                entries = [_dict_to_tar_entry(e) for e in cached["entries"]]
                result = LayerPeekResult(
                    digest=digest,
                    partial=True,
                    bytes_downloaded=0,  # Already cached, no new download
                    bytes_decompressed=cached["bytes_decompressed"],
                    entries_found=cached["entries_count"],
                    entries=entries,
                )
                layer_results.append(result)
                all_entries.extend(entries)
                layers_from_cache += 1
                continue
        
        # Fetch layer peek
        result = peek_layer_blob_partial(
            namespace=namespace,
            repo=repo,
            digest=digest,
            token=token,
        )
        
        layer_results.append(result)
        total_bytes += result.bytes_downloaded
        
        if not result.error:
            all_entries.extend(result.entries)
            # Cache the result
            if db:
                db.save_layer_peek(digest, namespace, repo, result)
    
    if progress_callback:
        progress_callback("Done", len(layer_digests), len(layer_digests))
    
    # Use the first layer's digest as image reference (or empty if none)
    image_digest = layer_digests[0] if layer_digests else ""
    
    return LayerSlayerResult(
        image_digest=image_digest,
        layers_peeked=len(layer_digests),
        layers_from_cache=layers_from_cache,
        total_bytes_downloaded=total_bytes,
        total_entries=len(all_entries),
        all_entries=all_entries,
        layer_results=layer_results,
    )

"""
Carve service for extracting files from OCI image layers.

Provides a reusable carve_file() function that extracts specific files
from Docker image layers using HTTP Range requests for efficiency.
"""

import time
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import requests

from app.core.utils.tar_parser import TarEntry, parse_tar_header


# =============================================================================
# Configuration
# =============================================================================

DEFAULT_CHUNK_SIZE = 65536  # 64KB chunks
DOWNLOADS_DIR = Path("./downloads")


# =============================================================================
# Result Types
# =============================================================================

@dataclass
class CarveResult:
    """Result of a carve operation."""
    success: bool
    saved_path: Optional[str] = None
    error: Optional[str] = None
    bytes_downloaded: int = 0
    layer_size: int = 0
    elapsed_seconds: float = 0.0


ProgressCallback = Callable[[str], None]


# =============================================================================
# Registry Authentication
# =============================================================================

_session = requests.Session()
_session.headers.update({
    "Accept": "application/vnd.docker.distribution.manifest.v2+json, "
              "application/vnd.oci.image.manifest.v1+json"
})


def _fetch_pull_token(namespace: str, repo: str) -> Optional[str]:
    """Retrieve a Docker Hub pull token (anonymous)."""
    auth_url = (
        f"https://auth.docker.io/token"
        f"?service=registry.docker.io&scope=repository:{namespace}/{repo}:pull"
    )
    try:
        resp = requests.get(auth_url, timeout=10, verify=False)
        resp.raise_for_status()
        return resp.json().get("token")
    except requests.RequestException:
        return None


def _registry_base_url(namespace: str, repo: str) -> str:
    """Get the registry base URL for a repository."""
    return f"https://registry-1.docker.io/v2/{namespace}/{repo}"


# =============================================================================
# Layer and Blob Classes
# =============================================================================

@dataclass
class LayerInfo:
    """Information about a layer from the manifest."""
    digest: str
    size: int
    media_type: str


def _fetch_manifest(namespace: str, repo: str, tag: str, token: str) -> list[LayerInfo]:
    """
    Fetch image manifest and extract layer information.
    
    Returns list of LayerInfo in order (base layer first).
    """
    url = f"{_registry_base_url(namespace, repo)}/manifests/{tag}"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        resp = _session.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        manifest = resp.json()
    except requests.RequestException:
        return []
    
    # Handle manifest list (multi-arch) - pick first amd64/linux
    if manifest.get("mediaType") == "application/vnd.docker.distribution.manifest.list.v2+json" or \
       manifest.get("mediaType") == "application/vnd.oci.image.index.v1+json":
        manifests = manifest.get("manifests", [])
        # Find amd64/linux manifest
        target = None
        for m in manifests:
            platform = m.get("platform", {})
            if platform.get("architecture") == "amd64" and platform.get("os") == "linux":
                target = m
                break
        if not target and manifests:
            target = manifests[0]  # Fallback to first
        
        if target:
            # Fetch the actual manifest
            digest = target.get("digest")
            url = f"{_registry_base_url(namespace, repo)}/manifests/{digest}"
            resp = _session.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            manifest = resp.json()
    
    # Extract layers
    layers = []
    for layer in manifest.get("layers", []):
        layers.append(LayerInfo(
            digest=layer.get("digest", ""),
            size=layer.get("size", 0),
            media_type=layer.get("mediaType", ""),
        ))
    
    return layers


class IncrementalBlobReader:
    """Fetches blob data in chunks using HTTP Range requests."""
    
    def __init__(self, namespace: str, repo: str, digest: str, token: str, 
                 chunk_size: int = DEFAULT_CHUNK_SIZE):
        self.url = f"{_registry_base_url(namespace, repo)}/blobs/{digest}"
        self.token = token
        self.chunk_size = chunk_size
        self.current_offset = 0
        self.bytes_downloaded = 0
        self.total_size = 0  # Set after first request
        self.exhausted = False
    
    def fetch_chunk(self) -> bytes:
        """Fetch the next chunk of data. Returns empty bytes if exhausted."""
        if self.exhausted:
            return b""
        
        end_offset = self.current_offset + self.chunk_size - 1
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Range": f"bytes={self.current_offset}-{end_offset}"
        }
        
        try:
            resp = _session.get(self.url, headers=headers, stream=True, timeout=30)
            
            # Check response
            if resp.status_code == 416:  # Range not satisfiable
                self.exhausted = True
                return b""
            
            resp.raise_for_status()
            
            # Get total size from Content-Range header
            content_range = resp.headers.get("Content-Range", "")
            if "/" in content_range:
                self.total_size = int(content_range.split("/")[-1])
            
            data = resp.raw.read(self.chunk_size)
            resp.close()
            
            if not data:
                self.exhausted = True
                return b""
            
            self.bytes_downloaded += len(data)
            self.current_offset += len(data)
            
            # Check if we've reached the end
            if self.total_size and self.current_offset >= self.total_size:
                self.exhausted = True
            
            return data
            
        except requests.RequestException:
            self.exhausted = True
            return b""


class IncrementalGzipDecompressor:
    """Decompresses gzip data incrementally."""
    
    def __init__(self):
        # 16 + MAX_WBITS tells zlib to expect gzip format
        self.decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
        self.buffer = b""
        self.bytes_decompressed = 0
        self.error: Optional[str] = None
    
    def feed(self, compressed_data: bytes) -> bytes:
        """
        Feed compressed data and return newly decompressed bytes.
        Also appends to internal buffer.
        """
        if not compressed_data:
            return b""
        
        try:
            decompressed = self.decompressor.decompress(compressed_data)
            self.buffer += decompressed
            self.bytes_decompressed += len(decompressed)
            return decompressed
        except zlib.error as e:
            self.error = str(e)
            return b""
    
    def get_buffer(self) -> bytes:
        """Return the full decompressed buffer."""
        return self.buffer


@dataclass
class ScanResult:
    """Result of scanning for a target file."""
    found: bool
    entry: Optional[TarEntry] = None
    content_offset: int = 0  # Offset in decompressed buffer where content starts
    content_size: int = 0
    entries_scanned: int = 0


class TarScanner:
    """Scans tar headers looking for a target file."""
    
    def __init__(self, target_path: str):
        self.target_path = self._normalize_path(target_path)
        self.entries_scanned = 0
        self.current_offset = 0
    
    def _normalize_path(self, path: str) -> str:
        """Normalize path for comparison (remove leading ./ or /)."""
        path = path.strip()
        if path.startswith("./"):
            path = path[2:]
        if path.startswith("/"):
            path = path[1:]
        return path
    
    def _matches(self, entry_name: str) -> bool:
        """Check if entry name matches target."""
        normalized = self._normalize_path(entry_name)
        return normalized == self.target_path
    
    def scan(self, data: bytes) -> ScanResult:
        """
        Scan buffer for target file.
        
        Returns ScanResult indicating whether file was found and where.
        Updates internal state to continue scanning from where we left off.
        """
        while self.current_offset + 512 <= len(data):
            entry, next_offset = parse_tar_header(data, self.current_offset)
            
            if entry is None:
                # End of archive or invalid header
                break
            
            self.entries_scanned += 1
            
            # Check if this is our target
            if self._matches(entry.name):
                content_offset = self.current_offset + 512
                return ScanResult(
                    found=True,
                    entry=entry,
                    content_offset=content_offset,
                    content_size=entry.size,
                    entries_scanned=self.entries_scanned,
                )
            
            # Move to next header
            if next_offset <= self.current_offset:
                break
            self.current_offset = next_offset
        
        return ScanResult(
            found=False,
            entries_scanned=self.entries_scanned,
        )


# =============================================================================
# File Extraction and Saving
# =============================================================================

def _extract_and_save(
    data: bytes,
    content_offset: int,
    content_size: int,
    target_path: str,
    output_dir: Path
) -> str:
    """
    Extract file content from buffer and save to disk.
    
    Returns the path where file was saved.
    """
    # Extract content
    content = data[content_offset:content_offset + content_size]
    
    # Prepare output path
    # Remove leading slash from target path
    clean_path = target_path.lstrip("/")
    output_path = output_dir / clean_path
    
    # Create parent directories
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write file
    output_path.write_bytes(content)
    
    return str(output_path)


# =============================================================================
# Main Carve Function
# =============================================================================

def carve_file(
    namespace: str,
    repo: str,
    tag: str,
    target_path: str,
    progress: Optional[ProgressCallback] = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> CarveResult:
    """
    Carve a single file from an image layer.
    
    Args:
        namespace: Docker Hub namespace (e.g., 'drichnerdisney').
        repo: Repository name (e.g., 'ollama').
        tag: Image tag (e.g., 'v1').
        target_path: Path to file inside container (e.g., '/etc/passwd').
        progress: Optional callback for status updates.
        chunk_size: Size of chunks to fetch.
        
    Returns:
        CarveResult with success status and saved_path or error.
    """
    start_time = time.time()
    
    def _progress(msg: str) -> None:
        if progress:
            progress(msg)
    
    # Build output directory: ./downloads/<namespace>/<repo>/<tag>/
    output_dir = DOWNLOADS_DIR / namespace / repo / tag
    
    _progress(f"Authenticating for {namespace}/{repo}...")
    token = _fetch_pull_token(namespace, repo)
    if not token:
        return CarveResult(
            success=False, 
            error="Failed to get authentication token",
            elapsed_seconds=time.time() - start_time,
        )
    
    _progress(f"Fetching manifest for {namespace}/{repo}:{tag}...")
    layers = _fetch_manifest(namespace, repo, tag, token)
    if not layers:
        return CarveResult(
            success=False, 
            error="No layers found in manifest",
            elapsed_seconds=time.time() - start_time,
        )
    
    _progress(f"Scanning {len(layers)} layer(s) for {target_path}...")
    
    # Scan each layer
    for i, layer in enumerate(layers):
        _progress(f"Scanning layer {i+1}/{len(layers)}: {layer.digest[:20]}...")
        
        # Initialize components
        reader = IncrementalBlobReader(namespace, repo, layer.digest, token, chunk_size)
        decompressor = IncrementalGzipDecompressor()
        scanner = TarScanner(target_path)
        
        # Stream and scan
        chunks_fetched = 0
        while not reader.exhausted:
            # Fetch next chunk
            compressed = reader.fetch_chunk()
            if not compressed:
                break
            
            chunks_fetched += 1
            
            # Check gzip magic on first chunk
            if chunks_fetched == 1:
                if len(compressed) < 2 or compressed[0:2] != b'\x1f\x8b':
                    # Layer is not gzip compressed, skip
                    break
            
            # Decompress
            decompressor.feed(compressed)
            
            if decompressor.error:
                break
            
            # Scan for target
            result = scanner.scan(decompressor.get_buffer())
            
            if result.found:
                # Check if we have enough data for the file content
                buffer = decompressor.get_buffer()
                bytes_needed = result.content_offset + result.content_size
                
                # Fetch more if needed
                while len(buffer) < bytes_needed and not reader.exhausted:
                    compressed = reader.fetch_chunk()
                    if not compressed:
                        break
                    decompressor.feed(compressed)
                    buffer = decompressor.get_buffer()
                    _progress(f"Fetching file content... {len(buffer):,} / {bytes_needed:,} bytes")
                
                buffer = decompressor.get_buffer()
                if len(buffer) >= bytes_needed:
                    # Found and have full content!
                    _progress(f"Found {target_path} ({result.content_size:,} bytes)")
                    
                    # Extract and save
                    saved_path = _extract_and_save(
                        buffer,
                        result.content_offset,
                        result.content_size,
                        target_path,
                        output_dir
                    )
                    
                    elapsed = time.time() - start_time
                    
                    return CarveResult(
                        success=True,
                        saved_path=saved_path,
                        bytes_downloaded=reader.bytes_downloaded,
                        layer_size=layer.size,
                        elapsed_seconds=elapsed,
                    )
                else:
                    return CarveResult(
                        success=False,
                        error=f"Found file but couldn't get full content (have {len(buffer):,}, need {bytes_needed:,})",
                        bytes_downloaded=reader.bytes_downloaded,
                        layer_size=layer.size,
                        elapsed_seconds=time.time() - start_time,
                    )
    
    elapsed = time.time() - start_time
    return CarveResult(
        success=False,
        error=f"File not found: {target_path} (searched {len(layers)} layers)",
        elapsed_seconds=elapsed,
    )

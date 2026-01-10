"""
Carve a single file from an OCI image layer using incremental streaming.

This script extracts a specific file from a Docker image without downloading
the entire layer. It uses HTTP Range requests to fetch compressed data in
chunks, decompresses incrementally, and stops as soon as the target file
is fully extracted.

Usage:
    python app/modules/carve/carve-file-from-layer.py "aciliadevops/disney-local-web:latest" /etc/passwd
"""

### DO NOT USE THIS IN PRODUCTION

import argparse
import os
import sys
import time
import zlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

# Add workspace root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.core.utils.tar_parser import TarEntry, parse_tar_header


# =============================================================================
# Configuration
# =============================================================================

DEFAULT_CHUNK_SIZE = 65536  # 64KB chunks
DEFAULT_OUTPUT_DIR = "." # Need to move this to its own subdirectory


# =============================================================================
# Registry Authentication
# =============================================================================

_session = requests.Session()
_session.headers.update({
    "Accept": "application/vnd.docker.distribution.manifest.v2+json, "
              "application/vnd.oci.image.manifest.v1+json"
})


def fetch_pull_token(namespace: str, repo: str) -> Optional[str]:
    """Retrieve a Docker Hub pull token (anonymous)."""
    auth_url = (
        f"https://auth.docker.io/token"
        f"?service=registry.docker.io&scope=repository:{namespace}/{repo}:pull"
    )
    try:
        resp = requests.get(auth_url, timeout=10)
        resp.raise_for_status()
        return resp.json().get("token")
    except requests.RequestException as e:
        print(f"Error fetching auth token: {e}")
        return None


def registry_base_url(namespace: str, repo: str) -> str:
    """Get the registry base URL for a repository."""
    return f"https://registry-1.docker.io/v2/{namespace}/{repo}"


# =============================================================================
# Manifest Fetching
# =============================================================================

@dataclass
class LayerInfo:
    """Information about a layer from the manifest."""
    digest: str
    size: int
    media_type: str


def fetch_manifest(namespace: str, repo: str, tag: str, token: str) -> list[LayerInfo]:
    """
    Fetch image manifest and extract layer information.
    
    Returns list of LayerInfo in order (base layer first).
    """
    url = f"{registry_base_url(namespace, repo)}/manifests/{tag}"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        resp = _session.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        manifest = resp.json()
    except requests.RequestException as e:
        print(f"Error fetching manifest: {e}")
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
            url = f"{registry_base_url(namespace, repo)}/manifests/{digest}"
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


# =============================================================================
# Incremental Blob Reader
# =============================================================================

class IncrementalBlobReader:
    """Fetches blob data in chunks using HTTP Range requests."""
    
    def __init__(self, namespace: str, repo: str, digest: str, token: str, 
                 chunk_size: int = DEFAULT_CHUNK_SIZE):
        self.url = f"{registry_base_url(namespace, repo)}/blobs/{digest}"
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
            
        except requests.RequestException as e:
            print(f"Error fetching chunk: {e}")
            self.exhausted = True
            return b""


# =============================================================================
# Incremental Gzip Decompressor
# =============================================================================

class IncrementalGzipDecompressor:
    """Decompresses gzip data incrementally."""
    
    def __init__(self):
        # 16 + MAX_WBITS tells zlib to expect gzip format
        self.decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
        self.buffer = b""
        self.bytes_decompressed = 0
        self.error = None
    
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


# =============================================================================
# Tar Scanner
# =============================================================================

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
    
    def needs_more_data(self, buffer_size: int) -> bool:
        """Check if we need more data to continue scanning."""
        return self.current_offset + 512 > buffer_size


# =============================================================================
# File Extraction and Saving
# =============================================================================

def extract_and_save(
    data: bytes,
    content_offset: int,
    content_size: int,
    target_path: str,
    output_dir: str
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
    output_path = Path(output_dir) / clean_path
    
    # Create parent directories
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write file
    output_path.write_bytes(content)
    
    return str(output_path)


# =============================================================================
# Main Carving Logic
# =============================================================================

def carve_file(
    namespace: str,
    repo: str,
    tag: str,
    target_path: str,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    verbose: bool = True
) -> Optional[str]:
    """
    Carve a single file from an image layer.
    
    Returns the path where file was saved, or None if not found.
    """
    start_time = time.time()
    
    # Step 1: Authenticate
    print(f"Fetching manifest for {namespace}/{repo}:{tag}...")
    token = fetch_pull_token(namespace, repo)
    if not token:
        print("Failed to get authentication token")
        return None
    
    # Step 2: Get manifest and layers
    layers = fetch_manifest(namespace, repo, tag, token)
    if not layers:
        print("No layers found in manifest")
        return None
    
    print(f"Found {len(layers)} layer(s). Searching for {target_path}...")
    
    # Step 3: Scan each layer
    for i, layer in enumerate(layers):
        if verbose:
            print(f"\nScanning layer {i+1}/{len(layers)}: {layer.digest[:20]}...")
            print(f"  Layer size: {layer.size:,} bytes")
        else:
            print(f"Scanning layer {i+1}/{len(layers)}: {layer.digest[:20]}...")
        
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
                    print(f"  Layer is not gzip compressed, skipping")
                    break
            
            # Decompress
            decompressor.feed(compressed)
            
            if decompressor.error:
                if verbose:
                    print(f"  Decompression error: {decompressor.error}")
                break
            
            # Scan for target
            result = scanner.scan(decompressor.get_buffer())
            
            if verbose:
                print(f"  Downloaded: {reader.bytes_downloaded:,}B -> "
                      f"Decompressed: {decompressor.bytes_decompressed:,}B -> "
                      f"Entries: {scanner.entries_scanned}")
            
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
                    if verbose:
                        print(f"  Fetching more for file content... "
                              f"Have {len(buffer):,} / need {bytes_needed:,}")
                
                buffer = decompressor.get_buffer()
                if len(buffer) >= bytes_needed:
                    # Found and have full content!
                    print(f"  FOUND: {target_path} ({result.content_size:,} bytes) "
                          f"at entry #{result.entries_scanned}")
                    
                    # Extract and save
                    saved_path = extract_and_save(
                        buffer,
                        result.content_offset,
                        result.content_size,
                        target_path,
                        output_dir
                    )
                    
                    elapsed = time.time() - start_time
                    efficiency = (reader.bytes_downloaded / layer.size * 100) if layer.size else 0
                    
                    print(f"\nDone! File saved to: {saved_path}")
                    print(f"Stats: Downloaded {reader.bytes_downloaded:,} bytes "
                          f"of {layer.size:,} byte layer ({efficiency:.1f}%) "
                          f"in {elapsed:.2f}s")
                    
                    return saved_path
                else:
                    print(f"  ERROR: Found file but couldn't get full content")
                    print(f"    Have {len(buffer):,} bytes, need {bytes_needed:,}")
    
    elapsed = time.time() - start_time
    print(f"\nFile not found: {target_path} (searched {len(layers)} layers in {elapsed:.2f}s)")
    return None


# =============================================================================
# CLI Entry Point
# =============================================================================

def parse_image_ref(image_ref: str) -> tuple[str, str, str]:
    """
    Parse image reference into namespace, repo, and tag.
    
    Examples:
        "nginx" -> ("library", "nginx", "latest")
        "nginx:alpine" -> ("library", "nginx", "alpine")
        "library/ubuntu:24.04" -> ("library", "ubuntu", "24.04")
        "aciliadevops/disney-local-web:latest" -> ("aciliadevops", "disney-local-web", "latest")
    """
    # Split off tag first
    if ":" in image_ref:
        image_part, tag = image_ref.rsplit(":", 1)
    else:
        image_part = image_ref
        tag = "latest"
    
    # Then split namespace/repo
    if "/" in image_part:
        parts = image_part.split("/", 1)
        return parts[0], parts[1], tag
    else:
        # Official images are under "library" namespace
        return "library", image_part, tag


def main():
    parser = argparse.ArgumentParser(
        description="Extract a single file from a Docker image layer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python carve-file-from-layer.py ubuntu:24.04 /etc/passwd
  python carve-file-from-layer.py nginx:alpine /etc/nginx/nginx.conf
  python carve-file-from-layer.py alpine:edge /etc/os-release
  python carve-file-from-layer.py aciliadevops/disney-local-web:latest /etc/passwd
  python carve-file-from-layer.py alpine /etc/os-release  # defaults to :latest
        """
    )
    
    parser.add_argument(
        "image",
        help="Docker image reference (e.g., 'ubuntu:24.04', 'nginx:alpine', 'user/repo:tag')"
    )
    parser.add_argument(
        "filepath",
        help="Target file path in container (e.g., '/etc/passwd')"
    )
    parser.add_argument(
        "--output-dir", "-o",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})"
    )
    parser.add_argument(
        "--chunk-size", "-c",
        type=int,
        default=DEFAULT_CHUNK_SIZE // 1024,
        help=f"Fetch chunk size in KB (default: {DEFAULT_CHUNK_SIZE // 1024})"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress detailed progress output"
    )
    
    args = parser.parse_args()
    
    # Parse image reference
    namespace, repo, tag = parse_image_ref(args.image)
    
    # Run carve
    result = carve_file(
        namespace=namespace,
        repo=repo,
        tag=tag,
        target_path=args.filepath,
        output_dir=args.output_dir,
        chunk_size=args.chunk_size * 1024,
        verbose=not args.quiet,
    )
    
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()

"""
List all files in a Docker Hub container image using partial streaming.

Enumerates all layers and iterates through them to build a complete
filesystem listing, using HTTP Range requests to minimize bandwidth.

Usage:
    python experiments/list_dockerhub_container_files.py aciliadevops/disney-local-web:latest

Based on the streaming approach proven in experiments/success/streampartial/test_partial_tar.py
"""

import argparse
import sys
import time
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.api.layerslayer.parser import TarEntry, parse_tar_header


# =============================================================================
# Configuration
# =============================================================================

DEFAULT_INITIAL_BYTES = 262144  # 256KB - good balance for file listings


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
# Image Reference Parsing
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
    if ":" in image_ref:
        image_part, tag = image_ref.rsplit(":", 1)
    else:
        image_part = image_ref
        tag = "latest"
    
    if "/" in image_part:
        parts = image_part.split("/", 1)
        return parts[0], parts[1], tag
    else:
        return "library", image_part, tag


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
        target = None
        for m in manifests:
            platform = m.get("platform", {})
            if platform.get("architecture") == "amd64" and platform.get("os") == "linux":
                target = m
                break
        if not target and manifests:
            target = manifests[0]
        
        if target:
            digest = target.get("digest")
            url = f"{registry_base_url(namespace, repo)}/manifests/{digest}"
            resp = _session.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            manifest = resp.json()
    
    layers = []
    for layer in manifest.get("layers", []):
        layers.append(LayerInfo(
            digest=layer.get("digest", ""),
            size=layer.get("size", 0),
            media_type=layer.get("mediaType", ""),
        ))
    
    return layers


# =============================================================================
# Partial Layer Streaming
# =============================================================================

@dataclass
class FileEntry:
    """A file entry with its source layer digest."""
    entry: TarEntry
    layer_digest: str
    layer_index: int  # 0-based layer index


@dataclass
class LayerPeekResult:
    """Result of peeking into a layer."""
    digest: str
    bytes_downloaded: int
    bytes_decompressed: int
    entries: list[TarEntry]
    partial: bool  # True if we didn't read the full layer
    error: Optional[str] = None


def peek_layer(
    namespace: str,
    repo: str,
    digest: str,
    token: str,
    initial_bytes: int = DEFAULT_INITIAL_BYTES,
    verbose: bool = False
) -> LayerPeekResult:
    """
    Fetch only the first N bytes of a layer using HTTP Range request,
    decompress, and parse tar headers.
    
    Returns partial file listing without downloading the full layer.
    """
    url = f"{registry_base_url(namespace, repo)}/blobs/{digest}"
    
    if verbose:
        print(f"  Fetching first {initial_bytes:,} bytes...")
    
    # Use HTTP Range header to fetch only first N bytes
    headers = {
        "Authorization": f"Bearer {token}",
        "Range": f"bytes=0-{initial_bytes - 1}"
    }
    
    try:
        resp = _session.get(url, headers=headers, stream=True, timeout=30)
        resp.raise_for_status()
        
        # Read the partial data
        compressed_data = resp.raw.read(initial_bytes)
        resp.close()
    except requests.RequestException as e:
        return LayerPeekResult(
            digest=digest,
            bytes_downloaded=0,
            bytes_decompressed=0,
            entries=[],
            partial=True,
            error=str(e),
        )
    
    if verbose:
        print(f"  Downloaded: {len(compressed_data):,} bytes")
    
    # Check gzip magic (0x1f 0x8b)
    if len(compressed_data) < 2 or compressed_data[0:2] != b'\x1f\x8b':
        return LayerPeekResult(
            digest=digest,
            bytes_downloaded=len(compressed_data),
            bytes_decompressed=0,
            entries=[],
            partial=True,
            error="Not a gzip file",
        )
    
    # Decompress what we have
    try:
        decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
        decompressed = decompressor.decompress(compressed_data)
    except zlib.error as e:
        return LayerPeekResult(
            digest=digest,
            bytes_downloaded=len(compressed_data),
            bytes_decompressed=0,
            entries=[],
            partial=True,
            error=f"Decompression error: {e}",
        )
    
    if verbose:
        print(f"  Decompressed: {len(decompressed):,} bytes")
    
    if len(decompressed) < 512:
        return LayerPeekResult(
            digest=digest,
            bytes_downloaded=len(compressed_data),
            bytes_decompressed=len(decompressed),
            entries=[],
            partial=True,
            error="Not enough decompressed data",
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
            break
        offset = next_offset
    
    if verbose:
        print(f"  Found {len(entries)} entries")
    
    return LayerPeekResult(
        digest=digest,
        bytes_downloaded=len(compressed_data),
        bytes_decompressed=len(decompressed),
        entries=entries,
        partial=True,
    )


# =============================================================================
# Main Listing Logic
# =============================================================================

def short_digest(digest: str) -> str:
    """Return shortened digest (first 12 chars after sha256:)."""
    if digest.startswith("sha256:"):
        return digest[7:19]
    return digest[:12]


def list_container_files(
    image_ref: str,
    initial_bytes: int = DEFAULT_INITIAL_BYTES,
    verbose: bool = True,
    show_all: bool = False
) -> list[FileEntry]:
    """
    List all files in a Docker container image.
    
    Iterates through all layers and builds a complete filesystem listing.
    
    Args:
        image_ref: Docker image reference (e.g., "ubuntu:24.04")
        initial_bytes: How many bytes to fetch per layer
        verbose: Show detailed progress
        show_all: Show all entries from all layers (vs merged view)
    
    Returns:
        List of all FileEntry objects (TarEntry + layer digest)
    """
    start_time = time.time()
    
    # Parse image reference
    namespace, repo, tag = parse_image_ref(image_ref)
    
    print(f"Listing files in: {namespace}/{repo}:{tag}")
    print("="*60)
    
    # Authenticate
    print(f"\nAuthenticating with Docker Hub...")
    token = fetch_pull_token(namespace, repo)
    if not token:
        print("Failed to get authentication token")
        return []
    
    # Get manifest
    print(f"Fetching manifest...")
    layers = fetch_manifest(namespace, repo, tag, token)
    if not layers:
        print("No layers found")
        return []
    
    total_layer_size = sum(l.size for l in layers)
    print(f"Found {len(layers)} layer(s), total size: {total_layer_size:,} bytes ({total_layer_size/1024/1024:.1f} MB)")
    
    # Iterate through all layers
    all_entries: list[FileEntry] = []
    total_bytes_downloaded = 0
    
    print(f"\nScanning layers (fetching {initial_bytes//1024}KB per layer)...")
    
    for i, layer in enumerate(layers):
        print(f"\nLayer {i+1}/{len(layers)}: {layer.digest[:20]}...")
        print(f"  Size: {layer.size:,} bytes ({layer.size/1024/1024:.1f} MB)")
        
        result = peek_layer(
            namespace, repo, layer.digest, token,
            initial_bytes=initial_bytes,
            verbose=verbose
        )
        
        if result.error:
            print(f"  Error: {result.error}")
            continue
        
        total_bytes_downloaded += result.bytes_downloaded
        
        # Wrap each entry with layer info
        for entry in result.entries:
            all_entries.append(FileEntry(
                entry=entry,
                layer_digest=layer.digest,
                layer_index=i,
            ))
        
        print(f"  Entries found: {len(result.entries)}")
    
    elapsed = time.time() - start_time
    
    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Image: {namespace}/{repo}:{tag}")
    print(f"Layers scanned: {len(layers)}")
    print(f"Total entries found: {len(all_entries)}")
    print(f"Bytes downloaded: {total_bytes_downloaded:,} ({total_bytes_downloaded/1024:.1f} KB)")
    print(f"Total layer size: {total_layer_size:,} ({total_layer_size/1024/1024:.1f} MB)")
    print(f"Efficiency: {total_bytes_downloaded/total_layer_size*100:.2f}% of layers downloaded")
    print(f"Time elapsed: {elapsed:.2f}s")
    
    # Print file listing with layer digest
    print(f"\n{'='*60}")
    print(f"FILE LISTING ({len(all_entries)} entries)")
    print(f"{'='*60}")
    print(f"{'Layer':<14} {'Type':<6} {'Mode':<11} {'Size':>10}  Path")
    print(f"{'-'*14} {'-'*6} {'-'*11} {'-'*10}  {'-'*30}")
    
    for file_entry in all_entries:
        entry = file_entry.entry
        digest_short = short_digest(file_entry.layer_digest)
        
        type_str = "DIR" if entry.is_dir else "FILE"
        if entry.is_symlink:
            type_str = "LINK"
        
        size_str = f"{entry.size:>10,}" if not entry.is_dir else "         -"
        
        if entry.is_symlink and entry.linkname:
            print(f"{digest_short:<14} {type_str:<6} {entry.mode} {size_str}  {entry.name} -> {entry.linkname}")
        else:
            print(f"{digest_short:<14} {type_str:<6} {entry.mode} {size_str}  {entry.name}")
    
    return all_entries


# =============================================================================
# CLI Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="List all files in a Docker Hub container image",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python list_dockerhub_container_files.py ubuntu:24.04
  python list_dockerhub_container_files.py nginx:alpine
  python list_dockerhub_container_files.py aciliadevops/disney-local-web:latest
  python list_dockerhub_container_files.py alpine --bytes 512
        """
    )
    
    parser.add_argument(
        "image",
        help="Docker image reference (e.g., 'ubuntu:24.04', 'user/repo:tag')"
    )
    parser.add_argument(
        "--bytes", "-b",
        type=int,
        default=DEFAULT_INITIAL_BYTES // 1024,
        help=f"KB to fetch per layer (default: {DEFAULT_INITIAL_BYTES // 1024})"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress verbose output"
    )
    
    args = parser.parse_args()
    
    list_container_files(
        image_ref=args.image,
        initial_bytes=args.bytes * 1024,
        verbose=not args.quiet,
    )


if __name__ == "__main__":
    main()

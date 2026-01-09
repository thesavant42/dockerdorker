"""
Partial tar.gz streaming experiment - Docker Hub Production Version.

Goal: Parse tar headers from the FIRST N KB of a layer blob from Docker Hub,
then close the connection - getting a partial file listing
without downloading the full layer.

This is a production-ready version of test_partial_tar.py that uses
Docker Hub's registry API with proper JWT authentication.

Usage:
    python experiments/success/streampartial/test_partial_tar_dockerhub.py
    python experiments/success/streampartial/test_partial_tar_dockerhub.py ubuntu:24.04
    python experiments/success/streampartial/test_partial_tar_dockerhub.py nginx:alpine
"""

import sys
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.api.layerslayer.parser import TarEntry, parse_tar_header


# =============================================================================
# Configuration
# =============================================================================

# Default test image
DEFAULT_IMAGE = "alpine:edge"


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

def peek_layer(
    namespace: str,
    repo: str,
    digest: str,
    token: str,
    initial_bytes: int = 65536
) -> list[TarEntry]:
    """
    Fetch only the first N bytes of a layer using HTTP Range request,
    decompress, and parse tar headers.
    
    This gives us a partial file listing without downloading the full layer.
    """
    url = f"{registry_base_url(namespace, repo)}/blobs/{digest}"
    
    print(f"Fetching first {initial_bytes:,} bytes from {url[:60]}...")
    
    # Use HTTP Range header to fetch only first N bytes
    headers = {
        "Authorization": f"Bearer {token}",
        "Range": f"bytes=0-{initial_bytes - 1}"
    }
    
    resp = _session.get(url, headers=headers, stream=True, timeout=30)
    
    # Check if server supports Range requests
    if resp.status_code == 206:
        print(f"Server supports Range requests (206 Partial Content)")
    elif resp.status_code == 200:
        print(f"Server returned full content (no Range support), reading first {initial_bytes} bytes")
    
    # Read only what we need
    compressed_data = resp.raw.read(initial_bytes)
    resp.close()
    
    print(f"Downloaded: {len(compressed_data):,} bytes")
    
    # Check gzip magic (0x1f 0x8b)
    if len(compressed_data) < 2:
        print("Not enough data")
        return []
    
    if compressed_data[0:2] != b'\x1f\x8b':
        print(f"Not gzip: magic bytes are {compressed_data[0:2].hex()}")
        return []
    
    print("Found gzip magic bytes")
    
    # Decompress what we have
    try:
        decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)  # 16 = gzip format
        decompressed = decompressor.decompress(compressed_data)
        print(f"Decompressed: {len(decompressed):,} bytes")
    except zlib.error as e:
        print(f"Decompression error (expected for partial data): {e}")
        # Try with what we got before error
        decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
        decompressed = b""
        try:
            decompressed = decompressor.decompress(compressed_data)
        except:
            pass
        print(f"Partial decompression got: {len(decompressed):,} bytes")
    
    if len(decompressed) < 512:
        print("Not enough decompressed data for tar header")
        return []
    
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
    
    return entries


def test_varying_sizes(namespace: str, repo: str, digest: str, layer_size: int, token: str):
    """Test with different initial byte sizes to find minimum needed."""
    sizes = [8192, 16384, 32768, 65536, 131072, 262144]
    
    for size in sizes:
        print(f"\n{'='*60}")
        print(f"Testing with {size:,} bytes ({size/1024:.0f} KB)")
        print(f"{'='*60}")
        
        entries = peek_layer(namespace, repo, digest, token, initial_bytes=size)
        
        print(f"\nFound {len(entries)} entries:")
        for i, e in enumerate(entries):
            type_str = "[DIR] " if e.is_dir else "[FILE]"
            print(f"  {type_str} {e.name} ({e.size:,} bytes)")
        
        # Calculate efficiency
        efficiency = (size / layer_size * 100) if layer_size else 0
        print(f"\nEfficiency: Downloaded {size:,} of {layer_size:,} bytes ({efficiency:.2f}%)")


def main():
    # Parse command line argument or use default
    if len(sys.argv) > 1:
        image_ref = sys.argv[1]
    else:
        image_ref = DEFAULT_IMAGE
    
    namespace, repo, tag = parse_image_ref(image_ref)
    
    print(f"Testing partial tar streaming with: {namespace}/{repo}:{tag}")
    print("="*60)
    
    # Authenticate
    print(f"\nFetching auth token for {namespace}/{repo}...")
    token = fetch_pull_token(namespace, repo)
    if not token:
        print("Failed to get authentication token")
        sys.exit(1)
    print("Got auth token")
    
    # Get manifest
    print(f"\nFetching manifest for {tag}...")
    layers = fetch_manifest(namespace, repo, tag, token)
    if not layers:
        print("No layers found")
        sys.exit(1)
    
    print(f"Found {len(layers)} layer(s)")
    
    # Test with first layer
    layer = layers[0]
    print(f"\nUsing layer: {layer.digest[:40]}...")
    print(f"Layer size: {layer.size:,} bytes ({layer.size/1024/1024:.1f} MB)")
    
    # Run tests with varying sizes
    test_varying_sizes(namespace, repo, layer.digest, layer.size, token)


if __name__ == "__main__":
    main()

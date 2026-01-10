"""
Layerslayer module for docker-dorker.

Provides partial layer peek functionality using HTTP Range requests
to fetch only the first 8-64KB of a layer blob, decompress, and parse
tar headers for a file listing preview without downloading the full layer.

Key insight: 8KB download → 41 files discovered from a 30MB layer (0.027% of data)

Layer Slayer mode: Peek ALL layers for an image and cache the filesystem metadata.
"""

from app.core.api.layerslayer.parser import TarEntry, parse_tar_header
from app.core.api.layerslayer.fetcher import (
    LayerPeekResult,
    LayerSlayerResult,
    peek_layer_blob_partial,
    peek_layer_blob_streaming,
    layerslayer,
)

__all__ = [
    "TarEntry",
    "parse_tar_header",
    "LayerPeekResult",
    "LayerSlayerResult",
    "peek_layer_blob_partial",
    "peek_layer_blob_streaming",
    "layerslayer",
]

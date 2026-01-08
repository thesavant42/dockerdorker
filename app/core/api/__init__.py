"""
Docker Hub API shared constants and re-exports.
"""

# Re-export constants
from app.core.api.constants import HEADERS, RATE_LIMIT_DELAY

# Re-export from dockerhub_fetch
from app.core.api.dockerhub_fetch import fetch_page, BASE_URL, MAX_RETRIES, BACKOFF_DELAYS

# Re-export from dockerhub_parse
from app.core.api.dockerhub_parse import resolve_value, parse_result, parse_response

# Re-export from dockerhub_search
from app.core.api.dockerhub_search import search

# Re-export from dockerhub_v2_api
from app.core.api.dockerhub_v2_api import fetch_all_tags, fetch_tag_images, TAGS_BASE_URL

# Re-export from layer utilities (partial layer peek with HTTP Range requests)
from app.core.utils.tar_parser import TarEntry, parse_tar_header
from app.core.utils.layer_fetcher import (
    LayerPeekResult,
    peek_layer_blob_partial,
    peek_layer_blob_streaming,
)

__all__ = [
    # Constants
    "HEADERS",
    "RATE_LIMIT_DELAY",
    # dockerhub_fetch
    "fetch_page",
    "BASE_URL",
    "MAX_RETRIES",
    "BACKOFF_DELAYS",
    # dockerhub_parse
    "resolve_value",
    "parse_result",
    "parse_response",
    # dockerhub_search
    "search",
    # dockerhub_v2_api
    "fetch_all_tags",
    "fetch_tag_images",
    "TAGS_BASE_URL",
    # layer utilities
    "TarEntry",
    "parse_tar_header",
    "LayerPeekResult",
    "peek_layer_blob_partial",
    "peek_layer_blob_streaming",
]

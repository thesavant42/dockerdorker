"""
Docker Hub API shared constants and re-exports.
"""

# Exact headers from original implementation - DO NOT MODIFY
HEADERS = {
    "Host": "hub.docker.com",
    "Cookie": "search-dialog-recent-searches=WyJkaXNuZXkiXQ%3D%3D",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Referer": "https://hub.docker.com/u/ai",
    "Accept-Encoding": "gzip, deflate, br",
}

RATE_LIMIT_DELAY = 0.5  # seconds between requests

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

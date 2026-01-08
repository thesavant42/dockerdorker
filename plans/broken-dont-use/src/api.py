"""
Docker Hub API client for docker-dorker.
Handles search requests with rate limiting and caching.
"""

# Re-export from dockerhub_fetch
from src.api.dockerhub_fetch import fetch_page, BASE_URL, MAX_RETRIES, BACKOFF_DELAYS

# Re-export from dockerhub_parse
from src.api.dockerhub_parse import resolve_value, parse_result, parse_response

# Re-export from dockerhub_search
from src.api.dockerhub_search import search

# Re-export from dockerhub_v2_api
from src.api.dockerhub_v2_api import fetch_all_tags, fetch_tag_images, TAGS_BASE_URL

# Re-export shared constants (imported from package __init__.py)
from src.api import HEADERS, RATE_LIMIT_DELAY

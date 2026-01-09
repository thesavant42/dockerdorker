"""
Docker Hub HTTP fetching functions.
Handles search page fetching with retry backoff.
"""

import time
from typing import Any

import requests

from app.core.api import HEADERS

BASE_URL = "https://hub.docker.com/search.data"
MAX_RETRIES = 3
BACKOFF_DELAYS = [1, 2, 4, 8]  # progressive backoff

proxies = {
    'http': 'http://localhost:8080',
    'https': 'http://localhost:8080',
}

def fetch_page(query: str, page: int = 1) -> requests.Response:
    """Fetch a single page of search results with retry backoff."""
    params = {
        "q": query,
        "sort": "updated_at",
        "order": "desc",
        "page": page,
    }

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(BASE_URL, params=params, headers=HEADERS, proxies=proxies, verify=False)
            response.raise_for_status()
            return response
        except (requests.RequestException, OSError) as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                delay = BACKOFF_DELAYS[min(attempt, len(BACKOFF_DELAYS) - 1)]
                time.sleep(delay)

    raise last_error

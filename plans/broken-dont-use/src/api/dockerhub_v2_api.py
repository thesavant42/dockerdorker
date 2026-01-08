"""
Docker Hub v2 API client functions.
Handles repository tags and image config fetching.
"""

import time
from typing import Dict, List

import requests

from src.api import HEADERS, RATE_LIMIT_DELAY

TAGS_BASE_URL = "https://hub.docker.com/v2/repositories"


def fetch_all_tags(namespace: str, repo: str, progress_callback=None) -> List[Dict]:
    """Fetch all tags for a repository, paginating through all pages."""
    all_tags = []
    page = 1
    page_size = 100
    total_count = None
    
    while True:
        url = f"{TAGS_BASE_URL}/{namespace}/{repo}/tags"
        params = {"page": page, "page_size": page_size}
        
        if progress_callback:
            progress_callback(f"Fetching tags page {page}...", len(all_tags), total_count or 0)
        
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        data = response.json()
        
        # First page gives us total count
        if total_count is None:
            total_count = data.get("count", 0)
        
        # Add results from this page
        all_tags.extend(data.get("results", []))
        
        # Stop when we have all tags OR no next page
        if len(all_tags) >= total_count or not data.get("next"):
            break
        
        page += 1
        time.sleep(RATE_LIMIT_DELAY)
    
    return all_tags


def fetch_tag_images(namespace: str, repo: str, tag_name: str) -> List[Dict]:
    """Fetch image configs for a specific tag."""
    url = f"{TAGS_BASE_URL}/{namespace}/{repo}/tags/{tag_name}/images"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()

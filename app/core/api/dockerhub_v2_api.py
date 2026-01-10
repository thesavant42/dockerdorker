"""
Docker Hub v2 API client functions.
Handles repository tags and image config fetching.
"""

import time
from typing import Dict, List, Optional

import requests

from app.core.api import HEADERS, RATE_LIMIT_DELAY
from app.core.database import get_database

TAGS_BASE_URL = "https://hub.docker.com/v2/repositories"


def fetch_all_tags(namespace: str, repo: str, progress_callback=None) -> List[Dict]:
    """Fetch all tags for a repository, paginating through all pages.
    
    Checks database cache first, returns cached data if valid (< 24 hours old).
    Otherwise fetches from Docker Hub and saves to cache.
    """
    db = get_database()
    
    # Check cache first
    if db.repository_cache_valid(namespace, repo):
        cached_tags = db.get_cached_tags(namespace, repo)
        if cached_tags:
            return cached_tags
    
    # Cache miss or expired - fetch from API
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
    
    # Save to cache
    repository_id = db.get_or_create_repository(namespace, repo)
    db.save_repository_tags(repository_id, all_tags)
    db.update_repository_fetched(repository_id)
    
    return all_tags


def fetch_tag_images(namespace: str, repo: str, tag_name: str) -> List[Dict]:
    """Fetch image configs for a specific tag.
    
    Checks database cache first for this tag. If cached, returns cached data.
    Otherwise fetches from Docker Hub and saves to cache.
    """
    db = get_database()
    repository_id = db.get_or_create_repository(namespace, repo)
    
    # Check for cached image configs for this tag
    cached_configs = db.get_cached_image_configs(repository_id)
    tag_configs = [(t, img) for t, img in cached_configs if t == tag_name]
    
    if tag_configs:
        # Return cached configs as list of dicts (matching API response format)
        return [img for _, img in tag_configs]
    
    # Cache miss - fetch from API
    url = f"{TAGS_BASE_URL}/{namespace}/{repo}/tags/{tag_name}/images"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    images = response.json()
    
    # Handle both list and dict responses
    if isinstance(images, dict):
        images_list = images.get("results", images.get("images", []))
    else:
        images_list = images if isinstance(images, list) else []
    
    # Save each image config to cache
    for image in images_list:
        if isinstance(image, dict):
            db.save_image_config(repository_id, tag_name, image)
    
    return images_list


def get_image_layers_for_peek(namespace: str, repo: str, tag_name: str) -> List[Dict]:
    """Get layer digests from tag images, filtered for peek.
    
    Fetches image configs for a tag and extracts layers that have
    actual content (digest and size > 0).
    
    Args:
        namespace: Docker Hub namespace
        repo: Repository name
        tag_name: Tag name
        
    Returns:
        List of layer dicts with digest, size, and instruction fields
    """
    images = fetch_tag_images(namespace, repo, tag_name)
    if not images:
        return []
    
    # Pick first image (usually amd64/linux)
    image = images[0]
    layers = image.get("layers", [])
    
    # Filter to layers with digests (actual content layers)
    return [l for l in layers if l.get("digest") and l.get("size", 0) > 0]
"""
Docker Hub search orchestration.
Handles search requests with caching and pagination.
"""

import math
import time
from typing import Dict, Any

from app.core.api import RATE_LIMIT_DELAY
from app.core.api.dockerhub_fetch import fetch_page
from app.core.api.dockerhub_parse import parse_response
from app.core.database import get_database


def search(query: str) -> Dict[str, Any]:
    """Search Docker Hub with caching. Returns dict with query, total, results, cached flag.
    
    This function runs synchronously (typically in a background thread).
    All pagination happens here without callbacks to avoid thread safety issues.
    """
    # Check cache first
    db = get_database()
    cached_results = db.get_cached_results(query)

    if cached_results:
        db.close()
        return cached_results

    # Fetch page 1
    response = fetch_page(query, page=1)
    data = response.json()

    parsed = parse_response(data)
    total = parsed["total"]
    page_size = parsed["page_size"]
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    all_results = parsed["results"]

    # Fetch remaining pages (no callbacks - just like standalone module)
    for page in range(2, total_pages + 1):
        time.sleep(RATE_LIMIT_DELAY)
        response = fetch_page(query, page=page)
        data = response.json()
        parsed = parse_response(data)
        all_results.extend(parsed["results"])

    # Build results dictionary
    results = {
        "query": query,
        "total": total,
        "total_pages": total_pages,
        "results": all_results,
        "cached": False
    }

    # Save to cache
    db.save_search_results(query, results)
    db.close()

    return results

"""
Docker Hub API shared constants.
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

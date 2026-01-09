#!/usr/bin/env python3
"""
Standalone Docker Hub repository enumeration script.
Self-contained - no external dependencies beyond 'requests'.

Given a repository address (owner/repo), this script:
- Detects if the owner is an Organization or User
- Fetches owner profile information
- Fetches repository metadata
- Fetches all tags with platform information

Usage:
    python tag-and-enum.py aswindapp/natgeo-mail
    python tag-and-enum.py homedepottech/github-webhook-resource
"""

import argparse
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import requests

# --- Constants ---

HEADERS = {
    "Host": "hub.docker.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Encoding": "gzip, deflate, br",
}

BASE_URL = "https://hub.docker.com/v2"
MAX_RETRIES = 3
BACKOFF_DELAYS = [1, 2, 4]
RATE_LIMIT_DELAY = 0.3


# --- HTTP Fetching ---

def fetch_with_retry(
    url: str,
    allow_redirects: bool = True,
    headers: Optional[Dict] = None
) -> requests.Response:
    """Fetch a URL with retry backoff."""
    req_headers = {**HEADERS, **(headers or {})}
    
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(
                url,
                headers=req_headers,
                allow_redirects=allow_redirects,
                timeout=30
            )
            return response
        except requests.RequestException as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                delay = BACKOFF_DELAYS[min(attempt, len(BACKOFF_DELAYS) - 1)]
                print(f"  Retry {attempt + 1}/{MAX_RETRIES} after {delay}s...", file=sys.stderr)
                time.sleep(delay)
    
    raise last_error


# --- Input Parsing ---

def parse_repo_input(input_str: str) -> Tuple[str, str]:
    """
    Parse repository input into owner and repository name.
    
    Accepts formats:
        - owner/repo
        - https://hub.docker.com/v2/repositories/owner/repo
        - https://hub.docker.com/r/owner/repo
    
    Returns: (owner, repository)
    """
    # Strip whitespace
    input_str = input_str.strip()
    
    # Handle full URLs
    if input_str.startswith("https://hub.docker.com"):
        # Extract path after hub.docker.com
        path = input_str.replace("https://hub.docker.com", "")
        
        # Handle /v2/repositories/owner/repo format
        if path.startswith("/v2/repositories/"):
            path = path[len("/v2/repositories/"):]
        # Handle /r/owner/repo format
        elif path.startswith("/r/"):
            path = path[len("/r/"):]
        
        # Remove trailing slashes and query params
        path = path.rstrip("/").split("?")[0]
        input_str = path
    
    # Now we should have owner/repo
    if "/" not in input_str:
        print(f"Error: Invalid input '{input_str}'. Expected format: owner/repo", file=sys.stderr)
        sys.exit(1)
    
    parts = input_str.split("/")
    if len(parts) < 2:
        print(f"Error: Invalid input '{input_str}'. Expected format: owner/repo", file=sys.stderr)
        sys.exit(1)
    
    return parts[0], parts[1]


# --- Owner Info Functions ---

def get_owner_info(owner: str) -> Dict[str, Any]:
    """
    Fetch owner information by first trying /orgs/, then /users/ if redirected.
    
    Returns dict with owner info including 'type' field (Organization or User).
    """
    print(f"Fetching owner info for: {owner}", file=sys.stderr)
    
    # First, probe /v2/orgs/{owner} without following redirects
    org_url = f"{BASE_URL}/orgs/{owner}/"
    
    try:
        response = fetch_with_retry(org_url, allow_redirects=False)
        
        if response.status_code == 200:
            # It's an organization
            data = response.json()
            data["_owner_type"] = "Organization"
            print(f"  Owner type: Organization", file=sys.stderr)
            return data
        
        elif response.status_code == 308:
            # Permanent redirect to /users/
            location = response.headers.get("Location", "")
            print(f"  Redirected to: {location}", file=sys.stderr)
            
            # Fetch user info
            if "/users/" in location:
                user_url = f"{BASE_URL}/users/{owner}/"
                response = fetch_with_retry(user_url)
                
                if response.status_code == 200:
                    data = response.json()
                    data["_owner_type"] = "User"
                    print(f"  Owner type: User", file=sys.stderr)
                    return data
        
        elif response.status_code == 404:
            print(f"  Owner not found: {owner}", file=sys.stderr)
            return {"_owner_type": "Unknown", "_error": "Not found"}
        
        else:
            print(f"  Unexpected status: {response.status_code}", file=sys.stderr)
            return {"_owner_type": "Unknown", "_error": f"HTTP {response.status_code}"}
    
    except requests.RequestException as e:
        print(f"  Error fetching owner info: {e}", file=sys.stderr)
        return {"_owner_type": "Unknown", "_error": str(e)}
    
    return {"_owner_type": "Unknown"}


# --- Repository Info Functions ---

def get_repository_info(owner: str, repo: str) -> Dict[str, Any]:
    """Fetch repository metadata."""
    print(f"Fetching repository info for: {owner}/{repo}", file=sys.stderr)
    
    url = f"{BASE_URL}/repositories/{owner}/{repo}/"
    
    try:
        response = fetch_with_retry(url)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            print(f"  Repository not found: {owner}/{repo}", file=sys.stderr)
            return {"_error": "Not found"}
        else:
            print(f"  Unexpected status: {response.status_code}", file=sys.stderr)
            return {"_error": f"HTTP {response.status_code}"}
    
    except requests.RequestException as e:
        print(f"  Error fetching repository info: {e}", file=sys.stderr)
        return {"_error": str(e)}


# --- Tags Functions ---

def get_tags(owner: str, repo: str, page_size: int = 100) -> List[Dict[str, Any]]:
    """
    Fetch all tags for a repository, handling pagination.
    
    Uses the /v2/namespaces/{owner}/repositories/{repo}/tags endpoint.
    """
    print(f"Fetching tags for: {owner}/{repo}", file=sys.stderr)
    
    all_tags = []
    page = 1
    
    while True:
        url = (
            f"{BASE_URL}/namespaces/{owner}/repositories/{repo}/tags"
            f"?platforms=true&page_size={page_size}&page={page}&ordering=last_updated"
        )
        
        try:
            response = fetch_with_retry(url)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                all_tags.extend(results)
                
                print(f"  Page {page}: {len(results)} tags", file=sys.stderr)
                
                # Check for more pages
                if data.get("next"):
                    page += 1
                    time.sleep(RATE_LIMIT_DELAY)
                else:
                    break
            elif response.status_code == 404:
                print(f"  Tags endpoint not found", file=sys.stderr)
                break
            else:
                print(f"  Unexpected status: {response.status_code}", file=sys.stderr)
                break
        
        except requests.RequestException as e:
            print(f"  Error fetching tags: {e}", file=sys.stderr)
            break
    
    print(f"  Total tags: {len(all_tags)}", file=sys.stderr)
    return all_tags


# --- Formatting Functions ---

def format_size(size_bytes: Optional[int]) -> str:
    """Format byte size with appropriate unit."""
    if size_bytes is None:
        return "-"
    
    if size_bytes >= 1_000_000_000:
        return f"{size_bytes / 1_000_000_000:.2f} GB"
    elif size_bytes >= 1_000_000:
        return f"{size_bytes / 1_000_000:.2f} MB"
    elif size_bytes >= 1_000:
        return f"{size_bytes / 1_000:.2f} KB"
    else:
        return f"{size_bytes} B"


def format_count(count: Optional[int]) -> str:
    """Format large numbers with K/M/B suffix."""
    if count is None:
        return "-"
    
    if count >= 1_000_000_000:
        return f"{count / 1_000_000_000:.1f}B"
    elif count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    elif count >= 1_000:
        return f"{count / 1_000:.1f}K"
    else:
        return str(count)


def format_date(date_str: Optional[str]) -> str:
    """Format ISO date string to a shorter format."""
    if not date_str:
        return "-"
    
    # Return first 19 chars (YYYY-MM-DDTHH:MM:SS)
    return date_str[:19].replace("T", " ")




# --- Table Printing Functions ---

def print_separator(width: int = 80) -> None:
    """Print a separator line."""
    print("=" * width)


def print_owner_table(owner_info: Dict[str, Any]) -> None:
    """Print owner information as a formatted table."""
    print_separator()
    print("OWNER INFORMATION")
    print_separator()
    
    owner_type = owner_info.get("_owner_type", "Unknown")
    
    if owner_type == "Organization":
        rows = [
            ("Type", "Organization"),
            ("Org Name", owner_info.get("orgname", "-")),
            ("Full Name", owner_info.get("full_name", "-")),
            ("Company", owner_info.get("company", "-")),
            ("Location", owner_info.get("location", "-")),
            ("Profile URL", owner_info.get("profile_url", "-")),
            ("Date Joined", format_date(owner_info.get("date_joined"))),
            ("Is Active", str(owner_info.get("is_active", "-"))),
            ("Badge", owner_info.get("badge", "-") or "-"),
            ("UUID", owner_info.get("uuid", "-")),
        ]
    elif owner_type == "User":
        rows = [
            ("Type", "User"),
            ("Username", owner_info.get("username", "-")),
            ("Full Name", owner_info.get("full_name", "-") or "-"),
            ("Company", owner_info.get("company", "-") or "-"),
            ("Location", owner_info.get("location", "-") or "-"),
            ("Profile URL", owner_info.get("profile_url", "-") or "-"),
            ("Date Joined", format_date(owner_info.get("date_joined"))),
            ("UUID", owner_info.get("uuid", "-")),
        ]
    else:
        rows = [
            ("Type", "Unknown"),
            ("Error", owner_info.get("_error", "Unknown error")),
        ]
    
    # Calculate column width
    label_width = max(len(row[0]) for row in rows) + 2
    
    for label, value in rows:
        print(f"  {label:<{label_width}}: {value}")
    
    print()


def print_repository_table(repo_info: Dict[str, Any]) -> None:
    """Print repository information as a formatted table."""
    print_separator()
    print("REPOSITORY INFORMATION")
    print_separator()
    
    if "_error" in repo_info:
        print(f"  Error: {repo_info['_error']}")
        print()
        return
    
    rows = [
        ("Namespace", repo_info.get("namespace", "-")),
        ("Name", repo_info.get("name", "-")),
        ("Full Name", f"{repo_info.get('namespace', '')}/{repo_info.get('name', '')}"),
        ("Description", repo_info.get("description", "-") or "(no description)"),
        ("Status", repo_info.get("status_description", "-")),
        ("Repository Type", repo_info.get("repository_type", "-")),
        ("Is Private", str(repo_info.get("is_private", "-"))),
        ("Is Automated", str(repo_info.get("is_automated", "-"))),
        ("Star Count", format_count(repo_info.get("star_count"))),
        ("Pull Count", format_count(repo_info.get("pull_count"))),
        ("Storage Size", format_size(repo_info.get("storage_size"))),
        ("Date Registered", format_date(repo_info.get("date_registered"))),
        ("Last Updated", format_date(repo_info.get("last_updated"))),
        ("Last Modified", format_date(repo_info.get("last_modified"))),
        ("Collaborator Count", str(repo_info.get("collaborator_count", "-"))),
        ("Media Types", ", ".join(repo_info.get("media_types", [])) or "-"),
        ("Content Types", ", ".join(repo_info.get("content_types", [])) or "-"),
    ]
    
    # Calculate column width
    label_width = max(len(row[0]) for row in rows) + 2
    
    for label, value in rows:
        print(f"  {label:<{label_width}}: {value}")
    
    print()


def print_tags_table(tags: List[Dict[str, Any]]) -> None:
    """Print tags as a formatted table."""
    print_separator()
    print(f"TAGS ({len(tags)} total)")
    print_separator()
    
    if not tags:
        print("  No tags found.")
        print()
        return
    
    # Column widths
    name_w = 30
    size_w = 12
    date_w = 19
    digest_w = 20
    status_w = 8
    
    # Header
    header = (
        f"{'Tag Name':<{name_w}} "
        f"{'Size':>{size_w}} "
        f"{'Last Updated':<{date_w}} "
        f"{'Status':<{status_w}} "
        f"{'Digest':<{digest_w}}"
    )
    print(header)
    print("-" * len(header))
    
    for tag in tags:
        name = tag.get("name", "-")
        size = format_size(tag.get("full_size"))
        date = format_date(tag.get("last_updated"))
        status = tag.get("tag_status", "-")
        
        # Get digest, prefer top-level, fall back to first image
        digest = tag.get("digest", "")
        if not digest:
            images = tag.get("images", [])
            if images:
                digest = images[0].get("digest", "")
        
        # Print full values - no truncation
        print(
            f"{name:<{name_w}} "
            f"{size:>{size_w}} "
            f"{date:<{date_w}} "
            f"{status:<{status_w}} "
            f"{digest}"
        )
    
    print()


def print_tag_details(tags: List[Dict[str, Any]]) -> None:
    """Print detailed tag information including platform data."""
    print_separator()
    print("TAG DETAILS (Platforms)")
    print_separator()
    
    if not tags:
        print("  No tags found.")
        print()
        return
    
    for tag in tags:
        name = tag.get("name", "-")
        images = tag.get("images", [])
        
        print(f"\n  Tag: {name}")
        print(f"  Full Size: {format_size(tag.get('full_size'))}")
        print(f"  Last Updated: {format_date(tag.get('last_updated'))}")
        print(f"  Status: {tag.get('tag_status', '-')}")
        
        if images:
            print(f"  Platforms ({len(images)}):")
            for img in images:
                os_name = img.get("os", "?")
                arch = img.get("architecture", "?")
                variant = img.get("variant", "")
                size = format_size(img.get("size"))
                
                platform_str = f"{os_name}/{arch}"
                if variant:
                    platform_str += f"/{variant}"
                
                digest = img.get("digest", "")
                if digest.startswith("sha256:"):
                    digest_short = digest[7:19]
                else:
                    digest_short = digest[:12]
                
                print(f"    - {platform_str:<20} {size:>12}  {digest_short}")
        
        print()


# --- Main ---

def main():
    parser = argparse.ArgumentParser(
        description="Enumerate Docker Hub repository metadata, owner info, and tags",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tag-and-enum.py aswindapp/natgeo-mail
  python tag-and-enum.py homedepottech/github-webhook-resource
  python tag-and-enum.py library/nginx
  python tag-and-enum.py https://hub.docker.com/v2/repositories/aswindapp/natgeo-mail
        """
    )
    
    parser.add_argument(
        "repository",
        help="Repository address (owner/repo) or full Docker Hub URL"
    )
    parser.add_argument(
        "--details", "-d",
        action="store_true",
        help="Show detailed tag information including platforms"
    )
    parser.add_argument(
        "--tags-only", "-t",
        action="store_true",
        help="Only show tags (skip owner and repository info)"
    )
    parser.add_argument(
        "--no-tags",
        action="store_true",
        help="Skip fetching tags"
    )
    
    args = parser.parse_args()
    
    # Parse input
    owner, repo = parse_repo_input(args.repository)
    
    print(f"\nEnumerating: {owner}/{repo}", file=sys.stderr)
    print(f"{'=' * 40}", file=sys.stderr)
    
    # Fetch data
    owner_info = {}
    repo_info = {}
    tags = []
    
    if not args.tags_only:
        owner_info = get_owner_info(owner)
        time.sleep(RATE_LIMIT_DELAY)
        
        repo_info = get_repository_info(owner, repo)
        time.sleep(RATE_LIMIT_DELAY)
    
    if not args.no_tags:
        tags = get_tags(owner, repo)
    
    # Print results
    print()  # Blank line before output
    
    if not args.tags_only:
        print_owner_table(owner_info)
        print_repository_table(repo_info)
    
    if not args.no_tags:
        print_tags_table(tags)
        
        if args.details:
            print_tag_details(tags)
    
    print_separator()
    print(f"Repository URL: https://hub.docker.com/r/{owner}/{repo}")
    print_separator()


if __name__ == "__main__":
    main()

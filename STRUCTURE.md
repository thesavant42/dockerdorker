# dockerDorker Project Structure

This document describes the permanent directory structure for the dockerDorker project.

## Overview

```
textular-experiments/
├── app.py                              # Main entry point - Textual TUI application
├── styles.tcss                         # UI stylesheet
├── STRUCTURE.md                        # This file
├── TODO.md                             # Legacy notes
├── app/                                # Main application package
│   ├── __init__.py                     # Package init (version info)
│   ├── core/                           # Shared utilities and APIs
│   │   ├── __init__.py                 # Re-exports Database, api, utils
│   │   ├── database.py                 # SQLite caching for search/layers
│   │   ├── api/                        # Docker Hub API functions
│   │   │   ├── __init__.py             # Re-exports all API functions
│   │   │   ├── constants.py            # HEADERS, RATE_LIMIT_DELAY
│   │   │   ├── dockerhub_fetch.py      # HTTP fetching with retry
│   │   │   ├── dockerhub_parse.py      # Response parsing
│   │   │   ├── dockerhub_search.py     # Search with caching
│   │   │   └── dockerhub_v2_api.py     # Tags/images API
│   │   └── utils/                      # Utility functions
│   │       ├── __init__.py             # Re-exports all utilities
│   │       ├── tar_parser.py           # Tar header parsing (TarEntry)
│   │       ├── layer_fetcher.py        # HTTP Range layer peeking
│   │       ├── filesystem_utils.py     # Directory listing, layer merging
│   │       ├── formatters.py           # Data formatting for display
│   │       ├── image_config_formatter.py # Image config parsing
│   │       └── image_formatters.py     # Size/digest formatting
│   └── modules/                        # Feature modules
│       ├── __init__.py                 # (to be added)
│       ├── search/                     # Docker Hub search module
│       │   ├── README-search.md        # Module documentation
│       │   └── search-docker-hub.py    # Standalone search script
│       ├── enumerate/                  # Container file enumeration
│       │   ├── README-enumerate.md     # Module documentation
│       │   ├── list_dockerhub_container_files.py
│       │   └── tag-and-enum.py         # Tag enumeration (standalone)
│       └── carve/                      # File extraction module
│           ├── README-carve-file.md    # Module documentation
│           ├── carve-file-from-layer.py # Standalone carve script
│           └── src/                    # (Legacy - to be removed after verification)
├── data/                               # Runtime data directory
│   ├── .gitkeep                        # Keeps directory in git
│   ├── docker-dorker.db                # SQLite database (auto-created)
│   ├── cache/                          # Layer cache (future)
│   └── output/                         # Carved files output (future)
├── plans/                              # Project planning documents
│   ├── in-progress/                    # Current work
│   │   └── refactor-to-submodules-plan.md
│   ├── completed/                      # Done plans
│   └── to-do/                          # Future plans
└── docs/                               # Documentation
    └── textual-docs/                   # Textual framework reference
```

## Core Modules

### app/core/database.py

SQLite database for caching:
- Search results (24-hour expiration)
- Repository tags
- Image configs
- Layer peek metadata (permanent - digests are immutable)

### app/core/api/

Docker Hub API functions:

| Module | Purpose |
|--------|---------|
| `constants.py` | HTTP headers, rate limit delay |
| `dockerhub_fetch.py` | HTTP fetching with retry backoff |
| `dockerhub_parse.py` | Indexed JSON response parsing |
| `dockerhub_search.py` | Search orchestration with caching |
| `dockerhub_v2_api.py` | Tags and images API |

### app/core/utils/

Utility functions:

| Module | Purpose |
|--------|---------|
| `tar_parser.py` | Parse tar headers from partial data (`TarEntry`) |
| `layer_fetcher.py` | HTTP Range requests for layer peeking |
| `filesystem_utils.py` | Directory listing, whiteout handling |
| `formatters.py` | Date, size, architecture formatting |
| `image_config_formatter.py` | Image config parsing to dataclasses |
| `image_formatters.py` | Simple size/digest formatters |

## Feature Modules

### app/modules/search/

Docker Hub repository search.

**Usage:**
```bash
python app/modules/search/search-docker-hub.py <query>
```

**Output:** Formatted table with repository name, pulls, stars, etc.

### app/modules/enumerate/

List files in Docker container images using partial HTTP Range requests.

**Usage:**
```bash
python app/modules/enumerate/list_dockerhub_container_files.py <image:tag>
```

**Output:** File listing with layer info, permissions, sizes.

### app/modules/carve/

Extract specific files from Docker image layers without downloading the full layer.

**Usage:**
```bash
python app/modules/carve/carve-file-from-layer.py <image:tag> <filepath>
```

**Output:** Extracted file saved to disk.

## Data Flow

```
Search -> Enumerate Tags -> List Files -> Carve

1. Search (search-docker-hub.py): Find repositories on Docker Hub
2. Enumerate Tags (tag-and-enum.py): List owner info, repo metadata, and all tags
3. List Files (list_dockerhub_container_files.py): Show files in each layer
4. Carve (carve-file-from-layer.py): Extract specific files from layers
```

The tag-and-enum.py step is critical - it bridges repository discovery and image inspection:
- Input: Repository address (owner/repo)
- Output: Owner type (Org/User), repository metadata, all tags with platform info

## Import Patterns

### From workspace root:

```python
# API functions
from app.core.api import search, fetch_all_tags, HEADERS

# Utilities
from app.core.utils import TarEntry, parse_tar_header, LayerPeekResult

# Database
from app.core import Database, get_database
```

### From module scripts:

```python
# Add workspace root to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# Then import normally
from app.core.utils.tar_parser import TarEntry, parse_tar_header
```

## Notes

- Original `app/modules/carve/src/` is kept for reference but should be removed after full verification
- The `data/` directory is for runtime data and should not be committed (except `.gitkeep`)
- All modules support standalone CLI execution for testing

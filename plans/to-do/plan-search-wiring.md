## Corrected Summary of Search Wiring Plan

The plan describes wiring Docker Hub search functionality into your Textual-based application.

### User Journey
1. User launches app and opens command palette (Ctrl+P)
2. User types a search command like `search dockerhub homedepot`
3. The query is passed to the search submodule (async - palette can close while search runs, loading indicator shows progress)
4. Results appear in the left panel

### UI Layout

**Left Panel - 4-Column Grid of Results:**
```
+-------------------------+-------------------------+-------------------------+-------------------------+
| mdpdisney/openpose      | another/repo            | third/image             | fourth/container        |
| LastPushed: 12/12/2026  | LastPushed: 01/05/2025  | LastPushed: 03/15/2024  | LastPushed: 06/20/2023  |
| :star: 69 pulls: 666    | :star: 42 pulls: 1000   | :star: 100 pulls: 5000  | :star: 5 pulls: 50      |
| OpenPose (2017-08-08)...| Description text...     | Description text...     | Description text...     |
+-------------------------+-------------------------+-------------------------+-------------------------+
```

Each column is 25% width, showing one search result with:
- **Row 1:** `owner/repository` (bold, ellipsis overflow)
- **Row 2:** `Last Push: <DATE> :star: <N> Pulls: <N>`
- **Row 3:** Description (italic, ellipsis overflow)

**Additional DataTable settings:**
- Vertical scrolling (scrollbar-size: 4)
- No header row
- Tabs at top for pagination
- Cursor type: cell

### Remaining Tasks
1. Wire Command palette search
    - (@app/core/api/dockerhub_search.py)

2. Display search results in left panel
    - List a Repo's: container Image Tags, which are needed to view layers' digest

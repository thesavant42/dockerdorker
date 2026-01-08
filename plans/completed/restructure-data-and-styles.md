# Plan: Restructure data/ and styles.tcss into app/ Directory

## Summary

Move runtime data directory and styles file from project root into the `app/` subdirectory to keep the project structure tidy.

## Current State

```
dockerdorker/
├── data/                    # Runtime data at project root (wrong)
│   └── .gitkeep
├── styles.tcss              # Styles at project root (wrong)
├── app/
│   ├── styles/              # Empty directory exists
│   ├── core/
│   │   └── database.py      # References data/ at root
│   └── modules/carve/src/
│       └── database.py      # References data/ at root
```

## Target State

```
dockerdorker/
├── app/
│   ├── data/                # Runtime data inside app/
│   │   └── .gitkeep
│   ├── styles/
│   │   └── styles.tcss      # Styles inside app/styles/
│   ├── core/
│   │   └── database.py      # Updated path
│   └── modules/carve/src/
│       └── database.py      # Updated path
```

## Files to Modify

### 1. app.py - Line 34
**Current:**
```python
CSS_PATH = "styles.tcss"
```

**Change to:**
```python
CSS_PATH = "app/styles/styles.tcss"
```

### 2. app/core/database.py - Line 16
**Current:**
```python
DB_FILE = Path(__file__).parent.parent.parent / "data" / "docker-dorker.db"
```

**Change to:**
```python
DB_FILE = Path(__file__).parent.parent / "data" / "docker-dorker.db"
```

Note: Remove one `.parent` since data/ moves from project root to app/.

### 3. app/modules/carve/src/database.py - Line 16
**Current:**
```python
DB_FILE = Path(__file__).parent.parent / "docker-dorker.db"
```

**Change to:**
```python
DB_FILE = Path(__file__).parent.parent.parent.parent / "data" / "docker-dorker.db"
```

Note: Navigate up to app/ then into data/.

## Files to Move/Create

| Action | Source | Destination |
|--------|--------|-------------|
| Move | styles.tcss | app/styles/styles.tcss |
| Create | - | app/data/.gitkeep |
| Delete | data/ | - |

## Verification

The `.gitignore` already has `**/*.db` which covers `app/data/*.db` - no changes needed.

## Execution Steps

1. Move `styles.tcss` to `app/styles/styles.tcss`
2. Update `app.py` CSS_PATH
3. Create `app/data/.gitkeep`
4. Update `app/core/database.py` DB_FILE path
5. Update `app/modules/carve/src/database.py` DB_FILE path
6. Delete `data/` directory from project root
7. Update `STRUCTURE.md` to reflect new layout

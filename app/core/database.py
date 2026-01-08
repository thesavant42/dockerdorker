"""
Database module for docker-dorker.
Handles SQLite caching of Docker Hub search results and layer peek metadata.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.utils.layer_fetcher import LayerPeekResult

# Database file location (in project root/data directory)
DB_FILE = Path(__file__).parent.parent.parent / "data" / "docker-dorker.db"

# Cache expiration time (24 hours)
CACHE_EXPIRATION_HOURS = 24


class Database:
    """Database connection and operations manager."""

    def __init__(self, db_path: Path = DB_FILE):
        """Initialize database connection."""
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self) -> None:
        """Create database and tables if they don't exist."""
        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row  # Return rows as dict-like objects

        cursor = self.conn.cursor()

        # Create searches table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS searches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                total_results INTEGER NOT NULL,
                UNIQUE(query)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_searches_query ON searches(query)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_searches_timestamp ON searches(timestamp)")

        # Create search_results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                slug TEXT,
                publisher TEXT,
                pull_count INTEGER,
                star_count INTEGER,
                short_description TEXT,
                updated_at DATETIME,
                operating_systems TEXT,
                architectures TEXT,
                os_count INTEGER,
                architecture_count INTEGER,
                created_at DATETIME,
                FOREIGN KEY (search_id) REFERENCES searches(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_results_search_id ON search_results(search_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_results_name ON search_results(name)")

        # Create repositories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS repositories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                namespace TEXT NOT NULL,
                repo TEXT NOT NULL,
                tags_json TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                fetched_at DATETIME
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_repositories_name ON repositories(name)")

        # Create image_configs table - stores ENTIRE JSON for each image config
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS image_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repository_id INTEGER NOT NULL,
                tag_name TEXT NOT NULL,
                architecture TEXT,
                os TEXT,
                digest TEXT,
                size INTEGER,
                status TEXT,
                raw_json TEXT,
                fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE,
                UNIQUE(repository_id, digest)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_image_configs_repository_id ON image_configs(repository_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_image_configs_tag_name ON image_configs(tag_name)")

        # Migration: Add last_pushed and last_pulled columns if they don't exist
        try:
            cursor.execute("ALTER TABLE image_configs ADD COLUMN last_pushed TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        try:
            cursor.execute("ALTER TABLE image_configs ADD COLUMN last_pulled TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Create layer_peek_cache table - stores layer filesystem metadata (NOT file contents)
        # Layer digests are immutable, so no expiration needed
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS layer_peek_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                digest TEXT NOT NULL UNIQUE,
                namespace TEXT NOT NULL,
                repo TEXT NOT NULL,
                bytes_downloaded INTEGER,
                bytes_decompressed INTEGER,
                entries_count INTEGER,
                entries_json TEXT,
                fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_layer_peek_cache_digest ON layer_peek_cache(digest)")

        self.conn.commit()

    def search_exists(self, query: str) -> bool:
        """
        Check if search query exists in cache and is recent (< 24 hours old).
        
        Args:
            query: Search query string
            
        Returns:
            True if cached and recent, False otherwise
        """
        cursor = self.conn.cursor()
        expiration_time = datetime.now() - timedelta(hours=CACHE_EXPIRATION_HOURS)

        cursor.execute(
            """
            SELECT id, timestamp FROM searches 
            WHERE query = ? AND timestamp > ?
            """,
            (query, expiration_time)
        )
        result = cursor.fetchone()
        return result is not None

    def get_cached_results(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached search results for a query.
        
        Args:
            query: Search query string
            
        Returns:
            Dictionary with search metadata and results, or None if not cached
        """
        if not self.search_exists(query):
            return None

        cursor = self.conn.cursor()

        # Get search metadata
        cursor.execute("SELECT * FROM searches WHERE query = ?", (query,))
        search = cursor.fetchone()
        if not search:
            return None

        search_id = search["id"]

        # Get all results for this search
        cursor.execute(
            "SELECT * FROM search_results WHERE search_id = ? ORDER BY id",
            (search_id,)
        )
        results = cursor.fetchall()

        # Convert to list of dicts and deserialize JSON fields
        parsed_results = []
        for row in results:
            result = dict(row)
            # Deserialize JSON fields
            if result["operating_systems"]:
                result["operating_systems"] = json.loads(result["operating_systems"])
            else:
                result["operating_systems"] = []

            if result["architectures"]:
                result["architectures"] = json.loads(result["architectures"])
            else:
                result["architectures"] = []

            parsed_results.append(result)

        return {
            "query": query,
            "total": search["total_results"],
            "total_pages": (search["total_results"] + 29) // 30,  # Assuming 30 per page
            "results": parsed_results,
            "cached": True,
            "timestamp": search["timestamp"]
        }

    def save_search_results(self, query: str, results: Dict[str, Any]) -> None:
        """
        Store search results in database.
        
        Args:
            query: Search query string
            results: Dictionary with 'total' and 'results' list
        """
        cursor = self.conn.cursor()

        try:
            # Insert or replace search record
            cursor.execute(
                """
                INSERT OR REPLACE INTO searches (query, timestamp, total_results)
                VALUES (?, CURRENT_TIMESTAMP, ?)
                """,
                (query, results["total"])
            )
            search_id = cursor.lastrowid

            # Delete old results for this search (if updating)
            cursor.execute("DELETE FROM search_results WHERE search_id = ?", (search_id,))

            # Insert new results
            for result in results["results"]:
                # Serialize JSON fields
                os_json = json.dumps(result.get("operating_systems", []))
                arch_json = json.dumps(result.get("architectures", []))

                cursor.execute(
                    """
                    INSERT INTO search_results (
                        search_id, name, slug, publisher, pull_count, star_count,
                        short_description, updated_at, operating_systems, architectures,
                        os_count, architecture_count, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        search_id,
                        result.get("name"),
                        result.get("slug"),
                        result.get("publisher"),
                        result.get("pull_count"),
                        result.get("star_count"),
                        result.get("short_description"),
                        result.get("updated_at"),
                        os_json,
                        arch_json,
                        result.get("os_count", 0),
                        result.get("architecture_count", 0),
                        result.get("created_at")
                    )
                )

            self.conn.commit()

        except sqlite3.Error as e:
            self.conn.rollback()
            raise Exception(f"Database error: {e}")

    def get_all_searches(self) -> List[Dict[str, Any]]:
        """
        Get list of all searches in history.
        
        Returns:
            List of search records with metadata
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT query, timestamp, total_results FROM searches ORDER BY timestamp DESC"
        )
        results = cursor.fetchall()
        return [dict(row) for row in results]

    def get_or_create_repository(self, namespace: str, repo: str) -> int:
        """Get existing repository ID or create new one."""
        name = f"{namespace}/{repo}"
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM repositories WHERE name = ?", (name,))
        result = cursor.fetchone()
        if result:
            return result["id"]
        cursor.execute(
            "INSERT INTO repositories (name, namespace, repo) VALUES (?, ?, ?)",
            (name, namespace, repo)
        )
        self.conn.commit()
        return cursor.lastrowid

    def save_repository_tags(self, repository_id: int, tags: List[Dict]) -> None:
        """Save all tags JSON to repository record."""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE repositories SET tags_json = ? WHERE id = ?",
            (json.dumps(tags), repository_id)
        )
        self.conn.commit()

    def save_image_config(self, repository_id: int, tag_name: str, image: Dict) -> None:
        """Store ENTIRE image config JSON in database."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO image_configs
            (repository_id, tag_name, architecture, os, digest, size, status, last_pushed, last_pulled, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            repository_id,
            tag_name,
            image.get("architecture"),
            image.get("os"),
            image.get("digest"),
            image.get("size"),
            image.get("status"),
            image.get("last_pushed"),
            image.get("last_pulled"),
            json.dumps(image)  # ENTIRE JSON stored here
        ))
        self.conn.commit()

    def update_repository_fetched(self, repository_id: int) -> None:
        """Update the fetched_at timestamp for a repository."""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE repositories SET fetched_at = CURRENT_TIMESTAMP WHERE id = ?",
            (repository_id,)
        )
        self.conn.commit()

    def repository_cache_valid(self, namespace: str, repo: str) -> bool:
        """
        Check if repository data exists in cache and is recent (< 24 hours old).
        
        Args:
            namespace: Repository namespace (e.g., 'library')
            repo: Repository name (e.g., 'python')
            
        Returns:
            True if cached and recent, False otherwise
        """
        name = f"{namespace}/{repo}"
        cursor = self.conn.cursor()
        expiration_time = datetime.now() - timedelta(hours=CACHE_EXPIRATION_HOURS)
        
        cursor.execute("""
            SELECT id FROM repositories
            WHERE name = ? AND fetched_at > ? AND tags_json IS NOT NULL
        """, (name, expiration_time))
        return cursor.fetchone() is not None

    def get_cached_tags(self, namespace: str, repo: str) -> Optional[List[Dict]]:
        """
        Retrieve cached tags for a repository.
        
        Args:
            namespace: Repository namespace (e.g., 'library')
            repo: Repository name (e.g., 'python')
            
        Returns:
            List of tag dictionaries, or None if not cached
        """
        name = f"{namespace}/{repo}"
        cursor = self.conn.cursor()
        cursor.execute("SELECT tags_json FROM repositories WHERE name = ?", (name,))
        result = cursor.fetchone()
        if result and result["tags_json"]:
            return json.loads(result["tags_json"])
        return None

    def get_cached_image_configs(self, repository_id: int) -> List[Tuple[str, Dict]]:
        """
        Retrieve all cached image configs for a repository.
        
        Args:
            repository_id: The repository database ID
            
        Returns:
            List of (tag_name, image_config_dict) tuples ordered by most recently pushed
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT tag_name, raw_json FROM image_configs
            WHERE repository_id = ?
            ORDER BY last_pushed DESC, tag_name
        """, (repository_id,))
        results = []
        for row in cursor.fetchall():
            image = json.loads(row["raw_json"])
            results.append((row["tag_name"], image))
        return results

    # =========================================================================
    # Layer Peek Cache Methods
    # =========================================================================

    def layer_peek_cached(self, digest: str) -> bool:
        """
        Check if layer peek metadata is cached.
        
        Layer digests are immutable (content-addressable), so no expiration needed.
        
        Args:
            digest: Layer digest (sha256:...)
            
        Returns:
            True if cached, False otherwise
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM layer_peek_cache WHERE digest = ?", (digest,))
        return cursor.fetchone() is not None

    def all_layers_cached(self, layer_digests: List[str]) -> bool:
        """
        Check if ALL layer digests are cached in layer_peek_cache.
        
        Used by auto-peek feature to determine if layers need to be fetched.
        
        Args:
            layer_digests: List of layer digest strings (sha256:...)
            
        Returns:
            True if ALL are cached, False if ANY are missing
        """
        if not layer_digests:
            return True
        
        cursor = self.conn.cursor()
        placeholders = ','.join('?' * len(layer_digests))
        cursor.execute(f"""
            SELECT COUNT(*) FROM layer_peek_cache
            WHERE digest IN ({placeholders})
        """, layer_digests)
        cached_count = cursor.fetchone()[0]
        return cached_count == len(layer_digests)

    def save_layer_peek(
        self,
        digest: str,
        namespace: str,
        repo: str,
        result: "LayerPeekResult"
    ) -> None:
        """
        Cache layer peek metadata (filesystem structure, NOT file contents).
        
        Args:
            digest: Layer digest (sha256:...)
            namespace: Repository namespace (e.g., 'library')
            repo: Repository name (e.g., 'nginx')
            result: LayerPeekResult with entries to cache
        """
        cursor = self.conn.cursor()
        entries_json = json.dumps([e.to_dict() for e in result.entries])
        cursor.execute("""
            INSERT OR REPLACE INTO layer_peek_cache
            (digest, namespace, repo, bytes_downloaded, bytes_decompressed, entries_count, entries_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            digest,
            namespace,
            repo,
            result.bytes_downloaded,
            result.bytes_decompressed,
            result.entries_found,
            entries_json
        ))
        self.conn.commit()

    def get_cached_layer_peek(self, digest: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached layer peek metadata.
        
        Args:
            digest: Layer digest (sha256:...)
            
        Returns:
            Dict with bytes_downloaded, bytes_decompressed, entries_count, entries (as dicts)
            or None if not cached
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT bytes_downloaded, bytes_decompressed, entries_count, entries_json
            FROM layer_peek_cache WHERE digest = ?
        """, (digest,))
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "digest": digest,
            "bytes_downloaded": row["bytes_downloaded"],
            "bytes_decompressed": row["bytes_decompressed"],
            "entries_count": row["entries_count"],
            "entries": json.loads(row["entries_json"]) if row["entries_json"] else []
        }

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Convenience function for getting a database instance
def get_database() -> Database:
    """Get a database connection."""
    return Database()

"""
Repository detail screen for docker-dorker.

Displays all image configs for a repository with tag information.
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Header, Static, DataTable
from textual import work

from src import keys
from src.api import fetch_all_tags, fetch_tag_images
from src.database import get_database


class RepositoryScreen(Screen):
    """
    Screen showing all image configs for a repository.

    Fetches all tags and their image configurations from Docker Hub,
    saves them to the database, and displays them in a DataTable.

    Keyboard Navigation:
        Up/Down: Navigate rows
        Escape: Go back to results screen
    """



    BINDINGS = [keys.ENTER, keys.BACK]

    def __init__(self, namespace: str, repo: str):
        """
        Initialize repository screen.

        Args:
            namespace: Repository namespace (e.g., 'library' for official images)
            repo: Repository name
        """
        super().__init__()
        self.namespace = namespace
        self.repo = repo
        self._row_data: Dict[int, Tuple[str, dict]] = {}  # row_idx -> (tag, image)

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()
        yield Static(f"Repository: {self.namespace}/{self.repo}", id="title")
        yield Static("Loading...", id="status")
        yield DataTable(
            id="images-table",
            cursor_type="row",
            zebra_stripes=True,
        )
        yield Footer()

    def on_mount(self) -> None:
        """Called when screen is mounted - setup table and fetch data."""
        table = self.query_one("#images-table", DataTable)
        for column in ("Repo: ", "Tag: ", "OS: ", "Arch: ", "Size: ", "Last Pushed: ", "Last Pulled: ", " Digest: "):
            table.add_column(column)
        self.fetch_all_data()
    
    # Navigation Actions

    def action_go_back(self) -> None:
        """Go back to the results screen."""
        self.app.pop_screen()

    def action_select(self) -> None:
        """Show full raw JSON for selected image."""
        selected = self._get_selected_image()
        if selected:
            from src.screens.image_config_screen import ImageConfigScreen
            self.app.push_screen(ImageConfigScreen(
                tag_name=selected[0],
                image_data=selected[1],
                namespace=self.namespace,
                repo=self.repo,
            ))

    def _get_selected_image(self) -> Optional[Tuple[str, dict]]:
        """Get selected image data."""
        table = self.query_one("#images-table", DataTable)
        if table.cursor_row is not None and table.cursor_row in self._row_data:
            return self._row_data[table.cursor_row]
        return None

    # Background Worker

    @work(exclusive=True, thread=True)
    def fetch_all_data(self) -> None:
        """Fetch all tags and image configs in background, using cache if available."""
        self._update_status("Checking cache...")

        db = get_database()
        
        # Check if we have valid cached data
        if db.repository_cache_valid(self.namespace, self.repo):
            self._update_status("Loading from cache...")
            repo_id = db.get_or_create_repository(self.namespace, self.repo)
            cached_images = db.get_cached_image_configs(repo_id)
            db.close()
            
            if cached_images:
                self.app.call_from_thread(self._populate_table, cached_images)
                return
        
        # No valid cache - fetch from API
        self._update_status("Connecting to database...")
        repo_id = db.get_or_create_repository(self.namespace, self.repo)
        db.close()

        # Step 2: Fetch ALL tags (paginated)
        self._update_status("Fetching tags...")
        all_tags = fetch_all_tags(self.namespace, self.repo)

        # Save tags to repository
        db = get_database()
        db.save_repository_tags(repo_id, all_tags)
        db.close()

        # Step 3: For each tag, fetch image configs
        total_tags = len(all_tags)
        all_images: List[Tuple[str, dict]] = []

        for idx, tag in enumerate(all_tags):
            tag_name = tag.get("name")
            self._update_status(
                f"Fetching images for tag: {tag_name} ({idx + 1}/{total_tags})"
            )

            try:
                images = fetch_tag_images(self.namespace, self.repo, tag_name)

                # Save EACH image config to database
                db = get_database()
                for image in images:
                    db.save_image_config(repo_id, tag_name, image)
                    all_images.append((tag_name, image))
                db.close()
            except Exception:
                # Continue on error, just skip this tag
                pass

        # Update fetched timestamp
        db = get_database()
        db.update_repository_fetched(repo_id)
        db.close()

        # Sort by last_pushed descending (most recent first)
        all_images.sort(key=lambda x: x[1].get("last_pushed") or "", reverse=True)

        # Populate the table on main thread
        self.app.call_from_thread(self._populate_table, all_images)

    # Thread-safe UI Updates

    def _update_status(self, message: str) -> None:
        """Thread-safe status update."""
        self.app.call_from_thread(self._set_status, message)

    def _set_status(self, message: str) -> None:
        """Update status label (must be called from main thread)."""
        try:
            status = self.query_one("#status", Static)
            status.update(message)
        except Exception:
            pass

    def _populate_table(self, images: List[Tuple[str, dict]]) -> None:
        """Populate the table with image configs."""
        table = self.query_one("#images-table", DataTable)
        repo_name = f"{self.namespace}/{self.repo}"
        for idx, (tag, image) in enumerate(images):
            os_name = f"{image.get('os', '?')}"
            arch = f"{image.get('architecture', '?')}"
            size = f"{self._format_size(image.get('size', 0))}"
            pushed = f"{self._format_datetime(image.get('last_pushed'))}"
            pulled = f"{self._format_datetime(image.get('last_pulled'))}"
            digest = f"{image.get('digest') or ''}"
            table.add_row(repo_name, f"{tag}", os_name, arch, size, pushed, pulled, digest)
            self._row_data[idx] = (tag, image)
        self._set_status(f"Found {len(images)} Image Config Digests (Enter=view JSON)")
        table.focus()

    def _format_size(self, size_bytes: int) -> str:
        """Format size in human-readable format."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

    def _format_datetime(self, iso_str: Optional[str]) -> str:
        """Format ISO datetime string to readable format."""
        if not iso_str:
            return "N/A"
        try:
            dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
            return dt.strftime("%m-%d-%Y")
        except Exception:
            return iso_str[:10] if iso_str else "N/A"

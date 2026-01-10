"""
Layer contents screen for docker-dorker.

Displays the files found in a layer blob using partial download (HTTP Range request).
Shows results in ls -la format with directory navigation support using DataTable.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Static, LoadingIndicator, DataTable
from textual import work
from rich.text import Text

from src import keys
from src.api.layerslayer import peek_layer_blob_partial, LayerPeekResult
from src.api.layerslayer.parser import TarEntry
from src.utils.filesystem_utils import get_directory_contents


class LayerContentsScreen(Screen):
    """
    Screen showing the contents of a layer blob in ls -la format.

    Uses HTTP Range requests to fetch only the first 64KB of the layer,
    decompress, and parse tar headers for a file listing preview.

    Features:
    - ls -la style output with permissions, uid/gid, size, date, name
    - Directory navigation (Enter to open, Backspace for parent)
    - Symlink display with -> target

    Keyboard Navigation:
        Up/Down: Navigate rows (built-in DataTable)
        Enter: Open directory or preview file
        Backspace: Go to parent directory
        Escape: Go back to image config screen
    """

    BINDINGS = [
        keys.BACK,
        keys.ENTER,
        Binding("backspace", "go_parent", "Parent"),
    ]

    def __init__(
        self,
        namespace: str,
        repo: str,
        digest: str,
        layer_size: int = 0,
        instruction: str = "",
    ):
        """
        Initialize layer contents screen.

        Args:
            namespace: Docker Hub namespace (e.g., "owner")
            repo: Repository name (e.g., "nginx")
            digest: Layer digest (sha256:...)
            layer_size: Full layer size in bytes (for display)
            instruction: The Dockerfile instruction that created this layer
        """
        super().__init__()
        self.namespace = namespace
        self.repo = repo
        self.digest = digest
        self.layer_size = layer_size
        self.instruction = instruction
        self.result: LayerPeekResult | None = None

        # Filesystem navigation state
        self.current_path = "/"
        self.all_entries: list[TarEntry] = []
        self._row_data: dict[int, TarEntry | None] = {}  # row_idx -> entry (None = parent)

        # Layer Slayer mode: pre-injected entries (set by image_config_screen)
        self._layerslayer_entries: list[TarEntry] | None = None
        self._layerslayer_bytes: int = 0
        self._layerslayer_cached: int = 0

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()

        # Title showing digest
        yield Static(f"Layer: {self.digest}", id="layer-title")

        # Stats row (updated after loading)
        yield Static("Loading layer contents...", id="layer-stats")

        # Current path display
        yield Static("Path: /", id="current-path")

        # Loading indicator (shown while fetching)
        yield LoadingIndicator(id="loading")

        # DataTable for ls -la output (hidden initially)
        table = DataTable(id="file-listing", cursor_type="row", zebra_stripes=True)
        table.display = False
        yield table

        # Error display (hidden initially)
        yield Static("", id="error-display")

        yield Footer()

    def on_mount(self) -> None:
        """Start loading layer contents when screen mounts."""
        # Hide error display initially
        self.query_one("#error-display", Static).display = False

        # Setup DataTable columns
        table = self.query_one("#file-listing", DataTable)
        table.add_column("Perms", key="perms")
        table.add_column("UID/GID", key="uidgid")
        table.add_column("Size", key="size")
        table.add_column("Date", key="date")
        table.add_column("Name", key="name")

        # Check if we have pre-injected Layer Slayer entries
        if self._layerslayer_entries is not None:
            self._display_layerslayer_results()
        else:
            self._fetch_layer_contents()

    def _display_layerslayer_results(self) -> None:
        """Display pre-injected Layer Slayer results."""
        # Hide loading, show file listing
        self.query_one("#loading", LoadingIndicator).display = False
        table = self.query_one("#file-listing", DataTable)
        table.display = True

        # Store all entries for navigation
        self.all_entries = self._layerslayer_entries

        # Format stats
        dl_kb = self._layerslayer_bytes / 1024
        stats_text = (
            f"Layer Slayer: Downloaded {dl_kb:.1f} KB | "
            f"{self._layerslayer_cached} layers from cache | "
            f"Found: {len(self.all_entries)} entries"
        )
        self.query_one("#layer-stats", Static).update(stats_text)

        # Render current directory
        self._render_directory()
        table.focus()

    @work(exclusive=True, thread=True)
    def _fetch_layer_contents(self) -> None:
        """Fetch layer contents in background thread."""
        try:
            result = peek_layer_blob_partial(
                namespace=self.namespace,
                repo=self.repo,
                digest=self.digest,
                initial_bytes=65536,  # 64KB - good balance of speed vs coverage
            )
            self.result = result
            self.app.call_from_thread(self._display_results)
        except Exception as e:
            self.app.call_from_thread(self._display_error, str(e))

    def _display_results(self) -> None:
        """Display the layer contents after loading."""
        if not self.result:
            return

        # Hide loading, show file listing
        self.query_one("#loading", LoadingIndicator).display = False
        table = self.query_one("#file-listing", DataTable)
        table.display = True

        # Update stats
        stats = self.query_one("#layer-stats", Static)
        if self.result.error:
            stats.update(f"Error: {self.result.error}")
            self.query_one("#error-display", Static).update(self.result.error)
            self.query_one("#error-display", Static).display = True
            table.display = False
            return

        # Store all entries for navigation
        self.all_entries = self.result.entries

        # Format stats
        dl_kb = self.result.bytes_downloaded / 1024
        decomp_kb = self.result.bytes_decompressed / 1024
        pct = (self.result.bytes_downloaded / self.layer_size * 100) if self.layer_size > 0 else 0

        stats_text = (
            f"Downloaded: {dl_kb:.1f} KB ({pct:.2f}%) | "
            f"Decompressed: {decomp_kb:.1f} KB | "
            f"Found: {self.result.entries_found} entries"
        )
        stats.update(stats_text)

        # Render current directory
        self._render_directory()
        table.focus()

    def _render_directory(self) -> None:
        """Render the current directory contents as DataTable rows."""
        table = self.query_one("#file-listing", DataTable)
        table.clear()
        self._row_data.clear()

        # Update path display
        path_widget = self.query_one("#current-path", Static)
        path_widget.update(f"Path: {self.current_path}")

        # Get current directory listing
        listing = get_directory_contents(self.all_entries, self.current_path)

        row_index = 0

        # Add parent directory entry (if not at root)
        if listing.parent is not None:
            table.add_row(
                Text("drwxr-xr-x", style="cyan"),
                "0/0",
                "",
                "----.--.-- --:--",
                Text("../", style="cyan bold"),
            )
            self._row_data[row_index] = None  # None represents parent
            row_index += 1

        # Add each entry
        for entry in listing.entries:
            name = self._format_entry_name(entry)
            uid_gid = f"{entry.uid}/{entry.gid}"

            # Style based on entry type
            if entry.is_dir:
                perms_styled = Text(entry.mode, style="cyan")
                name_styled = Text(name, style="cyan bold")
            elif entry.is_symlink:
                perms_styled = Text(entry.mode, style="magenta")
                name_styled = Text(name, style="magenta")
            else:
                perms_styled = Text(entry.mode)
                name_styled = Text(name)

            table.add_row(
                perms_styled,
                uid_gid,
                self._format_size(entry.size),
                entry.mtime,
                name_styled,
            )
            self._row_data[row_index] = entry
            row_index += 1

        # Show message if directory is empty
        if not listing.entries and listing.parent is None:
            table.add_row("", "", "", "", Text("(empty directory)", style="dim"))

    def _format_entry_name(self, entry: TarEntry) -> str:
        """Format entry name with trailing slash for dirs and symlink target."""
        name = entry.name.rstrip("/").split("/")[-1]
        if entry.is_dir:
            name += "/"
        if entry.is_symlink and entry.linkname:
            name += f" -> {entry.linkname}"
        return name

    def _display_error(self, error: str) -> None:
        """Display an error message."""
        self.query_one("#loading", LoadingIndicator).display = False
        self.query_one("#file-listing", DataTable).display = False

        error_widget = self.query_one("#error-display", Static)
        error_widget.update(f"Error loading layer:\n\n{error}")
        error_widget.display = True

        stats = self.query_one("#layer-stats", Static)
        stats.update("Failed to load layer contents")

    # Navigation Actions

    def action_go_back(self) -> None:
        """Go back to the image config screen."""
        self.app.pop_screen()

    def action_select(self) -> None:
        """Open the currently selected entry (directory or file)."""
        table = self.query_one("#file-listing", DataTable)
        if table.cursor_row is None:
            return

        entry = self._row_data.get(table.cursor_row)

        if entry is None:
            # Parent directory (../)
            self.action_go_parent()
        elif entry.is_dir:
            # Navigate into directory
            new_path = "/" + entry.name.rstrip("/") + "/"
            self.current_path = new_path
            self._render_directory()
        else:
            # File - show notification (future: push preview screen)
            size_str = self._format_size(entry.size)
            self.notify(f"File: {entry.name} ({size_str})")

    def action_go_parent(self) -> None:
        """Navigate to parent directory."""
        listing = get_directory_contents(self.all_entries, self.current_path)
        if listing.parent:
            self.current_path = listing.parent
            self._render_directory()

    def action_go_root(self) -> None:
        """Navigate to root directory."""
        if self.current_path != "/":
            self.current_path = "/"
            self._render_directory()

    def action_refresh(self) -> None:
        """Reload layer contents."""
        # Reset state
        self.current_path = "/"
        self.all_entries = []
        self._row_data.clear()

        # Reset display
        self.query_one("#loading", LoadingIndicator).display = True
        self.query_one("#file-listing", DataTable).display = False
        self.query_one("#error-display", Static).display = False
        self.query_one("#layer-stats", Static).update("Loading layer contents...")
        self.query_one("#current-path", Static).update("Path: /")

        # Clear existing table
        table = self.query_one("#file-listing", DataTable)
        table.clear()

        # Reload
        self._fetch_layer_contents()

    def _format_size(self, size: int) -> str:
        """Format size in bytes to human-readable format."""
        if size == 0:
            return ""
        for unit in ["B", "KB", "MB", "GB"]:
            if abs(size) < 1024:
                return f"{size:.1f} {unit}" if unit != "B" else f"{size} B"
            size /= 1024
        return f"{size:.1f} TB"

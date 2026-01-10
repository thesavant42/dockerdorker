"""
Image config detail screen for docker-dorker.

Docker Hub-style two-panel layout with Collapsible widgets for layers.
Left panel: Collapsible layer sections
Right panel: Details for selected item

Press 'a' to peek ALL layers at once (Layer Slayer mode).
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Static, Collapsible, DataTable
from textual import on, work
from rich.text import Text
from rich.panel import Panel

from src import keys
from src.utils.image_config_formatter import parse_image_config, ImageConfigSummary, LayerInfo
from src.screens.layer_contents_screen import LayerContentsScreen
from src.api.layerslayer import layerslayer
from src.database import get_database


class ImageConfigScreen(Screen):
    """
    Screen showing the image config in a Docker Hub-style two-panel layout.

    Left panel: Collapsible layers and config sections (ENTRYPOINT, EXPOSE, etc.)
    Right panel: Details for the currently selected/expanded item

    Keyboard Navigation:
        Up/Down: Navigate between collapsible items
        Enter or p: Peek into selected layer contents
        a: Peek ALL layers at once (Layer Slayer mode)
        Escape: Go back to repository screen
    """
    
    BINDINGS = [
        keys.BACK,
        keys.ENTER,
        keys.COLLAPSE,
        Binding("a", "slay_all", "Peek All Layers"),
    ]

    def __init__(self, tag_name: str, image_data: dict, namespace: str = "library", repo: str = ""):
        """
        Initialize image config screen.

        Args:
            tag_name: The tag name for this image
            image_data: The full image config dictionary
            namespace: Docker Hub namespace (e.g., "library")
            repo: Repository name (e.g., "nginx")
        """
        super().__init__()
        self.tag_name = tag_name
        self.image_data = image_data
        self.namespace = namespace
        self.repo = repo
        self.config: ImageConfigSummary = parse_image_config(image_data)
        self._selected_layer: LayerInfo | None = None
        self._all_collapsed: bool = False
        
        # Filesystem state
        self.current_path: str = "/"
        self.all_entries: list = []
        self._row_data: dict = {}

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()
        
        # Title showing tag and architecture
        arch_display = f"{self.config.os}/{self.config.arch}"
        if self.config.variant:
            arch_display += f"/{self.config.variant}"
        
        yield Static(
            f"Tag: {self.tag_name} | {arch_display} | {self.config.total_size_formatted}",
            id="config-title"
        )
        
        with Horizontal(id="main-container"):
            # Left panel: Collapsible layers
            with VerticalScroll(id="layers-panel"):
                yield from self._compose_layers()
            
            # Right panel: Details
            with Vertical(id="details-panel"):
                yield Static(self._format_image_summary(), id="image-summary")
                yield Static("Path: /", id="fs-path")
                yield DataTable(id="fs-listing", cursor_type="row", zebra_stripes=True)
        
        yield Footer()

    def on_mount(self) -> None:
        """Called when screen is mounted - setup DataTable and check cache."""
        # Setup DataTable columns
        table = self.query_one("#fs-listing", DataTable)
        table.add_column("Perms", key="perms")
        table.add_column("UID/GID", key="uidgid")
        table.add_column("Size", key="size")
        table.add_column("Date", key="date")
        table.add_column("Name", key="name")
        
        self._check_and_auto_peek()

    def _check_and_auto_peek(self) -> None:
        """Check if layers are cached in database.py; if not, start background auto-peek."""
        layers = self.image_data.get("layers", [])
        layer_digests = [layer.get("digest") for layer in layers if layer.get("digest")]
        
        if not layer_digests:
            return  # No layers to peek
        
        # Check cache using database.py all_layers_cached()
        db = get_database()
        all_cached = db.all_layers_cached(layer_digests)
        db.close()
        
        # Start background auto-peek
        self._auto_peek_layers(layers)

    @work(exclusive=True, thread=True)
    def _auto_peek_layers(self, layers: list) -> None:
        """Auto-peek all layers in background thread using layerslayer from fetcher.py."""
        layer_count = sum(1 for layer in layers if layer.get("digest"))
        
        # Update #layer-details Static widget to show progress
        self.app.call_from_thread(
            self._update_details_panel,
            f"Auto-peeking {layer_count} layers..."
        )
        
        db = get_database()
        try:
            # Call layerslayer() from src/api/layerslayer/fetcher.py
            result = layerslayer(
                namespace=self.namespace,
                repo=self.repo,
                layers=layers,
                db=db,
                progress_callback=self._progress_callback_thread_safe,
            )
            
            # Update #layer-details Static widget on completion
            if result.error:
                self.app.call_from_thread(
                    self._update_details_panel,
                    f"Auto-peek error: {result.error}"
                )
            else:
                self.app.call_from_thread(self._show_layerslayer_result, result)
                self.app.call_from_thread(
                    self.notify,
                    f"Cached {result.layers_peeked} layers ({result.total_entries} entries)"
                )
        finally:
            db.close()

    def _progress_callback_thread_safe(self, message: str, current: int, total: int) -> None:
        """Progress callback that updates #layer-details Static from worker thread."""
        self.app.call_from_thread(
            self._update_details_panel,
            f"Peeking layer {current + 1}/{total}..."
        )

    def _update_details_panel(self, message: str) -> None:
        """Update the #fs-path Static widget text."""
        try:
            details = self.query_one("#fs-path", Static)
            details.update(message)
        except Exception:
            pass

    def _compose_layers(self) -> ComposeResult:
        """Generate collapsible widgets for layers and config sections."""
        # Layer sections
        for layer in self.config.layers:
            title = f"Layer {layer.index}: {layer.short_digest}  [{layer.size_formatted}]"
            with Collapsible(title=title, id=f"layer-{layer.index}", collapsed=False):
                instruction_text = layer.instruction if layer.instruction else "(no instruction)"
                yield Static(instruction_text, classes="layer-instruction")
        
        # ENTRYPOINT section
        if self.config.entrypoint:
            entrypoint_str = " ".join(self.config.entrypoint) if isinstance(self.config.entrypoint, list) else str(self.config.entrypoint)
            with Collapsible(title="ENTRYPOINT", id="config-entrypoint", collapsed=False):
                yield Static(entrypoint_str, classes="config-value")
        
        # CMD section
        if self.config.cmd:
            cmd_str = " ".join(self.config.cmd) if isinstance(self.config.cmd, list) else str(self.config.cmd)
            with Collapsible(title="CMD", id="config-cmd", collapsed=False):
                yield Static(cmd_str, classes="config-value")
        
        # EXPOSE section
        if self.config.exposed_ports:
            ports_count = len(self.config.exposed_ports)
            with Collapsible(title=f"EXPOSE ({ports_count} ports)", id="config-expose", collapsed=False):
                for port in self.config.exposed_ports:
                    yield Static(port, classes="config-value")
        
        # WORKDIR section
        if self.config.workdir:
            with Collapsible(title="WORKDIR", id="config-workdir", collapsed=False):
                yield Static(self.config.workdir, classes="config-value")
        
        # ENV section
        if self.config.env_vars:
            env_count = len(self.config.env_vars)
            with Collapsible(title=f"ENV ({env_count} variables)", id="config-env", collapsed=False):
                for key, value in self.config.env_vars.items():
                    # Truncate long values for display
                    display_value = value if len(value) <= 50 else value[:47] + "..."
                    yield Static(f"{key}={display_value}", classes="env-item")

    def _format_image_summary(self) -> Text:
        """Format the image summary for the right panel using Rich Text (no markup parsing)."""
        text = Text()
        
        # Line 1: Digest
        if self.config.digest:
            text.append(f"Digest: {self.config.digest}\n")
        
        # Line 2: Total Layers, OS/Arch, Created, Total Size
        arch_display = f"{self.config.os or 'unknown'}/{self.config.arch or 'unknown'}"
        if self.config.variant:
            arch_display += f"/{self.config.variant}"
        
        text.append(f"Total Layers: {len(self.config.layers)}   OS/Arch: {arch_display}  Created: {self.config.created or 'unknown'}   Total Size: {self.config.total_size_formatted}")
        
        return text

    def _format_layer_details(self, layer: LayerInfo) -> Text:
        """Format layer details for the right panel using Rich Text (no markup parsing)."""
        # Use Rich Text object directly to avoid any markup parsing issues
        text = Text()
        
        # Title
        text.append(f"LAYER {layer.index} DETAILS", style="bold")
        text.append("\n\n")
        
        # Digest
        text.append("Digest:", style="dim")
        text.append("\n  ")
        text.append(layer.digest if layer.digest else "(no digest)")
        text.append("\n\n")
        
        # Size
        text.append("Size:", style="dim")
        text.append(f" {layer.size_formatted}")
        text.append("\n\n")
        
        # Instruction
        text.append("Instruction:", style="dim")
        text.append("\n")
        
        # Word-wrap long instructions
        instruction = layer.instruction if layer.instruction else "(no instruction)"
        words = instruction.split()
        current_line = "  "
        for word in words:
            if len(current_line) + len(word) + 1 > 65:
                text.append(current_line + "\n")
                current_line = "  " + word
            else:
                current_line += " " + word if current_line.strip() else "  " + word
        if current_line.strip():
            text.append(current_line)
        
        # text.append("\n\n")
        
        return text

    def _format_config_details(self, config_type: str) -> Text:
        """Format config section details for the right panel using Rich Text (no markup parsing)."""
        text = Text()
        
        if config_type == "entrypoint" and self.config.entrypoint:
            text.append("ENTRYPOINT", style="bold")
            text.append("\n\n")
            entrypoint = self.config.entrypoint
            if isinstance(entrypoint, list):
                text.append("\n".join(entrypoint))
            else:
                text.append(str(entrypoint))
        
        elif config_type == "cmd" and self.config.cmd:
            text.append("CMD", style="bold")
            text.append("\n\n")
            cmd = self.config.cmd
            if isinstance(cmd, list):
                text.append("\n".join(cmd))
            else:
                text.append(str(cmd))
        
        elif config_type == "expose" and self.config.exposed_ports:
            text.append("EXPOSED PORTS", style="bold")
            text.append("\n\n")
            for port in self.config.exposed_ports:
                text.append(f"  {port}\n")
        
        elif config_type == "workdir" and self.config.workdir:
            text.append("WORKING DIRECTORY", style="bold")
            text.append("\n\n")
            text.append(self.config.workdir)
        
        elif config_type == "env" and self.config.env_vars:
            text.append("ENVIRONMENT VARIABLES", style="bold")
            text.append("\n\n")
            for k, v in self.config.env_vars.items():
                text.append(f"  {k}={v}\n")
        
        else:
            text.append("Select a layer or config section to view details")
        
        return text

    @on(Collapsible.Toggled)
    def on_collapsible_toggled(self, event: Collapsible.Toggled) -> None:
        """Handle collapsible toggle events to update details panel."""
        collapsible_id = event.collapsible.id
        details_widget = self.query_one("#fs-path", Static)
        
        if collapsible_id and collapsible_id.startswith("layer-"):
            # Layer toggled
            try:
                layer_index = int(collapsible_id.split("-")[1])
                layer = self.config.layers[layer_index - 1]
                self._selected_layer = layer
                details_widget.update(self._format_layer_details(layer))
            except (ValueError, IndexError):
                self._selected_layer = None
        
        elif collapsible_id and collapsible_id.startswith("config-"):
            # Config section toggled
            self._selected_layer = None
            config_type = collapsible_id.split("-")[1]
            details_widget.update(self._format_config_details(config_type))

    # Navigation Actions

    def action_go_back(self) -> None:
        """Go back to the repository screen."""
        self.app.pop_screen()

    def action_select(self) -> None:
        """Peek into the selected layer's contents."""
        if not self._selected_layer:
            self.notify("Select a layer first by clicking on it", severity="warning")
            return
        
        layer = self._selected_layer
        
        if not layer.digest:
            self.notify("This layer has no digest to peek into", severity="error")
            return
        
        # Push the layer contents screen
        self.app.push_screen(
            LayerContentsScreen(
                namespace=self.namespace,
                repo=self.repo,
                digest=layer.digest,
                layer_size=layer.size,
                instruction=layer.instruction,
            )
        )

    def action_toggle_collapse(self) -> None:
        """Toggle collapsed state of all Collapsible widgets."""
        self._all_collapsed = not self._all_collapsed
        for collapsible in self.query(Collapsible):
            collapsible.collapsed = self._all_collapsed

    def action_slay_all(self) -> None:
        """Peek into ALL layers at once (Layer Slayer mode)."""
        layers = self.image_data.get("layers", [])
        if not layers:
            self.notify("No layers found in this image", severity="warning")
            return
        
        # Count layers with digests
        layer_count = sum(1 for l in layers if l.get("digest"))
        if layer_count == 0:
            self.notify("No layer digests available", severity="warning")
            return
        
        self.notify(f"Peeking {layer_count} layers...")
        self._run_layerslayer(layers)

    @work(exclusive=True, thread=True)
    def _run_layerslayer(self, layers: list) -> None:
        """Run layerslayer in background thread."""
        db = get_database()
        try:
            result = layerslayer(
                namespace=self.namespace,
                repo=self.repo,
                layers=layers,
                db=db,
            )
            self.app.call_from_thread(self._show_layerslayer_result, result)
        except Exception as e:
            self.app.call_from_thread(
                self.notify, f"Layer Slayer error: {e}", severity="error"
            )
        finally:
            db.close()

    def _show_layerslayer_result(self, result) -> None:
        """Display Layer Slayer results in embedded DataTable."""
        if result.error:
            self.notify(f"Error: {result.error}", severity="error")
            return
        
        # Store entries
        self.all_entries = result.all_entries
        
        # Populate the DataTable
        table = self.query_one("#fs-listing", DataTable)
        table.clear()
        self._row_data.clear()
        
        for idx, entry in enumerate(result.all_entries):
            # Get just the filename
            name = entry.name.rstrip("/").split("/")[-1]
            if entry.is_dir:
                name += "/"
            if entry.is_symlink and entry.linkname:
                name += f" -> {entry.linkname}"
            
            uid_gid = f"{entry.uid}/{entry.gid}"
            size_str = f"{entry.size}" if entry.size else ""
            
            table.add_row(entry.mode, uid_gid, size_str, entry.mtime, name)
            self._row_data[idx] = entry
        
        # Update path display
        kb = result.total_bytes_downloaded / 1024
        self.query_one("#fs-path", Static).update(
            f"Path: / | {result.total_entries} entries | {kb:.1f} KB downloaded"
        )
        
        self.notify(
            f"Loaded {result.total_entries} entries from {result.layers_peeked} layers"
        )

"""
Search input screen for docker-dorker.

Initial screen with search query input.
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Static
from textual.containers import Container


class SearchScreen(Screen):
    """Initial screen with search input."""

    BINDINGS = [
        ("escape", "quit_app", "Exit"),
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()
        yield Container(
            Static("dockerDorker", id="title"),
            Static("Enter a search query:", id="prompt"),
            Input(placeholder="e.g., example", id="search-input"),
            Button("yolo", variant="primary", id="search-button"),
            id="search-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Focus the input on mount."""
        self.query_one("#search-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input."""
        query = event.value.strip()
        if query:
            self.app.perform_search(query)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle search button click."""
        if event.button.id == "search-button":
            query = self.query_one("#search-input", Input).value.strip()
            if query:
                self.app.perform_search(query)

    def action_quit_app(self) -> None:
        """Exit the application."""
        self.app.exit()

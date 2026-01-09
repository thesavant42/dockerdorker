"""Pagination navigation widget."""

from __future__ import annotations

from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Static


class PaginationWidget(Static):
    """Displays pagination controls: < Page X/YYY >."""

    current_page: reactive[int] = reactive(1)
    total_pages: reactive[int] = reactive(1)

    class PageChanged(Message):
        """Posted when user navigates to a different page."""

        def __init__(self, page: int) -> None:
            """Initialize with new page number.
            
            Args:
                page: The new page number.
            """
            self.page = page
            super().__init__()

    def __init__(self, **kwargs) -> None:
        """Initialize the pagination widget."""
        super().__init__(**kwargs)
        self._visible = False

    def on_mount(self) -> None:
        """Initial render on mount."""
        self._update_display()

    def watch_current_page(self, page: int) -> None:
        """React to page changes.
        
        Args:
            page: The new current page number.
        """
        self._update_display()

    def watch_total_pages(self, total: int) -> None:
        """React to total pages changes.
        
        Args:
            total: The new total page count.
        """
        self._update_display()

    def _update_display(self) -> None:
        """Update the displayed text."""
        if not self._visible or self.total_pages <= 1:
            self.update("")
            return

        # Format: < Page   1/123 >
        # Using 3-digit width for page numbers
        self.update(f"< Page {self.current_page:3d}/{self.total_pages:3d} >")

    def show(self, current: int, total: int) -> None:
        """Show pagination with given values.
        
        Args:
            current: Current page number.
            total: Total number of pages.
        """
        self._visible = True
        self.current_page = current
        self.total_pages = total

    def hide(self) -> None:
        """Hide pagination display."""
        self._visible = False
        self.update("")

    def next_page(self) -> None:
        """Navigate to next page if available."""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.post_message(self.PageChanged(self.current_page))

    def prev_page(self) -> None:
        """Navigate to previous page if available."""
        if self.current_page > 1:
            self.current_page -= 1
            self.post_message(self.PageChanged(self.current_page))

"""Tag selector widget using compact Select dropdown."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from textual.widgets import Select

from app.ui.messages import TagSelected


class TagSelectorWidget(Select[str]):
    """A compact dropdown widget for selecting Docker image tags."""

    def __init__(self, **kwargs) -> None:
        """Initialize the tag selector widget."""
        super().__init__([], prompt="Select tag...", **kwargs)
        self._namespace: Optional[str] = None
        self._repo: Optional[str] = None
        self._tags: List[Dict[str, Any]] = []

    def load_tags(self, namespace: str, repo: str, tags: List[Dict[str, Any]]) -> None:
        """Load tags into the selector.
        
        Args:
            namespace: Repository namespace/owner.
            repo: Repository name.
            tags: List of tag dictionaries from Docker Hub API.
        """
        self._namespace = namespace
        self._repo = repo
        self._tags = tags
        
        # Build options: (display_label, value)
        options = [(tag.get("name", "unknown"), tag.get("name", "unknown")) for tag in tags]
        self.set_options(options)

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle tag selection change."""
        if not self._namespace or not self._repo or event.value == Select.BLANK:
            return
        
        tag_name = str(event.value)
        tag_data = next(
            (t for t in self._tags if t.get("name") == tag_name),
            {}
        )
        
        self.post_message(
            TagSelected(
                namespace=self._namespace,
                repo=self._repo,
                tag_name=tag_name,
                tag_data=tag_data
            )
        )

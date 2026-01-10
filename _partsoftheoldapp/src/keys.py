"""
Centralized key bindings for docker-dorker.

All app key bindings defined here for consistency.
Import these in screens rather than defining Binding() inline.

NOTE: Arrow keys are NOT defined here - they are handled automatically
by focused widgets (DataTable, Tree, etc.). Defining them at screen level
with priority=True would intercept them before the widget gets them,
breaking widget navigation.

Tab/Shift+Tab focus navigation is also automatic in Textual.
"""

from textual.binding import Binding

# Back navigation - priority ensures it works even when a widget has focus
BACK = Binding("escape", "go_back", "Back", priority=True)

# Selection/activation - priority ensures it works even when a widget has focus
ENTER = Binding("enter", "select", "Select", priority=True)

# Collapse/expand all - for screens with Collapsible widgets
COLLAPSE = Binding("c", "toggle_collapse", "Collapse All")

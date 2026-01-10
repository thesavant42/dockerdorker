# Refactor Styles.tcss into Submodules

## Problem Statement

- The default [styles](app\styles\styles.tcss) grows cumbersome and is getting hard to manage.

## Solution

I want to break out the styles by widget, and by panel.

### Panels & Body Styles

- `styles.tcss` - This is the page that currently exists today, with all of the styles. - 125 loc
    - will still exist and contain a minimal set of styles and comments to build the body structure of the tui

- New styles needed:
    - `top-panel.tcss`
    - `left-pane.tcss`
    - `right-panel.tcss`
- Custom Widgets will also need styles
    - Search Results Widget
        - `search-results-widgets.tcss`
    - Build Info custom widget
        - `build-info-widgets.tcss`
    - Files Info Widget
        - `terminal-simulator-widget.tcss`

## 1. Current Layout Info
Styles, Body panels

- `styles.tcss`
    - These should stay in `styles.tcss` 
- Header styling - built-in widget with `dock:top`
    - No additional styling needed - Header has its own internal CSS
- Footer styling - uses built-in `dock:bottom`
    - No additional styling needed - footer has its own internal CSS
- Screen uses **vertical layout** by default
     - widgets stack **top to bottom**
- Main content area 
    - horizontal split for left/right panels
    - `main-content`

## 2. Current Panels Info

These define the 3 main rectangular elements that fill in the superstructure of the  layout

### Top Panels

- Top panel - flows below header in vertical layout (not docked)
    - Top panel content - horizontal layout for details and tag selector
    - Result details widget - takes most of top panel width - `result-details`
- Left panel - 50% width, contains search results - `left-panel`
- Right panel - 50% width, contains result details - `right-panel`

## - Refactor Styles
Sub-Tasks : Custom Widget Styles
- [ ] Task Refactor Styles
    - [ ] Task: Redfactor Search Results Widget
    - [ ] Task: Redfactor Selector Widget 
    - [ ] Task: Redfactor Tabbed Content Switcher Widget
    - [ ] Task: Redfactor Build Info Custom Widget (in right panel)

### Constraints
**THESE ARE MANDATORY**
Read the following link for implementational guidance outline, then build out a plan with subtasks that can be delegated to a programming agent.
- Sub-task instructions must:
    - reference [STYLES.MD](STYLES.MD)
    - must include instructions to use textual docs MCP
    - Must read [how-to-split-styles.md](app\styles\how-to-split-styles.md)

### Files/Terminal Simulator Custom Widget (TBD)

 How to split CSS into multiple files [app\styles\how-to-split-styles.md](app\styles\how-to-split-styles.md)

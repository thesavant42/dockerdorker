# DeepWiki Q&A with Code Context for Repository: Textualize/textual

### NOT YET READY FOR IMPLEMENTATION


## Q1

Can I use a tabbed content switcher to alternate between 2 data table widgets?

### Answer

- Yes, you can use `TabbedContent` to alternate between 2 `DataTable` widgets. The `TabbedContent` widget is designed to switch between different content panes, and each pane can contain any widget including `DataTable` textual:1-14 .

## Example Implementation

Here's how to set up two `DataTable` widgets in a tabbed interface:

```python
from textual.app import App, ComposeResult
from textual.widgets import TabbedContent, TabPane, DataTable

class DataTableTabsApp(App):
    def compose(self) -> ComposeResult:
        with TabbedContent():
            with TabPane("Table 1", id="table-1"):
                yield DataTable(id="data-table-1")
            with TabPane("Table 2", id="table-2"):
                yield DataTable(id="data-table-2")
    
    def on_mount(self) -> None:
        # Configure first table
        table1 = self.query_one("#data-table-1", DataTable)
        table1.add_columns("Name", "Age", "City")
        table1.add_row("Alice", "30", "New York")
        table1.add_row("Bob", "25", "London")
        
        # Configure second table
        table2 = self.query_one("#data-table-2", DataTable)
        table2.add_columns("Product", "Price", "Stock")
        table2.add_row("Laptop", "$999", "50")
        table2.add_row("Mouse", "$25", "200")
```

## Key Points

- Each `TabPane` acts as a container for one `DataTable` textual:165-169 
- The `TabbedContent` widget automatically handles switching between panes when tabs are clicked
- You can programmatically switch tabs using the `active` reactive attribute textual:56-61 
- Each `DataTable` maintains its own state independently when switching between tabs

## Programmatic Tab Switching

You can also switch between tables programmatically:

```python
# Switch to the second table
self.query_one(TabbedContent).active = "table-2"
```

The `TabbedContent` widget combines `Tabs` and `ContentSwitcher` to provide this functionality textual:10-13 , making it perfect for alternating between multiple data tables.

## Notes

- Each `DataTable` will maintain its scroll position and cursor state when switching between tabs
- You can style individual tabs and tables independently using CSS
- The `TabbedContent` widget was added in version 0.16.0 textual:3-3 

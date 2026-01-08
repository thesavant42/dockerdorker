# dockerdorker

The flow described below is the ideal state.

## App Usage Flow 

1. - [x] User starts the application:
```bash
python app.y
```

... which launches the Textual GUI.

2. Searching [Searching](docs\README-search.md)

To get started I will need to search for something on dockerhub, which will get passed through to the search submodule.
    - Use [textual.system_commands](https://textual.textualize.io/api/system_commands_source/#textual.system_commands.SystemCommandsProvider.search) to search via the[command palette](https://textual.textualize.io/guide/command_palette/).
    - [search method](https://textual.textualize.io/guide/command_palette/#search-method)
    - After user types in the search query and hits the enter key:
        - the the search is executed asyncronously
        - the command palette menu can be closed without cancelling the search, and a status indicator animation [loading indicator](https://textual.textualize.io/widgets/loading_indicator/)
            - Animator should be centered over the "Left" Panel, which is the the Left square, undearneath the panel, and above the footer.
            - This is also where search results should be rendered after the results finish.
            - Left panel search results should be rendered in 4 vertical columns. The columns should support vertical scrolling.
    2a. Rendering Search Results [dataTable](https://textual.textualize.io/widgets/data_table/)
        - No header for this datatable
        "Left Panel" (lower Left panel, above the footer, beneatht the wide panel)
        - a Verticle scroll bar on the left side of the panel (needs to be added)
        4 Columns, equal width (25% each)
        - Tabs along the top of the panel for pagination [tabs](https://textual.textualize.io/widgets/tabbed_content/)
            - variable width? shrink as needed? Either way is fine.
            - zebra_stripes: False
            - cursortype: cell

3. Enumerate Tags for selected Repository [Enumerate](docs/README-enumerate.md)
    - `app\core\api\dockerhub_v2_api.py` has the methods to use for this
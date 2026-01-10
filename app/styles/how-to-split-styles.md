# How to split Textual TCSS into multiple files



## How to split Textual CSS into multiple files

Instead of a single `CSS_PATH = "styles.tcss"`, you can set `CSS_PATH` to a list of file paths as seen in this *example* code:

```python
class MyApp(App):
    CSS_PATH = ["base.tcss", "components.tcss", "themes.tcss"]
```

Textual will load and combine all specified CSS files during application startup

## How it works internally

The `Stylesheet` class manages multiple CSS sources through its `source` dictionary.

- When you provide multiple paths:

    1. Each file is added as a separate `CssSource` via `add_source()` textual:333-370 
    2. All sources are parsed and combined into a single stylesheet textual:409-438 
    3. The combined rules are applied to widgets with normal CSS specificity rules

## Limitations

- Textual CSS doesn't support `@import` statements like web CSS.
- You *must* explicitly list all files in `CSS_PATH`.
- However, this approach provides the same organizational benefits
     - you can group related styles in separate files
     - and maintain them independently.


## Notes

- File order in `CSS_PATH` matters for specificity when rules have equal specificity
- All files share the same CSS variable scope
- The `read_all()` method handles loading multiple files efficiently 

### Using multiple CSS files

You can also set the `CSS_PATH` class variable to a list of paths. Textual will combine the rules from all of the supplied paths.

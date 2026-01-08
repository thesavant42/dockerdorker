"""
Utility functions for dockerDorker.

This package contains:
- tar_parser: Tar header parsing for layer inspection
- layer_fetcher: HTTP Range request handling for partial downloads
- formatters: Output formatting utilities
- filesystem_utils: Directory listing and layer merging utilities
- image_config_formatter: Image config data structures
- image_formatters: Size and digest formatting
"""

from app.core.utils.tar_parser import TarEntry, parse_tar_header
from app.core.utils.layer_fetcher import (
    LayerPeekResult,
    LayerSlayerResult,
    peek_layer_blob_partial,
    peek_layer_blob_streaming,
    layerslayer,
)
from app.core.utils.filesystem_utils import (
    DirectoryListing,
    get_directory_contents,
    format_ls_line,
    format_parent_entry,
    get_entry_basename,
    merge_layer_entries,
)
from app.core.utils.formatters import (
    format_date,
    abbreviate_os,
    abbreviate_arch,
    format_result_row,
    empty_row,
)
from app.core.utils.image_config_formatter import (
    LayerInfo,
    ImageConfigSummary,
    parse_image_config,
    format_image_config,
    fmt_date,
    fmt_size,
)
from app.core.utils.image_formatters import format_size, format_digest

__all__ = [
    # tar_parser
    "TarEntry",
    "parse_tar_header",
    # layer_fetcher
    "LayerPeekResult",
    "LayerSlayerResult",
    "peek_layer_blob_partial",
    "peek_layer_blob_streaming",
    "layerslayer",
    # filesystem_utils
    "DirectoryListing",
    "get_directory_contents",
    "format_ls_line",
    "format_parent_entry",
    "get_entry_basename",
    "merge_layer_entries",
    # formatters
    "format_date",
    "abbreviate_os",
    "abbreviate_arch",
    "format_result_row",
    "empty_row",
    # image_config_formatter
    "LayerInfo",
    "ImageConfigSummary",
    "parse_image_config",
    "format_image_config",
    "fmt_date",
    "fmt_size",
    # image_formatters
    "format_size",
    "format_digest",
]

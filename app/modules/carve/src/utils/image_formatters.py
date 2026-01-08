"""Image config formatting utilities."""


def format_size(size_bytes: int) -> str:
    """Format byte size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def format_digest(digest: str) -> str:
    """Return full digest without truncation."""
    return digest or "N/A"

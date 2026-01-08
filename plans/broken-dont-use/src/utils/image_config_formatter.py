"""
Image config formatter for docker-dorker.

Parses Docker Hub image JSON and returns data structures for DataTable display.
Includes dataclasses for structured image config representation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


# =============================================================================
# Utility functions
# =============================================================================


def fmt_date(iso: Optional[str]) -> str:
    """Format ISO date string to MM-DD-YYYY format."""
    if not iso:
        return "null"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%m-%d-%Y")
    except Exception:
        return iso


def fmt_size(size: Optional[int]) -> str:
    """Format size in bytes to human-readable format."""
    if size is None or size == 0:
        return "0 B"
    
    for unit in ["B", "KB", "MB", "GB"]:
        if abs(size) < 1024:
            return f"{size:.1f} {unit}" if unit != "B" else f"{size} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


# =============================================================================
# Dataclasses for structured image config representation
# =============================================================================


@dataclass
class LayerInfo:
    """Information about a single image layer."""
    index: int              # Layer number (1, 2, 3...)
    digest: str             # Full sha256 digest
    short_digest: str       # First 12 chars of hash (after sha256:)
    size: int               # Size in bytes
    size_formatted: str     # Human readable size
    instruction: str        # Full instruction text
    instruction_type: str   # RUN, COPY, ADD, CMD, etc.


@dataclass
class ImageConfigSummary:
    """Structured summary of an image configuration."""
    os: str
    arch: str
    variant: Optional[str]
    created: str
    total_size: int
    total_size_formatted: str
    digest: str
    entrypoint: Optional[list[str]]
    cmd: Optional[list[str]]
    workdir: Optional[str]
    exposed_ports: list[str] = field(default_factory=list)
    env_vars: dict[str, str] = field(default_factory=dict)
    layers: list[LayerInfo] = field(default_factory=list)


# =============================================================================
# Parser functions
# =============================================================================


def _extract_instruction_type(instruction: str) -> str:
    """Extract the instruction type (RUN, COPY, ADD, etc.) from instruction text."""
    if not instruction:
        return ""
    # Instruction typically starts with the command like "RUN", "COPY", etc.
    parts = instruction.strip().split(None, 1)
    if parts:
        cmd = parts[0].upper()
        # Known Dockerfile instructions
        if cmd in ("RUN", "COPY", "ADD", "ENV", "WORKDIR", "EXPOSE", "CMD",
                   "ENTRYPOINT", "LABEL", "ARG", "USER", "VOLUME", "SHELL"):
            return cmd
    return ""


def parse_image_config(image_data: dict) -> ImageConfigSummary:
    """
    Parse image config data into a structured ImageConfigSummary.
    
    Args:
        image_data: The image config dictionary from Docker Hub API
        
    Returns:
        ImageConfigSummary with all parsed fields
    """
    # Basic info
    os_name = image_data.get("os", "unknown")
    arch = image_data.get("arch", image_data.get("architecture", "unknown"))
    variant = image_data.get("variant")
    created = fmt_date(image_data.get("last_pushed"))
    digest = image_data.get("digest", "")
    
    # Parse layers and calculate total size
    layers_data = image_data.get("layers", [])
    layers: list[LayerInfo] = []
    total_size = 0
    layer_index = 1
    
    for layer in layers_data:
        layer_digest = layer.get("digest", "")
        size = layer.get("size", 0)
        instruction = (layer.get("instruction") or "").strip()
        
        # Only count layers with actual digests (not instruction-only entries)
        if layer_digest:
            total_size += size
            
            # Extract short digest (first 12 chars after sha256:)
            short_digest = layer_digest[7:19] if layer_digest.startswith("sha256:") else layer_digest[:12]
            
            layers.append(LayerInfo(
                index=layer_index,
                digest=layer_digest,
                short_digest=short_digest,
                size=size,
                size_formatted=fmt_size(size),
                instruction=instruction,
                instruction_type=_extract_instruction_type(instruction),
            ))
            layer_index += 1
        elif instruction:
            # Instruction-only entry (like ENTRYPOINT, CMD, etc.)
            # These don't create layers but we may want to track them separately
            pass
    
    # Parse config entries (entrypoint, cmd, workdir, env, expose)
    config = image_data.get("config", {})
    
    # Entrypoint
    entrypoint = config.get("Entrypoint") or image_data.get("entrypoint")
    
    # CMD
    cmd = config.get("Cmd") or image_data.get("cmd")
    
    # Working directory
    workdir = config.get("WorkingDir") or image_data.get("workdir")
    
    # Exposed ports
    exposed_ports: list[str] = []
    ports_data = config.get("ExposedPorts") or image_data.get("exposed_ports", {})
    if isinstance(ports_data, dict):
        exposed_ports = list(ports_data.keys())
    elif isinstance(ports_data, list):
        exposed_ports = ports_data
    
    # Environment variables
    env_vars: dict[str, str] = {}
    env_list = config.get("Env") or image_data.get("env", [])
    if isinstance(env_list, list):
        for env_str in env_list:
            if "=" in env_str:
                key, value = env_str.split("=", 1)
                env_vars[key] = value
    
    return ImageConfigSummary(
        os=os_name,
        arch=arch,
        variant=variant,
        created=created,
        total_size=total_size,
        total_size_formatted=fmt_size(total_size),
        digest=digest,
        entrypoint=entrypoint,
        cmd=cmd,
        workdir=workdir,
        exposed_ports=exposed_ports,
        env_vars=env_vars,
        layers=layers,
    )


# =============================================================================
# Legacy function for backward compatibility with existing DataTable display
# =============================================================================


def format_image_config(image_data: dict) -> list[tuple[str, str, str]]:
    """
    Format image config data into rows for DataTable.
    
    Args:
        image_data: The image config dictionary from Docker Hub API
        
    Returns:
        List of tuples (type, key, value) for each row:
        - type: "header", "info", "layer_digest", "instruction"
        - key: Label for the row
        - value: Content for the row
    """
    rows = []
    
    # Header row with digest and architecture
    digest = image_data.get("digest", "unk")
    arch = image_data.get("arch", "unk")
    os_name = image_data.get("os", "unk")
    variant = image_data.get("variant", "")
    
    arch_display = f"{os_name}/{arch}"
    if variant:
        arch_display += f"/{variant}"
    
    rows.append(("header", "DIGEST", f"{digest}  Architecture: {arch_display}"))
    
    # Info row with dates and features
    last_pushed = fmt_date(image_data.get("last_pushed"))
    last_pulled = fmt_date(image_data.get("last_pulled"))
    features = image_data.get("features") or "null"
    
    rows.append(("info", "Info", f"Pushed: {last_pushed}    Pulled: {last_pulled}    Features: {features}"))
    
    # Empty separator
    rows.append(("separator", "", ""))
    
    # Process layers
    layers = image_data.get("layers", [])
    for layer in layers:
        layer_digest = layer.get("digest")
        instruction = (layer.get("instruction") or "").strip()
        size = layer.get("size", 0)
        
        if not layer_digest:
            # Instruction-only layer (no digest)
            if instruction:
                rows.append(("instruction", "INSTRUCTION", instruction))
            else:
                rows.append(("instruction", "INSTRUCTION", ""))
        else:
            # Layer with digest
            rows.append(("layer_digest", "DIGEST", f"{layer_digest}    SIZE: {fmt_size(size)}"))
            if instruction:
                rows.append(("instruction", "INSTRUCTION", instruction))
            # Empty row after each layer with digest
            rows.append(("separator", "", ""))
    
    return rows

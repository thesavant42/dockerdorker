"""Build info widget for displaying Docker image configuration details."""

from __future__ import annotations

from typing import Optional

from textual.widgets import Static

from app.core.utils.image_config_formatter import ImageConfigSummary


class BuildInfoWidget(Static):
    """Widget for displaying parsed Docker image build information."""

    def __init__(self, **kwargs) -> None:
        """Initialize the build info widget."""
        super().__init__("", markup=False, **kwargs)
        self._current_summary: Optional[ImageConfigSummary] = None

    def load_config(self, summary: ImageConfigSummary) -> None:
        """Load and display image configuration summary.
        
        Args:
            summary: Parsed ImageConfigSummary to display.
        """
        self._current_summary = summary
        content = self._format_build_info(summary)
        self.update(content)
    
    def _format_build_info(self, summary: ImageConfigSummary) -> str:
        """Format ImageConfigSummary into displayable text.
        
        Args:
            summary: The image config summary to format.
            
        Returns:
            Formatted string with all build information.
        """
        lines = []
        
        # Header
        lines.append("Image Configuration")
        lines.append("")
        
        # Basic info
        arch_line = f"OS/Arch: {summary.os}/{summary.arch}"
        if summary.variant:
            arch_line += f"/{summary.variant}"
        lines.append(arch_line)
        lines.append(f"Created: {summary.created}")
        lines.append(f"Total Size: {summary.total_size_formatted}")
        if summary.digest:
            digest_display = summary.digest[:64] + "..." if len(summary.digest) > 64 else summary.digest
            lines.append(f"Digest: {digest_display}")
        else:
            lines.append("Digest: (not available)")
        lines.append("")
        
        # Working directory
        if summary.workdir:
            lines.append(f"WORKDIR: {summary.workdir}")
            lines.append("")
        
        # Entrypoint
        if summary.entrypoint:
            entrypoint_str = " ".join(str(item) for item in summary.entrypoint)
            lines.append(f"ENTRYPOINT: {entrypoint_str}")
            lines.append("")
        
        # CMD
        if summary.cmd:
            cmd_str = " ".join(str(item) for item in summary.cmd)
            lines.append(f"CMD: {cmd_str}")
            lines.append("")
        
        # Exposed ports
        if summary.exposed_ports:
            ports_str = ", ".join(str(port) for port in summary.exposed_ports)
            lines.append(f"EXPOSE: {ports_str}")
            lines.append("")
        
        # Environment variables
        if summary.env_vars:
            lines.append("ENV Variables:")
            for key, value in sorted(summary.env_vars.items()):
                lines.append(f"  {key}={value}")
            lines.append("")
        
        # Layers
        if summary.layers:
            lines.append("Layers:")
            for layer in summary.layers:
                lines.append(f"  Layer {layer.index}: {layer.short_digest} ({layer.size_formatted})")
                if layer.instruction:
                    lines.append(f"    {layer.instruction_type}: {layer.instruction}")
            lines.append("")
        
        return "\n".join(lines)

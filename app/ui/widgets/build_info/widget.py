"""Build info widget for displaying Docker image configuration details."""

from __future__ import annotations

from typing import Optional

from textual.widgets import Static

from app.core.utils.image_config_formatter import ImageConfigSummary


def _escape_markup(text: str) -> str:
    """Escape square brackets in text to prevent markup interpretation."""
    return text.replace("[", r"\[").replace("]", r"\]")


class BuildInfoWidget(Static):
    """Widget for displaying parsed Docker image build information."""

    def __init__(self, **kwargs) -> None:
        """Initialize the build info widget."""
        super().__init__("", markup=True, **kwargs)
        self._current_summary: Optional[ImageConfigSummary] = None

    def load_config(self, summary: ImageConfigSummary) -> None:
        """Load and display image configuration summary.
        
        Args:
            summary: Parsed ImageConfigSummary to display.
        """
        self._current_summary = summary
        content = self._format_build_info(summary)
        self.update(content)
    
    def _format_instruction(self, instruction: str, instruction_type: str, max_length: int = 80) -> str:
        """Format a long instruction with line breaks at logical points.
        
        Args:
            instruction: The instruction text to format.
            instruction_type: The instruction type (RUN, COPY, etc.).
            max_length: Maximum length before splitting.
            
        Returns:
            Formatted instruction with line breaks at && or | if needed.
        """
        # Escape markup characters first
        instruction = _escape_markup(instruction)
        
        if len(instruction) <= max_length:
            return instruction
        
        # Split at && or | if present
        if " && " in instruction:
            parts = instruction.split(" && ")
            formatted = parts[0]
            indent = " " * (len(instruction_type) + 2)  # "  RUN: " = 6 spaces
            for part in parts[1:]:
                formatted += "\n" + indent + "&& " + part
            return formatted
        elif " | " in instruction:
            parts = instruction.split(" | ")
            formatted = parts[0]
            indent = " " * (len(instruction_type) + 2)
            for part in parts[1:]:
                formatted += "\n" + indent + "| " + part
            return formatted
        
        return instruction
    
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
            lines.append(f"WORKDIR: {_escape_markup(summary.workdir)}")
            lines.append("")
        
        # Entrypoint
        if summary.entrypoint:
            entrypoint_str = " ".join(_escape_markup(str(item)) for item in summary.entrypoint)
            lines.append(f"ENTRYPOINT: {entrypoint_str}")
            lines.append("")
        
        # CMD
        if summary.cmd:
            cmd_str = " ".join(_escape_markup(str(item)) for item in summary.cmd)
            lines.append(f"CMD: {cmd_str}")
            lines.append("")
        
        # Exposed ports
        if summary.exposed_ports:
            ports_str = ", ".join(_escape_markup(str(port)) for port in summary.exposed_ports)
            lines.append(f"EXPOSE: {ports_str}")
            lines.append("")
        
        # Environment variables
        if summary.env_vars:
            lines.append("ENV Variables:")
            for key, value in sorted(summary.env_vars.items()):
                lines.append(f"  {_escape_markup(key)}={_escape_markup(value)}")
            lines.append("")
        
        # Layers
        if summary.layers:
            lines.append("")
            lines.append("Layers:")
            for layer in summary.layers:
                lines.append("")
                # Colorize layer number, digest, and size
                layer_line = f"  [bold green]Layer {layer.index}[/]: [cyan]{layer.short_digest}[/] [yellow]({layer.size_formatted})[/]"
                lines.append(layer_line)
                if layer.instruction:
                    formatted_instruction = self._format_instruction(
                        layer.instruction, 
                        layer.instruction_type
                    )
                    # Split multi-line instructions and add each line with proper indentation
                    instruction_lines = formatted_instruction.split("\n")
                    for i, inst_line in enumerate(instruction_lines):
                        if i == 0:
                            # Colorize instruction type
                            lines.append(f"    [bold]{layer.instruction_type}[/]: {inst_line}")
                        else:
                            lines.append(f"      {inst_line}")
        
        return "\n".join(lines)

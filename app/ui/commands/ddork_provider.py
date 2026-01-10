"""DdorkProvider - /ddork CLI-style commands for the command palette."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from textual.command import DiscoveryHit, Hit, Hits, Provider

if TYPE_CHECKING:
    from textual.app import App


# Subcommand definitions with help text
SUBCOMMANDS = {
    "search": "Search Docker Hub for repositories",
    "repos": "List repositories for a namespace",
    "tags": "List tags for a repository (ns/repo)",
    "containers": "List container digests for a tag (ns/repo:tag)",
    "layers": "Get layer digests from registry (ns/repo:tag)",
    "files": "Run layer peek to list files (ns/repo:tag)",
    "carve": "Extract a file from image layers (ns/repo:tag /path/to/file)",
}


class DdorkProvider(Provider):
    """Provides /ddork CLI-style commands to the command palette."""

    @property
    def _app(self) -> App:
        """Get the app instance."""
        return self.screen.app

    async def discover(self) -> Hits:
        """Show available /ddork commands when palette opens."""
        for cmd, help_text in SUBCOMMANDS.items():
            yield DiscoveryHit(
                display=f"/ddork {cmd}",
                command=self._no_op,
                help=help_text,
            )

    async def _no_op(self) -> None:
        """Placeholder for discovery hits."""
        pass

    async def search(self, query: str) -> Hits:
        """Parse and handle /ddork commands."""
        query = query.strip()

        # Must start with /ddork
        if not query.lower().startswith("/ddork"):
            return

        # Just "/ddork" - show hint
        if query.lower() == "/ddork":
            yield Hit(
                score=50,
                match_display="/ddork <command>",
                command=self._no_op,
                help="Type a subcommand: search, repos, tags, containers, layers, files, carve",
            )
            return

        # Parse: /ddork <subcommand> [args]
        remainder = query[6:].strip()  # Remove "/ddork"
        parts = remainder.split(maxsplit=1)
        subcommand = parts[0].lower() if parts else ""
        args = parts[1].strip() if len(parts) > 1 else ""

        # Handle each subcommand
        if subcommand == "search":
            if args:
                yield Hit(
                    score=100,
                    match_display=f"Search Docker Hub: {args}",
                    command=lambda a=args: self._execute_search(a),
                    help=f"Search Docker Hub for '{args}'",
                )
            else:
                yield Hit(
                    score=50,
                    match_display="/ddork search <query>",
                    command=self._no_op,
                    help="Example: /ddork search nginx",
                )

        elif subcommand == "repos":
            if args:
                yield Hit(
                    score=100,
                    match_display=f"List repos for: {args}",
                    command=lambda ns=args: self._execute_repos(ns),
                    help=f"List repositories for namespace '{args}'",
                )
            else:
                yield Hit(
                    score=50,
                    match_display="/ddork repos <namespace>",
                    command=self._no_op,
                    help="Example: /ddork repos drichnerdisney",
                )

        elif subcommand == "tags":
            if args and "/" in args:
                yield Hit(
                    score=100,
                    match_display=f"List tags for: {args}",
                    command=lambda r=args: self._execute_tags(r),
                    help=f"List tags for repository '{args}'",
                )
            else:
                yield Hit(
                    score=50,
                    match_display="/ddork tags <namespace/repo>",
                    command=self._no_op,
                    help="Example: /ddork tags drichnerdisney/ollama",
                )

        elif subcommand == "containers":
            parsed = self._parse_image_ref(args)
            if parsed and parsed[2]:  # Has tag
                ns, repo, tag = parsed
                yield Hit(
                    score=100,
                    match_display=f"List containers for: {ns}/{repo}:{tag}",
                    command=lambda n=ns, r=repo, t=tag: self._execute_containers(n, r, t),
                    help=f"List container digests for '{ns}/{repo}:{tag}'",
                )
            else:
                yield Hit(
                    score=50,
                    match_display="/ddork containers <namespace/repo:tag>",
                    command=self._no_op,
                    help="Example: /ddork containers drichnerdisney/ollama:v1",
                )

        elif subcommand == "layers":
            parsed = self._parse_image_ref(args)
            if parsed and parsed[2]:  # Has tag
                ns, repo, tag = parsed
                yield Hit(
                    score=100,
                    match_display=f"Get layers for: {ns}/{repo}:{tag}",
                    command=lambda n=ns, r=repo, t=tag: self._execute_layers(n, r, t),
                    help=f"Get layer digests from registry for '{ns}/{repo}:{tag}'",
                )
            else:
                yield Hit(
                    score=50,
                    match_display="/ddork layers <namespace/repo:tag>",
                    command=self._no_op,
                    help="Example: /ddork layers drichnerdisney/ollama:v1",
                )

        elif subcommand == "files":
            parsed = self._parse_image_ref(args)
            if parsed and parsed[2]:  # Has tag
                ns, repo, tag = parsed
                yield Hit(
                    score=100,
                    match_display=f"List files for: {ns}/{repo}:{tag}",
                    command=lambda n=ns, r=repo, t=tag: self._execute_files(n, r, t),
                    help=f"Run layer peek for '{ns}/{repo}:{tag}'",
                )
            else:
                yield Hit(
                    score=50,
                    match_display="/ddork files <namespace/repo:tag>",
                    command=self._no_op,
                    help="Example: /ddork files drichnerdisney/ollama:v1",
                )

        elif subcommand == "carve":
            # Parse: <namespace/repo:tag> <filepath>
            # Example: drichnerdisney/ollama:v1 /etc/passwd
            carve_parts = args.split(maxsplit=1)
            image_ref = carve_parts[0] if carve_parts else ""
            filepath = carve_parts[1].strip() if len(carve_parts) > 1 else ""
            
            parsed = self._parse_image_ref(image_ref)
            if parsed and parsed[2] and filepath:  # Has tag and filepath
                ns, repo, tag = parsed
                yield Hit(
                    score=100,
                    match_display=f"Carve {filepath} from {ns}/{repo}:{tag}",
                    command=lambda n=ns, r=repo, t=tag, f=filepath: self._execute_carve(n, r, t, f),
                    help=f"Extract '{filepath}' from '{ns}/{repo}:{tag}'",
                )
            elif parsed and parsed[2] and not filepath:
                # Has image but no filepath
                yield Hit(
                    score=50,
                    match_display=f"/ddork carve {image_ref} <filepath>",
                    command=self._no_op,
                    help="Specify the file path to extract (e.g., /etc/passwd)",
                )
            else:
                yield Hit(
                    score=50,
                    match_display="/ddork carve <namespace/repo:tag> <filepath>",
                    command=self._no_op,
                    help="Example: /ddork carve drichnerdisney/ollama:v1 /etc/passwd",
                )

        elif subcommand:
            # Unknown subcommand - show available options
            yield Hit(
                score=30,
                match_display=f"Unknown command: {subcommand}",
                command=self._no_op,
                help="Available: search, repos, tags, containers, layers, files, carve",
            )

    def _parse_image_ref(self, ref: str) -> tuple[str, str, str] | None:
        """Parse namespace/repo:tag into components.
        
        Returns:
            Tuple of (namespace, repo, tag) or None if invalid.
        """
        if not ref:
            return None
        
        # Pattern: namespace/repo:tag
        match = re.match(r"^([^/]+)/([^:]+)(?::(.+))?$", ref)
        if match:
            ns, repo, tag = match.groups()
            return (ns, repo, tag or "")
        return None

    async def _execute_search(self, query: str) -> None:
        """Execute search command."""
        from app.ui.messages import SearchRequested
        self._app.post_message(SearchRequested(query=query))

    async def _execute_repos(self, namespace: str) -> None:
        """Execute repos command."""
        from app.ui.messages import ReposRequested
        self._app.post_message(ReposRequested(namespace=namespace))

    async def _execute_tags(self, repo_ref: str) -> None:
        """Execute tags command."""
        from app.ui.messages import TagsRequested
        parts = repo_ref.split("/", 1)
        if len(parts) == 2:
            self._app.post_message(TagsRequested(namespace=parts[0], repo=parts[1]))

    async def _execute_containers(self, namespace: str, repo: str, tag: str) -> None:
        """Execute containers command."""
        from app.ui.messages import ContainersRequested
        self._app.post_message(ContainersRequested(namespace=namespace, repo=repo, tag=tag))

    async def _execute_layers(self, namespace: str, repo: str, tag: str) -> None:
        """Execute layers command."""
        from app.ui.messages import LayersRequested
        self._app.post_message(LayersRequested(namespace=namespace, repo=repo, tag=tag))

    async def _execute_files(self, namespace: str, repo: str, tag: str) -> None:
        """Execute files command."""
        from app.ui.messages import FilesRequested
        self._app.post_message(FilesRequested(namespace=namespace, repo=repo, tag=tag))

    async def _execute_carve(self, namespace: str, repo: str, tag: str, filepath: str) -> None:
        """Execute carve command."""
        from app.ui.messages import CarveRequested
        self._app.post_message(CarveRequested(
            namespace=namespace, repo=repo, tag=tag, filepath=filepath
        ))

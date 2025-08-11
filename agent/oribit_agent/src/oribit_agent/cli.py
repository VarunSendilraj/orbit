from __future__ import annotations

import asyncio
import json

import typer

from .executor import execute_command
from .server import app  # FastAPI app for `serve`
import uvicorn


cli = typer.Typer(help="Orbit Agent CLI")


@cli.command()
def run(command: str, dry_run: bool = typer.Option(False, help="Plan only, do not execute")):
    """Execute a natural language command via CLI, streaming steps to stdout."""

    async def _main() -> None:
        result = await execute_command(command, dry_run=dry_run)
        print("\nResult:", json.dumps(result, indent=2))

    asyncio.run(_main())


@cli.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="Bind host"),
    port: int = typer.Option(8765, help="Bind port"),
    reload: bool = typer.Option(False, help="Reload on code changes"),
):
    """Start the FastAPI HTTP/WebSocket server."""
    uvicorn.run(app, host=host, port=port, reload=reload)


def main() -> None:
    cli()

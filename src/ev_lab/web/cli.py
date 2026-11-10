"""`ev web`: the trainer in the browser, on this machine only."""

from __future__ import annotations

import webbrowser
from pathlib import Path

import numpy as np
import typer
from rich.console import Console

from ev_lab.context import ConfigOption, start
from ev_lab.web.app import TrainerApp
from ev_lab.web.server import HOST, serve

console = Console()


def register(app: typer.Typer) -> None:
    @app.command("web")
    def web(
        port: int = typer.Option(8765, "--port", min=1024, max=65535),
        open_browser: bool = typer.Option(True, "--open/--no-open", help="Open the page."),
        seed: int | None = typer.Option(None, "--seed", help="Repeat sessions exactly."),
        config: Path = ConfigOption,
    ) -> None:
        """Serve the trainer at http://127.0.0.1:PORT (local only). Ctrl-C stops it."""
        ctx = start(config)
        chosen = seed if seed is not None else int(np.random.SeedSequence().generate_state(1)[0])
        ctx.logger.info("web trainer seed=%d port=%d", chosen, port)
        try:
            server = serve(TrainerApp(ctx, chosen), port)
        except OSError as e:
            console.print(f"[red]error:[/red] cannot listen on port {port}: {e}")
            raise typer.Exit(code=1) from e
        url = f"http://{HOST}:{port}/"
        console.print(f"Trainer at {url} (this machine only). Press Ctrl-C to stop.")
        if open_browser:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            console.print("\nStopped.")
        finally:
            server.server_close()

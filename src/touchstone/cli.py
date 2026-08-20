"""The CLI. Every command in docs/06 §1 lands here.

Phase 0 has exactly one: `doctor`. Commands arrive with the code they drive — a stub that
prints "not implemented" is a command that looks built.
"""

from __future__ import annotations

import typer

app = typer.Typer(
    name="touchstone",
    help="An agent-improvement loop that is required to prove the improvement.",
    no_args_is_help=True,
    add_completion=False,
)


@app.callback()
def _root() -> None:
    """Keep `doctor` a subcommand.

    Typer promotes a lone command to the root otherwise, and every command added
    later would silently change the CLI's shape.
    """


@app.command()
def doctor(
    probe: bool = typer.Option(
        True,
        "--probe/--no-probe",
        help="Make one live model call. It is the only source of the model id (D-001) "
        "and of the isolation check (D-034).",
    ),
) -> None:
    """Check the environment before anything spends quota."""
    from .doctor import run

    raise typer.Exit(run(probe=probe))


if __name__ == "__main__":
    app()

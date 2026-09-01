"""The CLI. Every command in docs/06 §1 lands here.

Commands arrive with the code they drive — a stub that prints "not implemented" is a command
that looks built. Four exist: `doctor` (P0), `run` and `score` (P1.6), and `mine` (P3.4).

Two of the four the P1.6 row names are deliberately absent, for different reasons:

    compare   phase 2's. It needs a second version to mean anything, and a comparator with
              one operand is scaffolding (D-080).
    suite     the row is stale. `suite log`/`show`/`diff` were deferred AFTER it was written,
              and `suite gauntlet`/`quarantine` are P3.5. All five read a regression tier that
              does not exist, so every one would be a formatter over an empty directory.

Each command imports what it drives inside the function. `touchstone doctor` exists to say
whether the machine can run anything at all, and a module-level import of τ² (1.71 s) or MLflow
would make the diagnostic pay for the thing it is diagnosing, or fail before it can report.
"""

from __future__ import annotations

import typer

from . import config

app = typer.Typer(
    name="touchstone",
    help="An agent-improvement loop that is required to prove the improvement.",
    no_args_is_help=True,
    add_completion=False,
)


@app.callback()
def _root() -> None:
    """Hold the command namespace open.

    Typer promotes a LONE command to the root, so without this `doctor` was the CLI itself and
    adding the second command would have silently changed the shape of the first.
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


@app.command()
def run(
    version: str = typer.Argument(..., help="The version label, e.g. `v1`. Names the run."),
    k: int = typer.Option(config.K, "--k", help="Trials per task."),
    resume: bool = typer.Option(
        False, "--resume", help="Skip simulations already on disk — τ²'s own `auto_resume`."
    ),
) -> None:
    """Run the frozen benchmark subset through τ², with the SDK behind every model role."""
    from .loop.run import run as run_suite

    typer.echo(f"wrote {run_suite(version, k, resume=resume)}")


@app.command()
def score(
    version: str = typer.Argument(..., help="The version to score — the label `run` was given."),
    k: int = typer.Option(config.K, "--k", help="Trials pass^k draws from."),
) -> None:
    """Score a run into `results/<version>.json` — no model call (D-007).

    Takes a version, never a file path. τ²'s shipped baselines sit one directory away and an
    arbitrary `--results` would publish four third-party models' numbers under one of our
    version labels — D-080 ceiling 1 forbids quoting them, and a flag is a poor place to
    enforce a ceiling. The corpus is mined (phase 3), not published.
    """
    from .loop.report import write
    from .loop.run import results_path

    results = results_path(version)
    if not results.exists():
        raise typer.BadParameter(f"{results} does not exist — run `touchstone run {version}`")

    typer.echo(f"wrote {write(results, version, k)}")


@app.command()
def mine(
    label: str = typer.Argument(..., help="Names the harvest — `results/mined-<label>.json`."),
    limit: int = typer.Option(5, "--limit", help="How many sessions, in corpus order."),
    session: list[str] = typer.Option(
        [], "--session", help="Work these session ids instead. Repeatable."
    ),
) -> None:
    """Mine sessions for eval gates — router, curator, critic, up to five attempts each.

    The default limit is 5 and it is deliberately small. Every session costs a router call
    before it can be skipped, and the quota is a five-hour window that rejects rather than
    bills (D-001) — a harvest that runs into it stops and keeps what it paid for, but the
    sessions after the wall are not worked at all.
    """
    from .loop.harvest import harvest

    typer.echo(f"wrote {harvest(label, limit, tuple(session))}")


if __name__ == "__main__":
    app()

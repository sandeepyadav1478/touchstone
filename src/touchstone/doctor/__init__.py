"""`touchstone doctor` — the first thing written in this project, and the first thing run.

It stops the two failures that each cost an evening (docs/00 §6).

1. `ANTHROPIC_API_KEY` set     → every run silently bills an API account instead of the
                                 subscription. Nothing else in the project would notice.
2. `setting_sources` not `[]`  → the developer's own CLAUDE.md, skills and MCP servers are
                                 loaded into the agent under test. The scores then describe
                                 this machine, not the agent.

Failure 2 is asserted by measurement, not by reading the constant: the SDK reports which
memory files it loaded, so `doctor` asks it. A config value that says isolation and a
session that is isolated are different claims (D-034).

Split across four modules by what a check needs in order to answer, because that is also
the order they must run in and the reason each one can be tested:

    result       the verdict type and the terminal alphabet — no dependencies
    environment  the machine: CLI, credentials, keys, lockfile. Neither τ² nor the SDK.
    pins         whether the pinned world still matches what was measured. Imports τ².
    runtime      what only a live process settles: a span round trip, a real model call.

`run()` stays here because it is the only part that knows about all four, and ordering
them is its entire job — a failing `environment` check makes a `runtime` result a
description of the wrong machine.
"""

from __future__ import annotations

import asyncio

from .. import config
from .environment import (
    _api_key_absent,
    _cerebras,
    _claude_cli,
    _http,
    _lockfile,
    _subscription_auth,
)
from .pins import _metrics, _tau2_data, metric_check, specimen_check
from .result import COLOUR, MARK, Check, Status
from .runtime import _probe, _tracing, model_check, tracing_check

__all__ = [
    "COLOUR",
    "MARK",
    "Check",
    "Status",
    "metric_check",
    "model_check",
    "run",
    "specimen_check",
    "tracing_check",
]


def run(probe: bool = True) -> int:
    """Print the report, return the process exit code."""
    from rich.console import Console

    console = Console()
    checks = [_claude_cli(), _subscription_auth(), _api_key_absent()]
    if probe:
        checks += asyncio.run(_probe())
    else:
        checks.append(Check(
            "warn", "model", "not probed",
            "--no-probe was passed; D-001 needs a live id",
        ))
    checks += [
        _cerebras(),
        # Unreachable is fine: D-067 makes ollama a diagnostic, never a model source.
        _http(f"{config.OLLAMA_URL}/api/tags", "ollama", "a diagnostic — never a model source"),
        # D-077 removed the trace-SERVER check and this is not it coming back — there is
        # still no service. What it replaces is the sentence D-077 left behind: "writes to
        # `mlruns/` on disk, so there is no service to be up or down" is true about the
        # architecture and false about the call, which raises by default (P1.2).
        _tracing(),
        _tau2_data(),
        _metrics(),
        _lockfile(),
    ]

    width = max(len(c.name) for c in checks)
    console.print("touchstone doctor")
    for c in checks:
        line = f"  [{COLOUR[c.status]}]{MARK[c.status]}[/] {c.name:<{width}}  {c.detail}"
        if c.note:
            line += f"   [dim]— {c.note}[/dim]"
        console.print(line)

    failed = [c for c in checks if c.status == "fail"]
    if failed:
        console.print(f"\n[bold red]✗ {len(failed)} blocking[/] — fix before running anything.")
        return 1
    if probe:
        console.print(
            "\n[green]✓ green.[/] Paste this output verbatim into your "
            "decision record (D-001)."
        )
    else:
        console.print("\n[green]✓ green[/], but unprobed — D-001 needs a run with the live call.")
    return 0

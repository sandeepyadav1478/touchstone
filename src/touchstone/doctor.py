"""`touchstone doctor` — the first file in the project.

It stops the two failures that each cost an evening (docs/00 §6).

1. `ANTHROPIC_API_KEY` set     → every run silently bills an API account instead of the
                                 subscription. Nothing else in the project would notice.
2. `setting_sources` not `[]`  → the developer's own CLAUDE.md, skills and MCP servers are
                                 loaded into the agent under test. The scores then describe
                                 this machine, not the agent.

Failure 2 is asserted by measurement, not by reading the constant: the SDK reports
which memory files it loaded, so `doctor` asks it. A config value that says isolation and
a session that is isolated are different claims (D-034).
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import httpx

from . import config

Status = Literal["pass", "warn", "fail"]

MARK = {"pass": "✓", "warn": "⚠", "fail": "✗"}
COLOUR = {"pass": "green", "warn": "yellow", "fail": "bold red"}


@dataclass
class Check:
    """One probe's verdict — what was checked, what was found, what to do about it."""

    status: Status
    name: str
    detail: str
    note: str = ""


def _claude_cli() -> Check:
    path = shutil.which("claude")
    if not path:
        return Check(
            "fail", "claude CLI", "not on PATH",
            "the SDK spawns it — nothing runs without it",
        )
    try:
        out = subprocess.run(
            [path, "--version"], capture_output=True, text=True, timeout=20, check=True
        ).stdout.strip()
    except (subprocess.SubprocessError, OSError) as exc:
        return Check("fail", "claude CLI", f"{path} — {type(exc).__name__}")
    return Check("pass", "claude CLI", f"{out.split()[0]}  ({path})")


def _subscription_auth() -> Check:
    creds = Path.home() / ".claude" / ".credentials.json"
    if not creds.exists():
        return Check(
            "fail", "subscription auth", "~/.claude/.credentials.json missing",
            "run `claude` once and log in",
        )
    mode = oct(creds.stat().st_mode & 0o777)[2:]
    return Check("pass", "subscription auth", f"~/.claude/.credentials.json present (mode {mode})")


def _api_key_absent() -> Check:
    """The one check this command exists for."""
    if os.environ.get(config.API_KEY_ENV):
        return Check(
            "fail",
            config.API_KEY_ENV,
            "SET",
            "runs would bill an API account, not the subscription (D-001). `unset` it",
        )
    return Check("pass", config.API_KEY_ENV, "absent")


def _lockfile() -> Check:
    lock = config.ROOT / "uv.lock"
    pyproject = config.ROOT / "pyproject.toml"
    if not lock.exists():
        return Check(
            "fail", "uv.lock", "missing",
            "a version table nobody can reproduce is anecdote",
        )
    data = tomllib.loads(pyproject.read_text())
    direct = (
        len(data["project"]["dependencies"])
        + sum(len(v) for v in data["project"].get("optional-dependencies", {}).values())
        + sum(len(v) for v in data.get("dependency-groups", {}).values())
    )
    return Check("pass", "uv.lock", f"present, {direct} direct deps")


def specimen_check(tasks: int, policy_bytes: int) -> Check:
    """Compare a resolved specimen against the measured pin — the logic half of P1.0.

    Split from `_tau2_data` so it tests without τ²'s 1.71 s import. The convention through
    this module: I/O in the private wrapper, the decision here.

    Args:
        tasks: How many tasks retail's `tasks.json` actually holds.
        policy_bytes: The on-disk size of retail's `policy.md`.

    Returns:
        A pass only when both match `config`'s measured values.
    """
    detail = f"retail: {tasks} tasks, policy {policy_bytes} B"
    if (tasks, policy_bytes) != (config.TAU2_RETAIL_TASKS, config.TAU2_RETAIL_POLICY_BYTES):
        return Check(
            "fail", "tau2 data", detail,
            f"expected {config.TAU2_RETAIL_TASKS} and {config.TAU2_RETAIL_POLICY_BYTES} B — "
            "a different specimen makes every number here about a different corpus",
        )
    return Check("pass", "tau2 data", detail)


def _tau2_data() -> Check:
    """Assert the specimen a run would actually load — P1.0.

    Reads τ²'s own constants rather than re-deriving the path — τ² resolves its data
    directory once at import and only warns, and the default fallback is broken under a venv
    install (DEF-051). The import is local so `doctor` can report that it failed.

    Returns:
        A pass only when both retail files are on disk AND match the measured pin.
    """
    try:
        from tau2.domains.retail.utils import RETAIL_POLICY_PATH, RETAIL_TASK_SET_PATH
    except ImportError as exc:
        return Check(
            "fail", "tau2 data", f"tau2 not importable — {exc}",
            "the specimen is pinned in pyproject's [tool.uv.sources]",
        )

    if missing := [p for p in (RETAIL_TASK_SET_PATH, RETAIL_POLICY_PATH) if not p.exists()]:
        return Check(
            "fail", "tau2 data", f"{len(missing)} of 2 files missing under {RETAIL_POLICY_PATH.parent}",
            "set TAU2_DATA_DIR to the checkout's data/ directory — τ² only warns",
        )

    return specimen_check(
        len(json.loads(RETAIL_TASK_SET_PATH.read_text())),
        RETAIL_POLICY_PATH.stat().st_size,
    )


def metric_check(disagreements: list[str]) -> Check:
    """Report whether our copied metrics still agree with upstream's — the logic half of D-099.

    `loop/score.py` copies the two metrics rather than importing them (D-099); this is what
    notices the copy drifting, and it costs nothing because `doctor` imports τ² anyway.
    Agreement is checked by behaviour — matching source text can hide changed arithmetic.

    Args:
        disagreements: One string per input where the two implementations differ.

    Returns:
        A pass only when every sampled input agrees.
    """
    if disagreements:
        return Check(
            "fail", "metrics", f"{len(disagreements)} disagreement(s): {disagreements[0]}",
            "loop/score.py copies upstream's metrics (D-099) — the copy has drifted from the pin",
        )
    return Check("pass", "metrics", "metrics and termination vocabulary agree with the pin")


def _metrics() -> Check:
    """Run our copies against τ²'s over a small exhaustive grid — D-099.

    Exhaustive over the shape, not a sample of it. Every `(trials, successes, k)` with
    `trials ≤ 5` is checked, which includes the `k < num_trials` rows where the plausible
    re-derivation ("passed every attempt") diverges — the corpus we develop against has 4
    trials on every task, so a spot check at `k == num_trials` would agree with a wrong copy.

    Returns:
        A pass only when every grid point and every tolerance point matches.
    """
    try:
        from tau2.data_model.simulation import TerminationReason
        from tau2.metrics.agent_metrics import is_successful as up_successful
        from tau2.metrics.agent_metrics import pass_hat_k as up_pass_hat_k
    except ImportError as exc:
        return Check(
            "fail", "metrics", f"tau2 not importable — {exc}",
            "the specimen is pinned in pyproject's [tool.uv.sources]",
        )

    from touchstone.loop.score import TERMINATION_REASONS, is_successful, pass_hat_k

    bad: list[str] = []
    for trials in range(1, 6):
        for successes in range(trials + 1):
            for k in range(1, trials + 1):
                ours, theirs = pass_hat_k(trials, successes, k), up_pass_hat_k(trials, successes, k)
                if ours != theirs:
                    bad.append(f"pass_hat_k({trials},{successes},{k}) {ours} != {theirs}")
    # The tolerance is the whole content of `is_successful`, so the points that matter are the
    # ones just inside and just outside it — 1.0 alone would agree with a bare `== 1.0`.
    for reward in (0.0, 0.5, 0.9999, 1 - 1e-7, 1.0, 1 + 1e-7, 1.001):
        if is_successful(reward) != up_successful(reward):
            bad.append(f"is_successful({reward}) disagrees")

    # A misspelt reason passes mypy and every test; only upstream's enum catches it (D-100).
    mine, upstream = set(TERMINATION_REASONS), {r.value for r in TerminationReason}
    if mine != upstream:
        bad.append(f"termination reasons differ: ours-only {sorted(mine - upstream)}, "
                   f"upstream-only {sorted(upstream - mine)}")
    return metric_check(bad)


def tracing_check(wrote: str, read_back: str | None, uri: str) -> Check:
    """Compare a marker written into the trace store against the one read back out — P1.2.

    A round trip, not an import: `start_span()` succeeds whether or not anything persists,
    and the failure has no symptom until a run ends with no evidence (DEF-052). Split from
    `_tracing` so the logic is testable without MLflow's 0.53 s import.

    Args:
        wrote: The marker put on the probe span.
        read_back: The marker found on the most recent probe trace, or None if there was none.
        uri: The tracking URI the store actually resolved to, for the operator to read.

    Returns:
        A pass only when the store returned the exact marker this process wrote.
    """
    where = uri.removeprefix("file://")
    if read_back is None:
        return Check(
            "fail", "tracing", f"wrote a span to {where}, read none back",
            "the run would score fine and leave no evidence — MLFLOW_ALLOW_FILE_STORE",
        )
    if read_back != wrote:
        return Check(
            "fail", "tracing", f"read back {read_back}, wrote {wrote}",
            "the newest trace is not this one — something else is writing to this store",
        )
    return Check("pass", "tracing", f"span round-tripped to {where}")


def _tracing() -> Check:
    """Write one span, flush, read it back — P1.2, and it replaces the check D-077 removed.

    `mlflow-skinny` 3.15.1 refuses the file store unless `MLFLOW_ALLOW_FILE_STORE=true`, so
    this fires on D-074's happy path, not on a misconfiguration. The probe writes to its own
    experiment: doctor spans are noise in the version table, and it makes "newest" mean ours.

    Returns:
        A pass only when the marker survives the write → flush → read cycle.
    """
    import uuid

    import mlflow

    from . import telemetry

    marker = uuid.uuid4().hex[:12]
    try:
        uri = telemetry.install()
        mlflow.set_experiment(f"{config.EXPERIMENT}-doctor")
        with mlflow.start_span("touchstone.doctor") as span:
            span.set_attribute("touchstone.probe", marker)
        telemetry.flush()
        traces = mlflow.search_traces(return_type="list", max_results=1)
    except Exception as exc:  # noqa: BLE001 — every failure here is the same finding
        return Check(
            "fail", "tracing", f"{type(exc).__name__}: {exc}".split("\n")[0][:110],
            f"no trace store means no evidence — {config.TRACKING_URI}",
        )

    spans = traces[0].data.spans if traces else []
    found = next((s.attributes.get("touchstone.probe") for s in spans), None)
    return tracing_check(marker, found, uri)


def _cerebras() -> Check:
    """Report the Cerebras key, with the polarity D-067 requires.

    Absent is the correct state and reads as a pass: under D-067 every role is Anthropic and
    Cerebras is a diagnostic, never a model source. The polarity was inverted before that.

    Returns:
        A pass when the key is absent, a warning when it is set.
    """
    if os.environ.get("CEREBRAS_API_KEY"):
        return Check(
            "warn", "CEREBRAS_API_KEY", "set",
            "nothing here reads it — D-067 allows no non-Anthropic model source",
        )
    return Check("pass", "CEREBRAS_API_KEY", "absent — correct, no fallback provider is used")


def _http(url: str, name: str, hint: str) -> Check:
    try:
        httpx.get(url, timeout=2.0)
    except httpx.HTTPError:
        return Check("warn", name, f"{url} unreachable", hint)
    return Check("pass", name, url)


def model_check(usage_by_model: dict[str, Any], total_cost_usd: float) -> Check:
    """Which model actually answered — matched by name, never by position.

    The id is a KEY of `model_usage`. Not because the SDK lacks a name field — it grew
    one: `ModelUsage.canonicalModel` at `claude_agent_sdk/types.py:1308`, `NotRequired`, so it
    may or may not arrive. The key is the half that is always there, which is why the match
    stays on it (D-033, restated 2026-08-26 against SDK 0.2.142).
    And there can be more than one key: in isolation mode the CLI makes its own
    housekeeping call on haiku, and that key sorts first. `next(iter(...))` therefore reads a
    model the agent never used — which is how this check failed on its first run against a
    correctly pinned model (D-035).
    """
    others = [m for m in usage_by_model if m != config.MODEL]
    if config.MODEL not in usage_by_model:
        return Check(
            "fail",
            "model",
            f"asked {config.MODEL}, answered {', '.join(usage_by_model) or 'nothing'}",
            "the pin did not take — every version-table row would be unattributable (D-013)",
        )
    return Check(
        "pass",
        "model",
        f"{config.MODEL}  (pinned, answered by a live call, ${total_cost_usd:.4f} total)",
        f"+ {', '.join(others)} — the CLI's own housekeeping, not the agent" if others else "",
    )


async def _probe() -> list[Check]:
    """One live call. It settles the model id AND whether the session is isolated.

    `max_turns` is not a count of model calls — with `output_format` the structured-output
    step spends one of its own (D-032). Nothing here uses output_format, so 2 is ample.
    """
    from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, ResultMessage

    options = ClaudeAgentOptions(
        setting_sources=config.SETTING_SOURCES,  # [] — see config.py
        model=config.MODEL,  # pinned; the probe exists to prove it resolves
        allowed_tools=[],
        max_turns=2,
        max_budget_usd=0.10,
    )

    result: ResultMessage | None = None
    async with ClaudeSDKClient(options=options) as client:
        await client.query("Reply with the single word: ok")
        async for message in client.receive_response():
            if isinstance(message, ResultMessage):
                result = message
        usage = await client.get_context_usage()

    if result is None or result.is_error:
        return [
            Check(
                "fail", "model", "no result from a live probe",
                str(result and result.errors),
            )
        ]

    checks = [model_check(result.model_usage or {}, result.total_cost_usd or 0.0)]

    memory = usage.get("memoryFiles") or []
    agents = usage.get("agents") or []
    mcp = [t for t in (usage.get("mcpTools") or []) if t.get("isLoaded")]
    contamination = len(memory) + len(agents) + len(mcp)
    if contamination:
        names = ", ".join(Path(m.get("path", "?")).name for m in memory) or "—"
        checks.append(
            Check(
                "fail",
                "setting_sources",
                f"{len(memory)} memory file(s), {len(agents)} agent(s), "
                f"{len(mcp)} MCP tool(s) loaded",
                f"the agent under test is reading this machine: {names}. Must be []",
            )
        )
    else:
        checks.append(
            Check(
                "pass",
                "setting_sources",
                f"[] — 0 memory files, 0 agents, 0 MCP tools "
                f"({usage.get('totalTokens', '?')} ctx tokens)",
            )
        )
    return checks


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
        # still no service. What it replaces is the sentence D-077 left behind: *"writes to
        # `mlruns/` on disk, so there is no service to be up or down"* is true about the
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

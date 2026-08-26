"""The checks that need something to actually happen — P1.2 and D-001.

A constant that says a thing and a process that does it are different claims (D-034), and
these are the three where the difference has already cost an evening:

    tracing     a marker written to the store and read back out. `start_span()` succeeds
                whether or not anything persists, and the failure has no symptom until a
                run ends with no evidence (DEF-052).
    model       which id actually answered, read off a live call rather than off `config`
    isolation   what the SDK reports it loaded, rather than what `setting_sources` says

Each pairs a pure comparison with a private wrapper holding the I/O, so the decision half
tests without MLflow's 0.53 s import or a live call.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .. import config
from .result import Check


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

    from .. import telemetry

    marker = uuid.uuid4().hex[:12]
    try:
        uri = telemetry.install()
        mlflow.set_experiment(f"{config.EXPERIMENT}-doctor")
        with mlflow.start_span("touchstone.doctor") as span:
            span.set_attribute("touchstone.probe", marker)
        telemetry.flush()
        traces = mlflow.search_traces(return_type="list", max_results=1)
    except Exception as exc:
        return Check(
            "fail", "tracing", f"{type(exc).__name__}: {exc}".split("\n")[0][:110],
            f"no trace store means no evidence — {config.TRACKING_URI}",
        )

    spans = traces[0].data.spans if traces else []
    found = next((s.attributes.get("touchstone.probe") for s in spans), None)
    return tracing_check(marker, found, uri)


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

"""Whether there is room for another model call, and the only place that decides.

Two limits, and they stop the loop for different reasons. `attempts_exhausted()` is the loop
giving up on one trace -- an honest failure, and a result. `quota_exhausted()` is the window
running out underneath it -- not a result at all, and resumable. Both live here because each is
a cap that exactly one function may read, and a cap with two readers is a cap that drifts.

The SDK emits `RateLimitEvent` when the status TRANSITIONS, not on every message, so a caller
that inspects one response sees nothing on almost every call. `observe()` keeps the newest
reading and `quota_exhausted()` answers from it. The state is module-level because the window
belongs to the account, not to a call site: two callers asking separately would disagree, and
the one that guessed low would be the one that killed the run.

Cost is deliberately not accumulated FOR THE DECISION, and that is unchanged. docs/03 requires
a budget derived from measured usage rather than a turn count, and `utilization` already is
that measurement -- taken by the vendor over the same window it enforces, which is a stronger
reading than anything summed on this side. `quota_exhausted()` is still the only thing that
answers whether to spend, and it still answers from `utilization` alone.

`spent()` records what a finished call cost, and nothing reads it back to make a decision. It
is here because it is the same seam: `extract.ask` already hands `observe()` the rate-limit
event, and a second module summing the same stream is the two-readers failure this file's own
caps avoid. The reason to record at all is that three constants in `config.py` are guesses
whose own comments ask for a number no run currently keeps -- `CRITIC_TURNS` wants `num_turns`
pinned to what the critic actually spends, `AGENT_TURNS` the same, and
`QUOTA_STOP_UTILIZATION` says calls-per-trace is unmeasured. The `ResultMessage` carrying all
three answers was arriving at `ask` and being dropped.

`turns` is the MAXIMUM, not a total, because that is the number a cap is pinned to: a maximum
equal to the cap means the ceiling was reached, which surfaces as an empty verdict rather than
an error (config.py:54). Token counts are summed by whatever key the SDK reports rather than
by a fixed list -- naming the keys here would make a renamed field read as zero.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from touchstone import config

if TYPE_CHECKING:  # annotation only -- the runtime SDK import is policed by test_invariants
    from claude_agent_sdk import RateLimitInfo, ResultMessage

__all__ = [
    "QuotaExhaustedError",
    "attempts_exhausted",
    "forget",
    "ledger",
    "observe",
    "quota_exhausted",
    "reading",
    "spent",
]


class QuotaExhaustedError(RuntimeError):
    """Raised instead of starting a call the window has no room for.

    Its own class because the caller has to tell it from a failure: a run that stops on quota
    is resumable and has lost nothing, while one that stops on a bad answer has burned an
    attempt. A single `RuntimeError` would make those two the same event.
    """


_last: RateLimitInfo | None = None


def observe(info: RateLimitInfo) -> None:
    """Record the newest reading, called from wherever the stream is being consumed."""
    global _last
    _last = info


def reading() -> RateLimitInfo | None:
    """The last reading, or None if the SDK has not reported one yet."""
    return _last


_spent: dict[str, dict[str, Any]] = {}


def spent(role: str, result: ResultMessage) -> None:
    """File what one finished call cost, under the role that made it.

    Called for a failed call too. A call that ran out of turns or came back an error spent the
    window exactly as an answered one did, and a ledger that only counted the successes would
    understate the cost of the thing most worth tuning.

    Per role rather than in one total: the three roles have different caps and different
    prompts, and the tuning question is always about one of them. A single figure would say the
    harvest was expensive without saying which knob to turn.
    """
    row = _spent.setdefault(
        role, {"calls": 0, "turns": 0, "duration_ms": 0, "usd": 0.0, "tokens": {}}
    )
    row["calls"] += 1
    row["turns"] = max(row["turns"], result.num_turns)
    row["duration_ms"] += result.duration_ms
    row["usd"] += result.total_cost_usd or 0.0
    for name, value in (result.usage or {}).items():
        if isinstance(value, int):
            row["tokens"][name] = row["tokens"].get(name, 0) + value


def ledger() -> dict[str, dict[str, Any]]:
    """What has been spent so far, by role. A copy -- a caller writing a header cannot edit it."""
    return {role: {**row, "tokens": dict(row["tokens"])} for role, row in _spent.items()}


def forget() -> None:
    """Start a fresh ledger. Called at the top of a harvest, so its header is its own cost."""
    _spent.clear()


def quota_exhausted() -> bool:
    """True when the next call should not be started.

    Three cases, and the middle one is why the constant exists. `rejected` is the vendor's own
    verdict and is final. With a number, the number decides against our reserve. Without one,
    the vendor's word is all there is, so anything short of `allowed` counts -- `allowed_warning`
    means it is close and never says how close.

    No reading at all is not exhausted. That is the state before the first call, and refusing
    to start on it would mean never starting.
    """
    if _last is None:
        return False
    if _last.status == "rejected":
        return True
    if _last.utilization is None:
        return _last.status != "allowed"
    return _last.utilization >= config.QUOTA_STOP_UTILIZATION


def attempts_exhausted(attempts: int) -> bool:
    """True when the loop has spent its attempts on one trace, and the sole reader of the cap.

    D-091 §C is the whole argument and it is about drift, not about tidiness: the graph's loop
    condition and the critic's `attempt_budget` tool both ask this, so the model can be told it
    has one attempt left by the same arithmetic that will actually stop it. A tool that counted
    for itself would be right until someone changed the constant.

    `test_the_attempt_cap_has_exactly_one_reader` holds it, because the invariant is not that
    this function exists -- it is that nothing else reads `MAX_ATTEMPTS`, and only a check over
    the whole source can say that.
    """
    return attempts >= config.MAX_ATTEMPTS

"""Tier 1 — deterministic constraints on a proposed tool call. No model, no DB, no network.

D-064 named five DB-checkable constraints for `exchange_delivered_order_items`. On the
current specimen only one of them can fire, and the other four are absent rather than
implemented-and-quiet. `tools.py:248-271` already raises on the rest:

    length_match         `if len(item_ids) != len(new_item_ids): raise`
    same_product         `_get_variant(product_id, new_item_id)` raises off the OLD item's product
    new_item_available   `if not variant.available: raise`
    payment_owned        `_get_payment_method(order.user_id, ...)` raises

Measured over the four shipped retail baselines: of 506 ACCEPTED exchange calls those four
fire on 0, and only ever fire on calls that already errored (7, 13, 13 and 0 of 113). A gate
that fires on a call the environment already refused has changed nothing — the write did not
happen either way.

`self_swap` is the one the environment does not check, and it is written down:
`policy.md:132` — "each item can be exchanged to an available new item of the same product
but of different product option". Same option is a no-op that still moves the order to
`exchange requested`.

Its firing rate depends on which population you ask about, and the two answers disagree
enough that quoting either alone is misleading — `scripts/measure-tier1.py` prints both:

    all 114 tasks, 1,824 sims   47 firings, 37 on a call the environment accepted
    the 107-task corpus, 1,712   9 firings,  0 on a call the environment accepted

Every accepted firing is on task 18, 91 or 107 — three of the seven tasks D-080 excluded
because their gold actions moved. So on the corpus this project mines, tier 1 has zero false
positives and zero true positives. It is correct and it is silent. That is a fact about the
corpus, not a fault in the check: the gold action of all three tasks is a genuine
different-option exchange, so the gate never contradicts ground truth.

The four absent constraints are a specimen property, not a permanent finding. A domain whose
tools validate less brings them back, and the way to find that out is to run the measurement
against it and read the firing counts, not to carry four dead branches until then.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, TypeGuard

EXCHANGE = "exchange_delivered_order_items"


@dataclass(frozen=True)
class Violation:
    """One constraint broken by one call, carrying where the constraint is written down.

    `rule` is not decoration. A gate whose reason is "the model thought so" cannot be
    argued with; a gate that cites a line of the policy it enforces can be shown to be
    wrong, which is the only way it ever gets fixed.
    """

    constraint: str
    rule: str
    detail: str


def _is_list(value: Any) -> TypeGuard[Sequence[Any]]:
    return isinstance(value, Sequence) and not isinstance(value, str | bytes)


def _pairs(arguments: Mapping[str, Any]) -> list[tuple[str, str]]:
    """Zip the old and new item ids, tolerating a malformed call rather than raising.

    A gate is fed proposed calls, including ones the environment is about to reject, so
    anything here that raises turns a bad call into a crashed run. `zip` truncates on a
    length mismatch, which is the environment's error to report, not ours.
    """
    old = arguments.get("item_ids")
    new = arguments.get("new_item_ids")
    # `str` is a Sequence, and zipping "111" with itself yields three self-swapped
    # characters. A model emitting a bare string where the schema says list is the
    # exact malformed call this function is fed, so the exclusion is not defensive.
    if not _is_list(old) or not _is_list(new):
        return []
    return [
        (a, b)
        for a, b in zip(old, new, strict=False)
        if isinstance(a, str) and isinstance(b, str)
    ]


def check(tool_name: str, arguments: Mapping[str, Any]) -> list[Violation]:
    """Every tier-1 violation in one proposed call. Empty means tier 1 has no opinion.

    Empty is not approval — tier 1's measured recall is about 2%, so silence is the
    normal answer and reading it as a pass is the misuse this docstring exists to stop.
    """
    if tool_name != EXCHANGE:
        return []
    return [
        Violation(
            "self_swap",
            "retail/policy.md:132",
            f"item {item_id} exchanged for itself — the new item must be a different "
            f"product option",
        )
        for item_id, new_item_id in _pairs(arguments)
        if item_id == new_item_id
    ]

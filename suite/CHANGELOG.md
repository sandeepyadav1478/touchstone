# Suite changelog

One entry per suite version: what changed, why, and which failure drove it. A suite whose
history you cannot read is a suite you will eventually stop trusting.

## benchmark v1 — 2026-08-18

**Ten cases, frozen at `4c935f06…`.** Eight answerable across eight of the ten mechanisms, two
made unanswerable by the deletion path.

**Why these ten:** every renderer is exercised, four of the eight answerable cases name a service
other than the one that paged, and 2 of 10 are unanswerable — the bottom of the 2–3 band
[docs/01](../docs/01-spec.md) §3 asks for, chosen because the escalation path needs more than one
case to be a path at all.

**Two design changes the corpus read forced**, both recorded here because they contradict what
was planned:

1. **Routine log volume was multiplied sevenfold** after the first draw came out at ~75% `INFO`.
   Loghub measures 96.0–98.5% on two of three corpora, and at 75% every `WARN` reads as a signal
   — the stylised-corpus failure D-002 exists to prevent.
2. **`noisy_neighbor` alerts on `product-catalog`, not `cart`.** `cart` reaches only `valkey` in
   the topology, so postgres saturation could not have slowed it and the mechanism did not hold.
   Caught by the invariant test that walks the dependency edges, not by review.

**Not in v1, deliberately:** `precedent` labels (no history corpus), and a case that scores
`config_drift` or `noisy_neighbor` as itself — see `benchmark/README.md`.

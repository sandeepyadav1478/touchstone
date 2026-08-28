"""The gates — the part that says no, and the reason it is allowed to.

Two tiers, and the split is about where a model is permitted to sit (D-064).

    tier1   deterministic. The constraint is fixed, the check is arithmetic over the call.
            No model, no network, no database read. This package's import cost is zero.
    tier2   a model translates the customer's stated constraint into a predicate; the
            verdict is still a mechanical evaluation of that predicate. P2.2.

Neither tier judges whether the agent did well. That is what makes a gate a gate rather
than a second scorer with a different opinion.
"""

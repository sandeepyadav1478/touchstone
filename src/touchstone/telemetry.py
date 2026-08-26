"""P1.2 — where a span goes after `adapter.py` opens it.

No provider and no exporter here, and that is the finding. D-074 made MLflow the spine and
deleted the OTel SDK, the OTLP exporter and the Phoenix container, so what is left is three
lines of configuration and one flush — `mlflow.start_span()` owns the tracer and the writer.

Three assumptions about that store, all wrong on `mlflow-skinny` 3.15.1. Measured
2026-08-26, not read from documentation:

1. `mlruns/` on disk raises by default — *"filesystem tracking backend is in maintenance
   mode"* — unless `MLFLOW_ALLOW_FILE_STORE=true` is set.
2. `sqlite:///`, the migration MLflow's own error suggests, is not registered in
   `mlflow-skinny`; the SQLAlchemy store ships in full `mlflow`. Do not "fix" item 1 by
   switching to sqlite without that dependency — it fails at `set_experiment`, not first write.
3. Export is asynchronous: `search_traces()` right after a closed span returned 0, then 1
   after `flush()`. The queue drains at interpreter exit — invisible in a script, wrong in a test.

Nothing here is a fallback. No store means no evidence, and a version table whose rows have no
traces is a table of anecdotes — so `doctor` asserts a round trip, not an import (DEF-052).
"""

from __future__ import annotations

import os

import mlflow

from touchstone import config


def install() -> str:
    """Point MLflow at the on-disk store. Returns the URI it actually resolved to.

    Returns a value rather than nothing — DEF-052. Three emitters in this project were
    assumed live for days because installing them raised nothing; a caller that cannot compare
    the result against what it asked for has not checked anything.
    """
    # `setdefault`, not assignment: an operator who has set it to something else has made a
    # decision, and silently overriding it is how a run stops writing where its logs say it does.
    os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")
    mlflow.set_tracking_uri(config.TRACKING_URI)
    mlflow.set_experiment(config.EXPERIMENT)
    return mlflow.get_tracking_uri()


def flush() -> None:
    """Drain the async export queue so a span written in this process can be read in it.

    `terminate` stays False. Draining is needed after every unit of work that something reads
    back; shutting the threads down is needed once, at exit, and doing both here would make the
    second call in a run a silent no-op.
    """
    mlflow.flush_trace_async_logging()

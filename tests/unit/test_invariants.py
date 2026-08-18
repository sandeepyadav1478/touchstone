"""P1.4: the corpus is checked against the four generator rules, not trusted to obey them.

Every assertion here corresponds to a numbered rule or invariant in the docs, and the ones that
matter most are the two that cannot be checked by reading the generator: rule 1 (determinism) is
checked by running it twice, and invariant 1 (no truth in the incident) is checked against the
**serialised JSON**, because that is the surface the agent actually sees. A test that walked the
model tree would pass a generator that leaked the cause into a log message.
"""

from __future__ import annotations

import json
import random

import pytest

from touchstone.config import BENCHMARK
from touchstone.domain import RootCause
from touchstone.incidents.generate import (
    SUITE,
    TOPOLOGY,
    benchmark_hash,
    generate_case,
    generate_suite,
    write_suite,
)
from touchstone.incidents.renderers import POINTS, RENDERERS, Scene

CASES = generate_suite()
SERVICES = {node.name for node in TOPOLOGY}
BY_ID = {inc.id: (inc, truth) for inc, truth in CASES}


# --- Invariant 1: the truth is never rendered -------------------------------


@pytest.mark.parametrize("case", CASES, ids=[inc.id for inc, _ in CASES])
def test_invariant_1_no_truth_string_survives_serialisation(case):
    incident, truth = case
    rendered = json.dumps(incident.model_dump(mode="json")).lower()
    # Not just this case's answer — ANY of the eleven class names. A log line reading
    # "possible cache stampede" would be a leak even in a case whose cause is something else.
    for cause in RootCause:
        assert str(cause) not in rendered, f"{incident.id} renders the class name {cause}"
        assert str(cause).replace("_", " ") not in rendered
    assert truth.rationale.lower()[:40] not in rendered
    assert "escalate" not in rendered
    assert "root_cause" not in rendered


def test_the_answer_key_is_a_separate_object():
    # The structural half. Nothing on Incident carries a GroundTruth.
    incident, _ = CASES[0]
    assert "truth" not in incident.model_dump()


# --- Rule 1: seeded and reproducible ----------------------------------------


def test_invariant_6_same_seed_gives_a_byte_identical_incident():
    again = generate_suite()
    for (a_inc, a_truth), (b_inc, b_truth) in zip(CASES, again, strict=True):
        assert a_inc.model_dump_json() == b_inc.model_dump_json()
        assert a_truth.model_dump_json() == b_truth.model_dump_json()


def test_rule_1_no_case_shares_a_seed_or_an_id():
    assert len({spec.id for spec in SUITE}) == len(SUITE)
    assert len({spec.seed for spec in SUITE}) == len(SUITE)


# --- Rule 3: every case carries a plausible wrong answer ---------------------


@pytest.mark.parametrize("case", CASES, ids=[inc.id for inc, _ in CASES])
def test_rule_3_every_case_has_a_repeating_distractor(case):
    """A distractor is a template repeated, not one odd line — the Loghub finding, docs/01 §4."""
    incident, _ = case
    warns = [line.message for line in incident.evidence.logs if line.level == "WARN"]
    assert warns, f"{incident.id} has no WARN at all"
    top = max(warns.count(message) for message in set(warns))
    assert top >= 5, f"{incident.id}'s most repeated WARN appears {top} times, not a template"


@pytest.mark.parametrize("case", CASES, ids=[inc.id for inc, _ in CASES])
def test_the_level_mix_matches_the_measured_corpora(case):
    """docs/01 §4: OpenStack is 98.5% INFO and HDFS 96.0%, both with zero ERROR in 2,000 lines.

    A suite that runs at 75% INFO teaches that any WARN is a signal. The floor is 90 rather
    than 96 because the renderers weight traffic per service and the quietest case is a lone
    worker — but nothing may drop into the register where a warning is remarkable by itself.
    """
    incident, _ = case
    logs = incident.evidence.logs
    info = sum(line.level == "INFO" for line in logs) / len(logs)
    errors = sum(line.level == "ERROR" for line in logs) / len(logs)
    assert info >= 0.90, f"{incident.id} is only {info:.1%} INFO"
    assert errors <= 0.03, f"{incident.id} is {errors:.1%} ERROR; the corpora measured 0%"


# --- Rule 4: insufficient_evidence is a deletion -----------------------------


def test_rule_4_two_of_ten_are_unresolvable():
    # docs/01 §3 wants 2 to 3 of 10. Both bounds, because "at least one" would pass an empty
    # escalation path and the escalation path is the thing D-040 makes load-bearing.
    unresolvable = [t for _, t in CASES if not t.resolvable]
    assert 2 <= len(unresolvable) <= 3
    assert all(t.root_cause_id is RootCause.INSUFFICIENT_EVIDENCE for t in unresolvable)


@pytest.mark.parametrize("spec", [s for s in SUITE if not s.resolvable], ids=lambda s: s.id)
def test_rule_4_deletion_removes_evidence_and_nothing_else(spec):
    """The deleted case must be the resolvable draw minus one bucket — not a different draw."""
    kept, _ = generate_case(spec)
    whole, _ = generate_case(spec._replace(resolvable=True))

    assert kept.alert == whole.alert
    assert kept.topology == whole.topology
    assert len(kept.evidence.series) < len(whole.evidence.series)
    # Everything that survived is byte-identical to its counterpart in the full draw.
    assert {s.model_dump_json() for s in kept.evidence.series} < {
        s.model_dump_json() for s in whole.evidence.series
    }


def test_rule_4_required_specialist_is_none_exactly_when_unresolvable():
    # D-042. `None` is not "unknown" here, it is "no specialist's tools could have settled it".
    for _, truth in CASES:
        assert (truth.required_specialist is None) is (not truth.resolvable)
        if truth.required_specialist is not None:
            assert truth.required_specialist in {"timeline", "resource", "dependency"}


# --- The shape of the evidence ----------------------------------------------


@pytest.mark.parametrize("case", CASES, ids=[inc.id for inc, _ in CASES])
def test_every_series_covers_the_whole_window_at_one_interval(case):
    """A missing series means ABSENT, not sparse — which is what makes rule 4 work at all."""
    incident, _ = case
    for series in incident.evidence.series:
        assert len(series.points) == POINTS
        assert series.points[0].at == incident.window.start
        assert series.points[-1].at == incident.window.end


@pytest.mark.parametrize("case", CASES, ids=[inc.id for inc, _ in CASES])
def test_every_named_service_is_in_the_topology(case):
    incident, truth = case
    named = (
        {s.service for s in incident.evidence.series}
        | {line.service for line in incident.evidence.logs}
        | {d.service for d in incident.evidence.deploys}
        | {incident.alert.service, truth.affected_service}
    )
    outside = named - SERVICES
    assert not outside, f"{incident.id} names services outside the topology: {outside}"


@pytest.mark.parametrize("case", CASES, ids=[inc.id for inc, _ in CASES])
def test_evidence_is_inside_the_window_and_in_order(case):
    incident, _ = case
    times = [line.at for line in incident.evidence.logs]
    assert times == sorted(times)
    assert all(incident.window.start <= t <= incident.window.end for t in times)


# --- The traps the suite exists to plant -------------------------------------


def test_the_alerting_service_is_not_always_the_answer():
    """docs/01 §2 plants `alert.service` as the most common naive triage failure."""
    misleading = [
        t.incident_id
        for inc, t in CASES
        if t.resolvable and inc.alert.service != t.affected_service
    ]
    assert len(misleading) >= 3, f"only {misleading} punish answering with the alerting service"


def test_noisy_neighbor_is_unreachable_from_its_alert():
    """docs/01 §3: its cause sits in a service with no dependency edge to the alerting one."""
    edges = {node.name: node.depends_on for node in TOPOLOGY}

    def reach(start: str) -> set[str]:
        seen, frontier = set(), [start]
        while frontier:
            for dep in edges.get(frontier.pop(), []):
                if dep not in seen:
                    seen.add(dep)
                    frontier.append(dep)
        return seen

    alerting = BY_ID["inc-010"][0].alert.service
    reached = reach(alerting)
    # The walk has to actually descend, or "accounting is absent" is true of an empty set.
    assert "postgres" in reached, f"{alerting} does not even reach the datastore it shares"
    assert "accounting" not in reached, "walking edges from the alert now reaches the culprit"
    # And the culprit really is accounting: nothing in the graph depends on it.
    assert not [n for n in TOPOLOGY if "accounting" in n.depends_on]


def test_all_ten_renderers_are_exercised():
    assert {spec.cause for spec in SUITE} == set(RENDERERS)
    assert len(RENDERERS) == len(RootCause) - 1


@pytest.mark.parametrize(("name", "render"), RENDERERS.items())
def test_every_renderer_names_its_distinguishing_evidence(name, render):
    """A renderer with an empty distinguishing bucket cannot be deleted from, so rule 4 dies."""
    drawn = render(Scene(rng=random.Random(7)))
    assert drawn.distinguishing.series or drawn.distinguishing.logs
    assert drawn.rival != name, f"{name} is its own plausible wrong answer"
    assert drawn.rival in RENDERERS


# --- benchmark_hash ----------------------------------------------------------


def test_benchmark_hash_is_stable_and_sensitive(tmp_path):
    a = write_suite(tmp_path / "a", added="2026-08-18")
    b = write_suite(tmp_path / "b", added="2026-08-18")
    assert a == b

    # Sensitive to the answer key, byte for byte — docs/09 §5's second row.
    truth = tmp_path / "a" / "truth.json"
    truth.write_text(truth.read_text().replace("checkout", "cart", 1))
    assert benchmark_hash(tmp_path / "a") != a


def test_invariant_7_a_frozen_case_is_never_modified():
    """The freeze itself. ⛔ A failure here means the committed bytes and the seeds disagree.

    This is the only test that reads `suite/benchmark/`, and it is the one that makes the tier
    a *benchmark* rather than a directory: if a hand edit, a merge or a generator change moves a
    single byte, every past score in the version table stops describing this suite.
    """
    frozen = benchmark_hash(BENCHMARK)
    fresh = {inc.id: inc.model_dump_json() for inc, _ in generate_suite()}
    for case_id, payload in fresh.items():
        on_disk = (BENCHMARK / f"{case_id}.json").read_text().rstrip("\n")
        assert json.loads(on_disk) == json.loads(payload), f"{case_id} on disk is not its seed"
    assert frozen == "4c935f063e1353017d9cefe71f13d60ee97b0a22fcdd6cb1d90ba7417e187c2f", (
        "benchmark v1's hash moved; if that was intended it is a version bump, "
        "and suite/CHANGELOG.md plus every quoted hash need the new value"
    )


def test_benchmark_hash_survives_a_reserialise(tmp_path):
    """`git checkout` alone must not be able to block a comparison — docs/09 §5, last row."""
    digest = write_suite(tmp_path / "a", added="2026-08-18")
    manifest = tmp_path / "a" / "manifest.json"
    reloaded = json.loads(manifest.read_text())
    manifest.write_text(json.dumps(reloaded, indent=2, sort_keys=False))
    assert benchmark_hash(tmp_path / "a") == digest


# --- docs/01 §6, by number ---------------------------------------------------
#
# 1 ✅ test_invariant_1_no_truth_string_survives_serialisation
# 4 ✅ tests/unit/test_domain.py::test_invariant_4_escalation_is_one_comparison
# 6 ✅ test_invariant_6_same_seed_gives_a_byte_identical_incident
# 7 ✅ test_invariant_7_a_frozen_case_is_never_modified
# 11 ✅ test_invariant_11_every_case_says_why_it_exists
#
# The rest are below as SKIPS carrying their reason, never as absences. ⛔ An invariant that is
# simply missing from the file looks exactly like one nobody thought of, and this suite's whole
# argument is that the difference is worth writing down. Invariant 5 is retired (D-040) and has
# no slot here for the same reason it has no slot in the docs: the numbers are cited.


def test_invariant_11_every_case_says_why_it_exists():
    """A case nobody can justify does not get to gate anything — D-024."""
    manifest = json.loads((BENCHMARK / "manifest.json").read_text())
    assert len(manifest["cases"]) == len(SUITE)
    for entry in manifest["cases"]:
        assert entry["why"].strip(), f"{entry['id']} has no justification"
        assert entry["added"].strip()
        assert entry["origin"].strip()


@pytest.mark.parametrize(
    ("number", "invariant", "blocked_on"),
    [
        (2, "every tool is read-only", "tools/ — P1.7"),
        (3, "exactly one verdict span per run", "telemetry.py — P1.5"),
        (8, "correctness never reads verdict.reasoning", "loop/score.py — P1.6"),
        (9, "history/ is disjoint from both tiers", "v5 — no history corpus exists"),
        (10, "nothing is ever written to history/", "v5 — no history corpus exists"),
        (12, "a locked regression case became locked by passing", "the regression tier — phase 3"),
        (13, "no specialist's prompt holds another's finding", "agent/nodes.py — P1.8"),
        (14, "no two specialist spans overlap in time", "telemetry.py + a run — P1.5"),
    ],
)
def test_invariant_is_not_yet_checkable(number, invariant, blocked_on):
    pytest.skip(f"docs/01 §6 invariant {number} ({invariant}) — blocked on {blocked_on}")

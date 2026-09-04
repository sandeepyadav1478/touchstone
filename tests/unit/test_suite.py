"""The regression tier's file: what it must carry, and the two writes it refuses.

Both refusals are D-024's provenance rule from opposite sides. A blank field answers
`why is this here?` with nothing; an overwrite answers it with whatever the last writer
believed. Each is asserted, because a writer that only ever saw a well-formed case would pass
a check that did nothing.

`config.REGRESSION` is redirected at a tmp_path throughout. A test that wrote into the real
suite would leave a case behind that gates the next agent version.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from touchstone import config, suite
from touchstone.gate.predicate import Predicate, RequiresPriorTool

AUTH = Predicate(
    rule="a lookup must follow authentication",
    source="policy.md:3",
    check=RequiresPriorTool(tool="get_order_details", prior=("get_user_details",)),
)


@pytest.fixture(autouse=True)
def _regression(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "REGRESSION", tmp_path / "regression")


def built(task: str = "7") -> dict[str, Any]:
    """One admitted case, cleared by all three gates."""
    return suite.case(AUTH, "s1", task, ("reproducible", "distinct", "justified"), "h1")


def test_an_admitted_case_carries_every_required_field() -> None:
    """Invariant 11's subject. A case nobody can justify does not get to gate anything."""
    assert suite.blank(built()) == []


def test_a_blank_field_is_refused_and_named() -> None:
    """Falsy, not missing. `"why": ""` and no `why` at all are one defect to a later reader.

    The empty string is the one a writer actually produces -- a predicate whose rule came back
    empty -- and a check that only caught the absent key would pass it.
    """
    record = built()
    record["why"] = ""
    assert suite.blank(record) == ["why"]
    with pytest.raises(ValueError, match="leaves \\['why'\\] empty"):
        suite.write(record)


def test_a_second_case_for_the_same_task_is_refused() -> None:
    """`distinct` should have stopped this, so the writer treats it as a bug and not a merge.

    Silently overwriting would lose the first case's `history`, which is the field D-024 makes
    append-only precisely so the answer to `why is this here?` cannot be replaced by a later
    writer's version of it.
    """
    suite.write(built("7"))
    with pytest.raises(ValueError, match="distinct"):
        suite.write(built("7"))


def test_the_why_is_the_rule_and_its_citation() -> None:
    """Not free text. `admit.justified` has already checked this citation resolves.

    A hand-written sentence would carry no such guarantee, which is why the field is composed
    from the predicate rather than supplied alongside it.
    """
    assert built()["why"] == "a lookup must follow authentication -- policy.md:3"


def test_an_absent_directory_is_an_empty_suite() -> None:
    """The first harvest runs before anything has ever been admitted, and must not raise."""
    assert suite.load() == []
    assert suite.covered() == set()


def test_covered_is_what_distinct_reads() -> None:
    """The two ends of D-083's task_id half, joined here so they cannot drift apart."""
    suite.write(built("7"))
    suite.write(built("9"))
    assert suite.covered() == {"7", "9"}


def test_a_written_case_round_trips_as_json() -> None:
    """The file is the record. Anything that does not survive `json.dumps` is not provenance."""
    out = suite.write(built("7"))
    assert json.loads(out.read_text())["origin"]["session_id"] == "s1"
    assert json.loads(out.read_text())["history"][0]["was"] == "admitted"


def test_a_written_case_reads_back_as_the_predicate_that_was_admitted() -> None:
    """The round trip the exact half of D-087 SS B rests on.

    `predicates()` goes back through `extract.parse` rather than a second constructor, so this
    asserts equality with the original object and not field-by-field: a shape that survived
    the write and came back as something else would gate a rule nobody admitted.
    """
    suite.write(built())
    assert suite.predicates() == (AUTH,)


def test_a_case_whose_shape_no_longer_parses_is_dropped_and_not_raised_on() -> None:
    """One hand-edited file must not stop every later harvest -- `distinct` is the backstop.

    The cost is bounded and named in the docstring: the loop may re-mine that task and
    admission refuses it on the task id. Asserted beside a good case, because a version that
    dropped the whole suite on one bad file would also return no bad predicate.
    """
    suite.write(built("7"))
    bad = built("8")
    bad["predicate"]["kind"] = "RequiresIncantation"
    suite.path("8").write_text(json.dumps(bad))
    assert suite.predicates() == (AUTH,)


def test_an_empty_suite_shows_the_curator_nothing_at_all() -> None:
    """Not an empty heading. A heading with nothing under it reads as a search that failed."""
    assert suite.index() == ""


def test_the_index_names_the_rules_and_never_the_shape_that_encodes_them() -> None:
    """D-092's guard is the reason. A curator shown a worked shape writes a fourth in it.

    What it needs is which rules are taken, so `task_id` and `why` are in and the encoded
    check is out. Asserted on the tool name rather than on the whole predicate: a leak would
    arrive as one field, and the field a curator would copy is the one naming a tool.
    """
    suite.write(built())
    index = suite.index()
    assert "7" in index
    assert AUTH.rule in index
    assert "RequiresPriorTool" not in index
    assert "get_user_details" not in index

"""Every field of the normalized model is either swept for aliases or knowingly ignored.

The same trade #11 made, for the same reason: the classifier visits named fields rather than
walking every string it meets, because a generic walk would sweep `source_id` — an opaque token
that could coincide with an alias and file a conversation under a project it never mentioned.

The cost of naming fields is that a field added to #8's model later could be forgotten. That cost
is paid here, and once more in the second test below: the two stages that read a conversation's
text must read the *same* text, or a project named in a tool result would be redacted by one stage
and invisible to the other. Nobody would intend that, and nothing but this assertion would catch
it.

The equality is asserted here rather than by importing one module into the other. `classification`
reading `sanitization` would couple two stages of §7 that the pipeline is supposed to be able to
reorder, for a constant.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from hermes_memory.classification.alias_classifier import IGNORED_FIELDS, SWEPT_FIELDS
from hermes_memory.normalization import Conversation, Message, NonTextPart, ToolActivity
from hermes_memory.sanitization.pattern_sanitizer import SCANNED_FIELDS

MODELS: tuple[type[BaseModel], ...] = (Conversation, Message, ToolActivity, NonTextPart)


@pytest.mark.parametrize("model", MODELS, ids=lambda model: model.__name__)
def test_every_field_is_accounted_for(model: type[BaseModel]) -> None:
    unaccounted = (
        set(model.model_fields) - SWEPT_FIELDS[model.__name__] - IGNORED_FIELDS[model.__name__]
    )

    assert not unaccounted, (
        f"{model.__name__} has fields the classifier neither sweeps nor ignores: "
        f"{sorted(unaccounted)}. Add each to SWEPT_FIELDS if it can carry text a person wrote, "
        "or to IGNORED_FIELDS if it is identity, structure or an enum (AM-8)."
    )


@pytest.mark.parametrize("model", MODELS, ids=lambda model: model.__name__)
def test_no_field_is_on_both_lists(model: type[BaseModel]) -> None:
    both = SWEPT_FIELDS[model.__name__] & IGNORED_FIELDS[model.__name__]

    assert not both, f"{model.__name__}: {sorted(both)} is both swept and ignored"


@pytest.mark.parametrize("model", MODELS, ids=lambda model: model.__name__)
def test_neither_list_names_a_field_that_does_not_exist(model: type[BaseModel]) -> None:
    named = SWEPT_FIELDS[model.__name__] | IGNORED_FIELDS[model.__name__]

    assert not named - set(model.model_fields)


@pytest.mark.parametrize("model", MODELS, ids=lambda model: model.__name__)
def test_the_classifier_reads_exactly_what_the_sanitizer_scans(model: type[BaseModel]) -> None:
    """The two stages of §7 that read text read the same text (research R10)."""
    assert SWEPT_FIELDS[model.__name__] == SCANNED_FIELDS[model.__name__], (
        f"{model.__name__}: the classifier sweeps {sorted(SWEPT_FIELDS[model.__name__])} while "
        f"the sanitizer scans {sorted(SCANNED_FIELDS[model.__name__])}. A field in one list and "
        "not the other is text one stage reads and the other does not."
    )


def test_identity_is_on_the_ignored_side() -> None:
    """AM-8. An alias coinciding with a native id is a coincidence, not evidence.

    AM-8 also names the derived `document_id`, which these tests do not reach: they walk
    `model_fields`, and a property is not a field. It is covered by consequence rather than by
    assertion — `document_id` is derived from `source` and `source_id`, both of which are on the
    ignored side, so nothing swept can contain it that was not swept already.
    """
    assert {"source", "source_id", "started_at"} <= IGNORED_FIELDS["Conversation"]
    assert "title" in SWEPT_FIELDS["Conversation"]

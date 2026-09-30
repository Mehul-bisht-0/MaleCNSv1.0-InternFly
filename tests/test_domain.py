import pytest

from internfly.domain import State, assert_transition


def test_legal_transition():
    assert_transition(State.BOOT, State.WAKE)


def test_illegal_transition_is_rejected():
    with pytest.raises(ValueError):
        assert_transition(State.BOOT, State.DRAFT_APPLICATION)


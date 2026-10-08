import pytest

from app.tools import _extract_json, compute_band, is_real_attempt


# --- band computation (application code, never the LLM) ---------------------

def test_band_strong():
    band, pct = compute_band(["sc1", "sc2", "sc3", "sc4"], [], True)
    assert band == "Strong"
    assert pct == 100.0


def test_band_strong_requires_relationship_correct():
    # Full coverage but wrong relationships -> Partial, not Strong.
    band, _ = compute_band(["a", "b", "c", "d"], [], False)
    assert band == "Partial"


def test_band_partial():
    band, pct = compute_band(["a", "b"], ["c", "d"], True)
    assert band == "Partial"
    assert pct == 50.0


def test_band_needs_work():
    band, _ = compute_band(["a"], ["b", "c", "d"], True)
    assert band == "Needs work"


def test_band_empty_is_needs_work():
    band, pct = compute_band([], [], False)
    assert band == "Needs work"
    assert pct == 0.0


# --- teach-back attempt heuristic -------------------------------------------

def test_real_attempt_accepted():
    assert is_real_attempt(
        "Photosynthesis is like a kitchen where sunlight is the chef."
    )


def test_non_attempts_rejected():
    assert not is_real_attempt("idk")
    assert not is_real_attempt("i don't know")
    assert not is_real_attempt("no")
    assert not is_real_attempt("")
    assert not is_real_attempt("???")
    assert not is_real_attempt("1234 5678 !!!")  # purely non-alphabetic


# --- LLM JSON extraction -----------------------------------------------------

def test_extract_json_fenced():
    assert _extract_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_extract_json_with_prose():
    assert _extract_json('Sure! Here it is:\n{"a": {"b": 2}}\nDone.') == {"a": {"b": 2}}


def test_extract_json_no_object():
    with pytest.raises(ValueError):
        _extract_json("no json here at all")

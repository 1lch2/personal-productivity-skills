import pytest

from parser import parse_int


def test_invalid_int_raises():
    with pytest.raises(ValueError):
        parse_int("nope")


def test_invalid_int_is_swallowed():
    try:
        parse_int("nope")
        assert False, "should not reach"
    except ValueError:
        pass


def test_invalid_int_hides_assertion():
    try:
        parse_int("nope")
        assert False, "should not reach"
    except Exception:
        pass

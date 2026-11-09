import pytest

from discount import calculate_discount


def test_silver_discount_is_hand_computed():
    assert calculate_discount(100, "silver") == 85.0


def test_discount_is_self_consistent():
    assert calculate_discount(100, "silver") == calculate_discount(100, "silver")


def test_unknown_tier_raises():
    with pytest.raises(ValueError):
        calculate_discount(100, "bronze")

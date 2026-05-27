from __future__ import annotations

from datetime import date

import pytest

from src.utils.business_days import subtract_business_days


def test_subtract_zero():
    d = date(2024, 6, 10)  # Monday
    assert subtract_business_days(d, 0) == d


def test_subtract_one_from_tuesday():
    d = date(2024, 6, 11)  # Tuesday → Monday
    assert subtract_business_days(d, 1) == date(2024, 6, 10)


def test_subtract_crosses_weekend():
    d = date(2024, 6, 10)  # Monday — go back 3 business days
    # Thu 6, Fri 7, Mon 10 — result = Wed 5
    assert subtract_business_days(d, 3) == date(2024, 6, 5)


def test_subtract_from_monday_skips_saturday_sunday():
    d = date(2024, 6, 10)  # Monday — 1 business day back = Friday
    assert subtract_business_days(d, 1) == date(2024, 6, 7)


def test_subtract_large_n():
    d = date(2024, 6, 28)  # Friday — go back 10 business days
    # Fri 28, Thu 27, Wed 26, Tue 25, Mon 24, Fri 21, Thu 20, Wed 19, Tue 18, Mon 17
    assert subtract_business_days(d, 10) == date(2024, 6, 14)


def test_negative_n_raises():
    with pytest.raises(ValueError):
        subtract_business_days(date(2024, 6, 10), -1)

from __future__ import annotations

from datetime import date, timedelta


def subtract_business_days(d: date, n: int) -> date:
    """Return the date that is n business days (Mon–Fri) before d.

    Does not account for public holidays — only weekends are skipped.
    For prazo de impugnação: use n=3 per Art. 164, Lei 14.133/2021.
    """
    if n < 0:
        raise ValueError("n must be non-negative")
    current = d
    remaining = n
    while remaining > 0:
        current -= timedelta(days=1)
        if current.weekday() < 5:  # Mon=0 … Fri=4
            remaining -= 1
    return current

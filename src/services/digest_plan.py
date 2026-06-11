"""Plan-gate do digest. Fonte única de verdade (worker + rota)."""
from __future__ import annotations

_PROFISSIONAL_PLANS = {"profissional", "business", "enterprise"}


def should_send_today(plan: str, weekday: int) -> bool:
    """trial → nunca; free → só segunda (weekday==0); profissional+ → diário."""
    plan = (plan or "free").lower()
    if plan == "trial":
        return False
    if plan in _PROFISSIONAL_PLANS:
        return True
    if plan == "free":
        return weekday == 0
    return False

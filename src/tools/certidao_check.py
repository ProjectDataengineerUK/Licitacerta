from __future__ import annotations

from datetime import date


def is_valid(expiry_date: date | None, reference_date: date | None = None) -> bool:
    """Retorna True se a certidão ainda está dentro da validade."""
    if expiry_date is None:
        return False
    ref = reference_date or date.today()
    return expiry_date >= ref


def days_until_expiry(expiry_date: date, reference_date: date | None = None) -> int:
    """Dias restantes até o vencimento. Negativo se já vencida."""
    ref = reference_date or date.today()
    return (expiry_date - ref).days


def expiring_soon(expiry_date: date, threshold_days: int = 30, reference_date: date | None = None) -> bool:
    """True se a certidão vence dentro de `threshold_days` dias."""
    remaining = days_until_expiry(expiry_date, reference_date)
    return 0 <= remaining <= threshold_days


def check_certidoes(certidoes: dict[str, date | None], reference_date: date | None = None) -> dict[str, dict]:
    """
    Verifica um conjunto de certidões.

    Args:
        certidoes: Mapeamento nome → data de vencimento (None = não informada)
        reference_date: Data de referência (padrão: hoje)

    Returns:
        Dict com status de cada certidão: valid, days_remaining, expiring_soon
    """
    ref = reference_date or date.today()
    result: dict[str, dict] = {}
    for name, expiry in certidoes.items():
        if expiry is None:
            result[name] = {"valid": False, "days_remaining": None, "expiring_soon": False}
        else:
            remaining = days_until_expiry(expiry, ref)
            result[name] = {
                "valid": remaining >= 0,
                "days_remaining": remaining,
                "expiring_soon": expiring_soon(expiry, threshold_days=30, reference_date=ref),
            }
    return result

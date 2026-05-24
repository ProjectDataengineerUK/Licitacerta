from decimal import Decimal

import pytest

from src.tools.margin_calc import build_scenarios, calculate_margin, mora_juros


def test_calculate_margin_basic():
    result = calculate_margin(
        cost=Decimal("1000.00"),
        target_margin_pct=20.0,
        tax_rate_pct=0.0,
        payment_delay_days=0,
        daily_cost_of_capital_pct=0.0,
    )
    assert result["price"] == Decimal("1250.00")
    assert result["net_margin_pct"] == Decimal("20.00")


def test_calculate_margin_with_taxes():
    result = calculate_margin(
        cost=Decimal("1000.00"),
        target_margin_pct=20.0,
        tax_rate_pct=9.25,
        payment_delay_days=0,
        daily_cost_of_capital_pct=0.0,
    )
    assert result["price"] > Decimal("1250.00"), "Preço deve ser maior quando há impostos"
    assert result["taxes"] > Decimal("0")


def test_calculate_margin_cost_of_capital():
    result_no_delay = calculate_margin(Decimal("1000.00"), 20.0, payment_delay_days=0)
    result_with_delay = calculate_margin(Decimal("1000.00"), 20.0, payment_delay_days=60)
    assert result_with_delay["price"] > result_no_delay["price"]


def test_mora_juros_basic():
    juros = mora_juros(Decimal("10000.00"), delay_days=30, daily_rate_pct=0.033)
    assert juros == Decimal("99.00")


def test_mora_juros_zero_days():
    assert mora_juros(Decimal("5000.00"), delay_days=0) == Decimal("0.00")


def test_build_scenarios_returns_three():
    scenarios = build_scenarios(Decimal("1000.00"), tax_rate_pct=9.25, payment_delay_days=30)
    assert set(scenarios.keys()) == {"pessimista", "realista", "otimista"}


def test_build_scenarios_price_order():
    scenarios = build_scenarios(Decimal("1000.00"), tax_rate_pct=9.25, payment_delay_days=30)
    # Pessimista tem menor margem alvo mas maior prazo de pagamento — pode ter preço similar
    # Otimista tem maior margem alvo
    assert scenarios["otimista"]["price"] > scenarios["realista"]["price"]


def test_margin_calc_precision():
    result = calculate_margin(Decimal("333.33"), 15.0, 6.5, 45)
    # Resultado deve ter no máximo 2 casas decimais
    assert result["price"] == result["price"].quantize(Decimal("0.01"))

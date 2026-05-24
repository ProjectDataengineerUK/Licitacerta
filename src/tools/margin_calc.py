from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def calculate_margin(
    cost: Decimal,
    target_margin_pct: float,
    tax_rate_pct: float = 0.0,
    payment_delay_days: int = 30,
    daily_cost_of_capital_pct: float = 0.05,
) -> dict[str, Decimal]:
    """
    Retorna preço sugerido e margem líquida considerando impostos e custo de capital.

    Args:
        cost: Custo direto do produto/serviço
        target_margin_pct: Margem alvo em percentual (ex: 20.0 para 20%)
        tax_rate_pct: Alíquota de impostos sobre o preço (ex: 9.25 para PIS+COFINS)
        payment_delay_days: Prazo de pagamento do órgão em dias
        daily_cost_of_capital_pct: Custo diário de capital em percentual (ex: 0.05 para 0.05%/dia)

    Returns:
        dict com cost_of_capital, price_before_tax, price, gross_margin_pct, net_margin_pct
    """
    cost_of_capital = (cost * Decimal(str(daily_cost_of_capital_pct / 100)) * payment_delay_days).quantize(CENT)
    total_cost = cost + cost_of_capital

    margin_factor = Decimal(str(1 - target_margin_pct / 100))
    tax_factor = Decimal(str(1 - tax_rate_pct / 100))

    price = (total_cost / (margin_factor * tax_factor)).quantize(CENT, rounding=ROUND_HALF_UP)

    gross_margin = price - total_cost
    gross_margin_pct = float((gross_margin / price * 100).quantize(Decimal("0.01")))

    taxes = (price * Decimal(str(tax_rate_pct / 100))).quantize(CENT)
    net_margin = gross_margin - taxes
    net_margin_pct = float((net_margin / price * 100).quantize(Decimal("0.01")))

    return {
        "cost": cost,
        "cost_of_capital": cost_of_capital,
        "total_cost": total_cost,
        "taxes": taxes,
        "price": price,
        "gross_margin_pct": Decimal(str(gross_margin_pct)),
        "net_margin_pct": Decimal(str(net_margin_pct)),
    }


def mora_juros(
    principal: Decimal,
    delay_days: int,
    daily_rate_pct: float = 0.033,
) -> Decimal:
    """Calcula juros de mora sobre valor atrasado (padrão: 1%/mês = ~0.033%/dia)."""
    return (principal * Decimal(str(daily_rate_pct / 100)) * delay_days).quantize(CENT, rounding=ROUND_HALF_UP)


def build_scenarios(
    cost: Decimal,
    tax_rate_pct: float = 9.25,
    payment_delay_days: int = 30,
) -> dict[str, dict[str, Decimal]]:
    """Gera os três cenários de precificação (pessimista/realista/otimista)."""
    return {
        "pessimista": calculate_margin(
            cost, target_margin_pct=10.0, tax_rate_pct=tax_rate_pct, payment_delay_days=payment_delay_days + 30
        ),
        "realista": calculate_margin(
            cost, target_margin_pct=18.0, tax_rate_pct=tax_rate_pct, payment_delay_days=payment_delay_days
        ),
        "otimista": calculate_margin(
            cost, target_margin_pct=25.0, tax_rate_pct=tax_rate_pct, payment_delay_days=max(0, payment_delay_days - 15)
        ),
    }

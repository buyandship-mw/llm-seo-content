from typing import Dict, Optional


def get_conversion_rate(
    from_currency: str,
    to_currency: str,
    rates_table: Dict[str, Dict[str, float]],
) -> Optional[float]:
    """Return the conversion rate from one currency to another.

    The function supports direct rates, inverse rates and using USD as an
    intermediary when a direct rate is unavailable.
    """
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    if from_currency == to_currency:
        return 1.0
    if from_currency in rates_table and to_currency in rates_table[from_currency]:
        return rates_table[from_currency][to_currency]

    # Try inverse if direct not found (e.g. table has USD:EUR but need EUR:USD)
    if to_currency in rates_table and from_currency in rates_table[to_currency]:
        inverse_rate = rates_table[to_currency][from_currency]
        if inverse_rate != 0:
            return 1.0 / inverse_rate

    usd = "USD"

    def _rate_to_usd(cur: str) -> Optional[float]:
        if cur == usd:
            return 1.0
        if cur in rates_table and usd in rates_table[cur]:
            return rates_table[cur][usd]
        if usd in rates_table and cur in rates_table[usd]:
            inv = rates_table[usd][cur]
            if inv != 0:
                return 1.0 / inv
        return None

    def _rate_from_usd(target: str) -> Optional[float]:
        if target == usd:
            return 1.0
        if usd in rates_table and target in rates_table[usd]:
            return rates_table[usd][target]
        if target in rates_table and usd in rates_table[target]:
            inv = rates_table[target][usd]
            if inv != 0:
                return 1.0 / inv
        return None

    to_usd = _rate_to_usd(from_currency)
    from_usd = _rate_from_usd(to_currency)
    if to_usd is not None and from_usd is not None:
        return to_usd * from_usd

    return None


def convert_price(
    amount: float,
    from_currency: str,
    to_currency: str,
    rates_table: Dict[str, Dict[str, float]],
) -> Optional[float]:
    """Convert ``amount`` from ``from_currency`` to ``to_currency``.

    Returns the converted value rounded to 2 decimal places, or ``None`` if no
    suitable conversion rate is found.
    """
    rate = get_conversion_rate(from_currency, to_currency, rates_table)
    if rate is None:
        return None
    return round(amount * rate, 2)


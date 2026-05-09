import logging
import re
from typing import Optional
from urllib.parse import quote

import requests
from google.adk.agents import Agent

logger = logging.getLogger(__name__)

# Frankfurter expects ISO 4217 codes. Passing "Mexican Peso" → 404 and breaks conversion.
_CURRENCY_ALIASES: dict[str, str] = {
    "usd": "USD",
    "us dollar": "USD",
    "dollar": "USD",
    "us$": "USD",
    "eur": "EUR",
    "euro": "EUR",
    "€": "EUR",
    "gbp": "GBP",
    "pound": "GBP",
    "pounds": "GBP",
    "british pound": "GBP",
    "pound sterling": "GBP",
    "sterling": "GBP",
    "£": "GBP",
    "mxn": "MXN",
    "mexican peso": "MXN",
    "mx peso": "MXN",
    "cad": "CAD",
    "canadian dollar": "CAD",
    "aud": "AUD",
    "australian dollar": "AUD",
    "jpy": "JPY",
    "yen": "JPY",
    "japanese yen": "JPY",
    "chf": "CHF",
    "swiss franc": "CHF",
    "brl": "BRL",
    "brazilian real": "BRL",
    "real": "BRL",
    "inr": "INR",
    "rupee": "INR",
    "indian rupee": "INR",
    "cny": "CNY",
    "rmb": "CNY",
    "yuan": "CNY",
}


def _normalize_currency(raw: str) -> Optional[str]:
    """Map common names/symbols to ISO 4217 (3 letters)."""
    if not raw:
        return None
    s = raw.strip()
    if re.fullmatch(r"[A-Za-z]{3}", s):
        return s.upper()
    key = s.lower().strip()
    if key in _CURRENCY_ALIASES:
        return _CURRENCY_ALIASES[key]
    # Drop parenthetical hints e.g. "Peso (MXN)"
    paren = re.search(r"\(([A-Za-z]{3})\)", s)
    if paren:
        return paren.group(1).upper()
    return None


def _fetch_frankfurter(base: str, quote_ccy: str) -> Optional[float]:
    """Return units of `quote_ccy` per 1 unit of `base`, or None."""
    url = (
        f"https://api.frankfurter.dev/v1/latest?"
        f"base={quote(base, safe='')}&symbols={quote(quote_ccy, safe='')}"
    )
    try:
        response = requests.get(url, timeout=(5, 20))
        response.raise_for_status()
        data = response.json()
        rates = data.get("rates") or {}
        if quote_ccy not in rates:
            return None
        return float(rates[quote_ccy])
    except requests.exceptions.HTTPError as err:
        logger.warning(
            "Frankfurter HTTP error for base=%s symbols=%s: %s", base, quote_ccy, err
        )
        return None
    except Exception as err:
        logger.warning("Frankfurter error for base=%s symbols=%s: %s", base, quote_ccy, err)
        return None


def _rate_via_eur(from_ccy: str, to_ccy: str) -> Optional[float]:
    """Cross-rate using ECB pivot EUR when direct base is unsupported."""
    url = (
        "https://api.frankfurter.dev/v1/latest?"
        f"base=EUR&symbols={quote(from_ccy, safe='')},{quote(to_ccy, safe='')}"
    )
    try:
        response = requests.get(url, timeout=(5, 20))
        response.raise_for_status()
        data = response.json()
        rates = data.get("rates") or {}
        if from_ccy not in rates or to_ccy not in rates:
            return None
        # Per 1 EUR: rates[from_ccy] units of from_ccy; rates[to_ccy] units of to_ccy.
        # So 1 from_ccy = (rates[to_ccy] / rates[from_ccy]) to_ccy
        return float(rates[to_ccy]) / float(rates[from_ccy])
    except Exception as err:
        logger.warning("EUR bridge failed %s→%s: %s", from_ccy, to_ccy, err)
        return None


def convert_currency(from_currency: str, to_currency: str):
    """Given a from and to currency, returns how many units of `to` equal 1 unit of `from`.

    Accepts ISO codes (MXN, GBP) or common names (Mexican Peso, British Pound).

    Args:
        from_currency: Source currency (ISO code or common English name).
        to_currency: Target currency (ISO code or common English name).

    Returns:
        Conversion multiplier (to per from), or None if lookup failed.
    """
    from_ccy = _normalize_currency(from_currency)
    to_ccy = _normalize_currency(to_currency)
    if not from_ccy or not to_ccy:
        logger.error("Could not normalize currencies: %r → %r", from_currency, to_currency)
        return None

    logger.debug("convert_currency normalized: %s → %s", from_ccy, to_ccy)

    if from_ccy == to_ccy:
        return 1.0

    direct = _fetch_frankfurter(from_ccy, to_ccy)
    if direct is not None:
        return direct

    bridged = _rate_via_eur(from_ccy, to_ccy)
    if bridged is not None:
        logger.info("Used EUR bridge for %s → %s", from_ccy, to_ccy)
        return bridged

    return None


instruction_prompt = """
    You're a currency agent that converts between currencies.
    Always call `convert_currency` with the two currencies (ISO codes like MXN/GBP or names like Mexican Peso / British Pound).
    Output in this format:
    X British Pounds (GBP) = Y Mexican Pesos (MXN)
    (Use the tool result to state the numeric rate; the tool returns how many units of `to_currency` equal 1 unit of `from_currency`.)
    If the tool returns nothing usable, say "I'm sorry, I cannot convert from X to Y".
"""

root_agent = Agent(
    name="currency_agent",
    model="gemini-2.5-flash",
    description="Agent to convert from one currency to another.",
    instruction=instruction_prompt,
    tools=[convert_currency],
)

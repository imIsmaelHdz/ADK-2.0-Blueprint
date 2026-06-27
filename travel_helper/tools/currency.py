import logging
from typing import Optional
from urllib.parse import quote

import requests

logger = logging.getLogger(__name__)


def _fetch_frankfurter(base: str, quote_ccy: str) -> Optional[float]:
    url = (
        f"https://api.frankfurter.dev/v1/latest?"
        f"base={quote(base, safe='')}&symbols={quote(quote_ccy, safe='')}"
    )
    try:
        response = requests.get(url, timeout=(5, 20))
        response.raise_for_status()
        rates = response.json().get("rates") or {}
        return float(rates[quote_ccy]) if quote_ccy in rates else None
    except requests.exceptions.HTTPError as err:
        logger.warning("Frankfurter HTTP error %s→%s: %s", base, quote_ccy, err)
        return None
    except Exception as err:
        logger.warning("Frankfurter error %s→%s: %s", base, quote_ccy, err)
        return None


def _rate_via_eur(from_ccy: str, to_ccy: str) -> Optional[float]:
    """Cross-rate using ECB pivot EUR when the direct base is unsupported."""
    url = (
        f"https://api.frankfurter.dev/v1/latest?"
        f"base=EUR&symbols={quote(from_ccy, safe='')},{quote(to_ccy, safe='')}"
    )
    try:
        response = requests.get(url, timeout=(5, 20))
        response.raise_for_status()
        rates = response.json().get("rates") or {}
        if from_ccy not in rates or to_ccy not in rates:
            return None
        return float(rates[to_ccy]) / float(rates[from_ccy])
    except Exception as err:
        logger.warning("EUR bridge failed %s→%s: %s", from_ccy, to_ccy, err)
        return None


def convert_currency(from_currency: str, to_currency: str) -> Optional[float]:
    """Return how many units of to_currency equal 1 unit of from_currency.

    Args:
        from_currency: ISO 4217 code, e.g. "MXN".
        to_currency: ISO 4217 code, e.g. "GBP".

    Returns:
        Exchange rate as a float, or None if the lookup failed.
    """
    from_ccy = from_currency.strip().upper()
    to_ccy = to_currency.strip().upper()

    if from_ccy == to_ccy:
        return 1.0

    direct = _fetch_frankfurter(from_ccy, to_ccy)
    if direct is not None:
        return direct

    bridged = _rate_via_eur(from_ccy, to_ccy)
    if bridged is not None:
        logger.info("Used EUR bridge for %s→%s", from_ccy, to_ccy)
        return bridged

    return None

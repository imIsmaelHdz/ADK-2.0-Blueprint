import logging
from typing import Any, Optional
from urllib.parse import quote_plus

import requests

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def api_request(url: str, timeout: tuple[int, int] = (5, 25)) -> Optional[Any]:
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        logger.debug("Response: %s", data)
        return data
    except requests.exceptions.HTTPError as err:
        logger.error("HTTP error occurred: %s", err)
    except Exception as err:
        logger.error("Other error occurred: %s", err)
    return None


def location_to_lat_long(location: str):
    """Given a location, returns the latitude and longitude

    Args:
        location: The location for which to get the weather.

    Returns:
        The latitude and longitude information in JSON.
    """
    logger.info("Calling location_to_lat_long(%s)", location)
    q = quote_plus(location.strip())
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={q}&count=1"
    return api_request(url)


def lat_long_to_weather(latitude: str, longitude: str):
    """Given a latitude and longitude, returns the weather information

    Args:
        latitude: The latitude of a location
        longitude: The longitude of a location

    Returns:
        The weather information for the location in JSON.
    """
    logger.info("Calling lat_long_to_weather(%s, %s)", latitude, longitude)
    lat = quote_plus(str(latitude).strip())
    lon = quote_plus(str(longitude).strip())
    url = (
        "https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        "&daily=temperature_2m_max,temperature_2m_min,sunrise,sunset,"
        "uv_index_max,precipitation_sum,precipitation_probability_max,wind_speed_10m_max"
        "&forecast_days=7"
    )
    return api_request(url)


def weather_for_city(city: str):
    """Fetch 7-day forecast for a city in one step (geocode + forecast).

    Prefer this over calling `location_to_lat_long` + `lat_long_to_weather` separately —
    it avoids mistakes copying latitude/longitude from nested JSON.

    Args:
        city: City name (e.g. "London", "Mexico City").

    Returns:
        A dict with keys `city`, `latitude`, `longitude`, and `forecast` (Open-Meteo JSON),
        or `{"error": "..."}` if lookup fails.
    """
    raw = (city or "").strip()
    if not raw:
        return {"error": "city name is empty"}

    geo = location_to_lat_long(raw)
    if not geo:
        return {"error": f"geocoding request failed for {raw!r}"}

    results = geo.get("results") or []
    if not results:
        return {"error": f'no geocoding results for {raw!r} — try "London, UK" spelling'}

    place = results[0]
    lat = place.get("latitude")
    lon = place.get("longitude")
    name = place.get("name") or raw

    if lat is None or lon is None:
        return {"error": "geocoder returned no coordinates"}

    forecast = lat_long_to_weather(str(lat), str(lon))
    if not forecast:
        return {"error": "weather API request failed"}

    return {
        "city": name,
        "latitude": lat,
        "longitude": lon,
        "forecast": forecast,
    }



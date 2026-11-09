from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import requests

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


class WeatherServiceError(RuntimeError):
    pass


def geocode_location(location: str, timeout: int = 15) -> dict[str, Any]:
    if not location or not location.strip():
        raise WeatherServiceError("Enter a village or town to find local weather.")
    search_terms = [location.strip()]
    # A saved profile may contain a comma-separated hierarchy. Try its local
    # parts in turn when the full label is not recognised by the geocoder.
    search_terms.extend(part.strip() for part in location.split(",") if part.strip())
    payload: dict[str, Any] = {}
    last_error: Exception | None = None
    for term in dict.fromkeys(search_terms):
        try:
            response = requests.get(
                GEOCODING_URL,
                params={"name": term, "count": 5, "language": "en", "format": "json"},
                timeout=timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            continue
        if payload.get("results"):
            break
    if not payload and last_error:
        raise WeatherServiceError("Location lookup failed. Check your internet connection and try again.") from last_error
    results = payload.get("results") or []
    india_results = [r for r in results if str(r.get("country_code", "")).upper() == "IN"]
    candidates = india_results or results
    if not candidates:
        raise WeatherServiceError("No matching location found. Try a nearby town or taluk name.")
    # Prefer Karnataka when a similar place name occurs in more than one state.
    selected = next((r for r in candidates if "Karnataka" in str(r.get("admin1", ""))), candidates[0])
    return {
        "name": selected.get("name", location),
        "admin1": selected.get("admin1", ""),
        "country": selected.get("country", "India"),
        "latitude": float(selected["latitude"]),
        "longitude": float(selected["longitude"]),
    }


def get_weather_forecast(
    location: str,
    timeout: int = 20,
    coordinates: tuple[float, float] | None = None,
) -> dict[str, Any]:
    """Fetch a forecast by a village name or an explicitly consented GPS point."""
    if coordinates is not None:
        latitude, longitude = coordinates
        if not (-90 <= float(latitude) <= 90 and -180 <= float(longitude) <= 180):
            raise WeatherServiceError("Saved GPS coordinates are invalid. Please update My Farm.")
        place = {
            "name": location or "Your farm",
            "admin1": "",
            "country": "India",
            "latitude": float(latitude),
            "longitude": float(longitude),
            "match_method": "consented farm GPS",
        }
    else:
        place = geocode_location(location, timeout=timeout)
        place["match_method"] = "place-name lookup"
    params = {
        "latitude": place["latitude"],
        "longitude": place["longitude"],
        "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,weather_code",
        "forecast_days": 5,
        "timezone": "Asia/Kolkata",
    }
    try:
        response = requests.get(FORECAST_URL, params=params, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise WeatherServiceError(f"Weather forecast could not be retrieved: {exc}") from exc

    current = payload.get("current") or {}
    daily = payload.get("daily") or {}
    dates = daily.get("time") or []
    rows: list[dict[str, Any]] = []
    keys = [
        "temperature_2m_max", "temperature_2m_min", "precipitation_sum",
        "precipitation_probability_max", "weather_code",
    ]
    for i, day in enumerate(dates):
        row = {"date": day}
        for key in keys:
            values = daily.get(key) or []
            row[key] = values[i] if i < len(values) else None
        rows.append(row)

    return {
        "location": place,
        "current": current,
        "daily": rows,
        "timezone": payload.get("timezone", "Asia/Kolkata"),
        "fetched_at": datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(timespec="minutes"),
        "source": "Open-Meteo forecast API",
        "source_url": "https://open-meteo.com/en/docs",
        "attribution": "Weather data by Open-Meteo.com (CC BY 4.0)",
    }


def weather_code_label(code: Any) -> str:
    try:
        code = int(code)
    except (TypeError, ValueError):
        return "Conditions unavailable"
    if code == 0:
        return "Clear sky"
    if code in {1, 2, 3}:
        return "Mainly clear / partly cloudy / overcast"
    if code in {45, 48}:
        return "Fog"
    if code in {51, 53, 55, 56, 57}:
        return "Drizzle"
    if code in {61, 63, 65, 66, 67, 80, 81, 82}:
        return "Rain or rain showers"
    if code in {71, 73, 75, 77, 85, 86}:
        return "Snow"
    if code in {95, 96, 99}:
        return "Thunderstorm"
    return "Variable conditions"

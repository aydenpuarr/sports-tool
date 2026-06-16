"""Open-Meteo client: free, no API key, covers US/Mexico/Canada World Cup
host cities, supports both forecast (16 days) and historical archive
(back to 1940) -- the latter is what makes weather backtesting possible.
"""
from __future__ import annotations

from dataclasses import dataclass

import requests

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# 2026 World Cup host city coordinates (subset -- add more as needed).
HOST_CITIES = {
    "New York/New Jersey": (40.8128, -74.0742),
    "Los Angeles": (34.0522, -118.2437),
    "Dallas": (32.7767, -96.7970),
    "Atlanta": (33.7490, -84.3880),
    "Miami": (25.7617, -80.1918),
    "Mexico City": (19.4326, -99.1332),
    "Guadalajara": (20.6597, -103.3496),
    "Monterrey": (25.6866, -100.3161),
    "Toronto": (43.6532, -79.3832),
    "Vancouver": (49.2827, -123.1207),
}


@dataclass
class WeatherSnapshot:
    temperature_c: float
    humidity_pct: float
    wind_kph: float
    precipitation_mm: float


def get_forecast(city: str, date: str) -> WeatherSnapshot:
    """date in YYYY-MM-DD, must be within ~16 days of today for the free
    forecast endpoint."""
    lat, lon = HOST_CITIES[city]
    resp = requests.get(
        FORECAST_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation",
            "start_date": date,
            "end_date": date,
            "timezone": "auto",
        },
        timeout=10,
    )
    resp.raise_for_status()
    return _midday_snapshot(resp.json())


def get_historical(city: str, date: str) -> WeatherSnapshot:
    """Historical archive lookup for backtesting -- works for any past date
    back to 1940."""
    lat, lon = HOST_CITIES[city]
    resp = requests.get(
        ARCHIVE_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation",
            "start_date": date,
            "end_date": date,
            "timezone": "auto",
        },
        timeout=10,
    )
    resp.raise_for_status()
    return _midday_snapshot(resp.json())


def _midday_snapshot(payload: dict) -> WeatherSnapshot:
    """Open-Meteo returns hourly arrays for the day; take the ~14:00 local
    slot (index 14) as a representative kickoff-time reading."""
    hourly = payload["hourly"]
    idx = min(14, len(hourly["temperature_2m"]) - 1)
    return WeatherSnapshot(
        temperature_c=hourly["temperature_2m"][idx],
        humidity_pct=hourly["relative_humidity_2m"][idx],
        wind_kph=hourly["wind_speed_10m"][idx],
        precipitation_mm=hourly["precipitation"][idx],
    )

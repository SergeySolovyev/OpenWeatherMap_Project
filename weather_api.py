from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, Optional

import aiohttp
import requests


OWM_URL = "https://api.openweathermap.org/data/2.5/weather"


class WeatherError(Exception):
    pass


def get_api_key(explicit: Optional[str] = None) -> str:
    api_key = explicit or os.getenv("OWM_API_KEY", "")
    if not api_key:
        raise WeatherError("OpenWeatherMap API key is missing.")
    return api_key


def fetch_current_weather(city: str, api_key: Optional[str] = None, timeout: int = 10) -> Dict[str, Any]:
    key = get_api_key(api_key)
    params = {"q": city, "appid": key, "units": "metric"}
    try:
        resp = requests.get(OWM_URL, params=params, timeout=timeout)
        if resp.status_code != 200:
            raise WeatherError(f"API error {resp.status_code}: {resp.text}")
        data = resp.json()
        return {
            "temp": data.get("main", {}).get("temp"),
            "description": data.get("weather", [{}])[0].get("description", ""),
            "raw": data,
        }
    except requests.RequestException as exc:
        raise WeatherError(f"Request failed: {exc}") from exc


async def fetch_current_weather_async(
    city: str, api_key: Optional[str] = None, timeout: int = 10, session: Optional[aiohttp.ClientSession] = None
) -> Dict[str, Any]:
    key = get_api_key(api_key)
    params = {"q": city, "appid": key, "units": "metric"}
    own_session = session is None
    sess = session or aiohttp.ClientSession()
    try:
        async with sess.get(OWM_URL, params=params, timeout=timeout) as resp:
            if resp.status != 200:
                raise WeatherError(f"API error {resp.status}: {await resp.text()}")
            data = await resp.json()
            return {
                "temp": data.get("main", {}).get("temp"),
                "description": data.get("weather", [{}])[0].get("description", ""),
                "raw": data,
            }
    except asyncio.TimeoutError as exc:
        raise WeatherError("Request timeout") from exc
    except aiohttp.ClientError as exc:
        raise WeatherError(f"Request failed: {exc}") from exc
    finally:
        if own_session:
            await sess.close()


from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, Dict, Optional

import aiohttp
import requests
from dotenv import load_dotenv

# Загружаем .env файл если он есть
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()  # Пробуем загрузить из текущей директории


OWM_URL = "https://api.openweathermap.org/data/2.5/weather"


class WeatherError(Exception):
    pass


def get_api_key(explicit: Optional[str] = None) -> str:
    api_key = explicit or os.getenv("OWM_API_KEY", "")
    if not api_key:
        raise WeatherError("OpenWeatherMap API key is missing.")
    return api_key


def fetch_current_weather(city: str, api_key: Optional[str] = None, timeout: int = 10) -> Dict[str, Any]:
    """Синхронный запрос текущей погоды через OpenWeatherMap API.
    
    ВЫВОД из экспериментов: sync запросы выполняются последовательно и медленнее async.
    Для множественных запросов async даёт ускорение в 18-19 раз.
    Рекомендуется использовать fetch_current_weather_async для лучшей производительности.
    См. experiments.ipynb для детального анализа.
    """
    key = get_api_key(api_key)
    params = {"q": city, "appid": key, "units": "metric"}
    try:
        resp = requests.get(OWM_URL, params=params, timeout=timeout)
        if resp.status_code != 200:
            # Специальная обработка ошибки 401 (некорректный API ключ)
            if resp.status_code == 401:
                error_data = resp.json() if resp.headers.get('content-type', '').startswith('application/json') else {}
                if error_data.get('cod') == 401:
                    raise WeatherError(
                        f"Invalid API key. Please see https://openweathermap.org/faq#error401 for more info.\n"
                        f"Response: {error_data.get('message', resp.text)}"
                    )
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
    """Асинхронный запрос текущей погоды через OpenWeatherMap API.
    
    ВЫВОД из экспериментов: async даёт ускорение в 18-19 раз для множественных запросов.
    Для одного запроса async быстрее на ~77%. Рекомендуется использовать async для всех API запросов.
    См. experiments.ipynb для детального анализа sync vs async.
    """
    key = get_api_key(api_key)
    params = {"q": city, "appid": key, "units": "metric"}
    own_session = session is None
    sess = session or aiohttp.ClientSession()
    try:
        async with sess.get(OWM_URL, params=params, timeout=timeout) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                # Специальная обработка ошибки 401 (некорректный API ключ)
                if resp.status == 401:
                    try:
                        error_data = await resp.json()
                        if error_data.get('cod') == 401:
                            raise WeatherError(
                                f"Invalid API key. Please see https://openweathermap.org/faq#error401 for more info.\n"
                                f"Response: {error_data.get('message', error_text)}"
                            )
                    except:
                        pass
                raise WeatherError(f"API error {resp.status}: {error_text}")
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


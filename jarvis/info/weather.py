"""Clima pelo Open-Meteo: gratuito, sem chave e sem cadastro."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request

GEOCODE = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST = "https://api.open-meteo.com/v1/forecast"

# Códigos WMO usados pelo Open-Meteo.
WMO = {
    0: "céu limpo", 1: "predomínio de sol", 2: "parcialmente nublado", 3: "nublado",
    45: "neblina", 48: "neblina com geada", 51: "garoa fraca", 53: "garoa", 55: "garoa forte",
    61: "chuva fraca", 63: "chuva", 65: "chuva forte", 66: "chuva congelante", 67: "chuva congelante forte",
    71: "neve fraca", 73: "neve", 75: "neve forte", 80: "pancadas de chuva fracas",
    81: "pancadas de chuva", 82: "pancadas de chuva fortes", 95: "trovoadas",
    96: "trovoadas com granizo", 99: "trovoadas fortes com granizo",
}


class WeatherError(RuntimeError):
    pass


def _get(url: str, params: dict, opener=urllib.request.urlopen) -> dict:
    full = url + "?" + urllib.parse.urlencode(params)
    try:
        with opener(full, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (OSError, ValueError) as exc:
        raise WeatherError(f"clima indisponível: {exc}") from exc


def locate(city: str, opener=urllib.request.urlopen) -> dict:
    data = _get(GEOCODE, {"name": city, "count": 1, "language": "pt", "countryCode": "BR"}, opener)
    if not data.get("results"):
        data = _get(GEOCODE, {"name": city, "count": 1, "language": "pt"}, opener)
    if not data.get("results"):
        raise WeatherError(f"cidade '{city}' não encontrada")
    place = data["results"][0]
    label = ", ".join(p for p in (place.get("name"), place.get("admin1")) if p)
    return {"nome": label, "lat": place["latitude"], "lon": place["longitude"]}


def forecast(city: str, opener=urllib.request.urlopen) -> dict:
    place = locate(city, opener)
    data = _get(FORECAST, {
        "latitude": place["lat"], "longitude": place["lon"], "timezone": "auto", "forecast_days": 1,
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code",
    }, opener)
    now, day = data.get("current", {}), data.get("daily", {})
    first = lambda key: (day.get(key) or [None])[0]  # noqa: E731
    return {
        "local": place["nome"],
        "agora_c": round(now.get("temperature_2m", 0)),
        "sensacao_c": round(now.get("apparent_temperature", 0)),
        "umidade_percent": now.get("relative_humidity_2m"),
        "condicao": WMO.get(now.get("weather_code"), "tempo indefinido"),
        "vento_kmh": round(now.get("wind_speed_10m", 0)),
        "maxima_c": round(first("temperature_2m_max") or 0),
        "minima_c": round(first("temperature_2m_min") or 0),
        "chance_chuva_percent": first("precipitation_probability_max"),
    }


def sentence(w: dict) -> str:
    text = (
        f"Em {w['local']} agora faz {w['agora_c']}°C, {w['condicao']}, "
        f"com sensação de {w['sensacao_c']}°C. Hoje a máxima é {w['maxima_c']}°C e a mínima {w['minima_c']}°C"
    )
    if w.get("chance_chuva_percent") is not None:
        text += f", com {w['chance_chuva_percent']}% de chance de chuva"
    return text + "."

"""
climate.py
===========
Contexto climático real via Open-Meteo (gratuito, sem chave de API).

Se a rede não estiver disponível (ex.: ambiente sem internet), cai para
um valor neutro e sinaliza isso na interface — nunca derruba o app.
"""

from __future__ import annotations

import requests

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT_SEGUNDOS = 4


def obter_clima_atual(lat, lon):
    """Retorna um dicionário com chuva (mm, última 1h), umidade relativa (%)
    e vento (km/h) para a coordenada informada. Em caso de falha, retorna
    valores neutros com 'ok': False."""
    try:
        resp = requests.get(
            OPEN_METEO_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "precipitation,relative_humidity_2m,wind_speed_10m,temperature_2m",
                "timezone": "auto",
            },
            timeout=TIMEOUT_SEGUNDOS,
        )
        resp.raise_for_status()
        dados = resp.json().get("current", {})
        return {
            "ok": True,
            "chuva_mm": dados.get("precipitation", 0.0),
            "umidade_pct": dados.get("relative_humidity_2m", 50.0),
            "vento_kmh": dados.get("wind_speed_10m", 0.0),
            "temperatura_c": dados.get("temperature_2m", 24.0),
        }
    except Exception as exc:
        return {
            "ok": False,
            "erro": str(exc),
            "chuva_mm": 0.0,
            "umidade_pct": 50.0,
            "vento_kmh": 0.0,
            "temperatura_c": 24.0,
        }

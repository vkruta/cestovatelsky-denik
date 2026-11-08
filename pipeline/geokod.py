"""Offline určení nejbližšího města k souřadnicím (data GeoNames cities1000)."""
import csv
import math
from pathlib import Path

import numpy as np

_DATA = Path(__file__).resolve().parent / "data" / "mesta.csv"
_mesta = None

ZEME = {
    "CZ": ("Česko", "Czechia"), "SK": ("Slovensko", "Slovakia"), "DE": ("Německo", "Germany"),
    "AT": ("Rakousko", "Austria"), "PL": ("Polsko", "Poland"), "HU": ("Maďarsko", "Hungary"),
    "ES": ("Španělsko", "Spain"), "PT": ("Portugalsko", "Portugal"), "FR": ("Francie", "France"),
    "IT": ("Itálie", "Italy"), "HR": ("Chorvatsko", "Croatia"), "SI": ("Slovinsko", "Slovenia"),
    "GR": ("Řecko", "Greece"), "RO": ("Rumunsko", "Romania"), "BG": ("Bulharsko", "Bulgaria"),
    "NO": ("Norsko", "Norway"), "SE": ("Švédsko", "Sweden"), "DK": ("Dánsko", "Denmark"),
    "FI": ("Finsko", "Finland"), "NL": ("Nizozemsko", "Netherlands"), "BE": ("Belgie", "Belgium"),
    "CH": ("Švýcarsko", "Switzerland"), "GB": ("Spojené království", "United Kingdom"),
    "IE": ("Irsko", "Ireland"), "IS": ("Island", "Iceland"), "ME": ("Černá Hora", "Montenegro"),
    "AL": ("Albánie", "Albania"), "MT": ("Malta", "Malta"), "CY": ("Kypr", "Cyprus"),
    "TR": ("Turecko", "Turkey"), "LU": ("Lucembursko", "Luxembourg"),
}


def _nacti():
    global _mesta
    if _mesta is None:
        rows = list(csv.DictReader(_DATA.open(encoding="utf-8")))
        lat = np.radians([float(r["lat"]) for r in rows])
        lon = np.radians([float(r["lon"]) for r in rows])
        _mesta = (rows, lat, lon)
    return _mesta


def nejblizsi(lat, lon):
    rows, la, lo = _nacti()
    p, q = math.radians(lat), math.radians(lon)
    h = np.sin((la - p) / 2) ** 2 + np.cos(p) * np.cos(la) * np.sin((lo - q) / 2) ** 2
    i = int(np.argmin(h))
    r = rows[i]
    km = 6371 * 2 * math.asin(math.sqrt(float(h[i])))
    zeme = ZEME.get(r["cc"], (r["cc"], r["cc"]))
    return {"mesto": r["name"], "region": r["admin1"], "cc": r["cc"],
            "zeme": {"cs": zeme[0], "en": zeme[1]}, "km": round(km, 1)}

#!/usr/bin/env python3
"""
Z vybraných fotek (site/vyber/<slug>.json) připraví veřejné soubory:
  site/foto/<slug>/velke/*.jpg, site/foto/<slug>/male/*.jpg  (bez EXIF)
  site/fotky/<slug>.json                                      (datum, místo, popisky)
Zdroj: data/fotky/<slug>/ (zmenšené fotky z Takeoutu + fotky.json), soukromé.
"""
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image

from geokod import nejblizsi

ROOT = Path(__file__).resolve().parent.parent
TZ = {"CZ": "Europe/Prague", "DE": "Europe/Berlin", "AT": "Europe/Vienna", "NO": "Europe/Oslo",
      "SE": "Europe/Stockholm", "DK": "Europe/Copenhagen", "RO": "Europe/Bucharest", "IT": "Europe/Rome",
      "ES": "Europe/Madrid", "PT": "Europe/Lisbon", "FR": "Europe/Paris", "GR": "Europe/Athens",
      "HR": "Europe/Zagreb", "BG": "Europe/Sofia", "GB": "Europe/London"}


def zona(lat, lon, cc):
    if cc == "ES" and lon < -10:
        return ZoneInfo("Atlantic/Canary")
    return ZoneInfo(TZ.get(cc, "Europe/Prague"))


def zpracuj(slug):
    vyber_f = ROOT / "site" / "vyber" / f"{slug}.json"
    if not vyber_f.exists():
        return
    vyber = json.loads(vyber_f.read_text(encoding="utf-8"))
    src = ROOT / "data" / "fotky" / slug
    meta = json.loads((src / "fotky.json").read_text(encoding="utf-8"))
    cil = ROOT / "site" / "foto" / slug
    if cil.exists():
        shutil.rmtree(cil)
    (cil / "velke").mkdir(parents=True)
    (cil / "male").mkdir()
    fotky = []
    for v in vyber["fotky"]:
        m = meta[v["i"]]
        g = nejblizsi(m["lat"], m["lon"]) if m.get("lat") else None
        tz = zona(m.get("lat"), m.get("lon"), g["cc"] if g else "CZ")
        t = datetime.fromtimestamp(m["cas"], timezone.utc).astimezone(tz)
        for velikost in ("velke", "male"):
            im = Image.open(src / velikost / m["soubor"])
            im.save(cil / velikost / m["soubor"], quality=82 if velikost == "velke" else 78,
                    optimize=True, progressive=True)  # uložení bez EXIF
        w, h = Image.open(cil / "velke" / m["soubor"]).size
        fotky.append({
            "soubor": m["soubor"], "datum": t.date().isoformat(), "cas": t.strftime("%H:%M"),
            "p": [round(m["lat"], 3), round(m["lon"], 3)] if m.get("lat") else None,
            "misto": g["mesto"] if g else None, "w": w, "h": h,
            "nahled": f"foto/{slug}/male/{m['soubor']}", "velke": f"foto/{slug}/velke/{m['soubor']}",
            "popis": v.get("popis", {}), "titulni": v["i"] == vyber.get("titulni"),
        })
    fotky.sort(key=lambda f: (f["datum"], f["cas"]))
    (ROOT / "site" / "fotky").mkdir(exist_ok=True)
    (ROOT / "site" / "fotky" / f"{slug}.json").write_text(
        json.dumps({"fotky": fotky}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{slug}: {len(fotky)} fotek")


if __name__ == "__main__":
    cesty = json.loads((ROOT / "cesty.json").read_text(encoding="utf-8"))
    for c in cesty:
        if len(sys.argv) < 2 or c["slug"] in sys.argv[1:]:
            zpracuj(c["slug"])

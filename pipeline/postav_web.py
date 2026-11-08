#!/usr/bin/env python3
"""
Vygeneruje statický web do složky public/ z:
  site/data/cesty/*.json   trasy (výstup zpracuj_trasy.py)
  site/obsah/<slug>.json   texty CZ/EN
  site/fotky/<slug>.json   vybrané veřejné fotky (výstup zpracuj_fotky.py)

  python pipeline/postav_web.py            web pro GitHub Pages
  python pipeline/postav_web.py --nahled   úvodní stránka bez <html>/<head> obalu (náhled v Claude)
"""
import json
import shutil
import sys
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
OUT = ROOT / "public"

MODY = ["let", "auto", "vlak", "autobus", "lod", "metro", "tramvaj", "kolo", "pesky"]

# názvy z GeoNames -> jak je chceme ukázat
NAZVY = {
    "Goeteborg": ("Göteborg", "Gothenburg"), "Majorna": ("Göteborg", "Gothenburg"),
    "Landvetter": ("letiště Landvetter", "Landvetter Airport"),
    "Kelsterbach": ("letiště Frankfurt", "Frankfurt Airport"),
    "Otopeni": ("Otopeni (letiště)", "Otopeni (airport)"),
    "Laerdalsoyri": ("Lærdalsøyri", "Lærdalsøyri"), "Rodberg": ("Rødberg", "Rødberg"),
    "Amot": ("Åmot", "Åmot"), "Hokksund": ("Hokksund", "Hokksund"),
    "Bucharest": ("Bukurešť", "Bucharest"), "Bucuresti": ("Bukurešť", "Bucharest"),
    "Brasov": ("Brašov", "Brașov"), "Constanta": ("Konstanca", "Constanța"),
    "Busteni": ("Bușteni", "Bușteni"), "Ploiesti": ("Ploješť", "Ploiești"),
    "Napoli": ("Neapol", "Naples"), "Tias": ("Tías", "Tías"), "Haria": ("Haría", "Haría"),
    "Sjolyststranda": ("Oslo", "Oslo"), "Aurlandsvangen": ("Aurland", "Aurland"),
}

T = {
    "cs": {
        "titul": "Cestovatelský deník", "podtitul": "Větší rodinné cesty: kudy jsme jeli, co jsme viděli a co bychom doporučili dalším.",
        "cest": "cest", "zemi": "zemí", "dni_na_cestach": "dní na cestách", "km": "km",
        "den": "Den", "dni": "dní", "nocleh": "Nocleh", "jazyk": "English", "jazyk_kod": "en",
        "vsechny_cesty": "Všechny cesty", "den_po_dni": "Den po dni", "tipy": "Tipy pro cestovatele",
        "ukazat": "Ukázat na mapě", "cela_trasa": "Celá trasa", "predchozi": "Předchozí cesta", "dalsi": "Další cesta",
        "zavrit": "Zavřít",
        "foto_chybi": "Fotky z tohoto dne doplníme", "km_celkem": "km celkem", "navstivili": "Kudy",
        "mody": {"let": "letadlem", "auto": "autem", "autobus": "autobusem", "vlak": "vlakem",
                 "metro": "metrem", "tramvaj": "tramvají", "lod": "lodí", "pesky": "pěšky",
                 "kolo": "na kole", "pobyt": "na místě", "jine": "jinak"},
        "mesice": ["ledna", "února", "března", "dubna", "května", "června", "července",
                   "srpna", "září", "října", "listopadu", "prosince"],
        "dny_tydne": ["pondělí", "úterý", "středa", "čtvrtek", "pátek", "sobota", "neděle"],
        "paticka": "Rodinný cestovatelský deník. Mapové podklady © přispěvatelé OpenStreetMap, hranice Natural Earth.",
        "ukazka": "Náhled k odsouhlasení: texty napsal Claude z trasy a fotek, nejsou zatím zkontrolované.",
    },
    "en": {
        "titul": "Travel Journal", "podtitul": "Our bigger family trips: where we went, what we saw and what we would recommend.",
        "cest": "trips", "zemi": "countries", "dni_na_cestach": "days on the road", "km": "km",
        "den": "Day", "dni": "days", "nocleh": "Overnight", "jazyk": "Česky", "jazyk_kod": "cs",
        "vsechny_cesty": "All trips", "den_po_dni": "Day by day", "tipy": "Tips for travellers",
        "ukazat": "Show on map", "cela_trasa": "Whole route", "predchozi": "Previous trip", "dalsi": "Next trip",
        "zavrit": "Close",
        "foto_chybi": "Photos from this day coming soon", "km_celkem": "km in total", "navstivili": "Route",
        "mody": {"let": "by plane", "auto": "by car", "autobus": "by bus", "vlak": "by train",
                 "metro": "by metro", "tramvaj": "by tram", "lod": "by boat", "pesky": "on foot",
                 "kolo": "by bike", "pobyt": "on site", "jine": "other"},
        "mesice": ["January", "February", "March", "April", "May", "June", "July",
                   "August", "September", "October", "November", "December"],
        "dny_tydne": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
        "paticka": "A family travel journal. Map data © OpenStreetMap contributors, borders by Natural Earth.",
        "ukazka": "Preview for review: texts were written by Claude from the route and photos and have not been checked yet.",
    },
}


def nazev(m, lang):
    if not m:
        return None
    return NAZVY.get(m, (m, m))[0 if lang == "cs" else 1]


def rozsah(od, do, lang):
    a, b = date.fromisoformat(od), date.fromisoformat(do)
    m = T[lang]["mesice"]
    if lang == "cs":
        if a.month == b.month:
            return f"{a.day}.–{b.day}. {m[b.month-1]} {b.year}"
        return f"{a.day}. {m[a.month-1]} – {b.day}. {m[b.month-1]} {b.year}"
    if a.month == b.month:
        return f"{m[a.month-1]} {a.day}–{b.day}, {b.year}"
    return f"{m[a.month-1]} {a.day} – {m[b.month-1]} {b.day}, {b.year}"


def den_nazev(d, lang):
    x = date.fromisoformat(d)
    t = T[lang]
    if lang == "cs":
        return f"{t['dny_tydne'][x.weekday()]} {x.day}. {t['mesice'][x.month-1]}"
    return f"{t['dny_tydne'][x.weekday()]}, {t['mesice'][x.month-1]} {x.day}"


def cislo(n, lang):
    s = f"{n:,}"
    return s.replace(",", " ") if lang == "cs" else s


def nacti(slug, adresar):
    f = SITE / adresar / f"{slug}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def mista_dne(den, lang):
    out = []
    for m in den["mista"]:
        n = nazev(m["misto"], lang)
        if n and n not in out:
            out.append(n)
    return out


def bez_obalu(html):
    """Pro náhled v Claude: obal <html>/<head>/<body> doplní hostitel sám."""
    import re
    html = re.sub(r"<!doctype html>\s*", "", html, flags=re.I)
    html = re.sub(r"</?(html|head|body)(\s[^>]*)?>", "", html, flags=re.I)
    return html


def main():
    nahled = "--nahled" in sys.argv
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(SITE / "static", OUT / "static")
    if (SITE / "foto").exists():
        shutil.copytree(SITE / "foto", OUT / "foto")

    env = Environment(loader=FileSystemLoader(SITE / "templates"), autoescape=select_autoescape(["html"]))
    env.filters["cislo"] = cislo
    cesty = [json.loads(f.read_text(encoding="utf-8")) for f in sorted((SITE / "data" / "cesty").glob("*.json"))]
    cesty.sort(key=lambda c: c["od"], reverse=True)

    for lang in ("cs", "en"):
        t = T[lang]
        pre = "" if lang == "cs" else "en/"       # podsložka jazyka
        karty = []
        for c in cesty:
            obsah = nacti(c["slug"], "obsah").get(lang, {})
            fotky = nacti(c["slug"], "fotky").get("fotky", [])
            titulni = next((f for f in fotky if f.get("titulni")), fotky[0] if fotky else None)
            karty.append({
                "c": c, "slug": c["slug"], "nazev": c["nazev"][lang], "obsah": obsah, "fotky": fotky,
                "rozsah": rozsah(c["od"], c["do"], lang), "dni": len(c["dny"]),
                "km": sum(c["km"].values()), "zeme": [z[lang] for z in c.get("zeme", [])],
                "titulni": titulni, "url": f"cesty/{c['slug']}/index.html",
            })
        zeme_vse = {z["cs"] for c in cesty for z in c.get("zeme", [])}
        souhrn = {"cest": len(cesty), "zemi": len(zeme_vse),
                  "dni": sum(len(c["dny"]) for c in cesty), "km": sum(sum(c["km"].values()) for c in cesty)}
        root = "" if lang == "cs" else "../"
        jazyk_url = ("en/index.html" if lang == "cs" else "../index.html")
        mapa = [{"slug": k["slug"], "nazev": k["nazev"], "rozsah": k["rozsah"], "url": k["url"],
                 "trasa": [{"mode": l["mode"], "body": l["body"]} for l in k["c"]["trasa"]]} for k in karty]
        html = env.get_template("index.html").render(
            t=t, lang=lang, karty=karty, souhrn=souhrn, root=root, jazyk_url=jazyk_url,
            nahled=nahled, mapa_json=json.dumps(mapa, ensure_ascii=False))
        (OUT / pre).mkdir(parents=True, exist_ok=True)
        if nahled and lang == "cs":
            html = bez_obalu(html)
        (OUT / pre / "index.html").write_text(html, encoding="utf-8")

        for i, k in enumerate(karty):
            c = k["c"]
            d = OUT / pre / "cesty" / c["slug"]
            d.mkdir(parents=True, exist_ok=True)
            texty = k["obsah"].get("dny", {})
            dny = []
            for n, den in enumerate(c["dny"], 1):
                fotky_dne = [f for f in k["fotky"] if f["datum"] == den["datum"]]
                if len(fotky_dne) % 2 == 0 and fotky_dne:
                    # šablona počítá s lichým počtem (1 velká + dvojice malých)
                    print(f"  pozor: {c['slug']} {den['datum']} má sudý počet fotek, poslední vynechávám")
                    fotky_dne = fotky_dne[:-1]
                dny.append({
                    "cislo": n, "datum": den["datum"], "nazev": den_nazev(den["datum"], lang),
                    "text": texty.get(den["datum"], ""), "cil": k["obsah"].get("cile", {}).get(den["datum"], ""), "mista": mista_dne(den, lang),
                    "nocleh": dict(den["nocleh"], nazev=nazev(den["nocleh"]["misto"], lang)) if den["nocleh"] else None,
                    "km": den.get("km", {}), "fotky": fotky_dne,
                })
            noclehy, posledni = [], None
            for x in dny:
                if x["nocleh"] and x["nocleh"]["nazev"] != posledni:
                    noclehy.append({"nazev": x["nocleh"]["nazev"], "p": x["nocleh"]["p"], "den": x["cislo"]})
                    posledni = x["nocleh"]["nazev"]
            r = "../../" + root
            data = {
                "trasa": c["trasa"], "bbox": c["bbox"], "noclehy": noclehy,
                "dny": [{"cislo": x["cislo"], "datum": x["datum"]} for x in dny],
                "fotky": [{"src": r + f["nahled"], "p": f["p"], "popis": f["popis"].get(lang, ""), "datum": f["datum"]}
                          for f in k["fotky"] if f.get("p")],
            }
            mody = [(m, c["km"][m]) for m in MODY if m in c["km"]]
            html = env.get_template("cesta.html").render(
                t=t, lang=lang, k=k, dny=dny, root=r, mody=mody, noclehy=noclehy, nahled=nahled,
                predchozi=karty[i + 1] if i + 1 < len(karty) else None,
                dalsi=karty[i - 1] if i > 0 else None,
                jazyk_url=("../../en/" if lang == "cs" else "../../../") + f"cesty/{c['slug']}/index.html",
                mapa_json=json.dumps(data, ensure_ascii=False))
            (d / "index.html").write_text(html, encoding="utf-8")
    (OUT / ".nojekyll").write_text("")
    print(f"Web vygenerován do {OUT} ({len(cesty)} cest){' – náhled' if nahled else ''}")


if __name__ == "__main__":
    main()

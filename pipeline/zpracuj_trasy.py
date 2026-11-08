#!/usr/bin/env python3
"""
Z výřezů časové osy (data/casova-osa/*.json, soukromé) vytvoří veřejná data
cest (site/data/cesty/<slug>.json).

Ochrana soukromí:
  - body blíž než DOMOV_KM (25 km) od domova se zahodí (domov = místa typu HOME),
  - souřadnice se zaokrouhlí na 4 desetinná místa (~10 m),
  - surové signály (Wi-Fi apod.) a ID míst se nepřenášejí.
"""
import json
import math
from datetime import datetime, timedelta, date
from pathlib import Path

from geokod import nejblizsi

ROOT = Path(__file__).resolve().parent.parent
VSTUP = ROOT / "data" / "casova-osa"
VYSTUP = ROOT / "site" / "data" / "cesty"
DOMOV_KM = 25.0

MODE_MAP = {
    "FLYING": "let", "IN_PASSENGER_VEHICLE": "auto", "IN_VEHICLE": "auto",
    "IN_BUS": "autobus", "IN_TRAIN": "vlak", "IN_SUBWAY": "metro",
    "IN_TRAM": "tramvaj", "IN_FERRY": "lod", "WALKING": "pesky",
    "RUNNING": "pesky", "CYCLING": "kolo", "MOTORCYCLING": "auto",
}


def t(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)


def ll(s):
    a, b = s.replace("°", "").split(",")
    return float(a), float(b)


def km(p, q):
    la1, lo1, la2, lo2 = map(math.radians, (*p, *q))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def great_circle(p, q, n=40):
    la1, lo1, la2, lo2 = map(math.radians, (*p, *q))
    d = 2 * math.asin(math.sqrt(math.sin((la2 - la1) / 2) ** 2
                                + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2))
    if d == 0:
        return [p, q]
    out = []
    for i in range(n + 1):
        f = i / n
        a = math.sin((1 - f) * d) / math.sin(d)
        b = math.sin(f * d) / math.sin(d)
        x = a * math.cos(la1) * math.cos(lo1) + b * math.cos(la2) * math.cos(lo2)
        y = a * math.cos(la1) * math.sin(lo1) + b * math.cos(la2) * math.sin(lo2)
        z = a * math.sin(la1) + b * math.sin(la2)
        out.append((math.degrees(math.atan2(z, math.hypot(x, y))), math.degrees(math.atan2(y, x))))
    return out


def r(p):
    return [round(p[0], 4), round(p[1], 4)]


def zpracuj(cesta):
    segs = json.loads((VSTUP / cesta["casova_osa"]).read_text(encoding="utf-8"))["semanticSegments"]
    homes = {ll(s["visit"]["topCandidate"]["placeLocation"]["latLng"]) for s in segs
             if s.get("visit", {}).get("topCandidate", {}).get("semanticType") == "HOME"}

    def u_domova(p):
        return any(km(p, h) < DOMOV_KM for h in homes)

    od = datetime.combine(date.fromisoformat(cesta["od"]), datetime.min.time())
    do = datetime.combine(date.fromisoformat(cesta["do"]) + timedelta(days=1), datetime.min.time())

    def v_rozsahu(a, b):
        return a < do and b > od

    activities, visits, points = [], [], []
    for s in segs:
        a, b = t(s["startTime"]), t(s["endTime"])
        if not v_rozsahu(a, b):
            continue
        if "activity" in s:
            ac = s["activity"]
            typ = ac.get("topCandidate", {}).get("type", "UNKNOWN")
            activities.append({
                "od": a, "do": b, "mode": MODE_MAP.get(typ, "jine"),
                "start": ll(ac["start"]["latLng"]), "end": ll(ac["end"]["latLng"]),
                "km": ac.get("distanceMeters", 0) / 1000,
            })
        elif "visit" in s:
            c = s["visit"].get("topCandidate", {})
            p = ll(c["placeLocation"]["latLng"])
            if c.get("semanticType") == "HOME" or u_domova(p):
                continue
            visits.append({"od": a, "do": b, "p": p})
        for tp in s.get("timelinePath", []):
            tt = t(tp["time"])
            if od <= tt < do:
                points.append((tt, ll(tp["point"])))
    points.sort()
    activities.sort(key=lambda x: x["od"])

    def mode_at(tt):
        for ac in activities:
            if ac["od"] <= tt <= ac["do"]:
                return ac["mode"]
        return None

    # trasa: úseky podle způsobu dopravy; lety jako oblouky
    legs = []
    for ac in activities:
        if ac["mode"] == "let":
            legs.append({"mode": "let", "od": ac["od"],
                         "body": [p for p in great_circle(ac["start"], ac["end"]) if not u_domova(p)]})
    cur = None
    for tt, p in points:
        if u_domova(p):
            cur = None
            continue
        m = mode_at(tt) or "pobyt"
        if m == "let":
            cur = None
            continue
        if cur and (cur["mode"] != m or km(cur["body"][-1], p) > 300):
            cur["body"].append(p) if km(cur["body"][-1], p) <= 300 else None
            legs.append(cur)
            cur = None
        if not cur:
            cur = {"mode": m, "od": tt, "body": []}
        cur["body"].append(p)
    if cur:
        legs.append(cur)
    legs = [l for l in legs if len(l["body"]) >= 2]
    legs.sort(key=lambda l: l["od"])

    # statistiky (bez úseků u domova)
    stats = {}
    for ac in activities:
        if u_domova(ac["start"]) and u_domova(ac["end"]):
            continue
        stats[ac["mode"]] = stats.get(ac["mode"], 0) + ac["km"]

    # dny: navštívená místa a nocleh
    dny = []
    d = od
    while d < do:
        d2 = d + timedelta(days=1)
        vd = [v for v in visits if v["od"] < d2 and v["do"] > d]
        noc = [v for v in visits if v["od"] <= d + timedelta(hours=27) and v["do"] >= d + timedelta(hours=26)]
        mista = []
        for v in vd:
            dur = (min(v["do"], d2) - max(v["od"], d)).total_seconds() / 60
            if dur >= 15:
                g = nejblizsi(*v["p"])
                mista.append({"p": r(v["p"]), "od": max(v["od"], d).strftime("%H:%M"),
                              "minut": round(dur), "misto": g["mesto"], "cc": g["cc"]})
        nocleh = None
        if noc:
            g = nejblizsi(*noc[0]["p"])
            nocleh = {"p": r(noc[0]["p"]), "misto": g["mesto"], "region": g["region"], "cc": g["cc"]}
        km_den = {}
        for ac in activities:
            if d <= ac["od"] < d2 and not (u_domova(ac["start"]) and u_domova(ac["end"])):
                km_den[ac["mode"]] = km_den.get(ac["mode"], 0) + ac["km"]
        dny.append({"datum": d.date().isoformat(), "mista": mista, "nocleh": nocleh,
                    "km": {k: round(v) for k, v in sorted(km_den.items(), key=lambda x: -x[1]) if v >= 1}})
        d = d2

    vsechny = [p for l in legs for p in l["body"]] + [v["p"] for v in visits]
    lat = [p[0] for p in vsechny]
    lon = [p[1] for p in vsechny]
    # země: kde se nocovalo, nebo kde se strávily aspoň dva dny (přestup na letišti se nepočítá)
    dny_v_zemi = {}
    for den in dny:
        for cc in {m["cc"] for m in den["mista"]}:
            dny_v_zemi[cc] = dny_v_zemi.get(cc, 0) + 1
    noc_zeme = {den["nocleh"]["cc"] for den in dny if den["nocleh"]}
    zeme = {}
    for v in visits:
        g = nejblizsi(*v["p"])
        if g["cc"] not in zeme and (g["cc"] in noc_zeme or dny_v_zemi.get(g["cc"], 0) >= 2):
            zeme[g["cc"]] = g["zeme"]
    return {
        "zeme": list(zeme.values()),
        "slug": cesta["slug"], "nazev": cesta["nazev"],
        "od": cesta["od"], "do": cesta["do"],
        "bbox": [[round(min(lat), 3), round(min(lon), 3)], [round(max(lat), 3), round(max(lon), 3)]],
        "km": {k: round(v) for k, v in sorted(stats.items(), key=lambda x: -x[1]) if v >= 1},
        "trasa": [{"mode": l["mode"], "datum": l["od"].date().isoformat(), "body": [r(p) for p in l["body"]]} for l in legs],
        "dny": dny,
    }


def main():
    VYSTUP.mkdir(parents=True, exist_ok=True)
    cesty = json.loads((ROOT / "cesty.json").read_text(encoding="utf-8"))
    for c in cesty:
        out = zpracuj(c)
        (VYSTUP / f"{c['slug']}.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
        print(f"{c['slug']}: {len(out['trasa'])} úseků, {sum(len(d['mista']) for d in out['dny'])} míst, km {out['km']}")


if __name__ == "__main__":
    main()

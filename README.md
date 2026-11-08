# Cestovatelský deník

Statický web s rodinnými cestami: trasa z časové osy Google Maps, vybrané fotky bez lidí z Google Takeoutu a krátké texty česky i anglicky. Dvě šablony (Časopis a Průvodce), mezi kterými přepíná návštěvník.

## Jak web vzniká

1. `pipeline/zpracuj_trasy.py` – z výřezů časové osy v `data/casova-osa/` (soukromé, mimo repozitář) vytvoří `site/data/cesty/*.json`. Vše do 25 km od domova se zahodí.
2. `pipeline/zpracuj_fotky.py` – z fotek v `data/fotky/<cesta>/` podle výběru `site/vyber/<cesta>.json` připraví zmenšené fotky bez EXIF do `site/foto/` a jejich seznam do `site/fotky/`.
3. Texty jsou v `site/obsah/<cesta>.json`.
4. `pipeline/postav_web.py` – vygeneruje web do `public/`.

Seznam cest a jejich termíny jsou v `cesty.json`.

```
pip install -r requirements.txt
python pipeline/zpracuj_trasy.py
python pipeline/zpracuj_fotky.py
python pipeline/postav_web.py
```

Mapa používá OpenStreetMap (Leaflet) a pod ní hranice států z Natural Earth (`site/static/svet.json`). Názvy míst určuje offline `pipeline/geokod.py` z dat GeoNames.

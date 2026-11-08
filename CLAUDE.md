# Pokyny pro Claude

- Komunikace s autorem česky. Autor neprogramuje a kód nekontroluje: změny vysvětluj výsledkem, ne kódem.
- Do repozitáře nikdy nepatří soukromá data: celý export časové osy, originály fotek, fotky s lidmi, poloha domova (vše do 25 km od domova se ořezává). Složka `data/` je v `.gitignore`.
- Na web jdou jen fotky bez lidí (ani rodina, ani cizí lidé v popředí). Výběr je v `site/vyber/<cesta>.json` a vždy ho schvaluje autor.
- Texty (`site/obsah/`) píše Claude česky i anglicky: odstavec o 4–6 větách na den, jednovětý popisek u fotky, neosobním stylem („zastávka u vodopádu“, ne „zastavili jsme“), klidně delší, bez jmen a osobních údajů. Nic nevymýšlet nad rámec trasy a fotek.
- Cesta se zveřejňuje až po návratu a po schválení náhledu autorem.
- Jediná šablona je Časopis. Každý den má lichý počet fotek (1 velká + dvojice malých), generátor sudý počet zkrátí.

/* Cestovatelský deník: mapy a prohlížeč fotek */
(function () {
  var D = window.DENIK || { root: "", mody: {} };
  var html = document.documentElement;

  /* --- barvy z CSS proměnných (reagují na tmavý režim) --- */
  function barva(mode) {
    return getComputedStyle(html).getPropertyValue("--m-" + mode).trim() || "#888";
  }
  function token(n) { return getComputedStyle(html).getPropertyValue(n).trim(); }

  /* --- podkladová mapa: OSM dlaždice + vektorové hranice jako záloha --- */
  function podklad(id) {
    var map = L.map(id, { scrollWheelZoom: false, zoomSnap: 0.25, attributionControl: true }).setView([50, 10], 4);
    var svet = L.layerGroup().addTo(map);
    fetch(D.root + "static/svet.json").then(function (r) { return r.json(); }).then(function (topo) {
      var geo = topojson.feature(topo, topo.objects.countries);
      L.geoJSON(geo, {
        interactive: false,
        style: function () { return { color: token("--linka"), weight: 1, fillColor: token("--plocha"), fillOpacity: 1 }; }
      }).addTo(svet);
      svet.eachLayer(function (l) { l.bringToBack && l.bringToBack(); });
    }).catch(function () {});
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18, attribution: "© OpenStreetMap", className: "dlazdice"
    }).addTo(map);
    return map;
  }

  function cara(l, opt) {
    var let_ = l.mode === "let";
    return L.polyline(l.body, Object.assign({
      color: barva(l.mode),
      weight: let_ ? 2 : (l.mode === "pesky" || l.mode === "pobyt" ? 2 : 3.5),
      opacity: l.mode === "pobyt" ? 0.5 : 0.95,
      dashArray: let_ ? "6 7" : null,
      lineJoin: "round"
    }, opt || {}));
  }

  function prepocitej(map, fn) {
    window.addEventListener("resize", function () { map.invalidateSize(); });
  }

  /* --- úvodní mapa všech cest --- */
  function prehled(id, cesty) {
    var el = document.getElementById(id);
    if (!el || !window.L) return;
    var map = podklad(id), vse = L.featureGroup().addTo(map);
    cesty.forEach(function (c) {
      var g = L.featureGroup();
      c.trasa.forEach(function (l) { if (l.mode !== "pobyt") cara(l).addTo(g); });
      g.bindTooltip("<b>" + c.nazev + "</b><br>" + c.rozsah, { sticky: true });
      g.on("mouseover", function () { g.eachLayer(function (x) { x.setStyle({ weight: 6 }); }); });
      g.on("mouseout", function () { g.eachLayer(function (x) { x.setStyle({ weight: x.options.dashArray ? 2 : 3.5 }); }); });
      g.on("click", function () { location.href = c.url; });
      g.addTo(vse);
      kreslitNahled(c);
    });
    var fit = function () { map.fitBounds(vse.getBounds(), { padding: [24, 24] }); };
    fit(); prepocitej(map, fit);
  }

  /* malá kresba trasy na kartě, když cesta ještě nemá fotku */
  function kreslitNahled(c) {
    var svg = document.querySelector('[data-nahled-trasy="' + c.slug + '"]');
    if (!svg) return;
    var body = [];
    c.trasa.forEach(function (l) { if (l.mode !== "let" && l.mode !== "pobyt") body = body.concat(l.body); });
    if (!body.length) c.trasa.forEach(function (l) { body = body.concat(l.body); });
    var la = body.map(function (p) { return p[0]; }), lo = body.map(function (p) { return p[1]; });
    var minA = Math.min.apply(0, la), maxA = Math.max.apply(0, la), minO = Math.min.apply(0, lo), maxO = Math.max.apply(0, lo);
    var k = Math.cos((minA + maxA) / 2 * Math.PI / 180);
    var w = (maxO - minO) * k || 0.01, h = (maxA - minA) || 0.01, s = Math.min(260 / w, 160 / h);
    var ox = 150 - w * s / 2, oy = 100 - h * s / 2, out = "";
    c.trasa.forEach(function (l) {
      if (l.mode === "let" || l.mode === "pobyt") return;
      var d = l.body.map(function (p, i) { return (i ? "L" : "M") + (ox + (p[1] - minO) * k * s).toFixed(1) + " " + (oy + (maxA - p[0]) * s).toFixed(1); }).join("");
      out += '<path d="' + d + '" fill="none" stroke="' + barva(l.mode) + '" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>';
    });
    svg.innerHTML = out;
  }

  /* --- mapa jedné cesty --- */
  function cesta(id, data) {
    var el = document.getElementById(id);
    if (!el || !window.L) return;
    var map = podklad(id), trasa = L.featureGroup().addTo(map), poDnech = {};
    data.trasa.forEach(function (l) {
      var c = cara(l).addTo(trasa);
      (poDnech[l.datum] = poDnech[l.datum] || []).push(c);
    });
    data.noclehy.forEach(function (n, i) {
      L.marker(n.p, {
        icon: L.divIcon({ className: "", html: '<div class="noc-znacka">' + (i + 1) + "</div>", iconSize: [26, 26], iconAnchor: [13, 13] }),
        title: n.nazev
      }).bindTooltip(n.nazev, { direction: "top", offset: [0, -12] }).addTo(map);
    });
    data.fotky.forEach(function (f) {
      L.circleMarker(f.p, { radius: 4, color: token("--plocha"), weight: 1.5, fillColor: token("--inkoust"), fillOpacity: 0.8 })
        .bindPopup('<img src="' + f.src + '" alt="" style="width:200px;border-radius:6px"><div style="margin-top:6px;max-width:200px">' + f.popis + "</div>", { maxWidth: 220 })
        .addTo(map);
    });
    var bezLetu = L.featureGroup(data.trasa.filter(function (l) { return l.mode !== "let"; }).map(function (l) { return L.polyline(l.body); }));
    function cela() { map.fitBounds((bezLetu.getLayers().length ? bezLetu : trasa).getBounds(), { padding: [28, 28] }); zvyrazni(null); }
    function zvyrazni(datum) {
      trasa.eachLayer(function (x) { x.setStyle({ opacity: datum ? 0.25 : 0.95 }); });
      if (datum && poDnech[datum]) poDnech[datum].forEach(function (x) { x.setStyle({ opacity: 1 }); x.bringToFront(); });
      document.querySelectorAll(".den").forEach(function (d) { d.classList.toggle("aktivni", d.getAttribute("data-datum") === datum); });
    }
    function den(datum) {
      var vrstvy = (poDnech[datum] || []).filter(function (x) { return !x.options.dashArray; });
      if (!vrstvy.length) vrstvy = poDnech[datum] || [];
      if (!vrstvy.length) return;
      map.fitBounds(L.featureGroup(vrstvy).getBounds(), { padding: [36, 36], maxZoom: 13 });
      zvyrazni(datum);
    }
    cela();
    prepocitej(map, cela);
  }

  /* --- prohlížeč fotek --- */
  document.addEventListener("click", function (e) {
    var a = e.target.closest && e.target.closest("[data-velke]");
    if (!a) return;
    e.preventDefault();
    var box = document.createElement("div");
    box.className = "lightbox";
    box.setAttribute("role", "dialog");
    box.innerHTML = '<img alt=""><p></p><button type="button">' + (D.zavrit || "×") + "</button>";
    box.querySelector("img").src = a.getAttribute("data-velke");
    box.querySelector("img").alt = a.getAttribute("data-popis") || "";
    box.querySelector("p").textContent = a.getAttribute("data-popis") || "";
    function zavri() { box.remove(); document.removeEventListener("keydown", klav); }
    function klav(ev) { if (ev.key === "Escape") zavri(); }
    box.addEventListener("click", function (ev) { if (ev.target !== box.querySelector("img")) zavri(); });
    document.addEventListener("keydown", klav);
    document.body.appendChild(box);
    box.querySelector("button").focus();
  });

  window.DenikMapa = { prehled: prehled, cesta: cesta };
})();

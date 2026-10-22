import pathlib

h = pathlib.Path("client/index.html")
s = h.read_text(encoding="utf-8")

s = s.replace('''        <strong>Координатная сетка</strong><em>через 10° / 5°</em></span>
      </label>''', '''        <strong>Координатная сетка</strong><em>через 10° / 5°</em></span>
      </label>
      <label class="switch">
        <input type="checkbox" id="phaseToggle">
        <span class="switch__ui"></span>
        <span class="switch__text"><strong>Фаза: снег</strong><em>по T₂ₘ GFS</em></span>
      </label>''')

s = s.replace('''          <div><dt>Источник</dt><dd id="probeStation">IMERG</dd></div>''', '''          <div><dt>Температура</dt><dd id="probeTemp">—</dd></div>
          <div><dt>CAPE · сдвиг</dt><dd id="probeEnv">—</dd></div>
          <div><dt>Источник</dt><dd id="probeStation">IMERG</dd></div>''')

s = s.replace('''<div class="hud__item"><span class="hud__label">эхо</span><b id="hudEcho">—</b></div>''', '''<div class="hud__item"><span class="hud__label">эхо</span><b id="hudEcho">—</b></div>
      <div class="hud__item"><span class="hud__label">ячейки</span><b id="hudCells">—</b></div>''')

s = s.replace('''    <p>Нужны полярные объёмы по углам места (ДМРЛ или GPM DPR). IMERG даёт только приземную интенсивность, поэтому вертикаль честно недоступна.</p>
  </div>''', '''    <p>Нужны полярные объёмы по углам места (ДМРЛ или GPM DPR). IMERG даёт только приземную интенсивность, поэтому вертикаль честно недоступна.</p>
  </div>

  <div class="mode mode--off">
    <div class="mode__top"><strong>Мезоциклон</strong><span class="tag tag--off">нет доплера</span></div>
    <p>Вращение определяется по радиальной скорости и её сдвигу — для этого нужен доплеровский радар. Вместо этого сайт считает прокси опасной грозы: ячейки ≥50 дБЗ, CAPE и сдвиг 0–6 км; это условие, а не обнаружение мезоциклона.</p>
  </div>''')

h.write_text(s, encoding="utf-8")

a = pathlib.Path("client/app.js")
j = a.read_text(encoding="utf-8")

insert = '''  /* ---------- environment, phase, storm cells ---------- */
  const ENV = DATA.env || null;
  function sampleEnv(key, lat, lon) {
    if (!ENV || !ENV[key]) return NaN;
    const fx = (lon - ENV.lon0) / ENV.step;
    const fy = (lat - ENV.lat0) / ENV.step;
    const x0 = Math.floor(fx), y0 = Math.floor(fy);
    if (x0 < 0 || y0 < 0 || x0 >= ENV.nx - 1 || y0 >= ENV.ny - 1) return NaN;
    const i = y0 * ENV.nx + x0;
    return (ENV[key][i] + ENV[key][i + 1] + ENV[key][i + ENV.nx] + ENV[key][i + ENV.nx + 1]) / 4;
  }

  let phaseOverlay = null;
  function renderPhase() {
    if (!P.phase) return;
    const frame = FRAMES[state.index];
    const mask = P.phase[frame.id];
    const canvas = document.createElement("canvas");
    canvas.width = P.nx;
    canvas.height = P.ny;
    const ctx = canvas.getContext("2d");
    const img = ctx.createImageData(P.nx, P.ny);
    if (mask) {
      for (let i = 0; i < mask.length; i++) {
        if (!mask[i]) continue;
        const o = i * 4;
        img.data[o] = 150;
        img.data[o + 1] = 220;
        img.data[o + 2] = 255;
        img.data[o + 3] = 120;
      }
    }
    ctx.putImageData(img, 0, 0);
    const url = canvas.toDataURL();
    if (!phaseOverlay) {
      phaseOverlay = L.imageOverlay(url, [[54, 104], [74, 166]], { opacity: 0.6, interactive: false }).addTo(map);
    } else {
      phaseOverlay.setUrl(url);
    }
  }

  const cellsLayer = L.layerGroup().addTo(map);
  function renderCells() {
    cellsLayer.clearLayers();
    const cells = FRAMES[state.index].cells || [];
    cells.forEach((c) => {
      L.circleMarker([c.lat, c.lon], {
        radius: 6, color: "#ff2d55", weight: 1.6, fillColor: "#ff2d55", fillOpacity: 0.28
      }).bindTooltip(c.max_dbz + " дБЗ · " + c.area_km2 + " км²").addTo(cellsLayer);
    });
    el("hudCells").textContent = cells.length;
  }

  el("phaseToggle").addEventListener("change", (e) => {
    if (e.target.checked) renderPhase();
    else if (phaseOverlay) map.removeLayer(phaseOverlay), (phaseOverlay = null);
  });

'''
j = j.replace("  /* ---------- mobile sheet ---------- */", insert + "  /* ---------- mobile sheet ---------- */")

j = j.replace('''    updateHud(f);''', '''    updateHud(f);
    renderCells();
    if (el("phaseToggle").checked) renderPhase();''')

j = j.replace('''    el("probeStation").textContent = M.source && M.source.provider ? M.source.provider : "IMERG";''', '''    el("probeStation").textContent = M.source && M.source.provider ? M.source.provider : "IMERG";
    const t = sampleEnv("t2m", lat, lon);
    const cape = sampleEnv("cape", lat, lon);
    const shear = sampleEnv("shear", lat, lon);
    el("probeTemp").textContent = Number.isFinite(t)
      ? Math.round(t * 10) / 10 + " °C · " + (t <= 0.5 ? "снег" : t < 2 ? "смешанные" : "дождь")
      : "—";
    el("probeEnv").textContent = Number.isFinite(cape) ? Math.round(cape) + " Дж/кг · " + (Number.isFinite(shear) ? Math.round(shear) : "—") + " м/с" : "—";''')

a.write_text(j, encoding="utf-8")
print("html", "phaseToggle" in s, "probeTemp" in s, "Мезоциклон" in s)
print("js", "sampleEnv" in j, "renderCells" in j)

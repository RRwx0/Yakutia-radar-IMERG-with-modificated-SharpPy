(() => {
  "use strict";

  const DATA = window.RADAR_STATE;
  if (!DATA) return;
  const API = (window.API_BASE || "").replace(/\/$/, "");

  let M = DATA.manifest;
  let FRAMES = M.frames;
  let OBS_N = FRAMES.filter((f) => f.kind === "obs").length;
  const P = DATA.probe;
  const TZ = "Asia/Yakutsk";
  const IS_FILE = location.protocol === "file:";

  const STOPS = [
    [5, "#c9f2e5"], [8, "#9fdbe0"], [12, "#7cc4d8"], [16, "#5da8c6"],
    [20, "#7fc98f"], [25, "#8fc874"], [30, "#c9d66b"], [35, "#e8d15a"],
    [40, "#e8a84c"], [45, "#e07a52"], [50, "#d5605a"], [55, "#b44a6d"],
    [60, "#9450a6"], [65, "#6f4f9e"], [70, "#503e8e"]
  ];

  const CLASSES = [
    [10, "следы", "#9fdbe0"], [15, "слабые", "#7cc4d8"], [20, "небольшие", "#5da8c6"],
    [25, "умеренные", "#7fc98f"], [30, "умеренный дождь", "#c9d66b"], [35, "сильные", "#e8d15a"],
    [40, "очень сильные", "#e8a84c"], [45, "ливневые", "#e07a52"], [50, "гроза/град", "#d5605a"],
    [1e9, "экстремальные", "#6f4f9e"]
  ];

  const CITIES = [
    ["Якутск", 62.0355, 129.6755, true], ["Олёкминск", 60.3747, 120.4211, true],
    ["Мирный", 62.5353, 113.9611, true], ["Нерюнгри", 56.6584, 124.7250, true],
    ["Ленск", 60.7253, 114.9277, false], ["Алдан", 58.6031, 125.3894, false],
    ["Тикси", 71.6390, 128.8694, false], ["Верхоянск", 67.5539, 133.3898, false],
    ["Усть-Нера", 64.5665, 143.2370, false], ["Оймякон", 63.4629, 142.7906, false],
    ["Среднеколымск", 67.4570, 153.7107, false], ["Черский", 68.7530, 161.3310, false],
    ["Вилюйск", 63.7517, 121.6241, false], ["Нюрба", 63.2842, 118.3313, false],
    ["Батагай", 67.6560, 134.6400, false], ["Жиганск", 66.7664, 123.3711, false]
  ];

  const state = { index: OBS_N - 1, timer: null, speed: 900, point: null, seq: 0, mode: "live", autoResume: false };

  const el = (id) => document.getElementById(id);
  const timeFmt = new Intl.DateTimeFormat("ru-RU", { timeZone: TZ, hour: "2-digit", minute: "2-digit", hour12: false });
  const dateFmt = new Intl.DateTimeFormat("ru-RU", { timeZone: TZ, day: "numeric", month: "long" });
  const fullFmt = new Intl.DateTimeFormat("ru-RU", { timeZone: TZ, day: "2-digit", month: "2-digit", year: "numeric" });
  const clockFmt = new Intl.DateTimeFormat("ru-RU", { timeZone: TZ, hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });

  const fmtTime = (iso) => timeFmt.format(new Date(iso));
  const fmtDate = (iso) => dateFmt.format(new Date(iso));

  /* ---------- map ---------- */
  const map = L.map("map", {
    zoomControl: false, minZoom: 3, maxZoom: 6, zoomSnap: 1,
    attributionControl: true, preferCanvas: true
  });
  map.createPane("radarGlow").style.zIndex = 290;
  map.createPane("radar").style.zIndex = 300;
  map.createPane("grid").style.zIndex = 410;
  map.createPane("border").style.zIndex = 420;
  map.createPane("places").style.zIndex = 450;

  const base = L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png", {
    subdomains: "abcd", maxZoom: 6, attribution: "© OpenStreetMap, © CARTO", opacity: 0.92
  }).addTo(map);

  L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Elevation/World_Hillshade/MapServer/tile/{z}/{y}/{x}", {
    maxZoom: 6, opacity: 0.35, className: "hillshade-tiles", attribution: "Esri, USGS"
  }).addTo(map);

  const RadarTile = L.TileLayer.extend({
    getTileUrl(coords) {
      const frame = FRAMES[state.index];
      if (!frame) return "";
      return "tiles/" + frame.id + "/" + coords.z + "/" + coords.x + "/" + coords.y + ".png?v=" + (M.tile_version || "");
    }
  });

  const glow = new RadarTile("", {
    pane: "radarGlow", opacity: 0.5, maxZoom: 6, minZoom: 3, keepBuffer: 1,
    className: "radar-glow", interactive: false
  }).addTo(map);

  const radar = new RadarTile("", {
    pane: "radar", opacity: 0.92, maxZoom: 6, minZoom: 3, keepBuffer: 2,
    className: "radar-sharp", attribution: "IMERG · NASA/JAXA"
  }).addTo(map);

  map.createPane("gibs").style.zIndex = 295;
  function gibsUrl(f) {
    const iso = new Date(f.time).toISOString().replace(/\.\d{3}Z$/, "Z");
    return "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/IMERG_Precipitation_Rate_30min/default/" + iso + "/GoogleMapsCompatible_Level6/{z}/{y}/{x}.png";
  }
  const gibs = L.tileLayer(gibsUrl(FRAMES[state.index]), {
    pane: "gibs", opacity: 0.85, maxZoom: 6, minZoom: 3, attribution: "NASA GIBS"
  });
  function syncGibs() {
    if (!gibs._map) return;
    gibs.setUrl(gibsUrl(FRAMES[state.index]));
    gibs.redraw();
    el("gibsStat").textContent = "IMERG " + fmtTime(FRAMES[state.index].time) + " · сырые тайлы";
  }
  el("gibsToggle").addEventListener("change", (e) => {
    if (e.target.checked) {
      gibs.addTo(map);
      syncGibs();
    } else {
      map.removeLayer(gibs);
      el("gibsStat").textContent = "—";
    }
  });

  /* ---------- спутник Himawari-9 (ИК 10,4 мкм, GIBS, «default» = свежий кадр) ---------- */
  const HIM_LAYER = "Himawari_AHI_Band13_Clean_Infrared";
  const himUrl = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/" + HIM_LAYER + "/default/GoogleMapsCompatible_Level6/{z}/{y}/{x}.png";
  const him = L.tileLayer(himUrl, {
    pane: "gibs", opacity: 0.8, maxZoom: 6, minZoom: 3,
    attribution: "Himawari-9 · JMA, NASA GIBS"
  });
  let himTimer = null;
  function himNow() {
    if (!him._map) return;
    him.setUrl(himUrl + "?v=" + Date.now());
    him.redraw();
    el("himStat").textContent = fmtTime(new Date()) + " · запрошен свежий кадр";
    scheduleHim();
  }
  function scheduleHim() {
    if (himTimer) clearTimeout(himTimer);
    const now = new Date();
    const next = new Date(Math.ceil(now.getTime() / 600000) * 600000);
    const ms = Math.max(30000, next.getTime() - now.getTime());
    el("himCountdown").textContent = "через " + Math.ceil(ms / 1000) + " с";
    himTimer = setTimeout(() => {
      if (him._map) himNow();
    }, ms);
  }
  el("himToggle").addEventListener("change", (e) => {
    if (e.target.checked) {
      him.addTo(map);
      himNow();
    } else {
      map.removeLayer(him);
      if (himTimer) clearTimeout(himTimer), himTimer = null;
      el("himStat").textContent = "—";
      el("himCountdown").textContent = "—";
    }
  });
  el("himNow").addEventListener("click", () => {
    if (him._map) himNow();
  });

  const home = M.focus || [[56, 108], [74, 158]];
  map.fitBounds(home, { paddingTopLeft: [320, 30], paddingBottomRight: [350, 150], maxZoom: 6 });

  const border = L.geoJSON(window.SAKHA_GEO, {
    pane: "border",
    style: { color: "#4fe3c1", weight: 1.2, opacity: 0.5, dashArray: "5 5", fillColor: "#0d3540", fillOpacity: 0.05, interactive: false }
  }).addTo(map);

  const placesLayer = L.layerGroup().addTo(map);
  CITIES.forEach(([name, lat, lon, main]) => {
    const icon = L.divIcon({
      className: "",
      html: '<span class="city' + (main ? "" : " city--minor") + '"><i></i>' + name + "</span>",
      iconSize: [0, 0], iconAnchor: [3, 3]
    });
    L.marker([lat, lon], { icon, keyboard: false, title: name }).addTo(placesLayer);
  });

  const gridLayer = L.layerGroup();
  for (let lon = 100; lon <= 170; lon += 10) {
    L.polyline([[50, lon], [76, lon]], {
      pane: "grid", color: "#7fd8e6", weight: 0.6, opacity: 0.16, dashArray: "2 6", interactive: false
    }).addTo(gridLayer);
  }
  for (let lat = 50; lat <= 75; lat += 5) {
    L.polyline([[lat, 100], [lat, 170]], {
      pane: "grid", color: "#7fd8e6", weight: 0.6, opacity: 0.16, dashArray: "2 6", interactive: false
    }).addTo(gridLayer);
  }
  gridLayer.addTo(map);

  L.control.zoom({ position: "bottomright" }).addTo(map);
  L.control.scale({ position: "bottomleft", imperial: false, maxWidth: 140 }).addTo(map);

  /* ---------- scales ---------- */
  function gradCss(angle, from, to) {
    const parts = STOPS.map(([v, c]) => c + " " + (((v - from) / (to - from)) * 100).toFixed(1) + "%");
    return "linear-gradient(" + angle + "," + parts.join(",") + ")";
  }
  el("legendBar").style.background = gradCss("90deg", 5, 70);
  el("reflectBar").style.background = gradCss("to top", 5, 70);
  [10, 20, 30, 40, 50, 60, 70].forEach((v) => {
    const t = document.createElement("span");
    t.className = "reflect__tick";
    t.style.bottom = 3 + ((v - 5) / 65) * 94 + "%";
    t.textContent = String(v);
    el("reflectTicks").appendChild(t);
  });

  function renderTicks() {
    const box = el("ticks");
    box.innerHTML = "";
    FRAMES.forEach((f) => {
      const s = document.createElement("span");
      if (f.kind !== "obs") s.classList.add("is-fc");
      box.appendChild(s);
    });
  }

  /* ---------- time ---------- */
  function ago(iso) {
    const min = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
    if (min < 1) return "сейчас";
    if (min < 60) return min + " мин назад";
    return Math.round(min / 60) + " ч назад";
  }

  function updateHud(f) {
    const s = f.stats || {};
    if (el('hudMax')) el('hudMax').textContent = s.max_dbz != null ? Math.round(s.max_dbz) + ' дБЗ' : '—';
    if (el('hudArea')) el('hudArea').textContent = s.area_30_km2 ? Math.round(s.area_30_km2 / 1000) + ' тыс. км²' : '0';
    if (el('hudEcho')) el('hudEcho').textContent = s.echo_pct != null ? s.echo_pct.toFixed(1) + ' %' : '—';
  }

  function updateMeta() {
    const method = M.nowcast && M.nowcast.method === "persistence" ? "инерция" : (M.nowcast && M.nowcast.method === "advection" ? "адвекция" : "—");
    el("metricMethod").textContent = method;
    el("footMeta").textContent = "кадров: " + FRAMES.length + " · " + (M.source && M.source.name ? M.source.name : "IMERG") + " · обновлено " + fmtTime(M.generated_at) + " (Якутск)";
  }

  function renderFrame() {
    const f = FRAMES[state.index];
    el("frameTime").textContent = fmtTime(f.time);
    el("frameDate").textContent = fmtDate(f.time);
    el("frameCounter").textContent = "кадр " + (state.index + 1) + " / " + FRAMES.length;
    el("scrub").value = String(state.index);
    updateHud(f);
    renderCells();
    renderSevere();
    if (!modesPanel.hidden) {
      drawProfile();
      drawHodo();
    }
    if (el("phaseToggle").checked) renderPhase();
    syncGibs();
    prefetchNext();

    const kind = el("frameKind");
    if (f.kind === "obs") {
      kind.textContent = state.mode === "archive" ? "архив" : "наблюдение";
      kind.classList.remove("kind-badge--fc");
      el("statusText").innerHTML = "кадр <b>" + fmtTime(f.time) + "</b> · " + fmtDate(f.time);
    } else {
      kind.textContent = "прогноз +" + f.lead_min + " мин";
      kind.classList.add("kind-badge--fc");
      el("statusText").innerHTML = "прогноз <b>+" + f.lead_min + " мин</b> · от " + fmtTime(FRAMES[OBS_N - 1].time);
    }

    if (state.point) refreshProbe(false);
    if (!state.timer) syncUrl();
  }

  function setFrame(i, user) {
    const idx = Math.max(0, Math.min(FRAMES.length - 1, i));
    if (idx === state.index) return;
    state.index = idx;
    radar.redraw();
    glow.redraw();
    renderFrame();
    if (user && state.timer) stopPlay();
  }

  let prefetchTimer = null;
  function prefetchNext() {
    clearTimeout(prefetchTimer);
    if (state.timer) return;
    prefetchTimer = setTimeout(() => {
      const next = FRAMES[(state.index + 1) % FRAMES.length];
      if (!next || !map.getZoom) return;
      const z = map.getZoom();
      const b = map.getBounds();
      const nw = map.project(b.getNorthWest(), z).divideBy(256).floor();
      const se = map.project(b.getSouthEast(), z).divideBy(256).floor();
      let count = 0;
      for (let x = nw.x; x <= se.x && count < 24; x++) {
        for (let y = nw.y; y <= se.y && count < 24; y++) {
          const img = new Image();
          img.src = "tiles/" + next.id + "/" + z + "/" + x + "/" + y + ".png?v=" + (M.tile_version || "");
          count++;
        }
      }
    }, 450);
  }

  function startPlay() {
    if (state.timer) return;
    el("play").classList.add("is-playing");
    el("play").setAttribute("aria-pressed", "true");
    state.timer = setInterval(() => setFrame((state.index + 1) % FRAMES.length), state.speed);
  }  function stopPlay() {
    clearInterval(state.timer);
    state.timer = null;
    el("play").classList.remove("is-playing");
    el("play").setAttribute("aria-pressed", "false");
  }

  /* ---------- manifest switching ---------- */
  function applyManifest(m, mode) {
    stopPlay();
    M = m;
    FRAMES = m.frames;
    OBS_N = FRAMES.filter((f) => f.kind === "obs").length;
    state.mode = mode;
    state.index = Math.max(0, OBS_N - 1);
    state.point = null;
    state.seq++;
    el("probeBody").hidden = true;
    el("probeEmpty").hidden = false;
    if (window.marker) { map.removeLayer(window.marker); window.marker = null; }

    el("scrub").max = String(FRAMES.length - 1);
    renderTicks();
    radar.redraw();
    glow.redraw();
    renderFrame();
    updateMeta();

    const badge = el("modeBadge");
    if (mode === "archive") {
      badge.textContent = "АРХИВ";
      badge.classList.add("badge-demo--archive");
    } else {
      badge.textContent = "LIVE";
      badge.classList.remove("badge-demo--archive");
    }

    if (m.focus) map.fitBounds(m.focus, { paddingTopLeft: [320, 30], paddingBottomRight: [350, 150], maxZoom: 6 });
    updateLatency();
  }

  /* ---------- UI wiring ---------- */
  el("play").addEventListener("click", () => (state.timer ? stopPlay() : startPlay()));
  el("scrub").addEventListener("input", (e) => {
    stopPlay();
    state.index = Number(e.target.value);
    radar.redraw();
    glow.redraw();
    renderFrame();
  });
  el("nowBtn").addEventListener("click", () => {
    stopPlay();
    if (state.mode === "archive") return loadLive();
    setFrame(OBS_N - 1);
  });
  el("speed").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-speed]");
    if (!b) return;
    state.speed = Number(b.dataset.speed);
    el("speed").querySelectorAll("button").forEach((x) => x.classList.toggle("is-active", x === b));
    if (state.timer) { stopPlay(); startPlay(); }
  });
  el("opacity").addEventListener("input", (e) => {
    el("opacityOut").textContent = e.target.value + " %";
    radar.setOpacity(Number(e.target.value) / 100);
    glow.setOpacity(Number(e.target.value) / 200);
  });
  el("mosaicToggle").addEventListener("change", (e) => {
    if (e.target.checked) { radar.addTo(map); glow.addTo(map); }
    else { map.removeLayer(radar); map.removeLayer(glow); }
  });
  el("citiesToggle").addEventListener("change", (e) => (e.target.checked ? placesLayer.addTo(map) : map.removeLayer(placesLayer)));
  el("borderToggle").addEventListener("change", (e) => (e.target.checked ? border.addTo(map) : map.removeLayer(border)));
  el("gridToggle").addEventListener("change", (e) => (e.target.checked ? gridLayer.addTo(map) : map.removeLayer(gridLayer)));

  /* ---------- probe ---------- */
  const gridCache = new Map();
  function valuesOf(id) {
    if (!gridCache.has(id)) {
      const src = P.frames[id] || [];
      const arr = new Float32Array(src.length);
      for (let i = 0; i < src.length; i++) arr[i] = src[i] === null ? NaN : src[i];
      gridCache.set(id, arr);
    }
    return gridCache.get(id);
  }
  function probOf(id) {
    const key = "p:" + id;
    if (!gridCache.has(key)) {
      const src = P.prob[id] || [];
      const arr = new Float32Array(src.length);
      for (let i = 0; i < src.length; i++) arr[i] = src[i] === null ? NaN : src[i];
      gridCache.set(key, arr);
    }
    return gridCache.get(key);
  }
  function bilinear(arr, lat, lon) {
    if (!arr || !arr.length) return NaN;
    const fx = (lon - P.lon0) / P.step;
    const fy = (lat - P.lat0) / P.step;
    const x0 = Math.floor(fx), y0 = Math.floor(fy);
    if (x0 < 0 || y0 < 0 || x0 >= P.nx - 1 || y0 >= P.ny - 1) return NaN;
    const tx = fx - x0, ty = fy - y0;
    const i = y0 * P.nx + x0;
    const vals = [arr[i], arr[i + 1], arr[i + P.nx], arr[i + P.nx + 1]];
    const w = [(1 - tx) * (1 - ty), tx * (1 - ty), (1 - tx) * ty, tx * ty];
    let s = 0, ws = 0;
    for (let k = 0; k < 4; k++) {
      if (Number.isFinite(vals[k])) { s += vals[k] * w[k]; ws += w[k]; }
    }
    return ws > 0 ? s / ws : NaN;
  }

  function classOf(dbz) {
    for (const [limit, name, color] of CLASSES) if (dbz < limit) return { name, color };
    return { name: "экстремальные", color: "#6f4f9e" };
  }

  const rateOf = (dbz, code) => {
    const z = Math.pow(10, dbz / 10);
    if (code === 1 || code === 2) return Math.sqrt(z / 2000);
    return Math.pow(z / 200, 1 / 1.6);
  };

  let marker = null;

  function openProbe(lat, lon) {
    state.point = { lat, lon };
    if (marker) map.removeLayer(marker);
    marker = L.marker([lat, lon], {
      icon: L.divIcon({ className: "", html: '<span class="probe-marker"></span>', iconSize: [16, 16], iconAnchor: [8, 8] }),
      interactive: false, zIndexOffset: 600
    }).addTo(map);
    window.marker = marker;
    el("probeEmpty").hidden = true;
    el("probeBody").hidden = false;
    el("probeCoords").textContent =
      Math.abs(lat).toFixed(2).replace(".", ",") + "° " + (lat >= 0 ? "с.ш." : "ю.ш.") + " · " +
      Math.abs(lon).toFixed(2).replace(".", ",") + "° " + (lon >= 0 ? "в.д." : "з.д.");
    el("probeStation").textContent = M.source && M.source.provider ? M.source.provider : "IMERG";
    const t = sampleEnv("t2m", lat, lon);
    const tw = sampleEnv("wetbulb", lat, lon);
    const cape = sampleEnv("cape", lat, lon);
    const shear = sampleEnv("shear", lat, lon);
    const code = phaseCode(tw);
    el("probeTemp").textContent = Number.isFinite(t)
      ? Math.round(t * 10) / 10 + " °C · " + phaseName(code) + (Number.isFinite(tw) ? " · Tw " + Math.round(tw * 10) / 10 + " °C" : "")
      : "—";
    el("probeEnv").textContent = Number.isFinite(cape) ? Math.round(cape) + " Дж/кг · " + (Number.isFinite(shear) ? Math.round(shear) : "—") + " м/с" : "—";
    refreshProbe(true);
  }

  function phaseCode(tw) {
    if (!Number.isFinite(tw)) return 0;
    return tw <= 0.5 ? 1 : tw < 2 ? 2 : 3;
  }

  function phaseName(code) {
    return code === 1 ? "снег" : code === 2 ? "смешанные" : code === 3 ? "дождь" : "—";
  }

  async function refreshProbe(full) {
    const f = FRAMES[state.index];
    const { lat, lon } = state.point;
    const seq = ++state.seq;

    let dbz = bilinear(valuesOf(f.id), lat, lon);
    let prob = f.kind === "nowcast" ? bilinear(probOf(f.id), lat, lon) : NaN;

    if (!IS_FILE) {
      try {
        const r = await fetch(API + "/api/probe?lat=" + lat.toFixed(4) + "&lon=" + lon.toFixed(4) + "&frame=" + f.id);
        if (r.ok) {
          const j = await r.json();
          if (seq !== state.seq) return;
          if (typeof j.dbz === "number") dbz = j.dbz;
          if (typeof j.prob30 === "number") prob = j.prob30;
        }
      } catch (e) { /* offline */ }
    }
    if (seq !== state.seq) return;

    if (!Number.isFinite(dbz) || dbz < 5) {
      el("probeSwatch").style.background = "rgba(120,150,175,.16)";
      el("probeSwatch").style.boxShadow = "inset 0 0 0 1px rgba(255,255,255,.12)";
      el("probeClass").textContent = "без эхо";
      el("probeRange").textContent = "ниже порога 5 дБЗ";
      el("probeDbz").textContent = "—";
      el("probeRate").textContent = "—";
    } else {
      const c = classOf(dbz);
      el("probeSwatch").style.background = c.color;
      el("probeSwatch").style.boxShadow = "inset 0 0 0 1px rgba(255,255,255,.22), 0 0 22px " + c.color + "66";
      el("probeClass").textContent = c.name;
      const code = phaseCode(sampleEnv("wetbulb", lat, lon));
      el("probeRange").textContent = "класс · " + phaseName(code);
      el("probeDbz").textContent = Math.round(dbz * 10) / 10 + " дБЗ";
      el("probeRate").textContent = rateOf(dbz, code).toFixed(1) + " мм/ч";
    }
    el("probeProb").textContent = f.kind === "nowcast"
      ? (Number.isFinite(prob) ? Math.round(prob * 100) + " %" : "—")
      : "только для прогноза";

    const obs = FRAMES.filter((x) => x.kind === "obs");
    const pos = obs.findIndex((x) => x.id === f.id);
    let trend = "—";
    if (pos > 2) {
      const prev = bilinear(valuesOf(obs[pos - 3].id), lat, lon);
      if (Number.isFinite(prev) && Number.isFinite(dbz)) {
        const d = dbz - prev;
        trend = (d > 0 ? "+" : "") + Math.round(d * 10) / 10 + " дБЗ";
      }
    }
    el("probeTrend").textContent = trend;
    el("probeAccum").textContent = "…";
    if (!IS_FILE) {
      try {
        const r = await fetch(API + "/api/accum?lat=" + lat.toFixed(4) + "&lon=" + lon.toFixed(4) + "&frame=" + f.id + "&window=12");
        const j = await r.json();
        el("probeAccum").textContent = j.mm != null ? j.mm.toFixed(1) + " мм" : "—";
      } catch (e) { el("probeAccum").textContent = "—"; }
    } else {
      el("probeAccum").textContent = "нужен сервер";
    }

    const values = FRAMES.map((x) => bilinear(valuesOf(x.id), lat, lon));
    drawSpark(values);
    const wet = values.filter((v) => Number.isFinite(v) && v >= 5).length;
    el("probeSummary").textContent = wet ? "эхо в " + wet + " из " + FRAMES.length + " кадров" : "эхо не зафиксировано";
  }

  function drawSpark(values) {
    const canvas = el("spark");
    const ctx = canvas.getContext("2d");
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    const w = canvas.clientWidth || 280, h = 60;
    canvas.width = Math.floor(w * dpr);
    canvas.height = Math.floor(h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    const gap = 2.5;
    const bw = (w - gap * (values.length - 1)) / values.length;
    const base = h - 10;
    const split = OBS_N * (bw + gap) - gap;
    if (OBS_N < values.length) {
      ctx.fillStyle = "rgba(255,180,84,.14)";
      ctx.fillRect(split, 0, w - split, base);
    }
    ctx.strokeStyle = "rgba(120,170,195,.18)";
    ctx.beginPath();
    ctx.moveTo(0, base + 0.5);
    ctx.lineTo(w, base + 0.5);
    ctx.stroke();
    values.forEach((v, i) => {
      const x = i * (bw + gap);
      if (!Number.isFinite(v) || v < 5) {
        ctx.fillStyle = "rgba(120,150,175,.18)";
        ctx.fillRect(x, base - 2, bw, 2);
        return;
      }
      const bh = 5 + ((v - 5) / 65) * (base - 8);
      ctx.fillStyle = classOf(v).color;
      ctx.fillRect(x, base - bh, bw, bh);
    });
    const mx = state.index * (bw + gap) + bw / 2;
    ctx.fillStyle = "rgba(255,180,84,.95)";
    ctx.fillRect(Math.min(w - 2, Math.max(0, mx - 1)), 0, 2, base);
  }

  el("probeReset").addEventListener("click", () => {
    state.point = null;
    if (marker) { map.removeLayer(marker); marker = null; }
    el("probeBody").hidden = true;
    el("probeEmpty").hidden = false;
    state.seq++;
  });
  map.on("click", (e) => openProbe(e.latlng.lat, e.latlng.lng));

  /* ---------- hover readout ---------- */
  const cursorReadout = el("cursorReadout");
  let hoverPoint = null, hoverTimer = 0;
  function updateReadout() {
    hoverTimer = 0;
    if (!hoverPoint) return;
    const f = FRAMES[state.index];
    const dbz = bilinear(valuesOf(f.id), hoverPoint.lat, hoverPoint.lng);
    if (!Number.isFinite(dbz) || dbz < 5) { cursorReadout.hidden = true; return; }
    const code = phaseCode(sampleEnv("wetbulb", hoverPoint.lat, hoverPoint.lng));
    const p = map.latLngToContainerPoint(hoverPoint);
    cursorReadout.hidden = false;
    cursorReadout.textContent = Math.round(dbz) + " дБЗ · " + phaseName(code);
    cursorReadout.style.transform = "translate(" + (p.x + 16) + "px," + (p.y + 16) + "px)";
  }
  map.on("mousemove", (e) => {
    hoverPoint = e.latlng;
    if (!hoverTimer) hoverTimer = setTimeout(updateReadout, 90);
  });
  map.on("mouseout", () => { hoverPoint = null; cursorReadout.hidden = true; });

  function syncUrl() {
    try {
      const p = new URLSearchParams();
      p.set("t", String(state.index));
      if (state.point) p.set("ll", state.point.lat.toFixed(3) + "," + state.point.lon.toFixed(3));
      history.replaceState(null, "", location.pathname + "?" + p.toString());
    } catch (e) { /* file: protocol */ }
  }

  function restoreUrl() {
    let t = NaN, ll = null;
    try {
      const p = new URLSearchParams(location.search);
      t = Number(p.get("t"));
      ll = p.get("ll");
    } catch (e) { return false; }
    let used = false;
    if (Number.isInteger(t) && t >= 0 && t < FRAMES.length) { state.index = t; used = true; }
    if (ll) {
      const [la, lo] = ll.split(",").map(Number);
      if (Number.isFinite(la) && Number.isFinite(lo)) {
        map.setView([la, lo], map.getZoom());
        openProbe(la, lo);
        used = true;
      }
    }
    return used;
  }

  /* ---------- chips ---------- */
  CITIES.filter((c) => c[3]).forEach(([name, lat, lon]) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "chip";
    b.textContent = name;
    b.addEventListener("click", () => {
      map.flyTo([lat, lon], 6, { duration: 0.7 });
      openProbe(lat, lon);
      closeSheet();
    });
    el("chips").appendChild(b);
  });

  /* ---------- archive ---------- */
  const archPanel = el("archivePanel");
  const archStatus = el("archiveStatus");

  function setArchiveOpen(open) {
    archPanel.hidden = !open;
    el("archiveBtn").setAttribute("aria-expanded", String(open));
  }
  el("archiveBtn").addEventListener("click", () => setArchiveOpen(archPanel.hidden));
  el("archiveClose").addEventListener("click", () => setArchiveOpen(false));

  async function loadLive() {
    if (IS_FILE) {
      applyManifest(DATA.manifest, "live");
      return;
    }
    archStatus.textContent = "Загружаю текущие данные…";
    try {
      const r = await fetch(API + "/api/state");
      const m = await r.json();
      applyManifest(m, "live");
      archStatus.textContent = "Текущие данные загружены.";
      setArchiveOpen(false);
    } catch (e) {
      archStatus.textContent = "Не удалось загрузить текущие данные.";
    }
  }

  el("archiveLive").addEventListener("click", loadLive);

  el("archiveLoad").addEventListener("click", async () => {
    if (IS_FILE) {
      archStatus.textContent = "Архив работает при запущенном сервере.";
      return;
    }
    const date = el("archiveDate").value;
    const hour = Number(el("archiveHour").value);
    if (!date) return;
    archStatus.textContent = "Собираю " + date + " " + String(hour).padStart(2, "0") + ":00 — это до минуты…";
    try {
      let r = await fetch("/api/archive?date=" + date + "&hour=" + hour);
      let j = await r.json();
      if (j.status === "building") {
        const key = j.key;
        for (let i = 0; i < 60; i++) {
          await new Promise((res) => setTimeout(res, 3000));
          const s = await fetch("/api/archive/status?key=" + encodeURIComponent(key)).then((x) => x.json());
          if (s.status === "done") { j = s; break; }
          if (s.status === "error") throw new Error(s.error || "build failed");
          archStatus.textContent = "Собираю кадры… " + (i + 1) * 3 + " с";
        }
      }
      if (j.status === "done" && j.manifest) {
        applyManifest(j.manifest, "archive");
        archStatus.textContent = "Готово: " + date + ", " + String(hour).padStart(2, "0") + ":00.";
        setArchiveOpen(false);
      } else {
        archStatus.textContent = "Сборка не завершилась, попробуйте ещё раз.";
      }
    } catch (e) {
      archStatus.textContent = "Ошибка: " + e.message;
    }
  });

  /* ---------- radar modes ---------- */
  const modesPanel = el("modesPanel");
  function setModesOpen(open) {
    modesPanel.hidden = !open;
    el("modesBtn").setAttribute("aria-expanded", String(open));
    if (open) {
      drawBeam();
      drawProfile();
      drawHodo();
    }
  }
  el("modesBtn").addEventListener("click", () => setModesOpen(modesPanel.hidden));
  el("modesClose").addEventListener("click", () => setModesOpen(false));

  const RE = (6371 * 4) / 3;
  function beamHeight(r, deg) {
    const th = (deg * Math.PI) / 180;
    return Math.sqrt(r * r + RE * RE + 2 * r * RE * Math.sin(th)) - RE + 0.12;
  }

  function drawBeam() {
    const canvas = el("beamChart");
    if (!canvas) return;
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    const w = canvas.clientWidth || 320, h = 110;
    canvas.width = Math.floor(w * dpr);
    canvas.height = Math.floor(h * dpr);
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    const padL = 26, padB = 15, padT = 8, padR = 8;
    const x0 = padL, y0 = h - padB, x1 = w - padR, y1 = padT;
    const RMAX = 250, HMAX = 12;
    const X = (r) => x0 + (r / RMAX) * (x1 - x0);
    const Y = (km) => y0 - (Math.min(HMAX, km) / HMAX) * (y0 - y1);

    ctx.strokeStyle = "rgba(120,170,195,.2)";
    ctx.fillStyle = "rgba(140,170,190,.8)";
    ctx.font = "9px ui-monospace, monospace";
    ctx.lineWidth = 1;
    [0, 50, 100, 150, 200, 250].forEach((r) => {
      ctx.beginPath(); ctx.moveTo(X(r), y0); ctx.lineTo(X(r), y1); ctx.stroke();
      ctx.fillText(String(r), X(r) - 6, h - 4);
    });
    [0, 4, 8, 12].forEach((k) => {
      ctx.beginPath(); ctx.moveTo(x0, Y(k)); ctx.lineTo(x1, Y(k)); ctx.stroke();
      ctx.fillText(String(k), 2, Y(k) + 3);
    });

    const deg = Number(el("beamAngle").value);
    ctx.strokeStyle = "#ffb454";
    ctx.lineWidth = 1.7;
    ctx.beginPath();
    for (let r = 0; r <= RMAX; r += 2) {
      const px = X(r), py = Y(beamHeight(r, deg));
      if (r === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
    }
    ctx.stroke();

    el("beamStats").innerHTML = [50, 100, 150, 200, 250]
      .map((r) => "<span>" + r + " км<b>" + beamHeight(r, deg).toFixed(1) + " км</b></span>")
      .join("");
  }
  el("beamAngle").addEventListener("change", drawBeam);

  const bToggle = el("broadcastToggle");
  function setBroadcast(on) {
    document.body.classList.toggle("broadcast", on);
    bToggle.checked = on;
    try { localStorage.setItem("broadcast", on ? "1" : "0"); } catch (e) { /* private mode */ }
  }
  bToggle.addEventListener("change", () => setBroadcast(bToggle.checked));
  try { if (localStorage.getItem("broadcast") === "1") setBroadcast(true); } catch (e) { /* ignore */ }

  function updateLatency() {
    const obs = M.frames.filter((f) => f.kind === "obs");
    if (!obs.length) return;
    const last = new Date(obs[obs.length - 1].time).getTime();
    const lagH = Math.max(0, (Date.now() - last) / 3600000);
    el("latencyTag").textContent = lagH >= 1 ? Math.round(lagH) + " ч" : Math.round(lagH * 60) + " мин";
  }
  updateLatency();

  const REFRESH_MS = 5 * 60 * 1000;
  let refreshAt = Date.now() + REFRESH_MS;
  let refreshing = false;

  function fmtCountdown(ms) {
    const total = Math.max(0, Math.ceil(ms / 1000));
    return Math.floor(total / 60) + ":" + String(total % 60).padStart(2, "0");
  }

  async function checkNow(manual) {
    if (IS_FILE) {
      el("refreshStat").textContent = "автообновление работает при запущенном сервере";
      return;
    }
    if (refreshing) return;
    refreshing = true;
    el("refreshStat").textContent = "проверяю…";
    try {
      const r = await fetch(API + "/api/state", { cache: "no-store" });
      if (!r.ok) throw new Error("HTTP " + r.status);
      const m = await r.json();
      if (m.tile_version !== M.tile_version) {
        applyManifest(m, "live");
        el("refreshStat").textContent = "новые данные: " + fmtTime(m.generated_at);
      } else {
        el("refreshStat").textContent = manual ? "новых данных нет" : "без изменений";
      }
    } catch (e) {
      el("refreshStat").textContent = "ошибка проверки";
    } finally {
      refreshing = false;
      refreshAt = Date.now() + REFRESH_MS;
    }
  }

  function refreshTick() {
    el("refreshCountdown").textContent = fmtCountdown(refreshAt - Date.now());
    if (Date.now() >= refreshAt) checkNow(false);
  }
  setInterval(refreshTick, 1000);
  refreshTick();
  el("refreshNow").addEventListener("click", () => checkNow(true));

  /* ---------- environment, phase, storm cells ---------- */
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
  const PHASE_RGBA = { 1: [170, 225, 255, 135], 2: [200, 170, 255, 125], 3: [90, 160, 255, 55] };
  function renderPhase() {
    if (!P.phase) return;
    const frame = FRAMES[state.index];
    const codes = P.phase[frame.id];
    const canvas = document.createElement("canvas");
    canvas.width = P.nx;
    canvas.height = P.ny;
    const ctx = canvas.getContext("2d");
    const img = ctx.createImageData(P.nx, P.ny);
    if (codes) {
      for (let i = 0; i < codes.length; i++) {
        const col = PHASE_RGBA[codes[i]];
        if (!col) continue;
        const o = i * 4;
        img.data[o] = col[0];
        img.data[o + 1] = col[1];
        img.data[o + 2] = col[2];
        img.data[o + 3] = col[3];
      }
    }
    ctx.putImageData(img, 0, 0);
    const url = canvas.toDataURL();
    const bounds = [[P.lat0, P.lon0], [P.lat0 + P.step * P.ny, P.lon0 + P.step * P.nx]];
    if (!phaseOverlay) {
      phaseOverlay = L.imageOverlay(url, bounds, { opacity: 0.65, interactive: false }).addTo(map);
    } else {
      phaseOverlay.setUrl(url);
      phaseOverlay.setBounds(bounds);
    }
  }

  const cellsLayer = L.layerGroup().addTo(map);
  function renderCells() {
    cellsLayer.clearLayers();
    const cells = FRAMES[state.index].cells || [];
    cells.forEach((c) => {
      const color = c.color || "#ff2d55";
      const tip =
        "<b>" + (c.label || "ячейка") + "</b> · " + Math.round((c.confidence || 0) * 100) + " %<br>" +
        c.max_dbz + " дБЗ · " + c.area_km2 + " км²" +
        (c.growth_dbz != null ? " · рост " + c.growth_dbz + " дБЗ" : "") +
        (c.reasons && c.reasons.length ? "<br><span style='opacity:.65'>" + c.reasons.join(" · ") + "</span>" : "");
      L.circleMarker([c.lat, c.lon], {
        radius: 6, color, weight: 1.6, fillColor: color, fillOpacity: 0.3
      }).bindTooltip(tip).addTo(cellsLayer);
    });
  }

  function renderSevere() {
    const f = FRAMES[state.index];
    const sev = (f.stats || {}).severe;
    el("severeScore").textContent = sev ? sev.score + " / 10" : "—";
    el("severeLevel").textContent = sev ? sev.level : "—";
    el("mesoStatus").textContent = "нет доплера";
  }

  function profilePoint() {
    return state.point || map.getCenter();
  }

  function sampleProfile(lat, lon) {
    const pr = ENV && ENV.profile;
    if (!pr) return null;
    const fx = (lon - pr.lon0) / pr.step;
    const fy = (lat - pr.lat0) / pr.step;
    const x0 = Math.floor(fx), y0 = Math.floor(fy);
    if (x0 < 0 || y0 < 0 || x0 >= pr.nx - 1 || y0 >= pr.ny - 1) return null;
    const tx = fx - x0, ty = fy - y0;
    const i = y0 * pr.nx + x0;
    const w = [(1 - tx) * (1 - ty), tx * (1 - ty), (1 - tx) * ty, tx * ty];
    const pick = (arr) => {
      let s = 0;
      for (let k = 0; k < 4; k++) {
        const dx = k === 1 || k === 3 ? 1 : 0;
        const dy = k >= 2 ? 1 : 0;
        s += arr[i + dy * pr.nx + dx] * w[k];
      }
      return s;
    };
    return {
      levels: pr.levels,
      t: pr.levels.map((_, li) => pick(pr.t[li])),
      u: pr.levels.map((_, li) => pick(pr.u[li])),
      v: pr.levels.map((_, li) => pick(pr.v[li])),
    };
  }

  function drawProfile() {
    const canvas = el("profileChart");
    if (!canvas) return;
    const pr = ENV && ENV.profile;
    const stat = el("profileStat");
    if (!pr) {
      stat.textContent = "профиль GFS недоступен";
      return;
    }
    const pt = profilePoint();
    const s = sampleProfile(pt.lat, pt.lng != null ? pt.lng : pt.lon);
    if (!s) {
      stat.textContent = "точка вне сетки профиля";
      return;
    }
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    const w = canvas.clientWidth || 320, h = 240;
    canvas.width = Math.floor(w * dpr);
    canvas.height = Math.floor(h * dpr);
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    const padL = 34, padR = 58, padT = 10, padB = 24;
    const x0 = padL, x1 = w - padR, y0 = h - padB, y1 = padT;
    const tMin = Math.min(...s.t) - 4, tMax = Math.max(...s.t) + 4;
    const pMin = Math.min(...s.levels), pMax = Math.max(...s.levels);
    const X = (t) => x0 + ((t - tMin) / (tMax - tMin)) * (x1 - x0);
    const Y = (p) => y0 - ((Math.log10(pMax) - Math.log10(p)) / (Math.log10(pMax) - Math.log10(pMin))) * (y0 - y1);

    ctx.strokeStyle = "rgba(120,170,195,.2)";
    ctx.fillStyle = "rgba(140,170,190,.8)";
    ctx.font = "9px ui-monospace, monospace";
    ctx.lineWidth = 1;
    s.levels.forEach((p) => {
      ctx.beginPath();
      ctx.moveTo(x0, Y(p));
      ctx.lineTo(x1, Y(p));
      ctx.stroke();
      ctx.fillText(String(p), 2, Y(p) + 3);
    });
    [tMin, (tMin + tMax) / 2, tMax].forEach((t) => {
      ctx.beginPath();
      ctx.moveTo(X(t), y0);
      ctx.lineTo(X(t), y1);
      ctx.stroke();
      ctx.fillText(Math.round(t) + "°", X(t) - 6, h - 8);
    });

    ctx.strokeStyle = "#ffb454";
    ctx.lineWidth = 1.7;
    ctx.beginPath();
    s.t.forEach((t, li) => {
      const px = X(t), py = Y(s.levels[li]);
      if (li === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
    });
    ctx.stroke();

    ctx.fillStyle = "#ffd9a0";
    ctx.font = "10px ui-monospace, monospace";
    s.t.forEach((t, li) => {
      const px = X(t), py = Y(s.levels[li]);
      ctx.beginPath();
      ctx.arc(px, py, 2.6, 0, Math.PI * 2);
      ctx.fill();
      const sp = Math.hypot(s.u[li], s.v[li]);
      ctx.fillStyle = "rgba(190,220,235,.85)";
      ctx.fillText(Math.round(sp) + " м/с", x1 + 6, py + 3);
      ctx.fillStyle = "#ffd9a0";
    });

    const windMax = Math.max(...s.levels.map((_, li) => Math.hypot(s.u[li], s.v[li])));
    stat.textContent =
      "точка " + pt.lat.toFixed(2) + "°, " + (pt.lng != null ? pt.lng : pt.lon).toFixed(2) + "° · " +
      s.levels.length + " уровня · T " + Math.round(s.t[0]) + "…" + Math.round(s.t[s.t.length - 1]) + " °C · ветер до " + Math.round(windMax) + " м/с";
  }

  function drawHodo() {
    const canvas = el("hodoChart");
    if (!canvas) return;
    const stat = el("hodoStat");
    const pr = ENV && ENV.profile;
    if (!pr) {
      stat.textContent = "профиль GFS недоступен";
      return;
    }
    const pt = profilePoint();
    const lon = pt.lng != null ? pt.lng : pt.lon;
    const s = sampleProfile(pt.lat, lon);
    if (!s) {
      stat.textContent = "точка вне сетки профиля";
      return;
    }
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    const w = canvas.clientWidth || 320, h = 240;
    canvas.width = Math.floor(w * dpr);
    canvas.height = Math.floor(h * dpr);
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    const pad = 26;
    const cx = w / 2, cy = h / 2;
    const extent = Math.max(12, ...s.levels.map((_, li) => Math.hypot(s.u[li], s.v[li]))) + 4;
    const S = (Math.min(w, h) / 2 - pad) / extent;
    const X = (u) => cx + u * S;
    const Y = (v) => cy - v * S;

    ctx.strokeStyle = "rgba(120,170,195,.2)";
    ctx.fillStyle = "rgba(140,170,190,.75)";
    ctx.font = "9px ui-monospace, monospace";
    ctx.lineWidth = 1;
    for (let k = -extent; k <= extent; k += 10) {
      ctx.beginPath(); ctx.moveTo(X(k), Y(-extent)); ctx.lineTo(X(k), Y(extent)); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(X(-extent), Y(k)); ctx.lineTo(X(extent), Y(k)); ctx.stroke();
    }
    ctx.strokeStyle = "rgba(160,200,220,.45)";
    ctx.beginPath(); ctx.moveTo(X(-extent), Y(0)); ctx.lineTo(X(extent), Y(0)); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(X(0), Y(-extent)); ctx.lineTo(X(0), Y(extent)); ctx.stroke();

    ctx.strokeStyle = "#7fd8e6";
    ctx.lineWidth = 1.8;
    ctx.beginPath();
    s.levels.forEach((_, li) => {
      const px = X(s.u[li]), py = Y(s.v[li]);
      if (li === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
    });
    ctx.stroke();

    ctx.font = "9px ui-monospace, monospace";
    s.levels.forEach((p, li) => {
      const px = X(s.u[li]), py = Y(s.v[li]);
      ctx.fillStyle = "#bfefff";
      ctx.beginPath(); ctx.arc(px, py, 2.4, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = "rgba(190,220,235,.8)";
      ctx.fillText(String(p), px + 4, py - 4);
    });

    const first = 0, last = s.levels.length - 1;
    const bulk = Math.hypot(s.u[last] - s.u[first], s.v[last] - s.v[first]);
    const low = sampleEnv("shear", pt.lat, lon);
    stat.textContent =
      "сдвиг 850→300: " + Math.round(bulk) + " м/с · 0–6 км: " +
      (Number.isFinite(low) ? Math.round(low) : "—") + " м/с · мезоциклон не детектируется";
  }

  el("phaseToggle").addEventListener("change", (e) => {
    if (e.target.checked) renderPhase();
    else if (phaseOverlay) map.removeLayer(phaseOverlay), (phaseOverlay = null);
  });

  /* ---------- модельный радар (GFS/ECMWF/ICON/MSM) ---------- */
  let modelOverlay = null;
  let modelCache = {};
  const modelSelect = el("modelSelect");
  const MODEL_COLORS = [
    [0.2, "#70d6b0", "rgba(112,214,176,0.28)"],
    [1, "#4aa8e0", "rgba(74,168,224,0.32)"],
    [2.5, "#2f6fd0", "rgba(47,111,208,0.36)"],
    [5, "#1e9e3a", "rgba(30,158,58,0.40)"],
    [10, "#9bd400", "rgba(155,212,0,0.45)"],
    [20, "#ffd400", "rgba(255,212,0,0.50)"],
    [35, "#ff8c1a", "rgba(255,140,26,0.55)"],
    [50, "#ff2d2d", "rgba(255,45,45,0.60)"],
    [65, "#c8007a", "rgba(200,0,122,0.62)"],
    [80, "#e05ad8", "rgba(224,90,216,0.60)"]
  ];
  function modelDbzToRate(dbz) {
    if (!Number.isFinite(dbz)) return 0;
    return Math.max(0, Math.pow(Math.pow(10, dbz / 10) / 200, 1 / 1.6));
  }
  function drawModelOverlay(payload) {
    if (!modelOverlay) {
      modelOverlay = L.imageOverlay("", [[54, 104], [74, 166]], { opacity: 0.72, interactive: false, pane: "radarGlow" });
    }
    const ny = payload.ny, nx = payload.nx, f = payload.field;
    const canvas = document.createElement("canvas");
    canvas.width = nx;
    canvas.height = ny;
    const ctx = canvas.getContext("2d");
    const img = ctx.createImageData(nx, ny);
    for (let i = 0; i < f.length; i++) {
      const v = f[i];
      if (v == null) continue;
      const rate = modelDbzToRate(v);
      let rgba = null;
      for (const [lim, rgb, fill] of MODEL_COLORS) {
        if (rate >= lim) rgba = fill;
      }
      if (!rgba) continue;
      const m = rgba.match(/rgba\((\d+),(\d+),(\d+),([0-9.]+)\)/);
      if (!m) continue;
      const o = i * 4;
      img.data[o] = +m[1]; img.data[o + 1] = +m[2]; img.data[o + 2] = +m[3]; img.data[o + 3] = Math.round(+m[4] * 255);
    }
    ctx.putImageData(img, 0, 0);
    modelOverlay.setUrl(canvas.toDataURL());
    if (!modelOverlay._map) modelOverlay.addTo(map);
  }
  async function loadModel(model) {
    const nm = el("modelName");
    if (!nm) return;
    if (modelCache[model]) {
      nm.textContent = modelCache[model].name + " · " + (modelCache[model].init || modelCache[model].valid || "");
      drawModelOverlay(modelCache[model]);
      return;
    }
    const base = (window.API_BASE || "").replace(/\/$/, "");
    nm.textContent = "загрузка " + model + "…";
    try {
      const r = await fetch(base + "/api/model_field?model=" + encodeURIComponent(model), { cache: "no-store" });
      if (!r.ok) throw new Error("HTTP " + r.status);
      const ct = r.headers.get("content-type") || "";
      if (ct.indexOf("json") < 0) throw new Error("API недоступен (статика)");
      const j = await r.json();
      if (!j || !j.field || !j.ny) throw new Error("пустой ответ");
      modelCache[model] = j;
      nm.textContent = j.name + " · " + (j.init || j.valid || "") + (j.note ? " · " + j.note : "");
      drawModelOverlay(j);
    } catch (e) {
      const st = (window.RADAR_STATIC && window.RADAR_STATIC.model && window.RADAR_STATIC.model.model === model) ? window.RADAR_STATIC.model : null;
      if (st) {
        modelCache[model] = st;
        nm.textContent = st.name + " · " + (st.valid || st.init || "") + " · встроенные данные";
        drawModelOverlay(st);
      } else {
        nm.textContent = "модель недоступна: бэкенд не подключён";
      }
      console.error("model", model, e);
    }
  }
  el("modelToggle").addEventListener("change", (e) => {
    if (e.target.checked) {
      loadModel(modelSelect.value);
    } else if (modelOverlay) {
      map.removeLayer(modelOverlay);
    }
  });
  modelSelect.addEventListener("change", () => {
    if (el("modelToggle").checked) loadModel(modelSelect.value);
  });


  /* ---------- mobile sheet ---------- */
  const sheet = el("layersPanel");
  const backdrop = el("sheetBackdrop");
  function openSheet() {
    sheet.classList.add("is-open");
    backdrop.hidden = false;
    requestAnimationFrame(() => backdrop.classList.add("is-open"));
    el("sheetToggle").setAttribute("aria-expanded", "true");
  }
  function closeSheet() {
    sheet.classList.remove("is-open");
    backdrop.classList.remove("is-open");
    setTimeout(() => { if (!backdrop.classList.contains("is-open")) backdrop.hidden = true; }, 260);
    el("sheetToggle").setAttribute("aria-expanded", "false");
  }
  el("sheetToggle").addEventListener("click", () => (sheet.classList.contains("is-open") ? closeSheet() : openSheet()));
  el("layersClose").addEventListener("click", closeSheet);
  backdrop.addEventListener("click", closeSheet);

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      if (state.timer) { state.autoResume = true; stopPlay(); }
    } else if (state.autoResume) {
      state.autoResume = false;
      startPlay();
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.target.matches("input, textarea, select")) return;
    if (e.code === "Space") { e.preventDefault(); state.timer ? stopPlay() : startPlay(); }
    else if (e.code === "ArrowLeft") { stopPlay(); setFrame(state.index - 1); }
    else if (e.code === "ArrowRight") { stopPlay(); setFrame(state.index + 1); }
    else if (e.code === "Home") { stopPlay(); setFrame(0); }
    else if (e.code === "End") { stopPlay(); setFrame(FRAMES.length - 1); }
    else if (e.code === "Escape") { closeSheet(); setArchiveOpen(false); setModesOpen(false); }
  });

  function tickClock() { el("clock").textContent = clockFmt.format(new Date()); }
  tickClock();
  setInterval(tickClock, 1000);

  /* ---------- boot ---------- */
  renderTicks();
  el("scrub").max = String(FRAMES.length - 1);
  updateMeta();
  renderFrame();

  const deepLinked = restoreUrl();
  if (deepLinked) {
    radar.redraw();
    glow.redraw();
    renderFrame();
  }

  if (!IS_FILE) {
    fetch(API + "/api/state").then((r) => r.json()).then((m) => {
      if (m && m.frames && m.frames.length) {
        const liveId = m.frames[0] && m.frames[0].id;
        if (liveId !== FRAMES[0].id) applyManifest(m, "live");
      }
    }).catch(() => {});
  }

  if (!deepLinked && window.matchMedia("(min-width: 861px)").matches) {
    setTimeout(() => { if (!state.timer && !document.hidden) startPlay(); }, 1400);
  }
})();

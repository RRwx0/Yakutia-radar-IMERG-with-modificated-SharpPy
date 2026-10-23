from pathlib import Path

p = Path("client/app.js")
s = p.read_text(encoding="utf-8")

anchor = '  modelSelect.addEventListener("change", () => {'
code = '''  modelSelect.addEventListener("change", () => {
    if (el("modelToggle").checked) loadModel(modelSelect.value);
  });

  /* ---------- предупреждения (зоны риска по GFS) ---------- */
  let warnLayer = null;
  let warnZones = [];
  const KIND_ORDER = { severe: 0, watch: 1, mention: 2 };
  async function loadWarnings() {
    const base = (window.API_BASE || "").replace(/\\/$/, "");
    try {
      const r = await fetch(base + "/api/warnings", { cache: "no-store" });
      if (!r.ok) throw new Error("HTTP " + r.status);
      const j = await r.json();
      warnZones = j.zones || [];
      renderWarnings();
    } catch (e) {
      renderWarningsError();
      console.error("warnings", e);
    }
  }
  function renderWarnings() {
    if (!warnLayer) {
      warnLayer = L.layerGroup();
      warnLayer.addTo(map);
    }
    warnLayer.clearLayers();
    const list = el("warnList");
    if (!list) return;
    list.innerHTML = "";
    if (!warnZones.length) {
      el("warnMeta").textContent = "Активных предупреждений нет";
      return;
    }
    warnZones.slice().sort((a, b) => (KIND_ORDER[a.kind] - KIND_ORDER[b.kind]) || (b.cape - a.cape)).forEach((z) => {
      const b = z.bounds || [[z.lat - 0.5, z.lon - 0.5], [z.lat + 0.5, z.lon + 0.5]];
      L.rectangle(b, {
        color: z.color, weight: 1.6, fillColor: z.color, fillOpacity: 0.16,
        interactive: true
      }).bindTooltip(z.label + " · CAPE " + z.cape + " · сдвиг " + z.shear + " м/с").addTo(warnLayer);
      const item = document.createElement("div");
      item.className = "warn-item warn-item--" + z.kind;
      item.innerHTML = '<i style="background:' + z.color + '"></i><span>' + z.label + "</span>";
      (() => {
        const zz = z;
        item.addEventListener("click", () => {
          map.flyTo([zz.lat, zz.lon], 6, { duration: 0.6 });
        });
      })();
      list.appendChild(item);
    });
    el("warnMeta").textContent = "обновлено " + (el("frameTime").textContent || "") + " · GFS";
  }
  function renderWarningsError() {
    const list = el("warnList");
    if (list) list.innerHTML = '<span class="warn-item">бэкенд не подключён</span>';
  }
  el("warnToggle").addEventListener("change", (e) => {
    if (e.target.checked) {
      el("warnPanel").hidden = false;
      loadWarnings();
    } else if (warnLayer) {
      el("warnPanel").hidden = true;
      map.removeLayer(warnLayer);
    }
  });
  el("warnClose").addEventListener("click", () => {
    el("warnToggle").checked = false;
    if (warnLayer) map.removeLayer(warnLayer);
    el("warnPanel").hidden = true;
  });
  loadWarnings();
'''

if anchor in s:
    s = s.replace(anchor, code, 1)
    p.write_text(s, encoding="utf-8")
    print("warnings js added")
else:
    print("anchor NOT found")
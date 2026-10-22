import pathlib, re
p = pathlib.Path("client/app.js")
s = p.read_text(encoding="utf-8")

# remove stations layer block
start = s.index("  const zones = L.layerGroup().addTo(map);")
end = s.index("  const placesLayer = L.layerGroup().addTo(map);")
s = s[:start] + s[end:]

# remove stations toggle handler
s = s.replace('''  el("stationsToggle").addEventListener("change", (e) => {
    if (e.target.checked) { stationsLayer.addTo(map); zones.addTo(map); }
    else { map.removeLayer(stationsLayer); map.removeLayer(zones); }
  });
''', "")

# chips from cities instead of stations
old_chips = s[s.index("  /* chips */"):s.index("  /* mobile sheet */")]
new_chips = '''  /* chips */
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

'''
s = s.replace(old_chips, new_chips)

# metric + footer
s = s.replace('''  el("metricSkill").textContent = M.nowcast && M.nowcast.skill && M.nowcast.skill.improvement_pct != null
    ? Math.round(M.nowcast.skill.improvement_pct) : "—";
  el("footMeta").textContent = "кадров: " + FRAMES.length + " · обновлено " + fmtTime(M.generated_at) + " (Якутск) · " + M.stations.length + " радара";''',
'''  const method = M.nowcast && M.nowcast.method === "persistence" ? "инерция" : "адвекция";
  el("metricMethod").textContent = method;
  el("footMeta").textContent = "кадров: " + FRAMES.length + " · " + M.source.name + " · обновлено " + fmtTime(M.generated_at) + " (Якутск)";''')

p.write_text(s, encoding="utf-8")
print("stations refs left:", s.count("stationsLayer"), s.count("zones"))

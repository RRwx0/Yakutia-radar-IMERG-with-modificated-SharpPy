import pathlib
p = pathlib.Path("client/app.js")
s = p.read_text(encoding="utf-8")
s = s.replace('else if (e.code === "Escape") { closeSheet(); setArchiveOpen(false); }',
              'else if (e.code === "Escape") { closeSheet(); setArchiveOpen(false); setModesOpen(false); }')
s = s.replace('    if (m.focus) map.fitBounds(m.focus, { paddingTopLeft: [320, 30], paddingBottomRight: [350, 150], maxZoom: 6 });',
              '    if (m.focus) map.fitBounds(m.focus, { paddingTopLeft: [320, 30], paddingBottomRight: [350, 150], maxZoom: 6 });\n    updateLatency();')
p.write_text(s, encoding="utf-8")
print("esc", "setModesOpen(false); }" in s, "lat", s.count("updateLatency();"))

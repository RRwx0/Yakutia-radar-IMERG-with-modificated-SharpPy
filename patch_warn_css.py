from pathlib import Path

p = Path("client/styles.css")
s = p.read_text(encoding="utf-8")

css = """
.warn-panel{position:absolute;left:14px;bottom:86px;width:290px;max-height:42vh;display:flex;flex-direction:column;background:rgba(8,14,22,.92);border:1px solid var(--line);border-radius:14px;padding:10px 12px;z-index:600;backdrop-filter:blur(4px)}
.warn-panel__head{display:flex;justify-content:space-between;align-items:center;font-size:13px;letter-spacing:.04em;color:var(--fg);margin-bottom:6px}
.warn-list{overflow:auto;display:flex;flex-direction:column;gap:6px}
.warn-item{display:flex;gap:8px;align-items:center;padding:7px 8px;border:1px solid var(--line);border-radius:9px;font-size:12.5px;color:#dceaf2;cursor:pointer;background:rgba(20,32,46,.4)}
.warn-item:hover{border-color:var(--acc)}
.warn-item i{width:9px;height:9px;border-radius:50%;flex:0 0 auto}
.warn-panel__meta{font-size:11px;color:var(--muted);margin:7px 0 0}
body.broadcast .warn-panel{background:rgba(0,0,0,.9)}
@media (max-width:760px){.warn-panel{left:10px;right:10px;width:auto;bottom:150px}}
"""

if ".warn-panel{" not in s:
    s += css
    p.write_text(s, encoding="utf-8")
    print("css added")
else:
    print("css exists")
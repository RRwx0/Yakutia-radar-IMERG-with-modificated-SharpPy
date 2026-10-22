from pathlib import Path
src = Path("index.html").read_text(encoding="utf-8")
preview = src.replace('<aside class="modes" id="modesPanel" hidden', '<aside class="modes" id="modesPanel"')
Path("_preview-modes.html").write_text(preview, encoding="utf-8")
print("ok")

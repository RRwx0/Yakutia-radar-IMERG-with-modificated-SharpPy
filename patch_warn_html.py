import re
from pathlib import Path

p = Path("client/index.html")
s = p.read_text(encoding="utf-8")

# панель списка предупреждений в нижней части хедера страницы (перед #timeline)
panel = """    <div class="warn-panel" id="warnPanel" hidden>
      <div class="warn-panel__head">
        <strong>Предупреждения</strong>
        <button class="icon-btn" id="warnClose" aria-label="Закрыть">×</button>
      </div>
      <div id="warnList" class="warn-list"></div>
      <p class="warn-panel__meta" id="warnMeta"></p>
    </div>
"""
anchor = '    <div class="timeline" id="timeline">'
if anchor in s and 'id="warnPanel"' not in s:
    s = s.replace(anchor, panel + anchor)
    print("panel added")

# переключатель в панели слоёв — после блока модельного радара
sw = """      <label class="switch">
        <input type="checkbox" id="warnToggle">
        <span class="switch__ui"></span>
        <span class="switch__text"><strong>Предупреждения</strong><em>зоны риска по GFS</em></span>
      </label>
"""
anchor2 = '      <label class="mode__row">Модель'
if anchor2 in s and 'id="warnToggle"' not in s:
    s = s.replace(anchor2, sw + anchor2)
    print("toggle added")

p.write_text(s, encoding="utf-8")
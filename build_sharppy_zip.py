from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

root = Path("client/sharppy")
files = sorted((root / "files").glob("*.py"))
readme = (
    "SHARPpy \u2014 \u043c\u043e\u0434\u0438\u0444\u0438\u043a\u0430\u0446\u0438\u044f hen1ch\n"
    "=========================================\n\n"
    "\u0410\u0432\u0442\u043e\u0440 \u043c\u043e\u0434\u0438\u0444\u0438\u043a\u0430\u0446\u0438\u0438 \u0438 \u043e\u0431\u043e\u043b\u043e\u0447\u043a\u0438: hen1ch, 2026\n\n"
    "\u0421\u043e\u0441\u0442\u0430\u0432:\n"
    "  wx_launcher.py      \u2014 \u043e\u0431\u043e\u043b\u043e\u0447\u043a\u0430: \u0438\u0441\u0442\u043e\u0447\u043d\u0438\u043a\u0438, \u043a\u0435\u0448, \u043a\u0430\u0440\u0442\u0430, \u043f\u0440\u043e\u0441\u043c\u043e\u0442\u0440\n"
    "  sharppy_core.py     \u2014 \u044f\u0434\u0440\u043e \u0440\u0430\u0441\u0447\u0451\u0442\u043e\u0432 \u0438 Skew-T\n"
    "  sharppy_layout.py   \u2014 \u043a\u043e\u043c\u043f\u043e\u043d\u043e\u0432\u043a\u0430 \u043e\u043a\u043d\u0430 SHARPpy \u0438 \u0432\u0440\u0435\u0437\u043a\u0438\n"
    "  stations_lookup.py  \u2014 \u043f\u043e\u0438\u0441\u043a \u0441\u0442\u0430\u043d\u0446\u0438\u0439, ICAO, \u043a\u043e\u043e\u0440\u0434\u0438\u043d\u0430\u0442\u044b\n"
    "  i18n.py             \u2014 \u0440\u0443\u0441\u0441\u043a\u0438\u0439 \u0438 \u0430\u043d\u0433\u043b\u0438\u0439\u0441\u043a\u0438\u0439 \u0438\u043d\u0442\u0435\u0440\u0444\u0435\u0439\u0441\n\n"
    "\u0417\u0430\u043f\u0443\u0441\u043a:\n"
    "  pip install requests\n"
    "  python wx_launcher.py\n\n"
    "\u0414\u043b\u044f \u0440\u0430\u0441\u0447\u0451\u0442\u043e\u0432 \u0438 \u0433\u0440\u0430\u0444\u0438\u043a\u043e\u0432 \u043d\u0443\u0436\u0435\u043d \u0443\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d\u043d\u044b\u0439 SHARPpy:\n"
    "  conda install -c conda-forge sharppy\n"
)
with ZipFile(root / "sharpy-hen1ch.zip", "w", ZIP_DEFLATED) as z:
    z.writestr("README.txt", readme)
    for f in files:
        z.write(f, arcname=f.name)
print("zip", (root / "sharpy-hen1ch.zip").stat().st_size, "files", len(files))

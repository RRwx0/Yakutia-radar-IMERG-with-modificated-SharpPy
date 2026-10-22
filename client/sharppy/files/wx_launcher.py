#!/usr/bin/env python3
"""
WX Sounding Launcher — оболочка для SHARPpy.

Зачем: SHARPpy сам ходит в сеть за данными, а половина его источников
давно мертва — отсюда вылеты при клике по точкам. Здесь загрузка вынесена
наружу: оболочка скачивает профиль, кладёт в кеш, пишет .snd и отдаёт
SHARPpy готовый локальный файл. В сеть SHARPpy при этом не ходит вообще.

Источники:
  * Вайоминг    — фактические зондирования (ARCC endpoint)
  * Open-Meteo  — модельные профили (GFS, ICON, ECMWF, ARPEGE, GEM)
  * Свой файл   — любой готовый .snd

Кеш: файлы лежат в cache/ рядом со скриптом, ключ — источник, станция,
дата, срок и модель. Повторный запрос берётся с диска. Раз в запуск
чистится по возрасту и объёму, чтобы не засорять диск.

Зависимости: requests (остальное из стандартной поставки).
    python wx_launcher.py
"""
import json
import math
import os
import queue
import re
import subprocess
import sys
import threading
import time
import tkinter as tk
from datetime import datetime, timedelta, timezone
from tkinter import filedialog, messagebox, ttk

import stations_lookup as SL

try:
    import requests
except ImportError:
    sys.exit(_('Нужен requests:  conda install -c conda-forge requests'))

# Где лежат наши файлы. Из exe __file__ указывает во временную папку
# распаковки, куда писать нельзя и откуда всё стирается после выхода,
# поэтому кеш, настройки и карту держим рядом с самим .exe.
FROZEN = getattr(sys, 'frozen', False)
HERE = (os.path.dirname(sys.executable) if FROZEN
        else os.path.dirname(os.path.abspath(__file__)))
# а данные, упакованные внутрь сборки, — в папке распаковки
BUNDLE = getattr(sys, '_MEIPASS', HERE)


def _fix_certificates():
    """Указывает requests путь к сертификатам внутри сборки.

    Именно это ломалось с ошибкой pyi_rth_certifi: в exe не попадал
    файл cacert.pem, и HTTPS-запросы к Вайомингу и Open-Meteo не могли
    проверить сертификат сервера. Сам файл кладёт в сборку ключ
    --collect-data certifi, а здесь мы явно говорим, где его искать.
    """
    try:
        import certifi
        pem = certifi.where()
        if os.path.exists(pem):
            os.environ.setdefault('SSL_CERT_FILE', pem)
            os.environ.setdefault('REQUESTS_CA_BUNDLE', pem)
    except Exception:
        pass


_fix_certificates()
CACHE = os.path.join(HERE, 'cache')
CFG = os.path.join(HERE, 'wx_launcher.json')

import i18n
i18n.init(CFG)
_, N = i18n._, i18n.N
UA = {'User-Agent': 'Mozilla/5.0'}
MISSING = -9999.0

CACHE_MAX_DAYS = 30
CACHE_MAX_MB = 300

# Станции: id Вайоминга, название, широта, долгота.
# Список можно расширить в wx_launcher.json (ключ "stations").
STATIONS = [
    ('24959', 'Якутск', 62.02, 129.72),
    ('24266', 'Верхоянск', 67.55, 133.38),
    ('24688', 'Оймякон', 63.25, 143.15),
    ('24908', 'Вилюйск', 63.77, 121.62),
    ('30710', 'Олёкминск', 60.40, 120.42),
    ('24944', 'Хандыга', 62.67, 135.60),
    ('21432', 'Тикси', 71.58, 128.92),
    ('25123', 'Черский', 68.75, 161.28),
    ('30758', 'Чита', 52.08, 113.48),
    ('30635', 'Иркутск', 52.27, 104.35),
    ('29634', 'Новосибирск', 55.03, 82.90),
    ('29862', 'Красноярск', 56.18, 92.62),
    ('31510', 'Благовещенск', 50.27, 127.50),
    ('31960', 'Владивосток', 43.12, 131.93),
    ('31736', 'Хабаровск', 48.53, 135.17),
    ('32540', 'Петропавловск-Камчатский', 53.08, 158.58),
    ('28698', 'Курган', 55.47, 65.40),
    ('27612', 'Москва (Долгопрудный)', 55.75, 37.57),
    ('26063', 'Санкт-Петербург', 59.97, 30.30),
    ('34880', 'Астрахань', 46.28, 48.03),
    ('23955', 'Александровское', 60.43, 77.87),
    ('20744', 'Малые Кармакулы', 72.37, 52.70),
]

# gfs_global, а не gfs_seamless: seamless склеивает несколько продуктов
# NOAA, и на один и тот же срок может отдать разное. Для сопоставимости
# берём предсказуемо один глобальный продукт.
MODELS = [
    ('Arpege', 'meteofrance_arpege_world'),
    ('ICON', 'icon_global'),
    ('GFS', 'gfs_global'),
    ('ECMWF', 'ecmwf_ifs'),
    ('GEM', 'gem_seamless'),
]

OBS = 'Observed (Wyoming)'

LEVELS = [1000, 950, 925, 900, 850, 800, 750, 700, 650, 600, 550, 500,
          450, 400, 350, 300, 275, 250, 225, 200, 175, 150, 125, 100,
          70, 50, 30, 10]


# --------------------------------------------------------------- кеш
def cache_path(key):
    os.makedirs(CACHE, exist_ok=True)
    return os.path.join(CACHE, key + '.snd')


def cache_sweep():
    """Удаляет старое и лишнее. Возвращает (файлов, мегабайт) после чистки."""
    if not os.path.isdir(CACHE):
        return 0, 0.0
    files = []
    for n in os.listdir(CACHE):
        p = os.path.join(CACHE, n)
        if os.path.isfile(p):
            files.append((os.path.getmtime(p), os.path.getsize(p), p))
    now = time.time()
    keep = []
    for mt, sz, p in files:
        if (now - mt) / 86400 > CACHE_MAX_DAYS:
            try:
                os.remove(p)
            except OSError:
                keep.append((mt, sz, p))
        else:
            keep.append((mt, sz, p))
    keep.sort()                                  # старые первыми
    total = sum(s for _, s, _ in keep)
    while total > CACHE_MAX_MB * 1e6 and keep:
        mt, sz, p = keep.pop(0)
        try:
            os.remove(p)
            total -= sz
        except OSError:
            break
    return len(keep), total / 1e6


# --------------------------------------------------------------- .snd
def write_snd(path, station, dt, levels):
    """levels: список (p, z, t, td, wd, ws_kts)."""
    out = ['%TITLE%',
           f' {station}   {dt:%y%m%d}/{dt:%H}00',
           '   LEVEL      HGHT       TEMP       DWPT       WDIR       WSPD',
           '-' * 66, '%RAW%']
    for p, z, t, td, wd, ws in levels:
        out.append(f'{p:7.1f},{z:10.1f},{t:10.1f},{td:10.1f},{wd:10.1f},{ws:10.1f}')
    out.append('%END%')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out) + '\n')


# --------------------------------------------------------------- Вайоминг
def fetch_wyoming(station, dt):
    url = ('https://weather.arcc.uwyo.edu/wsgi/sounding?'
           f'datetime={dt:%Y-%m-%d}%20{dt:%H}:00:00'
           f'&id={station}&src=UNKNOWN&type=TEXT:LIST')
    r = requests.get(url, headers=UA, timeout=40)
    r.raise_for_status()
    txt = r.text
    if '<PRE>' in txt:
        txt = txt.split('<PRE>')[1].split('</PRE>')[0]
    lines = txt.split('\n')
    hi = next((i for i, l in enumerate(lines)
               if 'PRES' in l and 'HGHT' in l and 'TEMP' in l), None)
    if hi is None:
        raise RuntimeError(_('Вайоминг не вернул профиль на этот срок.'))
    head = lines[hi]
    knots = 'SKNT' in head

    import re as _re
    def col(*names):
        for n in names:
            k = head.find(n)
            if k >= 0:
                return k + len(n)
        return None
    ends = {'p': col('PRES'), 'z': col('HGHT'), 't': col('TEMP'),
            'd': col('DWPT'), 'wd': col('DRCT'), 'ws': col('SPED', 'SKNT')}
    if any(v is None for v in ends.values()):
        raise RuntimeError(_('Не разобрал заголовок таблицы.'))
    allends = [m.end() for m in _re.finditer(r'\S+', head)]
    starts = {k: max([e for e in allends if e < v], default=0)
              for k, v in ends.items()}

    def grab(line, k):
        s = line[starts[k]:ends[k]].strip()
        try:
            return float(s)
        except ValueError:
            return None

    rows = []
    for line in lines[hi + 1:]:
        if not line.strip() or '---' in line or 'Station' in line:
            continue
        p, z, t = grab(line, 'p'), grab(line, 'z'), grab(line, 't')
        if None in (p, z, t):
            continue
        d = grab(line, 'd')
        wd, ws = grab(line, 'wd'), grab(line, 'ws')
        if wd is None or ws is None:
            wd = ws = MISSING
        elif not knots:
            ws *= 1.944
        rows.append((p, z, t, MISSING if d is None else d, wd, ws))
    if not rows:
        raise RuntimeError(_('Профиль пустой.'))
    rows.sort(key=lambda r: -r[0])
    clean, lp, lz = [], None, None
    for r in rows:
        if lp is not None and abs(r[0] - lp) < 0.01:
            continue
        if lz is not None and r[1] <= lz:
            continue
        clean.append(r)
        lp, lz = r[0], r[1]
    return clean


# --------------------------------------------------------------- Open-Meteo
def fetch_openmeteo(lat, lon, dt, model):
    hourly = ['temperature_2m', 'dew_point_2m', 'surface_pressure',
              'wind_speed_10m', 'wind_direction_10m']
    for p in LEVELS:
        hourly += [f'temperature_{p}hPa', f'relative_humidity_{p}hPa',
                   f'wind_speed_{p}hPa', f'wind_direction_{p}hPa',
                   f'geopotential_height_{p}hPa']
    past = (datetime.now(timezone.utc) - dt).days
    # archive-api (ERA5) уровней давления не содержит — только приземные поля.
    # А historical-forecast-api отдаёт полный профиль по архивным прогонам
    # моделей, начиная с 2021 года. Оперативный forecast — для свежих дат.
    if past > 7:
        base = 'https://historical-forecast-api.open-meteo.com/v1/forecast'
        par = {'latitude': lat, 'longitude': lon,
               'hourly': ','.join(hourly), 'wind_speed_unit': 'kn',
               'timezone': 'UTC', 'models': model,
               'start_date': dt.strftime('%Y-%m-%d'),
               'end_date': dt.strftime('%Y-%m-%d')}
    else:
        base = 'https://api.open-meteo.com/v1/forecast'
        par = {'latitude': lat, 'longitude': lon,
               'hourly': ','.join(hourly), 'wind_speed_unit': 'kn',
               'timezone': 'UTC', 'models': model,
               'past_days': min(max(past + 1, 1), 92), 'forecast_days': 16}
    r = requests.get(base, params=par, headers=UA, timeout=60)
    r.raise_for_status()
    js = r.json()
    h = js.get('hourly')
    if not h:
        raise RuntimeError(js.get('reason', _('Open-Meteo не вернул данные.')))
    stamp = dt.strftime('%Y-%m-%dT%H:00')
    if stamp not in h['time']:
        raise RuntimeError(_('Нет срока {stamp} в ответе модели.').format(stamp=stamp))
    i = h['time'].index(stamp)

    def g(name):
        v = h.get(name)
        return None if v is None or v[i] is None else float(v[i])

    def dewpoint(t, rh):
        import math
        rh = max(min(rh, 100.0), 1.0)
        a, b = 17.625, 243.04
        al = math.log(rh / 100.0) + a * t / (b + t)
        return b * al / (a - al)

    rows = []
    psfc = g('surface_pressure')
    tsfc, tdsfc = g('temperature_2m'), g('dew_point_2m')
    if None not in (psfc, tsfc, tdsfc):
        rows.append((psfc, 0.0, tsfc, tdsfc,
                     g('wind_direction_10m') or 0.0, g('wind_speed_10m') or 0.0))
    for p in LEVELS:
        if psfc and p > psfc:
            continue
        t = g(f'temperature_{p}hPa')
        z = g(f'geopotential_height_{p}hPa')
        rh = g(f'relative_humidity_{p}hPa')
        if None in (t, z):
            continue
        td = dewpoint(t, rh) if rh is not None else MISSING
        rows.append((float(p), z, t, td,
                     g(f'wind_direction_{p}hPa') or 0.0,
                     g(f'wind_speed_{p}hPa') or 0.0))
    if len(rows) < 5:
        got = [p for p in LEVELS if h.get(f'temperature_{p}hPa')
               and h[f'temperature_{p}hPa'][i] is not None]
        miss = [k for k in ('temperature_1000hPa', 'geopotential_height_1000hPa',
                            'relative_humidity_1000hPa')
                if k not in h]
        raise RuntimeError(
            _('Модель вернула {n} уровней (нужно 5+).\nМодель: {model}, '
              'дней назад: {age}').format(n=len(rows), model=model, age=past)
            + '\n' + _('Уровни с температурой: {got}').format(
                got=got if got else _('нет')) + '\n'
            + (_('Нет полей: {fields}\n').format(fields=', '.join(miss))
               if miss else '')
            + _('Для дат старше 92 дней доступен только архив ERA5, '
              'и выбор модели там не действует.'))
    rows.sort(key=lambda r: -r[0])
    if rows and rows[0][1] == 0.0 and len(rows) > 1:
        # высота приземного уровня по гипсометрической формуле
        # относительно ближайшего изобарического
        import math
        p1, z1, t1 = rows[1][0], rows[1][1], rows[1][2]
        p0, t0 = rows[0][0], rows[0][2]
        tm = (t0 + t1) / 2 + 273.15
        dz = 29.27 * tm * math.log(p0 / p1)
        rows[0] = (p0, max(z1 - dz, 0.0)) + rows[0][2:]
    out, lz = [], None
    for r in rows:
        if lz is not None and r[1] <= lz:
            continue
        out.append(r)
        lz = r[1]
    return out



MONTHS_RU = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль',
             'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
DAYS_RU = ['П', 'В', 'С', 'Ч', 'П', 'С', 'В']
if i18n.LANG == 'en':
    MONTHS_RU, DAYS_RU = i18n.MONTHS_EN, i18n.DAYS_EN


class Calendar(tk.Frame):
    """Месячный календарь как в окне выбора SHARPpy.

    Своя реализация: в стандартном tkinter календаря нет, а тянуть
    tkcalendar ради одной сетки — лишняя зависимость при сборке.
    Заголовок повторяет оригинал: стрелки, выпадающий месяц, счётчик года.
    """

    def __init__(self, master, bg, panel, fg, acc, on_pick, day_fg='#1a5fb4'):
        super().__init__(master, bg=bg, highlightthickness=1,
                         highlightbackground='#a0a0a0')
        self.bg, self.panel, self.fg, self.acc = bg, panel, fg, acc
        self.day_fg = day_fg
        self.on_pick = on_pick
        today = datetime.now(timezone.utc).date()
        self.selected = today
        self._busy = False

        head = tk.Frame(self, bg=acc)
        head.pack(fill='x')
        for txt, d, side in (('\u2190', -1, 'left'), ('\u2192', 1, 'right')):
            tk.Button(head, text=txt, command=lambda dd=d: self.shift(dd),
                      bg=acc, fg='white', relief='flat', bd=0,
                      activebackground=acc, activeforeground='white',
                      highlightthickness=0, font=('Segoe UI', 10, 'bold'),
                      cursor='hand2', padx=6).pack(side=side)

        # месяц и год не должны выделяться из синей полосы, поэтому вместо
        # обычных полей ввода — кнопка-меню и счётчик, покрашенные в тот же цвет
        self.mon_i = tk.IntVar(value=datetime.now(timezone.utc).month)
        self.mb = tk.Menubutton(head, bg=acc, fg='white', relief='flat', bd=0,
                                activebackground=acc, activeforeground='white',
                                highlightthickness=0, cursor='hand2',
                                font=('Segoe UI', 9, 'bold'))
        menu = tk.Menu(self.mb, tearoff=0)
        for i, m in enumerate(MONTHS_RU, 1):
            menu.add_radiobutton(label=m, variable=self.mon_i, value=i,
                                 command=self.from_head)
        self.mb.config(menu=menu)
        self.mb.pack(side='left', expand=True)

        self.yr = tk.Spinbox(head, from_=1946, to=2100, width=5,
                             font=('Segoe UI', 9, 'bold'),
                             bg=acc, fg='white', relief='flat', bd=0,
                             highlightthickness=0, buttonbackground=acc,
                             readonlybackground=acc, insertbackground='white',
                             justify='center', command=self.from_head)
        self.yr.delete(0, 'end')
        self.yr.insert(0, str(today.year))
        self.yr.bind('<Return>', lambda e: self.from_head())
        self.yr.pack(side='left', padx=(0, 4))

        grid = tk.Frame(self, bg='#ffffff')
        grid.pack(fill='both')
        for c, d in enumerate(DAYS_RU):
            tk.Label(grid, text=d, bg='#ffffff', fg=self.acc, width=3,
                     font=('Segoe UI', 8, 'bold')).grid(row=0, column=c)
        self.cells = []
        for r in range(6):
            row = []
            for c in range(7):
                b = tk.Label(grid, text='', bg='#ffffff', fg=fg, width=3,
                             font=('Segoe UI', 9), cursor='hand2')
                b.grid(row=r + 1, column=c, padx=1, pady=1)
                b.bind('<Button-1>', lambda e, rr=r, cc=c: self.click(rr, cc))
                row.append(b)
            self.cells.append(row)
        self.redraw()

    @property
    def year(self):
        try:
            return int(self.yr.get())
        except ValueError:
            return datetime.now(timezone.utc).year

    @property
    def month(self):
        return self.mon_i.get()

    def from_head(self):
        if not self._busy:
            self.redraw()

    def shift(self, d):
        m = self.month + d
        y = self.year + (m - 1) // 12
        m = (m - 1) % 12 + 1
        self._busy = True
        self.mon_i.set(m)
        self.yr.delete(0, 'end')
        self.yr.insert(0, str(y))
        self._busy = False
        self.redraw()

    def click(self, r, c):
        d = self.cells[r][c].day
        if d:
            self.selected = d
            self.redraw()
            self.on_pick(d)

    def redraw(self):
        import calendar as _cal
        self.mb.config(text=MONTHS_RU[self.month - 1])
        weeks = _cal.Calendar(firstweekday=0).monthdatescalendar(
            self.year, self.month)
        for r in range(6):
            for c in range(7):
                cell = self.cells[r][c]
                if r < len(weeks):
                    d = weeks[r][c]
                    cell.day = d
                    cell.config(text=str(d.day))
                    if d == self.selected:
                        cell.config(bg=self.acc, fg='white',
                                    font=('Segoe UI', 9, 'bold'))
                    elif d.month != self.month:
                        cell.config(bg='#ffffff', fg='#c0c0c0',
                                    font=('Segoe UI', 9))
                    else:
                        cell.config(bg='#ffffff', fg=self.day_fg,
                                    font=('Segoe UI', 9))
                else:
                    cell.day = None
                    cell.config(text='', bg='#ffffff')


class _TitleStatus:
    """Сообщения в заголовке окна: в оригинале строки состояния нет."""

    def __init__(self, win):
        self.win = win

    def config(self, text=''):
        self.win.title('WX Sounding Launcher' + (f' — {text}' if text else ''))


class _MenuCache:
    """Размер кеша показываем пунктом меню, а не подписью в окне."""

    def __init__(self, win, menu):
        self.menu = menu
        self.menu.add_separator()
        self.menu.add_command(label=_('Кеш: —'), state='disabled')
        self.idx = self.menu.index('end')

    def config(self, text=''):
        self.menu.entryconfig(self.idx, label=text or _('Кеш: —'))




# --------------------------------------------------------------- встроенный просмотр
def read_snd_arrays(path):
    """Читает .snd в аргументы для profile.create_profile.

    Кроме массивов достаём станцию и дату из заголовка: без них
    ConvectiveProfile не собирается — ему нужен месяц, чтобы определить
    климатический режим влагозапаса, и тогда считаются SARS, пожарные
    индексы и зимний блок. Без даты сборка падает и молча откатывается
    на BasicProfile, где половины полей просто нет.

    Пропуски отдаём как -9999: SHARPpy считает это своим признаком
    отсутствия данных и маскирует такие уровни сам.
    """
    import numpy as np
    from datetime import datetime
    txt = open(path, encoding='utf-8', errors='replace').read().replace('\r', '')
    if '%RAW%' not in txt:
        raise RuntimeError(_('Не похоже на файл .snd'))

    station, when = '', None
    head = txt.split('%RAW%')[0].split('\n')
    for line in head:
        m = re.search(r'(\S+)\s+(\d{6})/(\d{2})(\d{2})', line)
        if m:
            station = m.group(1)
            yy = int(m.group(2)[:2])
            year = 2000 + yy if yy < 70 else 1900 + yy
            try:
                when = datetime(year, int(m.group(2)[2:4]), int(m.group(2)[4:6]),
                                int(m.group(3)), int(m.group(4)))
            except ValueError:
                when = None
            break

    rows = []
    for line in txt.split('%RAW%')[1].split('%END%')[0].strip().split('\n'):
        p = [x.strip() for x in line.split(',')]
        if len(p) < 6:
            continue
        try:
            rows.append([float(x) for x in p[:6]])
        except ValueError:
            continue
    if len(rows) < 5:
        raise RuntimeError(_('В файле меньше пяти уровней'))
    a = np.array(rows, dtype=float)
    out = dict(pres=a[:, 0], hght=a[:, 1], tmpc=a[:, 2],
               dwpc=a[:, 3], wdir=a[:, 4], wspd=a[:, 5])
    if station:
        out['location'] = station
    if when is not None:
        out['date'] = when
    return out


def darken(fig):
    """Перекрашивает готовую фигуру в тёмную схему окна SHARPpy.

    Цветные элементы не трогаем: красная T, зелёная Td, синие изотермы,
    оранжевые адиабаты — цвет несёт смысл. Меняем только серые тона:
    у них насыщенность около нуля, и по яркости видно, тёмные они или
    светлые. Тёмно-серый текст на чёрном фоне нечитаем, поэтому все
    серые светлее делаем, сохраняя их относительную иерархию.
    """
    from matplotlib.colors import to_rgb

    def fix(c, floor=0.72):
        try:
            r, g, b = to_rgb(c)
        except Exception:
            return None
        if max(r, g, b) - min(r, g, b) > 0.12:
            return None                      # цветной — не трогаем
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        if lum > 0.65:
            return None                      # уже светлый
        # тёмные оттенки разворачиваем в светлые, порядок яркости сохраняем
        v = floor + (1.0 - floor) * (1.0 - min(lum / 0.65, 1.0))
        return (v, v, v)

    fig.patch.set_facecolor('#000000')
    for t in fig.texts:
        nc = fix(t.get_color())
        if nc:
            t.set_color(nc)

    for ax in fig.get_axes():
        ax.set_facecolor('#000000')
        for s in ax.spines.values():
            s.set_color('#8a8a8a')
        ax.tick_params(colors='#cfcfcf')
        for t in list(ax.get_xticklabels()) + list(ax.get_yticklabels()):
            t.set_color('#cfcfcf')
        ax.xaxis.label.set_color('#cfcfcf')
        ax.yaxis.label.set_color('#cfcfcf')
        if ax.get_title():
            ax.title.set_color('#ffffff')
        for t in ax.texts:
            nc = fix(t.get_color())
            if nc:
                t.set_color(nc)
        for ln in ax.lines:
            nc = fix(ln.get_color(), floor=0.45)
            if nc:
                ln.set_color(nc)
        lg = ax.get_legend()
        if lg is not None:
            lg.get_frame().set_facecolor('#121212')
            lg.get_frame().set_edgecolor('#8a8a8a')
            for t in lg.get_texts():
                t.set_color('#e8e8e8')


class Viewer(tk.Toplevel):
    """Окно профиля: Skew-T, годограф и таблицы прямо в оболочке.

    Расчёт и отрисовка берутся из sharppy_core — того же модуля, что
    работает в боте. Само приложение SHARPpy при этом не запускается,
    используются только его расчётные функции.
    """

    def __init__(self, master, path, dark=True):
        super().__init__(master)
        self.title(os.path.basename(path))
        self.geometry('1400x900')
        self.fig = None
        self.dark = dark
        self.path = path
        self.prof = None
        self.editor = None
        self.parcel_flag = 3          # по умолчанию MU, как в SHARPpy
        self.inset = 'stp'            # правая нижняя врезка

        bar = ttk.Frame(self)
        bar.pack(fill='x', padx=6, pady=4)
        ttk.Label(bar, text=os.path.basename(path)).pack(side='left')
        ttk.Button(bar, text=_('Сохранить PNG'),
                   command=self.save).pack(side='right')
        self.dark_var = tk.BooleanVar(value=dark)
        ttk.Checkbutton(bar, text=_('Тёмная схема'), variable=self.dark_var,
                        command=self.reload).pack(side='right', padx=8)
        self.edit_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(bar, text=_('Правка кривых'), variable=self.edit_var,
                        command=self.reload).pack(side='right', padx=8)
        ttk.Button(bar, text=_('Сбросить правки'),
                   command=self.reset_prof).pack(side='right', padx=4)

        self.holder = ttk.Frame(self)
        self.holder.pack(fill='both', expand=True)
        self.canvas = None
        self.status = ttk.Label(self, text=_('Считаю профиль...'), anchor='w')
        self.status.pack(fill='x', padx=6, pady=(0, 4))
        self.after(50, self.reload)

    def reload(self):
        try:
            import sharppy_core as core
        except Exception as e:
            self.status.config(text=_('Нет sharppy_core.py'))
            messagebox.showerror(
                _('Нет модуля'),
                f'{e}\n\n' + _('Положи sharppy_core.py рядом с оболочкой '
                'и запускай из окружения, где установлен SHARPpy.'))
            return
        try:
            import matplotlib
            matplotlib.use('TkAgg')
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

            if getattr(self, 'prof', None) is None:
                arr = read_snd_arrays(self.path)
                self.prof = core.make_profile(**arr)
            prof = self.prof
            res = core.compute_verdicts(prof)
            if self.fig is not None:
                plt.close(self.fig)
            # компоновка как в окне SHARPpy, если модуль рядом;
            # иначе обычная отрисовка ядра
            try:
                import sharppy_layout as lay
                self.fig = lay.draw(prof, res, os.path.basename(self.path),
                                    parcel_flag=self.parcel_flag,
                                    inset=self.inset)
                sharppy_style = True
            except Exception as e:
                # раньше ошибка глоталась молча, и было непонятно, почему
                # вместо компоновки SHARPpy рисуется обычная диаграмма
                import traceback
                tb = traceback.format_exc()
                print(_('[layout] не удалось:'), e, flush=True)
                print(tb, flush=True)
                self.fig = core.draw_skewt(prof, res, os.path.basename(self.path))
                sharppy_style = False
                if not getattr(self, '_warned', False):
                    self._warned = True
                    messagebox.showwarning(
                        _('Компоновка SHARPpy недоступна'),
                        f'{type(e).__name__}: {e}\n\n'
                        + _('Рисую обычную диаграмму ядра.\n'
                            'Подробности в консоли.'))
            i18n.translate_figure(self.fig)
            if self.dark_var.get() and not sharppy_style:
                darken(self.fig)
            if self.canvas is not None:
                self.canvas.get_tk_widget().destroy()
            self.canvas = FigureCanvasTkAgg(self.fig, master=self.holder)
            self.canvas.draw()
            self.canvas.get_tk_widget().pack(fill='both', expand=True)
            # правка кривых: тянем узел, профиль пересобирается и
            # все панели считаются заново
            if sharppy_style and self.edit_var.get():
                try:
                    import sharppy_layout as lay
                    for obj in (getattr(self, 'editor', None) or ()):
                        if hasattr(obj, 'disconnect'):
                            obj.disconnect()
                    self.editor = lay.attach_interaction(
                        self.fig, prof, self.on_edited, self.on_parcel,
                        self.inset_menu)
                except Exception:
                    self.editor = None
            self.status.config(text=_('Готово'))
        except Exception as e:
            import traceback
            self.status.config(text=_('Ошибка'))
            messagebox.showerror(_('Не получилось'),
                                 f'{type(e).__name__}: {e}\n\n'
                                 f'{traceback.format_exc()[-1200:]}')

    def on_edited(self, newprof):
        """Профиль изменён перетаскиванием — пересчитать и перерисовать."""
        self.prof = newprof
        self.status.config(text=_('Пересчитываю...'))
        self.after(10, self.reload)

    def inset_menu(self, event):
        """Выпадающее меню выбора врезки по правой кнопке."""
        import sharppy_layout as lay
        m = tk.Menu(self, tearoff=0)
        for key, label in lay.INSETS:
            m.add_radiobutton(label=label, value=key,
                              variable=tk.StringVar(value=self.inset),
                              command=lambda k=key: self.set_inset(k))
        try:
            x = self.winfo_pointerx()
            y = self.winfo_pointery()
            m.tk_popup(x, y)
        finally:
            m.grab_release()

    def set_inset(self, kind):
        self.inset = kind
        self.after(10, self.reload)

    def on_parcel(self, flag, name):
        """Выбрана другая частица — пересчитать диаграмму под неё."""
        self.parcel_flag = flag
        self.status.config(text=_('Частица: {name}').format(name=name))
        self.after(10, self.reload)

    def reset_prof(self):
        """Вернуть исходный профиль из файла."""
        self.prof = None
        self.reload()

    def save(self):
        if self.fig is None:
            return
        p = filedialog.asksaveasfilename(
            defaultextension='.png', filetypes=[('PNG', '*.png')],
            initialfile=os.path.basename(self.path).replace('.snd', '.png'))
        if not p:
            return
        # сохраняем в исходном масштабе, а не в том, до которого
        # приблизили; после сохранения вид возвращается как был
        zoomer = None
        for obj in (getattr(self, 'editor', None) or ()):
            if hasattr(obj, 'to_home'):
                zoomer = obj
        snap = zoomer.snapshot() if zoomer else None
        try:
            if zoomer:
                zoomer.to_home()
            # без bbox_inches='tight': размер и раскладка как на экране
            self.fig.savefig(p, dpi=170, facecolor=self.fig.get_facecolor())
        finally:
            if zoomer and snap:
                zoomer.restore(snap)
                self.fig.canvas.draw_idle()
        self.status.config(text=_('Сохранено: {p}').format(p=p))


# --------------------------------------------------------------- карта
COAST_URL = ('https://raw.githubusercontent.com/nvkelso/natural-earth-vector/'
             'master/geojson/ne_110m_coastline.geojson')
COAST_FILE = os.path.join(HERE, 'coastline.geojson')
if not os.path.exists(COAST_FILE):
    _b = os.path.join(BUNDLE, 'coastline.geojson')
    if os.path.exists(_b):
        COAST_FILE = _b

VIEWS = [
    (_('Якутия'), 129.7, 63.0, 9.0),
    (_('Сибирь'), 100.0, 60.0, 4.0),
    (_('Россия'), 95.0, 62.0, 2.4),
    (_('Северное полушарие'), 60.0, 55.0, 1.2),
    (_('США'), -97.0, 38.5, 3.2),
]


def load_coastline():
    """Береговая линия из GeoJSON рядом со скриптом.

    Файл не обязателен: без него карта рисуется одной сеткой координат.
    Скачивается один раз по кнопке и дальше лежит локально — качать
    при каждом запуске незачем.
    """
    if not os.path.exists(COAST_FILE):
        return []
    try:
        js = json.load(open(COAST_FILE, encoding='utf-8'))
    except Exception:
        return []
    lines = []
    for f in js.get('features', []):
        g = f.get('geometry') or {}
        if g.get('type') == 'LineString':
            lines.append(g['coordinates'])
        elif g.get('type') == 'MultiLineString':
            lines.extend(g['coordinates'])
    return lines


class MapView(tk.Canvas):
    """Карта станций: проекция, сетка, точки, выбор кликом.

    Своя отрисовка на Canvas вместо cartopy/basemap — те тянут geos, proj
    и кучу данных, что при сборке в один exe превращается в мучение.
    Здесь достаточно линий берега и равнопромежуточной проекции.
    """

    BG = '#000000'
    COAST = '#ffffff'
    GRID = '#3a3a3a'
    DOT = '#c8c8c8'
    SEL = '#ff5a3c'

    def __init__(self, master, stations, on_pick):
        super().__init__(master, bg=self.BG, highlightthickness=1,
                         highlightbackground='#a0a0a0')
        self.stations = stations
        self.on_pick = on_pick
        self.sel = 0
        self.coast = load_coastline()
        _, self.lon0, self.lat0, self.scale = VIEWS[0]
        self._drag = None
        self.bind('<Configure>', lambda e: self.redraw())
        self.bind('<Button-1>', self.click)
        self.bind('<B1-Motion>', self.drag)
        self.bind('<ButtonRelease-1>', lambda e: setattr(self, '_drag', None))
        self.bind('<Motion>', self.hover)
        self.bind('<MouseWheel>', self.wheel)

    # ---- проекция
    def kx(self):
        return math.cos(math.radians(self.lat0))

    def to_xy(self, lon, lat):
        w, h = self.winfo_width(), self.winfo_height()
        dl = (lon - self.lon0 + 180) % 360 - 180
        return (w / 2 + dl * self.scale * self.kx(),
                h / 2 - (lat - self.lat0) * self.scale)

    def to_ll(self, x, y):
        w, h = self.winfo_width(), self.winfo_height()
        return (self.lon0 + (x - w / 2) / (self.scale * self.kx()),
                self.lat0 - (y - h / 2) / self.scale)

    # ---- события
    def wheel(self, e):
        lon, lat = self.to_ll(e.x, e.y)
        self.scale *= 1.2 if e.delta > 0 else 1 / 1.2
        self.scale = min(max(self.scale, 0.5), 60)
        # держим точку под курсором на месте
        nlon, nlat = self.to_ll(e.x, e.y)
        self.lon0 += lon - nlon
        self.lat0 += lat - nlat
        self.redraw()

    def drag(self, e):
        if self._drag:
            dx, dy = e.x - self._drag[0], e.y - self._drag[1]
            self.lon0 -= dx / (self.scale * self.kx())
            self.lat0 += dy / self.scale
            self.redraw()
        self._drag = (e.x, e.y)

    def hover(self, e):
        lon, lat = self.to_ll(e.x, e.y)
        self.itemconfig('coords', text=f'{lat:.3f}; {lon:.3f}')

    def click(self, e):
        self._drag = (e.x, e.y)
        best, bd = None, 12 ** 2
        for i, (sid, nm, la, lo) in enumerate(self.stations):
            if la is None or lo is None:
                continue
            x, y = self.to_xy(lo, la)
            d = (x - e.x) ** 2 + (y - e.y) ** 2
            if d < bd:
                best, bd = i, d
        if best is not None:
            self.sel = best
            self.redraw()
            self.on_pick(best)

    def set_view(self, idx):
        _, self.lon0, self.lat0, self.scale = VIEWS[idx]
        self.redraw()

    def select(self, i):
        self.sel = i
        self.redraw()

    # ---- отрисовка
    def redraw(self):
        self.delete('all')
        w, h = self.winfo_width(), self.winfo_height()
        if w < 10:
            return

        step = 30 if self.scale < 2 else (10 if self.scale < 8 else 5)
        for lon in range(-180, 181, step):
            pts = [self.to_xy(lon, la) for la in range(-80, 81, 5)]
            self.create_line(*[c for p in pts for c in p], fill=self.GRID)
        for lat in range(-80, 81, step):
            pts = [self.to_xy(lo, lat) for lo in range(-180, 181, 5)]
            self.create_line(*[c for p in pts for c in p], fill=self.GRID)

        for line in self.coast:
            pts, prev = [], None
            for lon, lat in line:
                x, y = self.to_xy(lon, lat)
                # разрыв на шве 180 градусов
                if prev is not None and abs(x - prev) > w:
                    if len(pts) > 2:
                        self.create_line(*pts, fill=self.COAST)
                    pts = []
                pts += [x, y]
                prev = x
            if len(pts) > 3:
                self.create_line(*pts, fill=self.COAST)

        if not self.coast:
            self.create_text(w / 2, h / 2, fill='#666', font=('Segoe UI', 11),
                             text=_('Береговая линия не загружена\n'
                                  'Файл → Загрузить карту'))

        for i, (sid, nm, la, lo) in enumerate(self.stations):
            if la is None or lo is None:
                continue
            x, y = self.to_xy(lo, la)
            if not (-20 < x < w + 20 and -20 < y < h + 20):
                continue
            act = i == self.sel
            r = 4 if act else 3
            self.create_oval(x - r, y - r, x + r, y + r,
                             fill=self.SEL if act else self.DOT, outline='')
            if act or self.scale > 3:
                self.create_text(x + 7, y, anchor='w', text=N(nm),
                                 fill=self.SEL if act else '#9a9a9a',
                                 font=('Segoe UI', 8))

        self.create_text(10, 10, anchor='nw', text='', tags='coords',
                         fill='white', font=('Segoe UI', 12))


# --------------------------------------------------------------- GUI
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('WX Sounding Launcher')
        # размер снят с окна, подогнанного вручную под оригинальный Picker
        self.q = queue.Queue()
        self.cfg = self.load_cfg()
        self.obs_stations = [tuple(s) for s in self.cfg.get('stations', STATIONS)]
        # для моделей: аэродромы по ICAO и добавленные точки; координаты
        # аэродромов подтягиваются у NOAA при первом построении
        # встроенные точки всегда свежие из модуля, а из настроек берём
        # только то, что добавлено поиском, — иначе новые города из
        # обновлений не появились бы у тех, у кого уже есть конфиг
        builtin = ([(c, n, None, None) for c, n in SL.ICAO_PRESETS] +
                   SL.builtin_model_points())
        ids = {s[0] for s in builtin}
        added = [tuple(s) for s in self.cfg.get('model_points', [])
                 if s[0] not in ids]
        self.model_points = added + builtin
        self.stations = self.obs_stations
        self.build()
        self.update_idletasks()
        # если при другом системном шрифте содержимое не влезет,
        # окно расширится, но меньше заданного не станет
        w = max(957, self.winfo_reqwidth())
        h = max(585, self.winfo_reqheight())
        self.geometry(f'{w}x{h}')
        self.minsize(w, h)
        self.after(120, self.pump)
        n, mb = cache_sweep()
        self.set_cache_label(n, mb)

    # ---------- конфиг
    def load_cfg(self):
        if os.path.exists(CFG):
            try:
                return json.load(open(CFG, encoding='utf-8'))
            except Exception:
                pass
        return {}

    def save_cfg(self):
        self.cfg['sharppy_cmd'] = self.cmd_var.get()
        if hasattr(self, 'mode'):
            self.cfg['mode'] = self.mode.get()
            self.cfg['dark'] = bool(self.dark.get())
        # оба списка по отдельности: self.stations указывает на тот,
        # что сейчас на экране, и в режиме моделей это аэродромы
        self.cfg['stations'] = [list(s) for s in getattr(self, 'obs_stations', self.stations)]
        if hasattr(self, 'model_points'):
            self.cfg['model_points'] = [list(s) for s in self.model_points]
        if hasattr(self, 'lang'):
            self.cfg['lang'] = self.lang.get()
        try:
            json.dump(self.cfg, open(CFG, 'w', encoding='utf-8'),
                      ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ---------- интерфейс
    # Компоновка и цвета повторяют экран выбора данных SHARPpy:
    # слева колонка выпадающих списков, справа большая область
    # (сейчас список станций, потом карта), внизу кнопка запуска.
    # цвета сняты с окна выбора данных SHARPpy: светлый фон,
    # синие подписи разделов, синяя полоса заголовка календаря
    BG = '#f0f0f0'
    PANEL = '#ffffff'
    FG = '#000000'
    ACC = '#3c85d8'      # синяя полоса заголовка календаря
    LBL = '#000000'      # подписи разделов чёрные
    DAY = '#1a5fb4'      # числа текущего месяца

    def build(self):
        self.configure(bg=self.BG)
        st = ttk.Style(self)
        # родная тема Windows выглядит ближе к оригиналу, чем clam;
        # если её нет (Linux), падаем на clam
        for t in ('vista', 'winnative', 'clam'):
            try:
                st.theme_use(t)
                break
            except tk.TclError:
                continue
        st.configure('Sec.TLabel', foreground=self.LBL, background=self.BG)
        st.configure('Run.TButton', font=('Segoe UI', 9))

        menubar = tk.Menu(self)
        fm = tk.Menu(menubar, tearoff=0)
        fm.add_command(label=_('Открыть файл...'), command=self.pick_file)
        fm.add_command(label=_('Указать программу просмотра...'),
                       command=self.pick_viewer)
        fm.add_separator()
        fm.add_command(label=_('Загрузить карту'), command=self.fetch_coast)
        fm.add_command(label=_('Очистить кеш'), command=self.clear_cache)
        fm.add_command(label=_('Выход'), command=self.destroy)
        menubar.add_cascade(label=_('Файл'), menu=fm)
        vm = tk.Menu(menubar, tearoff=0)
        self.mode = tk.StringVar(value=self.cfg.get('mode', 'embed'))
        vm.add_radiobutton(label=_('Встроенный просмотр'), value='embed',
                           variable=self.mode, command=self.save_cfg)
        vm.add_radiobutton(label=_('Внешний SHARPpy'), value='extern',
                           variable=self.mode, command=self.save_cfg)
        vm.add_separator()
        self.dark = tk.BooleanVar(value=self.cfg.get('dark', True))
        vm.add_checkbutton(label=_('Тёмная схема'), variable=self.dark,
                           command=self.save_cfg)
        menubar.add_cascade(label=_('Вид'), menu=vm)

        # язык: названия языков пишем на них самих, как принято
        lm = tk.Menu(menubar, tearoff=0)
        self.lang = tk.StringVar(value=i18n.MODE)
        lm.add_radiobutton(label=_('Как в системе'), value='auto',
                           variable=self.lang, command=self.on_lang)
        lm.add_separator()
        lm.add_radiobutton(label='Русский', value='ru',
                           variable=self.lang, command=self.on_lang)
        lm.add_radiobutton(label='English', value='en',
                           variable=self.lang, command=self.on_lang)
        menubar.add_cascade(label=_('Язык'), menu=lm)

        hm = tk.Menu(menubar, tearoff=0)
        hm.add_command(label=_('О программе'), command=self.about)
        menubar.add_cascade(label=_('Справка'), menu=hm)
        self.config(menu=menubar)
        self._fm = fm

        body = ttk.Frame(self)
        body.pack(fill='both', expand=True, padx=16, pady=(10, 12))
        self.configure(bg=self.BG)

        # ширина левой колонки и шаги между группами сняты с оригинала:
        # колонка 262 px, подпись отбита от поля на 2, группы между собой на 13
        side = ttk.Frame(body, width=262)
        side.pack(side='left', fill='y')
        side.pack_propagate(False)
        GAP = (13, 2)

        ttk.Label(side, text=_('Источник зондирования'),
                  style='Sec.TLabel').pack(anchor='w', pady=(0, 2))
        self.source = ttk.Combobox(side, state='readonly',
                                   values=[OBS] + [m[0] for m in MODELS])
        self.source.current(0)
        self.source.pack(fill='x')
        self.source.bind('<<ComboboxSelected>>', lambda e: self.on_mode())

        ttk.Label(side, text=_('Выбор даты'),
                  style='Sec.TLabel').pack(anchor='w', pady=GAP)
        self.cal = Calendar(side, self.BG, self.PANEL, self.FG, self.ACC,
                            self.on_date, self.DAY)
        self.cal.pack(fill='x')

        self.cycle = ttk.Combobox(side, state='readonly')
        self.cycle.pack(fill='x', pady=(9, 0))

        ttk.Label(side, text=_('Выбор срока'),
                  style='Sec.TLabel').pack(anchor='w', pady=GAP)
        self.times = tk.Listbox(side, bg=self.PANEL, fg=self.FG,
                                selectbackground=self.ACC, selectforeground='white',
                                highlightthickness=1, highlightbackground='#a0a0a0',
                                borderwidth=0, activestyle='none',
                                exportselection=False, font=('Segoe UI', 9))
        self.times.pack(fill='both', expand=True)

        ttk.Button(side, text=_('Построить профиль'),
                   command=self.go).pack(fill='x', pady=(10, 0))
        ttk.Button(side, text=_('Только скачать'),
                   command=lambda: self.go(open_after=False)).pack(fill='x',
                                                                   pady=(6, 0))

        main = ttk.Frame(body)
        main.pack(side='right', fill='both', expand=True, padx=(24, 0))

        top = ttk.Frame(main)
        top.pack(fill='x')
        ttk.Label(top, text=_('Выбор станции'),
                  style='Sec.TLabel').pack(side='left', anchor='w')
        self.view = ttk.Combobox(top, state='readonly', width=22,
                                 values=[v[0] for v in VIEWS])
        self.view.current(0)
        self.view.pack(side='right')
        self.view.bind('<<ComboboxSelected>>',
                       lambda e: self.map.set_view(self.view.current()))

        nb = ttk.Notebook(main)
        nb.pack(fill='both', expand=True, pady=(2, 0))

        tab_map = ttk.Frame(nb)
        nb.add(tab_map, text=_('Карта'))
        self.map = MapView(tab_map, self.obs_stations, self.on_map_pick)
        self.map.pack(fill='both', expand=True)

        tab_list = ttk.Frame(nb)
        nb.add(tab_list, text=_('Список'))
        self.search = tk.StringVar()
        self.search.trace_add('write', lambda *_: self.refilter())
        srow = ttk.Frame(tab_list)
        srow.pack(fill='x')
        self.search_entry = ttk.Entry(srow, textvariable=self.search)
        self.search_entry.pack(side='left', fill='x', expand=True)
        self.search_entry.bind('<Return>', lambda e: self.find())
        self.find_btn = ttk.Button(srow, text=_('Найти'), command=self.find)
        self.find_btn.pack(side='left', padx=(4, 0))
        self.hint = ttk.Label(tab_list, text='')
        self.hint.pack(anchor='w')
        self.lb = tk.Listbox(tab_list, bg=self.PANEL, fg=self.FG,
                             selectbackground=self.ACC, selectforeground='white',
                             highlightthickness=1, highlightbackground='#a0a0a0',
                             borderwidth=0, activestyle='none',
                             font=('Segoe UI', 9))
        self.lb.pack(fill='both', expand=True, pady=(2, 0))
        self.lb.bind('<Double-Button-1>', lambda e: self.go())
        self.lb.bind('<<ListboxSelect>>', self.on_list_pick)
        self.refilter()
        self.lb.selection_set(0)

        self.cmd_var = tk.StringVar(value=self.cfg.get('sharppy_cmd', 'sharppy'))
        # строки состояния в оригинале нет, поэтому сообщения выводим
        # в заголовок окна, чтобы не ломать компоновку
        self.status = _TitleStatus(self)
        self.cache_lbl = _MenuCache(self, self._fm)
        self.on_date(self.cal.selected)

    def on_date(self, d):
        """Обновляет список сроков под выбранную дату и источник."""
        obs = self.source.get() == OBS
        hours = [0, 12] if obs else list(range(24))
        self.times.delete(0, 'end')
        for h in hours:
            self.times.insert('end', f'{d:%d.%m.%Y}  {h:02d}:00 UTC')
        self.times.selection_set(0)
        self.cycle.config(values=[f'{d:%d %B %Y} / {h:02d}00 UTC' for h in hours])
        self.cycle.current(0)

    def on_map_pick(self, i):
        """Клик по точке на карте — подсветить ту же станцию в списке."""
        sid = self.map.stations[i][0]
        for j, s in enumerate(self.shown):
            if s[0] == sid:
                self.lb.selection_clear(0, 'end')
                self.lb.selection_set(j)
                self.lb.see(j)
                break
        self.status.config(text=self.map.stations[i][1])

    def on_list_pick(self, e=None):
        sel = self.lb.curselection()
        if not sel:
            return
        sid = self.shown[sel[0]][0]
        for i, s in enumerate(self.map.stations):
            if s[0] == sid:
                self.map.select(i)
                break

    def fetch_coast(self):
        """Скачивает береговую линию один раз и кладёт рядом со скриптом."""
        if os.path.exists(COAST_FILE):
            if not messagebox.askyesno(_('Карта'), _('Файл уже есть. Скачать заново?')):
                return
        self.status.config(text=_('Качаю береговую линию...'))
        try:
            r = requests.get(COAST_URL, headers=UA, timeout=90)
            r.raise_for_status()
            json.loads(r.text)          # проверяем, что это разбираемый GeoJSON
            open(COAST_FILE, 'w', encoding='utf-8').write(r.text)
        except Exception as e:
            self.status.config(text=_('Ошибка'))
            messagebox.showerror(
                _('Не получилось'),
                f'{e}\n\n' + _('Можно положить любой GeoJSON с береговой '
                'линией вручную:\n{path}').format(path=COAST_FILE))
            return
        self.map.coast = load_coastline()
        self.map.redraw()
        self.status.config(text=_('Карта загружена: {n} линий').format(n=len(self.map.coast)))

    def on_lang(self):
        """Смена языка: сохранить выбор и предложить перезапуск.

        Подписи расставляются один раз при построении окна, поэтому
        честнее перезапустить программу, чем перекрашивать половину.
        """
        mode = self.lang.get()
        self.cfg['lang'] = mode
        self.save_cfg()
        new = i18n.system_lang() if mode == 'auto' else mode
        if new == i18n.LANG:
            return
        # спрашиваем уже на новом языке — так понятнее тому, кто его выбрал
        q = (i18n.EN if new == 'en' else {}).get(
            'Язык изменится после перезапуска. Перезапустить сейчас?',
            'Язык изменится после перезапуска. Перезапустить сейчас?')
        if messagebox.askyesno('SHARPpy Fix', q):
            self.restart()

    def restart(self):
        """Запускает программу заново и закрывает текущее окно."""
        args = ([sys.executable] + sys.argv[1:] if FROZEN
                else [sys.executable] + sys.argv)
        try:
            subprocess.Popen(args, cwd=HERE)
        except Exception as e:
            messagebox.showerror(_('Ошибка'), str(e))
            return
        self.destroy()

    def about(self):
        """Окно "о программе", по образцу такого же у SHARPpy."""
        w = tk.Toplevel(self)
        w.title('WX Sounding Launcher')
        w.configure(bg=self.PANEL)
        w.resizable(False, False)
        w.transient(self)
        import sys as _sys
        try:
            import numpy as _np
            npv = _np.__version__
        except Exception:
            npv = '—'
        try:
            import requests as _rq
            rqv = _rq.__version__
        except Exception:
            rqv = '—'
        txt = (
            'SHARPpy Fix v0.0.1\n\n'
            'Sounding and Hodograph Analysis and Research Program for Python\n\n'
            '(C) 2014-2026 by Patrick Marsh, John Hart, Kelton Halbert, '
            'Greg Blumberg, and Tim Supinie.\n\n'
            'SHARPpy is a collection of open source sounding and hodograph '
            'analysis routines, a sounding plotting package, and an '
            'interactive application for analyzing real-time soundings all '
            'written in Python. It was developed to provide the atmospheric '
            'science community a free and consistent source of routines for '
            'analyzing sounding data. SHARPpy is constantly updated and '
            'vetted by professional meteorologists and climatologists within '
            'the scientific community to help maintain a standard source of '
            'sounding routines.\n\n'
            + _('Источники:') + '\n'
            + _('   наблюдения — архив Университета Вайоминга') + '\n'
            + _('   модели — Open-Meteo (Arpege, ICON, GFS, ECMWF, GEM)') + '\n\n'
            + _('Модельные профили доступны с 2021 года, фактические — с 1970-х.')
            + '\n\n' + _('Кеш: {path}').format(path=CACHE) + '\n\n'
            f'Numpy version: {npv}\n'
            f'Python version: {_sys.version.split()[0]}\n'
            f'Requests version: {rqv}\n\n'
            'Contribute: https://github.com/sharppy/SHARPpy/\n\n'
            + _('Автор фикса и оболочки: Henich, 2026')
        )
        tk.Label(w, text=txt, bg=self.PANEL, fg=self.FG, justify='left',
                 wraplength=420, font=('Segoe UI', 9),
                 padx=16, pady=14).pack()
        ttk.Button(w, text=_('Закрыть'), command=w.destroy).pack(pady=(0, 14))
        w.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - w.winfo_width()) // 2
        y = self.winfo_rooty() + 80
        w.geometry(f'+{x}+{y}')
        w.grab_set()

    def pick_viewer(self):
        p = filedialog.askopenfilename(
            title=_('Исполняемый файл SHARPpy'),
            filetypes=[(_('Программы'), '*.exe;*.bat;*.cmd'), (_('Все файлы'), '*.*')])
        if p:
            self.cmd_var.set(p)

    def set_cache_label(self, n, mb):
        self.cache_lbl.config(text=_('Кеш: {n} файлов, {mb:.1f} МБ').format(n=n, mb=mb))

    def clear_cache(self):
        for n in os.listdir(CACHE) if os.path.isdir(CACHE) else []:
            try:
                os.remove(os.path.join(CACHE, n))
            except OSError:
                pass
        self.set_cache_label(*cache_sweep())

    def _is_obs(self):
        return self.source.get() == OBS

    def on_mode(self):
        """Наблюдения — станции Вайоминга, модели — ICAO и координаты."""
        self.stations = self.obs_stations if self._is_obs() else self.model_points
        # на карте — то, что сейчас выбирается: станции или точки моделей
        self.map.stations = self.stations
        self.map.sel = -1
        self.map.redraw()
        self.hint.config(text=(_('Код WMO, например 24959') if self._is_obs()
                               else _('ICAO (UEEE) или координаты (62.0, 129.7)')))
        self.search.set('')
        self.refilter()
        if self.shown:
            self.lb.selection_set(0)
        self.on_date(self.cal.selected)

    def find(self):
        """Ищет введённое: код на Вайоминге, ICAO у NOAA или координаты."""
        q = self.search.get().strip()
        if not q:
            return
        # уже есть в списке — просто выбрать
        for j, s in enumerate(self.shown):
            if s[0].upper() == q.upper():
                self.lb.selection_clear(0, 'end')
                self.lb.selection_set(j)
                return
        if not self._is_obs():
            c = SL.parse_coords(q)
            if c:
                self._add_found(SL.point_entry(*c))
                return
            if not SL.is_icao(q):
                messagebox.showinfo(_('Поиск'), _('Для моделей введи ICAO-код '
                                    '(например UEEE) или координаты (62.0, 129.7).'))
                return
        self.status.config(text=_('Ищу...'))
        self.find_btn.config(state='disabled')
        fn = SL.lookup_wyoming if self._is_obs() else SL.lookup_icao
        threading.Thread(target=self._find_worker, args=(fn, q), daemon=True).start()

    def _find_worker(self, fn, q):
        try:
            self.q.put(('found', fn(q), 0, False))
        except Exception as e:
            self.q.put(('err', str(e), 0, False))

    def _add_found(self, entry):
        target = self.obs_stations if self._is_obs() else self.model_points
        if not any(s[0] == entry[0] for s in target):
            target.insert(0, entry)
        self.cfg['stations'] = [list(s) for s in self.obs_stations]
        self.cfg['model_points'] = [list(s) for s in self.model_points]
        self.save_cfg()
        self.search.set(entry[0])
        self.refilter()
        if self.shown:
            self.lb.selection_clear(0, 'end')
            self.lb.selection_set(0)
        self.map.redraw()
        self.status.config(text=_('Найдено: {name}').format(name=N(entry[1])))

    def refilter(self):
        q = self.search.get().lower().strip()
        self.shown = [s for s in self.stations
                      if not q or q in s[1].lower() or q in s[0]]
        self.lb.delete(0, 'end')
        for sid, nm, la, lo in self.shown:
            is_point = bool(re.fullmatch(r'-?\d+\.\d+_-?\d+\.\d+', str(sid)))
            self.lb.insert('end', N(nm) if is_point else f'{N(nm)}  ({sid})')

    def pick_file(self):
        p = filedialog.askopenfilename(
            filetypes=[(_('Зондирования'), '*.snd *.txt'), (_('Все файлы'), '*.*')])
        if p:
            self.launch(p)

    # ---------- работа
    def go(self, open_after=True):
        sel = self.lb.curselection()
        if not sel:
            messagebox.showinfo(_('Станция'), _('Выбери станцию в списке справа.'))
            return
        sid, nm, la, lo = self.shown[sel[0]]

        tsel = self.times.curselection()
        if not tsel:
            messagebox.showinfo(_('Срок'), _('Выбери срок.'))
            return
        hour = int(self.times.get(tsel[0]).split()[1].split(':')[0])
        d = self.cal.selected
        dt = datetime(d.year, d.month, d.day, hour, tzinfo=timezone.utc)

        s = self.source.get()
        if s == OBS:
            src_kind, mdl = 'wyoming', ''
        else:
            src_kind = 'model'
            mdl = dict(MODELS)[s]

        if src_kind == 'model':
            if dt.year < 2021:
                messagebox.showwarning(
                    _('Модель недоступна'),
                    _('Архив модельных прогонов Open-Meteo начинается с 2021 года.'
                    '\n\nДля более ранних дат бери "Наблюдения (Вайоминг)" — '
                    'там архив с 1970-х.'))
                return

        safe = re.sub(r'[^A-Za-z0-9._-]', '_', str(sid))
        key = f'{src_kind}_{safe}_{dt:%Y%m%d_%H}' + (f'_{mdl}' if mdl else '')
        path = cache_path(key)
        if os.path.exists(path):
            self.status.config(text=_('Из кеша: {name}').format(name=os.path.basename(path)))
            if open_after:
                self.launch(path)
            return
        self.status.config(text=_('Загружаю...'))
        threading.Thread(target=self.worker,
                         args=(src_kind, sid, nm, la, lo, dt, mdl, path, open_after),
                         daemon=True).start()

    def worker(self, src, sid, nm, la, lo, dt, mdl, path, open_after):
        try:
            if src != 'wyoming' and (la is None or lo is None):
                _, _, la, lo = SL.lookup_icao(sid)
            rows = (fetch_wyoming(sid, dt) if src == 'wyoming'
                    else fetch_openmeteo(la, lo, dt, mdl))
            write_snd(path, sid, dt, rows)
            self.q.put(('ok', path, len(rows), open_after))
        except Exception as e:
            self.q.put(('err', str(e), 0, False))

    def pump(self):
        try:
            while True:
                kind, a, b, c = self.q.get_nowait()
                if kind == 'found':
                    self.find_btn.config(state='normal')
                    self._add_found(a)
                    continue
                if kind == 'err' and str(self.find_btn['state']) == 'disabled':
                    self.find_btn.config(state='normal')
                if kind == 'ok':
                    self.status.config(
                        text=_('Готово: {name} — {n} уровней').format(name=os.path.basename(a), n=b))
                    self.set_cache_label(*cache_sweep())
                    if c:
                        self.launch(a)
                else:
                    self.status.config(text=_('Ошибка'))
                    messagebox.showerror(_('Не получилось'), a)
        except queue.Empty:
            pass
        self.after(120, self.pump)

    def launch(self, path):
        self.save_cfg()
        if self.mode.get() == 'embed':
            Viewer(self, path, dark=bool(self.dark.get()))
            self.status.config(text=os.path.basename(path))
            return

        import shlex
        raw = self.cmd_var.get().strip() or 'sharppy'
        # команда может быть из нескольких слов ("python -m sharppy")
        # или путём с пробелами — разбираем как в оболочке, но не через shell,
        # иначе Windows берёт всю строку в кавычки целиком
        try:
            parts = shlex.split(raw, posix=False)
        except ValueError:
            parts = [raw]
        parts = [p.strip('"') for p in parts]
        print(_('[launcher] запускаю:'), parts + [path], flush=True)
        try:
            subprocess.Popen(parts + [path])
            self.status.config(text=_('Открываю: {name}').format(name=os.path.basename(path)))
        except Exception as e:
            messagebox.showwarning(
                _('SHARPpy не запустился'),
                f'{e}\n\n' + _('Команда: {cmd}\n\nФайл готов, открой его '
                'вручную:\n{path}').format(cmd=' '.join(parts), path=path))


if __name__ == '__main__':
    App().mainloop()

#!/usr/bin/env python3
"""
sharppy_layout — диаграмма в компоновке окна SHARPpy.

Расчёты берутся из sharppy_core (тот же модуль, что в боте), здесь только
раскладка панелей и отрисовка недостающих: колонка барбов, профиль
скорости ветра, инферированная адвекция температуры, storm slinky,
theta-e по давлению, SR-ветер по высоте, блок опасных явлений и
коробчатая диаграмма STP.

Пропорции сняты с окна SHARPpy v1.4: Skew-T слева на две трети высоты,
справа годограф, под ним четыре врезки, внизу пять таблиц.

    import sharppy_layout
    fig = sharppy_layout.draw(prof, res, 'заголовок')
"""
import numpy as np
import matplotlib.pyplot as plt

import sharppy_core as core

BG = '#000000'
FG = '#d8d8d8'
FRAME = '#e4e4e4'
INSET = '#3399CC'
GRIDL = '#7a7a7a'


def _q(fn, default=None):
    """Панель не должна ронять всю картинку из-за одного параметра."""
    try:
        return fn()
    except Exception:
        return default


def _ax(fig, rect, title=None, fs=9):
    ax = fig.add_axes(rect, facecolor=BG)
    for s in ax.spines.values():
        s.set_color(FRAME)
        s.set_linewidth(1.5)
    ax.tick_params(colors=FG, labelsize=7)
    ax.set_xticks([])
    ax.set_yticks([])
    if title:
        ax.set_title(title, color=FG, fontsize=fs, pad=3)
    return ax


# ------------------------------------------------------------ колонки справа от Skew-T
def _barbs(fig, rect, prof):
    """Колонка ветровых барбов вдоль оси давления, как у SHARPpy."""
    ax = _ax(fig, rect)
    p = np.asarray(prof.pres, float)
    u = np.asarray(prof.u, float)
    v = np.asarray(prof.v, float)
    ok = (np.isfinite(p) & np.isfinite(u) & np.isfinite(v) &
          (p >= core.P_TOP) & (np.abs(u) < 250) & (np.abs(v) < 250))
    p, u, v = p[ok], u[ok], v[ok]
    if len(p) < 2:
        return ax
    # прореживаем: барбы на каждом уровне сливаются в кашу
    keep, last = [], None
    for i in range(len(p)):
        if last is None or last / p[i] > 1.06:
            keep.append(i)
            last = p[i]
    keep = np.array(keep)
    y = core._sy(p[keep])
    ax.barbs(np.zeros_like(y), y, u[keep], v[keep], length=5.5,
             color=FG, linewidth=0.6)
    ax.set_xlim(-1, 1)
    ax.set_ylim(core._sy(core.P_BOT), core._sy(core.P_TOP))
    return ax


def _wind_speed(fig, rect, prof):
    """Профиль скорости ветра по sharppy/viz/speed.py.

    Шкала 0..140 узлов с шагом 20, изотахи цвета #9D5736 пунктиром,
    горизонтальные отрезки окрашены по высоте теми же цветами, что
    и годограф: до 3 км красный, до 6 зелёный, до 9 жёлтый, выше голубой.
    """
    ax = _ax(fig, rect)
    SMAX, DELTA = 140.0, 20.0
    for s in np.arange(DELTA, SMAX, DELTA):
        ax.axvline(s, color='#9D5736', lw=0.7, ls='--', zorder=0)
        if int(s) % int(DELTA * 2) == 0:
            ax.text(s, core._sy(core.P_BOT), str(int(s)), color=FG,
                    fontsize=5.6, ha='center', va='top')

    p = np.asarray(prof.pres, float)
    u = np.asarray(prof.u, float)
    v = np.asarray(prof.v, float)
    h = np.asarray(prof.hght, float)
    ok = (np.isfinite(p) & np.isfinite(u) & np.isfinite(v) & np.isfinite(h) &
          (np.abs(u) < 250) & (np.abs(v) < 250))
    if ok.sum() > 2:
        p, u, v, h = p[ok], u[ok], v[ok], h[ok]
        agl = h - h[0]
        spd = np.hypot(u, v)
        for pp, ss, zz in zip(p, spd, agl):
            if pp < core.P_TOP:
                continue
            c = ('#FF0000' if zz < 3000 else '#00FF00' if zz < 6000
                 else '#FFFF00' if zz < 9000 else '#00FFFF')
            ax.plot([0, ss], [core._sy(pp)] * 2, color=c, lw=1.4, zorder=3)

    ax.set_xlim(0, SMAX)
    ax.set_ylim(core._sy(core.P_BOT), core._sy(core.P_TOP))
    ax.text(0.04, 0.985, 'Wind Speed\n(kt)', transform=ax.transAxes,
            color=FG, fontsize=6.2, ha='left', va='top')
    return ax


def _temp_adv(fig, rect, prof):
    """Инферированная адвекция температуры по повороту ветра с высотой."""
    ax = _ax(fig, rect, 'Адв.\n°C/ч', fs=7)
    p = np.asarray(prof.pres, float)
    u = np.asarray(prof.u, float)
    v = np.asarray(prof.v, float)
    h = np.asarray(prof.hght, float)
    ok = np.isfinite(p) & np.isfinite(u) & np.isfinite(v) & np.isfinite(h)
    p, u, v, h = p[ok], u[ok], v[ok], h[ok]
    if len(p) < 3:
        return ax
    f = 2 * 7.292e-5 * np.sin(np.radians(60.0))       # параметр Кориолиса
    adv = np.zeros(len(p))
    for i in range(1, len(p) - 1):
        dz = h[i + 1] - h[i - 1]
        if dz <= 0:
            continue
        du = (u[i + 1] - u[i - 1]) * 0.514444 / dz
        dv = (v[i + 1] - v[i - 1]) * 0.514444 / dz
        # термический ветер: адвекция пропорциональна повороту
        adv[i] = -(f / 9.81) * (u[i] * 0.514444 * dv - v[i] * 0.514444 * du) * 3600 * 1e3
    y = core._sy(p)
    for yy, a in zip(y, adv):
        if not np.isfinite(a) or abs(a) < 1e-3:
            continue
        ax.plot([0, a], [yy, yy], color='#d62728' if a > 0 else '#4da6ff', lw=1.0)
    lim = max(0.5, float(np.nanpercentile(np.abs(adv), 95)) * 1.2)
    for pg in (1000, 850, 700, 500, 400, 300, 200, 150):
        ax.axhline(core._sy(pg), color=GRIDL, lw=0.4, ls=(0, (4, 3)), zorder=0)
    ax.axvline(0, color='#9a9a9a', lw=0.7, zorder=1)
    ax.set_xlim(-lim, lim)
    ax.set_ylim(core._sy(core.P_BOT), core._sy(core.P_TOP))
    return ax


# ------------------------------------------------------------ врезки под годографом
def _slinky(fig, rect, prof, pcl):
    """Storm Slinky по sharppy/viz/slinky.py.

    Траектория частицы считается штатной parcelTraj, масштаб кадра
    7000*1.7 метра на всю ширину, круги радиусом 5 px, цвета по высоте:
    до 3 км красный, до 6 зелёный, до 9 жёлтый, до 12 голубой,
    точка на уровне EL — сиреневая. Оси #003366 через центр.
    """
    ax = _ax(fig, rect)
    MAG = 7000.0 * 1.7
    ax.set_xlim(-MAG / 2, MAG / 2)
    ax.set_ylim(-MAG / 2, MAG / 2)
    ax.set_aspect('equal')
    ax.axhline(0, color='#003366', lw=1.6, zorder=1)
    ax.axvline(0, color='#003366', lw=1.6, zorder=1)
    ax.text(0.02, 0.04, 'Storm Slinky', transform=ax.transAxes, color=FG,
            fontsize=7.5, ha='left', va='bottom')

    res = _q(lambda: _traj(prof, pcl))
    if not res:
        # без положительной плавучести частица никуда не поднимается,
        # и траектории попросту нет — в оригинале окно тоже остаётся пустым
        ax.text(0.5, 0.55, 'нет траектории', transform=ax.transAxes,
                color='#8a8a8a', fontsize=6.4, ha='center', va='center')
        return ax
    traj, tilt = res
    has_el = bool(pcl is not None and getattr(pcl, 'bplus', 0) > 1e-3)
    last_z = traj[-1][2] if len(traj) else None
    for x, y, z in traj:
        if not np.isfinite(x) or not np.isfinite(y):
            continue
        if has_el and z == last_z:
            c = '#FF00FF'
        elif z < 3000:
            c = '#FF0000'
        elif z < 6000:
            c = '#00FF00'
        elif z < 9000:
            c = '#FFFF00'
        elif z < 12000:
            c = '#00FFFF'
        else:
            continue
        ax.add_patch(plt.Circle((x, y), MAG / 120, fill=False, edgecolor=c,
                                lw=1.0, zorder=3))
    if tilt is not None and np.isfinite(tilt):
        ax.text(0.98, 0.96, f'{tilt:.0f} deg', transform=ax.transAxes,
                color=FG, fontsize=7.5, ha='right', va='top')
    return ax


def _traj(prof, pcl):
    from sharppy.sharptab import params
    if pcl is None or not np.isfinite(getattr(pcl, 'bplus', np.nan)):
        return None
    smu, smv = prof.srwind[0], prof.srwind[1]
    traj, tilt = params.parcelTraj(prof, pcl, smu, smv)
    if traj is np.ma.masked or traj is None or len(traj) == 0:
        return None
    return [(float(t[0]), float(t[1]), float(t[2])) for t in traj], float(tilt)


def _theta_e(fig, rect, prof):
    """Theta-E по sharppy/viz/thetae.py: 1025..400 гПа, пределы по данным."""
    ax = _ax(fig, rect)
    p = np.asarray(prof.pres, float)
    the = _q(lambda: np.asarray(prof.thetae, float))
    if the is None:
        return ax
    ok = np.isfinite(p) & np.isfinite(the) & (p > 400)
    if ok.sum() < 3:
        return ax
    tmin, tmax = the[ok].min() - 10.0, the[ok].max() + 10.0
    for pg in (1000, 900, 800, 700, 600, 500):
        ax.axhline(pg, color=FG, lw=0.5, zorder=1)
        ax.text(tmin + (tmax - tmin) * 0.015, pg, str(pg), color=FG,
                fontsize=5.6, va='center', ha='left')
    ax.plot(the[ok], p[ok], color='#ff0000', lw=1.6, zorder=3)
    ax.set_xlim(tmin, tmax)
    ax.set_ylim(1025, 400)
    ax.text(0.5, 0.90, 'Theta-E\nv.\nPres', transform=ax.transAxes,
            color=FG, fontsize=6.6, ha='center', va='top')
    return ax


def _sr_wind(fig, rect, prof):
    """SR-ветер по sharppy/viz/srwinds.py.

    Оси 0..16 км и 0..80 узлов, штриховая линия на 15 узлах, коридор
    классической суперячейки 40..70 узлов в слое 8-16 км цветом #b1019a.
    """
    ax = _ax(fig, rect)
    ax.set_xlim(0, 80)
    ax.set_ylim(0, 16)
    ax.axvline(15, color=FG, lw=0.7, ls='--', zorder=1)
    for c in (40, 70):
        ax.plot([c, c], [8, 16], color='#b1019a', lw=0.9, ls='--', zorder=1)
    ax.text(55, 15.2, 'Classic\nSupercell', color='#b1019a', fontsize=5.6,
            ha='center', va='top')
    for h in (2, 4, 6, 8, 10, 12, 14):
        ax.text(1.5, h, str(h), color=FG, fontsize=5.6, va='center')

    u = np.asarray(prof.u, float)
    v = np.asarray(prof.v, float)
    z = np.asarray(prof.hght, float)
    ok = np.isfinite(u) & np.isfinite(v) & np.isfinite(z)
    smu, smv = _q(lambda: (prof.srwind[0], prof.srwind[1]), (None, None))
    if ok.sum() > 3 and smu is not None and np.isfinite(smu):
        agl = (z[ok] - z[ok][0]) / 1000.0
        srw = np.hypot(u[ok] - smu, v[ok] - smv)
        m = agl <= 16
        ax.plot(srw[m], agl[m], color='#ff0000', lw=1.6, zorder=3)
    ax.text(0.5, 0.97, 'SR Wind\nv.\nHeight', transform=ax.transAxes,
            color=FG, fontsize=6.4, ha='center', va='top')
    return ax


# цвета типов явлений — из sharppy/viz/watch.py
WATCH_COLORS = {
    'PDS TOR': '#ff00ff', 'TOR': '#ff0000', 'MRGL TOR': '#ff0000',
    'SVR': '#ffff00', 'MRGL SVR': '#0099cc', 'FLASH FLOOD': '#5ffb17',
    'BLIZZARD': '#3366ff', 'WIND CHILL': '#3366ff', 'FREEZE': '#3366ff',
    'FIRE WEATHER': '#ff9900', 'EXCESSIVE HEAT': '#c85a17', 'NONE': '#ffcc33',
}


def _hazard(fig, rect, prof, res):
    """Psbl Haz. Type по sharppy/viz/watch.py: заголовок, черта, вердикт."""
    ax = _ax(fig, rect)
    ax.text(0.5, 0.95, 'Psbl Haz. Type', transform=ax.transAxes, color=FG,
            fontsize=8, ha='center', va='top')
    ax.plot([0.0, 1.0], [0.80, 0.80], transform=ax.transAxes, color=FG,
            lw=0.8)
    wt = _q(lambda: str(prof.right_watch_type))
    if wt is None:
        wt = str(res.get('mode') or 'NONE')
    ax.text(0.5, 0.45, wt, transform=ax.transAxes,
            color=WATCH_COLORS.get(wt.upper(), '#ffcc33'),
            fontsize=11, ha='center', va='center')
    return ax


def _stp_box(fig, rect, res, prof):
    """Условные вероятности торнадо по STPC — sharppy/viz/stpef.py.

    Данные берутся из sharppy.databases.inset_data, как в оригинале,
    поэтому кривые и подписи совпадают с ним точно.
    """
    ax = _ax(fig, rect)
    ax.text(0.5, 0.99, 'Conditional Tornado Probs based on STPC',
            transform=ax.transAxes, color=FG, fontsize=6.6, ha='center',
            va='top')
    data = _q(lambda: __import__('sharppy.databases.inset_data',
                                 fromlist=['inset_data']).condSTPData())
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 70)
    for g in (10, 20, 30, 40, 50, 60):
        ax.axhline(g, color='#0080FF', lw=0.7, ls=(0, (5, 4)), zorder=0)
        ax.text(0.15, g, str(g), color=FG, fontsize=5.6, va='center')
    if not data:
        return ax
    xt = list(data['xticks'])
    centers = np.arange(1, len(xt) + 1)
    for name, col in (('EF1+', '#006600'), ('EF2+', '#FFCC33'),
                      ('EF3+', '#FF0000'), ('EF4+', '#FF00FF')):
        y = list(data[name])
        n = min(len(centers), len(y))
        ax.plot(centers[:n], y[:n], color=col, lw=1.8, zorder=3)
    for i, t in enumerate(xt):
        _t = ax.text(centers[i], -3.5, str(t), color=FG, fontsize=5.4,
                     ha='center', va='top')
        _t._noclip = True
    for lab, stp, col in (('EF1+', 0.2, '#006600'), ('EF2+', 1.1, '#FFCC33'),
                          ('EF3+', 3.1, '#FF0000'), ('EF4+', 6.1, '#FF00FF')):
        ax.text(_stp_bin(stp), 67, lab, color=col, fontsize=6.0, ha='center',
                va='top')
    stp = _q(lambda: float(prof.right_stp_cin))
    if stp is None:
        stp = _q(lambda: float(res.get('stp_cin', 0.0)), 0.0)
    ax.axvline(_stp_bin(stp), color=FG, lw=1.4, ls=':', zorder=4)
    return ax


def _stp_bin(stpc):
    """Номер корзины STPC — пороги из stpef.stpc_to_pix."""
    lims = (0.01, 0.5, 1, 2, 3, 4, 6, 8, 10, 12)
    i = 0
    for k, lim in enumerate(lims):
        if stpc >= lim:
            i = k + 1
    return i + 1



def _draw_hodo(ax, prof, rstu, rstv):
    """Годограф в оформлении SHARPpy.

    Кольца скорости тёмные пунктирные, оси — сплошные через центр,
    подписи колец стоят вдоль осей, а не по диагонали. Отрезки кривой
    по слоям 0-3, 3-6, 6-9 и 9-12 км теми же цветами, что колонка
    скорости. Отметки правого и левого движителей, векторы Корфиди.
    """
    from sharppy.sharptab import winds as _w, params as _pa
    def clean(a):
        # маскированные уровни и -9999 SHARPpy — это пропуски,
        # иначе масштаб годографа уезжает на тысячи узлов
        a = np.ma.filled(np.ma.asarray(a, dtype=float), np.nan)
        a = np.asarray(a, float)
        a[a < -900] = np.nan
        return a
    u, v, h = clean(prof.u), clean(prof.v), clean(prof.hght)
    # ветер сильнее 250 узлов в тропосфере не бывает — это мусор
    # в данных (другие маркеры пропуска, битые уровни), его отсекаем
    ok = (np.isfinite(u) & np.isfinite(v) & np.isfinite(h) &
          (np.abs(u) < 250) & (np.abs(v) < 250))
    u, v, h = u[ok], v[ok], h[ok]
    order = np.argsort(h)
    u, v, h = u[order], v[order], h[order]
    agl = h - h[0] if len(h) else h

    # Масштаб по максимуму ветра до 12 км: по процентилю самый сильный
    # участок струйного течения уходил за край. Мусорные значения уже
    # отсечены выше (больше 250 узлов), так что выброс масштаб не раздует
    top = 40.0
    if len(u):
        m12 = agl <= 12000
        if m12.sum() >= 2:
            spd = np.hypot(u[m12], v[m12])
            top = max(top, float(np.nanmax(spd)) * 1.12)
    top = float(min(np.ceil(top / 10.0) * 10, 150.0))

    for r in range(10, int(top) + 20, 10):
        ax.add_patch(plt.Circle((0, 0), r, fill=False, edgecolor='#4a4a4a',
                                lw=0.8, ls=(0, (4, 4)), zorder=1))
    ax.axhline(0, color=FG, lw=0.9, zorder=2)
    ax.axvline(0, color=FG, lw=0.9, zorder=2)
    for r in range(10, int(top) + 10, 10):
        for x, y, ha, va in ((r, 0, 'center', 'top'), (-r, 0, 'center', 'top'),
                             (0, r, 'left', 'center'), (0, -r, 'left', 'center')):
            ax.text(x + (1.2 if ha == 'left' else 0),
                    y - (1.2 if va == 'top' else 0), str(r), color=FG,
                    fontsize=6.4, ha=ha, va=va, zorder=3)

    layers = ((0, 3000, '#FF0000'), (3000, 6000, '#00FF00'),
              (6000, 9000, '#FFFF00'), (9000, 12000, '#00FFFF'))
    for lo, hi, col in layers:
        # Слой рисуем по своим точкам плюс ветру ровно на его границах.
        # Иначе между последней точкой одного слоя (скажем, 2800 м) и первой
        # следующего (3300 м) оставался разрыв, а слой из одной точки
        # не рисовался совсем — отсюда «отрезанный» годограф.
        if len(agl) < 2 or agl[-1] <= lo:
            continue
        m = (agl > lo) & (agl < hi)
        zz = [lo] + list(agl[m])
        top_z = min(hi, agl[-1])
        zz.append(top_z)
        uu = np.interp(zz, agl, u)
        vv = np.interp(zz, agl, v)
        ax.plot(uu, vv, color=col, lw=2.0, zorder=5, solid_capstyle='round')

    for km in (1, 3, 6, 9):
        if len(agl) and agl.max() >= km * 1000:
            uk = float(np.interp(km * 1000, agl, u))
            vk = float(np.interp(km * 1000, agl, v))
            ax.plot(uk, vk, 'o', color=FG, ms=3.5, zorder=6)
            ax.text(uk + 1.2, vk + 1.2, str(km), color=FG, fontsize=6.6,
                    zorder=6)

    def mark(uu, vv, lab, col, dx=2.5):
        if uu is None or vv is None or not np.isfinite(uu) or not np.isfinite(vv):
            return
        if abs(uu) > top or abs(vv) > top:
            return
        ax.plot(uu, vv, 'o', mfc='none', mec=col, ms=6, mew=1.2, zorder=6)
        d = np.degrees(np.arctan2(-uu, -vv)) % 360
        ax.text(uu + dx, vv, f'{d:.0f}/{np.hypot(uu, vv):.0f} {lab}',
                color=col, fontsize=6.6, va='center', zorder=6)

    mark(rstu, rstv, 'RM', FG)
    lm = _q(lambda: _w.non_parcel_bunkers_motion(prof)[2:4])
    if lm:
        mark(float(lm[0]), float(lm[1]), 'LM', FG)
    cor = _q(lambda: _w.corfidi_mcs_motion(prof))
    if cor:
        mark(float(cor[2]), float(cor[3]), 'DN', '#00ccff')
        mark(float(cor[0]), float(cor[1]), 'JP', '#00ccff')

    ca = _q(lambda: float(_pa.critical_angle(prof, stu=rstu, stv=rstv)))
    if ca is not None and np.isfinite(ca):
        ax.text(0.5, 0.08, f'Critical Angle = {ca:.0f}\u00b0',
                transform=ax.transAxes, color='#00ffff', fontsize=7.4,
                ha='center', va='center', zorder=7)

    ax.set_xlim(-top, top)
    ax.set_ylim(-top, top)
    ax.set_aspect('equal', adjustable='box')
    ax.set_xticks([])
    ax.set_yticks([])


# ------------------------------------------------------------ нижние блоки
def _box(fig, rect, title=None):
    """Обрамлённый блок, как секции внизу окна SHARPpy."""
    ax = fig.add_axes(rect, facecolor=BG)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_color(FRAME)
        s.set_linewidth(1.5)
    if title:
        ax.text(0.5, 0.965, title, ha='center', va='top', color='#9ecfff',
                fontsize=8.5, fontweight='bold', transform=ax.transAxes)
    return ax


def _pcl_block(fig, rect, prof, res, parcel_flag=3):
    """Левый нижний блок по исходнику sharppy/viz/thermo.py.

    Координаты взяты оттуда буквально. Для частиц ширина кадра делится
    на 8: подписи и числа центрируются в колонках с шагом brx/8.
    Для индексов делится на 10: левая колонка от поля, средняя с 3.5,
    правая с 6, вертикальная черта на 7. Лапс-рейты слева внизу,
    композиты справа от черты.
    """
    ax = _box(fig, rect)
    MONO = 'monospace'
    FS = 7.4

    # --- частицы: колонки brx/8, центры на 1..7
    c8 = [(i + 1) / 8.0 for i in range(7)]
    hdr = ('PCL', 'CAPE', 'CINH', 'LCL', 'LI', 'LFC', 'EL')
    for x, htxt in zip(c8, hdr):
        ax.text(x, 0.960, htxt, color='#a8a8a8', fontsize=7.0, family=MONO,
                ha='center', va='top')
    rows = _q(lambda: core._parcel_rows(prof), []) or []
    for ri, row in enumerate(rows[:4]):
        y = 0.880 - ri * 0.068
        # выбранная частица подсвечена голубым — так же, как pcl_sel_color
        want = dict((f, n) for n, f in PARCELS).get(parcel_flag, 'MU')
        sel = str(row[0]).strip().upper() == want
        col = '#00ffff' if sel else '#ffffff'
        for ci, cell in enumerate(row[:7]):
            ax.text(c8[ci], y, str(cell), color=col, fontsize=FS,
                    family=MONO, ha='center', va='center')
    ax.plot([0.0, 1.0], [0.600, 0.600], color='#ffffff', lw=0.8)

    # --- индексы: три колонки, x = 0.01 / 0.35 / 0.60
    th = list(_q(lambda: core._thermo_rows(prof), []) or [])
    # SHERB и MBURST ядро отдаёт среди композитов, а справа от черты
    # у SHARPpy только Supercell, STP и SHIP — без этого они пропадали.
    # MBURST в оригинале и так стоит в термодинамике, SHERB — рядом с ним
    comp = dict(_q(lambda: core._composite_rows(prof, res), []) or [])
    have = {str(lab) for lab, _ in th}
    for name in ('MBURST', 'SHERB'):
        if name in comp and name not in have:
            th.append((name, comp[name]))
    per = max(1, (len(th) + 2) // 3)
    # колонки шириной примерно по трети кадра; строка не должна залезать
    # в соседнюю, поэтому длинные подписи режутся по ширине колонки
    for ci, lx in enumerate((0.012, 0.345, 0.672)):
        for ri, (lab, val) in enumerate(th[ci * per:(ci + 1) * per]):
            y = 0.540 - ri * 0.060
            s = f'{lab} = {val}'
            if len(s) > 20:
                s = s[:19] + '\u2026'
            ax.text(lx, y, s, color='#ffffff', fontsize=6.3, family=MONO,
                    va='center')
    ax.plot([0.0, 1.0], [0.195, 0.195], color='#ffffff', lw=0.8)
    ax.plot([0.700, 0.700], [0.0, 0.195], color='#ffffff', lw=0.8)

    # --- лапс-рейты слева, композиты справа от вертикальной черты
    def pick(*keys):
        for k in keys:
            v = res.get(k)
            if v is not None:
                return v
        return None

    lrs = [('Sfc-3km AGL LR', pick('lr03', 'lr_03')),
           ('3-6km AGL LR', pick('lr36', 'lr_36')),
           ('850-500mb LR', pick('lr85', 'lr_850_500')),
           ('700-500mb LR', pick('lr75', 'lr_700_500'))]
    ri = 0
    for lab, val in lrs:
        if val is None:
            continue
        try:
            txt = f'{lab} = {float(val):.1f} C/km'
        except (TypeError, ValueError):
            txt = f'{lab} = {val}'
        ax.text(0.012, 0.160 - ri * 0.040, txt, color='#ffffff', fontsize=6.6,
                family=MONO, va='center')
        ri += 1

    # цвета порогов — из thermo.py (alert_colors)
    ALERT = ['#775000', '#996600', '#ffffff', '#ffff00', '#ff0000', '#e700df']

    def sev_color(name, v):
        if v is None or not np.isfinite(v):
            return ALERT[0]
        if name == 'Supercell':
            for lim, c in ((19.95, 5), (11.95, 4), (1.95, 2), (0.45, 1)):
                if v >= lim:
                    return ALERT[c]
            return ALERT[0]
        if name == 'STP (cin)':
            for lim, c in ((8, 5), (4, 4), (2, 3), (1, 2), (0.5, 1)):
                if v >= lim:
                    return ALERT[c]
            return ALERT[0]
        if name == 'STP (fix)':
            for lim, c in ((7, 5), (5, 4), (2, 3), (1, 2), (0.5, 1)):
                if v >= lim:
                    return ALERT[c]
            return ALERT[0]
        for lim, c in ((5, 5), (2, 4), (1, 3), (0.5, 2)):
            if v >= lim:
                return ALERT[c]
        return ALERT[0]

    sev = [('Supercell', pick('scp')), ('STP (cin)', pick('stp_cin', 'stp')),
           ('STP (fix)', pick('stp_fixed', 'stp_fix')), ('SHIP', pick('ship'))]
    for si, (lab, val) in enumerate(sev):
        try:
            fv = float(val)
            txt = f'{lab} = {fv:.1f}'
        except (TypeError, ValueError):
            fv, txt = None, f'{lab} = --'
        ax.text(0.715, 0.160 - si * 0.040, txt, color=sev_color(lab, fv),
                fontsize=6.6, family=MONO, va='center', fontweight='bold')
    return ax


def _kin_block(fig, rect, prof, rstu, rstv):
    """Кинематика по исходнику sharppy/viz/kinematics.py.

    Кадр делится на 10: заголовки центрируются на 3, 5.5, 7.5 и 9.5,
    значения прижимаются вправо к 4, 6, 8 и 10. Строки идут четырьмя
    группами с отбивками, как в оригинале.
    """
    ax = _box(fig, rect)
    MONO = 'monospace'
    FS = 6.6
    VX = (0.420, 0.620, 0.810, 0.985)

    for x, htxt in zip((0.300, 0.550, 0.750, 0.940),
                       ('SRH (m2/s2)', 'Shear (m/s)', 'MnWind', 'SRW')):
        ax.text(x, 0.965, htxt, color='#ffffff', fontsize=6.9, family=MONO,
                ha='center', va='top')

    rows = _q(lambda: core._kinematics_rows(prof, rstu, rstv), []) or []
    groups = (3, 4)          # первый блок из трёх строк, второй из четырёх
    LBL_MAX = 20             # подпись не должна доставать до колонки значений
    y = 0.880
    idx = 0
    for gsize in groups:
        for _ in range(gsize):
            if idx >= len(rows):
                break
            row = rows[idx]
            lab = str(row[0])
            if len(lab) > LBL_MAX:
                lab = lab[:LBL_MAX - 1] + '\u2026'
            ax.text(0.012, y, lab, color='#ffffff', fontsize=6.6,
                    family=MONO, va='center')
            for ci, cell in enumerate(row[1:5]):
                ax.text(VX[ci], y, str(cell), color='#ffffff', fontsize=6.6,
                        family=MONO, va='center', ha='right')
            y -= 0.062
            idx += 1
        y -= 0.026          # отбивка между блоками

    # BRN Shear в SHARPpy берётся из наиболее неустойчивой частицы
    # (kinematics.py: prof.mupcl.brnshear). Отдельного поля brnShear
    # у профиля нет — поэтому строка раньше тихо не рисовалась
    def _brn():
        pcl = getattr(prof, 'mupcl', None)
        if pcl is None:
            from sharppy.sharptab import params as _pa
            pcl = _pa.parcelx(prof, flag=3)
        return float(pcl.brnshear)
    brn = _q(_brn)
    ax.text(0.012, y, 'BRN Shear = ', color='#ffffff', fontsize=FS,
            family=MONO, va='center')
    ax.text(VX[1], y, (f'{brn:.0f} m2/s2' if _qc(brn) else '--'),
            color='#ffffff', fontsize=FS, family=MONO, va='center', ha='right')
    y -= 0.062

    # 4-6km SR Wind — вторая строка этого блока в оригинале
    def _srw46():
        from sharppy.sharptab import winds as _w, interp as _i
        pb = _i.pres(prof, _i.to_msl(prof, 4000.))
        pt = _i.pres(prof, _i.to_msl(prof, 6000.))
        su, sv = _w.sr_wind(prof, pbot=pb, ptop=pt, stu=rstu, stv=rstv)
        return float(su), float(sv)
    srw = _q(_srw46)
    txt = '--'
    if srw and _qc(srw[0]) and _qc(srw[1]):
        d = np.degrees(np.arctan2(-srw[0], -srw[1])) % 360
        txt = f'{d:.0f}/{np.hypot(*srw):.0f} kt'
    ax.text(0.012, y, '4-6km SR Wind = ', color='#ffffff', fontsize=FS,
            family=MONO, va='center')
    ax.text(VX[1], y, txt, color='#ffffff', fontsize=FS, family=MONO,
            va='center', ha='right')
    y -= 0.062
    y -= 0.020

    ax.text(0.012, y, '...Storm Motion Vectors...', color='#ffffff',
            fontsize=FS, family=MONO, va='center')
    y -= 0.062

    def vec(u, v):
        if u is None or not np.isfinite(u):
            return '--'
        d = np.degrees(np.arctan2(-u, -v)) % 360
        return f'{d:.0f}/{np.hypot(u, v):.0f} kt'

    lm = _q(lambda: __import__('sharppy.sharptab.winds', fromlist=['winds'])
            .non_parcel_bunkers_motion(prof)[2:4], (None, None))
    cor = _q(lambda: __import__('sharppy.sharptab.winds', fromlist=['winds'])
             .corfidi_mcs_motion(prof), None)
    items = [('Bunkers Right = ', vec(rstu, rstv), '#0099CC'),
             ('Bunkers Left = ', vec(lm[0], lm[1]), '#FF6666')]
    if cor:
        items.append(('Corfidi Downshear = ', vec(cor[2], cor[3]), '#ffffff'))
        items.append(('Corfidi Upshear = ', vec(cor[0], cor[1]), '#ffffff'))
    for lab, val, col in items:
        ax.text(0.012, y, lab, color=col, fontsize=FS, family=MONO, va='center')
        ax.text(VX[2], y, val, color=col, fontsize=FS, family=MONO,
                va='center', ha='right')
        y -= 0.062

    ax.text(0.985, 0.055, '1km & 6km AGL\nWind Barbs', color='#0A74C6',
            fontsize=6.4, family=MONO, ha='right', va='center')
    return ax


def _sars_block(fig, rect, prof, res):
    """SARS в оригинальном виде — по sharppy/viz/analogues.py.

    Заголовок и две колонки без разделителей. Каждый аналог — одна
    строка «дата (станция) тип», окрашенная по типу. Внизу колонки
    пурпурным число нестрогих совпадений и вероятность.
    """
    from datetime import datetime as _dt
    ax = _box(fig, rect)
    ax.text(0.5, 0.965, 'SARS - Sounding Analogue System',
            transform=ax.transAxes, color=FG, fontsize=8.6, ha='center',
            va='top')

    TOR_COL = {'SIGTOR': '#ff0000', 'WEAKTOR': '#00ffff',
               'NONTOR': '#c0a060'}

    def column(cx, title, matches, kind):
        ax.text(cx, 0.855, title, transform=ax.transAxes, color=FG,
                fontsize=7.4, ha='center', va='top')
        ids = [] if matches is None else list(matches[0])
        if not ids:
            ax.text(cx, 0.52, 'No Quality Matches', transform=ax.transAxes,
                    color=FG, fontsize=7.0, ha='center', va='center')
        else:
            for i, m in enumerate(ids[:9]):
                try:
                    md, loc = str(m).split('.')
                    ds = _dt.strptime(md, '%y%m%d%H').strftime('%d %b %y %HZ')
                except Exception:
                    ds, loc = str(m), ''
                val = matches[1][i] if len(matches) > 1 else ''
                if kind == 'tor':
                    tag = str(val).upper()
                    col = TOR_COL.get(tag, FG)
                    tag = {'SIGTOR': 'SIG', 'WEAKTOR': 'WEAK',
                           'NONTOR': 'NON'}.get(tag, tag)
                else:
                    try:
                        fv = float(val)
                        tag = f'{fv:.2f}'
                        col = '#ff0000' if fv >= 2 else '#00ffff'
                    except (TypeError, ValueError):
                        tag, col = str(val), FG
                ax.text(cx - 0.24, 0.775 - i * 0.070,
                        f'{ds} ({loc}) {tag}', transform=ax.transAxes,
                        color=col, fontsize=6.0, va='center')
        # как в analogues.py: статистика выводится только при наличии
        # хотя бы одного качественного совпадения. Без них — одно
        # «No Quality Matches», даже если нестрогих совпадений много
        if not ids:
            return
        try:
            prob = float(matches[-1]) * 100
            loose = int(matches[-3])
        except Exception:
            return
        if loose > 0:
            sig = 'TOR' if kind == 'tor' else 'SIG'
            # обе строки одним цветом: пурпурный от 50 %, иначе белый
            col = '#ff00ff' if prob >= 50 else FG
            ax.text(cx, 0.115, f'({loose} loose matches)',
                    transform=ax.transAxes, color=col, fontsize=6.6,
                    ha='center', va='center')
            ax.text(cx, 0.045, f'SARS: {prob:.0f}% {sig}',
                    transform=ax.transAxes, color=col, fontsize=6.8,
                    ha='center', va='center')

    column(0.25, 'SUPERCELL', _q(lambda: prof.right_supercell_matches), 'tor')
    column(0.75, 'SGFNT HAIL', _q(lambda: prof.right_matches), 'hail')
    return ax





# таблицы вероятностей EF2+ из sharppy/viz/stp.py
STP_TABLES = {
    'CAPE':   [(0, .00), (250, .12), (500, .14), (1000, .16), (1500, .15),
               (2000, .13), (2500, .14), (3000, .18), (4000, .20)],
    'LCL':    [(750, .19), (1000, .19), (1250, .15), (1500, .10),
               (1750, .06), (2000, .06), (2500, .02)],
    'ESRH':   [(50, .06), (100, .06), (200, .08), (300, .14), (400, .20),
               (500, .27), (600, .38), (700, .37)],
    'EBWD':   [(.01, .0), (20, .03), (30, .05), (40, .06), (50, .12),
               (60, .19), (70, .27), (80, .36)],
    'STPC':   [(.1, .06), (.5, .08), (1, .12), (2, .17), (4, .25),
               (6, .32), (8, .34), (10, .55)],
    'STP_fixed': [(.1, .05), (.5, .06), (1, .11), (2, .17), (3, .25),
                  (5, .25), (7, .39), (9, .55)],
}


def _stp_prob(name, v):
    """Вероятность и цвет по таблице. Для LCL шкала обратная: чем ниже
    основание, тем выше вероятность."""
    if v is None or not np.isfinite(v):
        return None, '#775000'
    tab = STP_TABLES[name]
    prob = tab[0][1]
    if name == 'LCL':
        for lim, p in tab:
            if v >= lim:
                prob = p
    else:
        for lim, p in tab:
            if v >= lim:
                prob = p
    col = ('#e700df' if prob >= .35 else '#ff0000' if prob >= .25 else
           '#ffff00' if prob >= .18 else '#ffffff' if prob >= .10 else
           '#996600')
    return prob, col


def _inset_stp(fig, rect, res, prof):
    """Effective Layer STP (with CIN) — по sharppy/viz/stp.py.

    Коробчатые диаграммы распределения STP по категориям EF и справа
    табличка вероятностей значимого торнадо при суперячейке, посчитанных
    по CAPE, LCL, ESRH, EBWD и двум версиям STP.
    """
    ax = _ax(fig, rect)
    ax.text(0.5, 0.995, 'Effective Layer STP (with CIN)',
            transform=ax.transAxes, color=FG, fontsize=6.8, ha='center',
            va='top')
    d = _q(lambda: __import__('sharppy.databases.inset_data',
                             fromlist=['inset_data']).stpData())
    ax.set_xlim(0, 7)
    ax.set_ylim(-0.35, 11)
    for g in range(1, 12):
        ax.axhline(g, color='#0080ff', lw=0.6, ls=(0, (4, 4)), zorder=0)
        ax.text(0.10, g, str(g), color=FG, fontsize=5.4, va='center')
    if d:
        ef = np.asarray(d.get('ef', d.get('stp_dist')), float)
        texts = list(d['stp_xtexts'])
        w = 0.30
        for i in range(ef.shape[0]):
            c = i + 1
            ax.plot([c, c], [ef[i, 0], ef[i, 1]], color='#00ff00', lw=1.6)
            ax.plot([c, c], [ef[i, 3], ef[i, 4]], color='#00ff00', lw=1.6)
            ax.add_patch(plt.Rectangle((c - w, ef[i, 1]), 2 * w,
                                       ef[i, 3] - ef[i, 1], fill=False,
                                       edgecolor='#00ff00', lw=1.6))
            ax.plot([c - w, c + w], [ef[i, 2], ef[i, 2]], color='#00ff00',
                    lw=1.6)
            _t = ax.text(c, -0.45, texts[i], color=FG, fontsize=5.4, ha='center',
                    va='top')
            _t._noclip = True

    stp = _q(lambda: float(prof.right_stp_cin))
    if stp is None:
        stp = _q(lambda: float(res.get('stp_cin', 0.0)), 0.0)
    if stp is not None and np.isfinite(stp):
        # в оригинале это белая линия текущего значения: по ней видно,
        # в какую категорию EF попадает профиль
        ax.axhline(min(max(stp, 0), 11), color='#ffffff', lw=0.9, zorder=7)

    # табличка вероятностей в правом верхнем углу
    vals = [
        ('CAPE', _q(lambda: float(prof.mlpcl.bplus))),
        ('LCL', _q(lambda: float(prof.mlpcl.lclhght))),
        ('ESRH', _q(lambda: float(prof.right_esrh[0]))),
        ('EBWD', _q(lambda: float(prof.ebwd))),
        ('STPC', stp),
        ('STP_fixed', _q(lambda: float(prof.right_stp_fixed))),
    ]
    # табличка начинается под заголовком, а не поверх него
    bx, by = 0.505, 0.905
    ax.add_patch(plt.Rectangle((bx, by - 0.50), 0.485, 0.50, fill=True,
                               facecolor='#0d0d0d', edgecolor=FRAME, lw=0.7,
                               transform=ax.transAxes, zorder=5))
    ax.text(bx + 0.015, by - 0.035, 'Prob EF2+ torn with supercell',
            transform=ax.transAxes, color=FG, fontsize=5.4, va='center',
            zorder=6)
    ax.text(bx + 0.015, by - 0.095, 'Sample CLIMO = .15 sigtor',
            transform=ax.transAxes, color=FG, fontsize=5.4, va='center',
            zorder=6)
    for i, (name, v) in enumerate(vals):
        p, col = _stp_prob(name, v)
        y = by - 0.155 - i * 0.058
        ax.text(bx + 0.015, y, f'based on {name}:', transform=ax.transAxes,
                color=col, fontsize=5.4, va='center', zorder=6)
        ax.text(bx + 0.470, y, '--' if p is None else f'{p:.2f}',
                transform=ax.transAxes, color=col, fontsize=5.4, va='center',
                ha='right', zorder=6)
    return ax


# ------------------------------------------------------------ сменные врезки
INSETS = [('stp', 'Effective Layer STP (with CIN)'),
          ('stpef', 'EF-Scale Probs (Sig-Tor)'),
          ('vrot', 'EF-Scale Probs (V-Rot)'),
          ('fire', 'Fire Weather'),
          ('ship', 'Sig-Hail Stats'),
          ('winter', 'Winter Weather')]


def _inset_vrot(fig, rect, prof):
    """Вероятности по EF-шкале от Vrot — по sharppy/viz/vrot.py."""
    ax = _ax(fig, rect)
    ax.text(0.5, 0.99, 'Conditional EF-scale Probs based on Vrot',
            transform=ax.transAxes, color=FG, fontsize=6.4, ha='center',
            va='top')
    d = _q(lambda: __import__('sharppy.databases.inset_data',
                             fromlist=['inset_data']).vrotData())
    ax.set_xlim(0, 110)
    ax.set_ylim(0, 70)
    for g in (10, 20, 30, 40, 50, 60):
        ax.axhline(g, color='#0080FF', lw=0.7, ls=(0, (5, 4)), zorder=0)
        ax.text(1.5, g, str(g), color=FG, fontsize=5.6, va='center')
    if not d:
        return ax
    x = np.asarray(d['xpts'], float)
    for key, col in (('EF0-EF1', '#006600'), ('EF2-EF3', '#FFCC33'),
                     ('EF4-EF5', '#FF00FF')):
        y = np.clip(np.asarray(d[key], float), 0, 70)
        ax.plot(x, y, color=col, lw=1.8, zorder=3)
    for lab, xv, col in (('EF0-EF1', 25, '#006600'), ('EF2-EF3', 50, '#FFCC33'),
                         ('EF4-EF5', 75, '#FF00FF')):
        ax.text(xv, 67, lab, color=col, fontsize=6.0, ha='center', va='top')
    for t in range(10, 111, 20):
        _t = ax.text(t, -3.5, str(t), color=FG, fontsize=5.4, ha='center',
                     va='top')
        _t._noclip = True
    return ax


def _inset_ship(fig, rect, prof):
    """Статистика значимого града — по sharppy/viz/ship.py."""
    ax = _ax(fig, rect)
    ax.text(0.5, 0.99, 'Significant Hail Param (SHIP)',
            transform=ax.transAxes, color=FG, fontsize=6.6, ha='center',
            va='top')
    d = _q(lambda: __import__('sharppy.databases.inset_data',
                             fromlist=['inset_data']).shipData())
    ax.set_xlim(0, 4)
    ax.set_ylim(0, 5)
    for g in range(1, 5):
        ax.axhline(g, color='#0080ff', lw=0.7, ls=(0, (5, 4)), zorder=0)
        ax.text(0.06, g, str(g), color=FG, fontsize=5.8, va='center')
    if d:
        ef = np.asarray(d['ship_dist'], float)
        texts = list(d['ship_xtexts'])
        for i in range(ef.shape[0]):
            c = i + 1
            w = 0.27
            ax.plot([c, c], [ef[i, 0], ef[i, 1]], color='#00ff00', lw=1.4)
            ax.plot([c, c], [ef[i, 3], ef[i, 4]], color='#00ff00', lw=1.4)
            ax.add_patch(plt.Rectangle((c - w, ef[i, 1]), 2 * w,
                                       ef[i, 3] - ef[i, 1], fill=False,
                                       edgecolor='#00ff00', lw=1.4))
            _t = ax.text(c, -0.22, texts[i], color=FG, fontsize=5.4, ha='center',
                    va='top')
            _t._noclip = True
    ship = _q(lambda: float(prof.ship))
    if ship is not None and np.isfinite(ship):
        v = min(max(ship, 0), 5)
        col = ('#e700df' if v >= 5 else '#ff0000' if v >= 2 else
               '#ffff00' if v >= 1 else '#ffffff' if v >= 0.5 else '#775000')
        ax.axhline(v, color=col, lw=1.6, zorder=4)
    return ax


def _inset_fire(fig, rect, prof):
    """Пожарная погода по sharppy/viz/fire.py.

    Две колонки: слева влага, справа низкоуровневый ветер, ниже
    производные индексы. Значения берутся из тех же полей профиля,
    что и в оригинале: sfc_rh, rh01km, pblrh, pwat, meanwind01km,
    meanwindpbl, pblmaxwind, fosberg, haines_*.
    """
    ax = _box(fig, rect, 'Fire Weather Parameters')
    MONO = 'monospace'
    ax.text(0.06, 0.845, 'Moisture', color='#00ff00', fontsize=6.6,
            family=MONO, va='center')
    ax.text(0.94, 0.845, 'Low-Level Wind', color='#00aaff', fontsize=6.6,
            family=MONO, va='center', ha='right')

    def vec(pair):
        v = _q(lambda: tuple(float(x) for x in pair()))
        if not v or not np.isfinite(v[0]):
            return '--'
        return f'{v[0]:.0f}/{v[1]:.0f}'

    def num(fn, fmt):
        v = _q(fn)
        return '--' if v is None or not np.isfinite(v) else fmt.format(v)

    from_uv = lambda u, v: (np.degrees(np.arctan2(-u, -v)) % 360, np.hypot(u, v))

    left = [
        ('SFC RH', num(lambda: float(prof.sfc_rh), '{:.0f}%')),
        ('0-1 km RH', num(lambda: float(prof.rh01km), '{:.0f}%')),
        ('BL mean RH', num(lambda: float(prof.pblrh), '{:.0f}%')),
        ('PW', num(lambda: float(prof.pwat), '{:.2f} in')),
    ]
    right = [
        ('SFC', vec(lambda: (prof.wdir[prof.get_sfc()],
                             prof.wspd[prof.get_sfc()]))),
        ('0-1 km mean', vec(lambda: from_uv(prof.meanwind01km[0],
                                            prof.meanwind01km[1]))),
        ('BL mean', vec(lambda: from_uv(prof.meanwindpbl[0],
                                        prof.meanwindpbl[1]))),
        ('BL max', vec(lambda: from_uv(prof.pblmaxwind[0],
                                       prof.pblmaxwind[1]))),
    ]
    for i in range(4):
        y = 0.745 - i * 0.082
        lab, val = left[i]
        ax.text(0.06, y, f'{lab} = {val}', color='#ffffff', fontsize=6.4,
                family=MONO, va='center')
        lab, val = right[i]
        ax.text(0.94, y, f'{lab} = {val}', color='#ffffff', fontsize=6.4,
                family=MONO, va='center', ha='right')

    pbl = _q(lambda: float(prof.pbl_h))
    if pbl is not None and np.isfinite(pbl):
        ax.text(0.5, 0.395, f'PBL Height = {pbl * 3.28084:.0f}ft / {pbl:.0f}m',
                color='#ffffff', fontsize=6.4, family=MONO, ha='center',
                va='center')

    ax.text(0.5, 0.300, 'Derived Indices', color='#00aaff', fontsize=6.6,
            family=MONO, ha='center', va='center')

    fos = _q(lambda: float(prof.fosberg))
    ax.text(0.5, 0.185,
            'Fosberg FWI = ' + ('M' if fos is None or not np.isfinite(fos)
                                else f'{fos:.0f}'),
            color=_fire_color(fos, (30, 50, 75)), fontsize=7.6, family=MONO,
            ha='center', va='center')

    hh = _q(lambda: int(prof.haines_hght))
    hv = _q(lambda: [float(prof.haines_low), float(prof.haines_mid),
                     float(prof.haines_high)])
    if hh is not None and hv:
        lab = ['L', 'M', 'H'][max(0, min(2, hh))]
        val = hv[max(0, min(2, hh))]
        ax.text(0.5, 0.075, f'Haines Index ({lab}) = {val:.0f}',
                color=_fire_color(val, (3, 4, 5)), fontsize=7.6, family=MONO,
                ha='center', va='center')
    return ax


def _fire_color(v, lims):
    """Окраска по порогам — как alert-цвета пожарной врезки."""
    if v is None or not np.isfinite(v):
        return '#775000'
    if v >= lims[2]:
        return '#ff0000'
    if v >= lims[1]:
        return '#ff9900'
    if v >= lims[0]:
        return '#ffff00'
    return '#996600'


def _inset_winter(fig, rect, prof):
    """Зимняя врезка — по sharppy/viz/winter.py: слой DGZ и тип осадков."""
    ax = _box(fig, rect)
    MONO = 'monospace'
    ax.text(0.5, 0.955, '*** DENDRITIC GROWTH ZONE (-12 TO -17 C) ***',
            transform=ax.transAxes, color='#ffff00', fontsize=6.2,
            ha='center', va='top')
    oprh = _q(lambda: float(prof.oprh))
    ax.text(0.5, 0.855, 'OPRH (Omega*PW*RH): ' +
            ('N/A' if oprh is None else f'{oprh:.2f}'),
            transform=ax.transAxes,
            color='#ff4d4d' if (oprh is not None and oprh < -0.1) else FG,
            fontsize=6.4, ha='center', va='center')
    rows = []
    zb = _q(lambda: float(__import__('sharppy.sharptab', fromlist=['tab'])
                          .utils.M2FT(__import__('sharppy.sharptab',
                          fromlist=['tab']).interp.hght(prof, prof.dgz_pbot))))
    zt = _q(lambda: float(__import__('sharppy.sharptab', fromlist=['tab'])
                          .utils.M2FT(__import__('sharppy.sharptab',
                          fromlist=['tab']).interp.hght(prof, prof.dgz_ptop))))
    if zb is not None and zt is not None and np.isfinite(zb) and np.isfinite(zt):
        rows.append(('Layer Depth', f'{zt - zb:.0f} ft'))
        rows.append(('DGZ', f'{zb:.0f}-{zt:.0f} ft msl'))
    for lab, fn, fmt in (('Mean Layer RH', lambda: float(prof.dgz_meanrh), '{:.0f} %'),
                         ('Mean Layer PW', lambda: float(prof.dgz_pw), '{:.2f} in'),
                         ('Mean MixRat', lambda: float(prof.dgz_meanq), '{:.1f} g/kg')):
        v = _q(fn)
        if v is not None and np.isfinite(v):
            rows.append((lab, fmt.format(v)))
    for i, (lab, val) in enumerate(rows):
        y = 0.72 - i * 0.095
        ax.text(0.06, y, lab, color='#ffffff', fontsize=6.6, family=MONO,
                va='center')
        ax.text(0.94, y, val, color='#ffffff', fontsize=6.6, family=MONO,
                va='center', ha='right')
    pt = _q(lambda: str(prof.precip_type))
    ax.text(0.5, 0.14, '*** BEST GUESS PRECIP TYPE ***', transform=ax.transAxes,
            color=FG, fontsize=6.0, ha='center', va='center')
    ax.text(0.5, 0.05, pt or '--', transform=ax.transAxes, color=FG,
            fontsize=10, ha='center', va='center', fontweight='bold')
    return ax


def draw_inset(fig, rect, kind, prof, res):
    """Рисует выбранную врезку в правом нижнем углу.

    Если врезка падает на данных профиля, вместо всей компоновки
    отваливается только она — в рамке пишется причина.
    """
    try:
        return _draw_inset_raw(fig, rect, kind, prof, res)
    except Exception as e:
        ax = _box(fig, rect)
        ax.text(0.5, 0.5, f'врезка недоступна\n{type(e).__name__}: {e}',
                transform=ax.transAxes, color='#8a8a8a', fontsize=6.4,
                ha='center', va='center', wrap=True)
        return ax


def _draw_inset_raw(fig, rect, kind, prof, res):
    if kind == 'stpef':
        return _stp_box(fig, rect, res, prof)
    if kind == 'vrot':
        return _inset_vrot(fig, rect, prof)
    if kind == 'ship':
        return _inset_ship(fig, rect, prof)
    if kind == 'fire':
        return _inset_fire(fig, rect, prof)
    if kind == 'winter':
        return _inset_winter(fig, rect, prof)
    return _inset_stp(fig, rect, res, prof)


# ------------------------------------------------------------ правка профиля
class Editor:
    """Перетаскивание кривых температуры и точки росы, как в SHARPpy.

    Движение разрешено только по горизонтали: давление уровня не меняется,
    меняется значение на нём. Это тот же приём, что в draggable.py с
    lock_dim='y'. После отпускания кнопки профиль пересобирается через
    Profile.copy — штатный способ SHARPpy пересчитать всё разом.
    """

    PICK_PX = 9          # радиус захвата узла в пикселях

    def __init__(self, fig, ax, prof, on_change, pick_px=None):
        self.fig, self.ax, self.prof = fig, ax, prof
        self.on_change = on_change
        if pick_px:
            self.PICK_PX = pick_px
        self.kind = None          # 'tmpc' или 'dwpc'
        self.idx = None
        self.line = None
        self.cids = [
            fig.canvas.mpl_connect('button_press_event', self.press),
            fig.canvas.mpl_connect('motion_notify_event', self.move),
            fig.canvas.mpl_connect('button_release_event', self.release),
        ]

    # ---- перевод координат
    def _xy(self, arr, p):
        return core._sx(arr, p), core._sy(p)

    def _t_from_x(self, x, p):
        return float(x) - core.SKEW * np.log10(core.P_BOT / float(p))

    def _nearest(self, event):
        """Ближайший узел любой из двух кривых в пределах радиуса захвата."""
        if event.inaxes is not self.ax or event.xdata is None:
            return None, None, None
        p = np.asarray(self.prof.pres, float)
        best = (None, None, self.PICK_PX ** 2)
        for kind in ('tmpc', 'dwpc'):
            arr = np.asarray(getattr(self.prof, kind), float)
            ok = np.isfinite(p) & np.isfinite(arr) & (p >= core.P_TOP)
            if not ok.any():
                continue
            xs, ys = self._xy(arr[ok], p[ok])
            pts = self.ax.transData.transform(np.column_stack([xs, ys]))
            d2 = (pts[:, 0] - event.x) ** 2 + (pts[:, 1] - event.y) ** 2
            i = int(np.argmin(d2))
            if d2[i] < best[2]:
                best = (kind, np.where(ok)[0][i], d2[i])
        return best

    # ---- события
    def press(self, event):
        if event.button != 1:
            return
        kind, idx, _ = self._nearest(event)
        if kind is None:
            return
        self.kind, self.idx = kind, idx
        arr = np.asarray(getattr(self.prof, kind), float).copy()
        p = float(self.prof.pres[idx])
        self.line, = self.ax.plot([core._sx(arr[idx], p)], [core._sy(p)],
                                  'o', color='#ffffff', ms=6, zorder=20)
        self.fig.canvas.draw_idle()

    def move(self, event):
        if self.kind is None or event.inaxes is not self.ax:
            return
        p = float(self.prof.pres[self.idx])
        t = self._t_from_x(event.xdata, p)
        self.line.set_data([core._sx(t, p)], [core._sy(p)])
        self.fig.canvas.draw_idle()

    def release(self, event):
        if self.kind is None:
            return
        kind, idx = self.kind, self.idx
        self.kind = self.idx = None
        if self.line is not None:
            self.line.remove()
            self.line = None
        if event.inaxes is not self.ax or event.xdata is None:
            self.fig.canvas.draw_idle()
            return

        p = float(self.prof.pres[idx])
        newval = self._t_from_x(event.xdata, p)
        tmpc = np.asarray(self.prof.tmpc, float).copy()
        dwpc = np.asarray(self.prof.dwpc, float).copy()
        if kind == 'tmpc':
            # температура не может стать ниже точки росы
            tmpc[idx] = max(newval, dwpc[idx] if np.isfinite(dwpc[idx]) else newval)
        else:
            dwpc[idx] = min(newval, tmpc[idx] if np.isfinite(tmpc[idx]) else newval)

        newprof = self._rebuild(tmpc, dwpc)
        if newprof is None:
            return
        self.prof = newprof
        self.on_change(newprof)

    def _rebuild(self, tmpc, dwpc):
        """Пересобирает профиль с изменёнными кривыми.

        Копировать нужно тем же классом, которым профиль создан:
        у базового Profile нет служебных полей вроде sfc, и расчёт
        частиц на нём падает. type(prof) даёт BasicProfile или
        ConvectiveProfile — смотря что было исходно.
        """
        try:
            return type(self.prof).copy(self.prof, tmpc=tmpc, dwpc=dwpc)
        except Exception:
            pass
        # запасной путь: собрать заново из массивов
        try:
            from sharppy.sharptab import profile as _prof
            kw = dict(pres=np.asarray(self.prof.pres, float),
                      hght=np.asarray(self.prof.hght, float),
                      tmpc=tmpc, dwpc=dwpc, strictQC=False)
            wdir = getattr(self.prof, 'wdir', None)
            wspd = getattr(self.prof, 'wspd', None)
            if wdir is not None and wspd is not None:
                kw.update(wdir=np.asarray(wdir, float),
                          wspd=np.asarray(wspd, float))
            else:
                kw.update(u=np.asarray(self.prof.u, float),
                          v=np.asarray(self.prof.v, float))
            return _prof.create_profile(profile='convective', **kw)
        except Exception:
            return None

    def disconnect(self):
        for cid in self.cids:
            self.fig.canvas.mpl_disconnect(cid)
        self.cids = []


def attach_editor(fig, prof, on_change):
    """Подключает правку к уже отрисованной фигуре.

    Ось Skew-T запоминается в draw(), поэтому искать её не нужно.
    """
    ax = getattr(fig, '_skew_ax', None)
    if ax is None:
        return None
    return Editor(fig, ax, prof, on_change)



class Zoomer:
    """Масштабирование колесом к точке под курсором.

    Приближать можно свободно, отдалять — не дальше исходного вида:
    иначе панель уезжает в угол и вернуть её можно только сбросом.
    Годографу даётся запас, чтобы кольца сетки помещались целиком.
    """

    MAX_OUT = {'skew': 1.0, 'hodo': 1.5}
    MIN_SPAN = 0.02          # предел приближения, доля исходного размера

    def __init__(self, fig, axes):
        self.fig = fig
        self.home = {}
        for ax, kind in axes:
            if ax is not None:
                self.home[ax] = (ax.get_xlim(), ax.get_ylim(),
                                 self.MAX_OUT.get(kind, 1.0))
        self.cids = [
            fig.canvas.mpl_connect('scroll_event', self.scroll),
            fig.canvas.mpl_connect('button_press_event', self.click),
        ]

    @staticmethod
    def _clamp(lo, hi, home_lo, home_hi, max_out, min_span):
        """Ужимает и сдвигает интервал, чтобы он остался в допуске.

        Ось может быть перевёрнутой (у давления значения убывают вверх),
        поэтому считаем всё в возрастающем порядке, а направление
        восстанавливаем в конце.
        """
        flip = home_hi < home_lo
        a, b = (hi, lo) if flip else (lo, hi)
        ha, hb = (home_hi, home_lo) if flip else (home_lo, home_hi)

        hspan = hb - ha
        span = min(max(b - a, hspan * min_span), hspan * max_out)
        c = (a + b) / 2.0
        a, b = c - span / 2.0, c + span / 2.0

        # допустимая внешняя рамка: исходный вид, расширенный на запас
        pad = hspan * (max_out - 1.0) / 2.0
        oa, ob = ha - pad, hb + pad
        if a < oa:
            a, b = oa, oa + span
        if b > ob:
            a, b = ob - span, ob
        return (b, a) if flip else (a, b)

    def scroll(self, event):
        ax = event.inaxes
        if ax not in self.home or event.xdata is None:
            return
        hx, hy, max_out = self.home[ax]
        f = 1 / 1.25 if event.button == 'up' else 1.25
        x0, x1 = ax.get_xlim()
        y0, y1 = ax.get_ylim()
        cx, cy = event.xdata, event.ydata
        nx = (cx + (x0 - cx) * f, cx + (x1 - cx) * f)
        ny = (cy + (y0 - cy) * f, cy + (y1 - cy) * f)
        ax.set_xlim(self._clamp(nx[0], nx[1], hx[0], hx[1], max_out,
                                self.MIN_SPAN))
        ax.set_ylim(self._clamp(ny[0], ny[1], hy[0], hy[1], max_out,
                                self.MIN_SPAN))
        self.fig.canvas.draw_idle()

    def click(self, event):
        # правая кнопка возвращает исходный вид панели
        if event.button != 3 or event.inaxes not in self.home:
            return
        hx, hy, _ = self.home[event.inaxes]
        event.inaxes.set_xlim(hx)
        event.inaxes.set_ylim(hy)
        self.fig.canvas.draw_idle()

    def snapshot(self):
        """Текущие пределы всех панелей — чтобы потом вернуть."""
        return {ax: (ax.get_xlim(), ax.get_ylim()) for ax in self.home}

    def to_home(self):
        for ax, (hx, hy, _) in self.home.items():
            ax.set_xlim(hx)
            ax.set_ylim(hy)

    def restore(self, snap):
        for ax, (xl, yl) in snap.items():
            ax.set_xlim(xl)
            ax.set_ylim(yl)

    def disconnect(self):
        for cid in self.cids:
            self.fig.canvas.mpl_disconnect(cid)
        self.cids = []


class ParcelPicker:
    """Смена частицы кликом по строке в таблице, как в оригинале."""

    def __init__(self, fig, on_pick):
        self.fig, self.on_pick = fig, on_pick
        self.ax = getattr(fig, '_pcl_ax', None)
        self.cid = fig.canvas.mpl_connect('button_press_event', self.click)

    def click(self, event):
        if event.button != 1 or event.inaxes is not self.ax:
            return
        # строки идут с шагом 0.068 от 0.880 вниз
        for i, (name, flag) in enumerate(PARCELS):
            y = 0.880 - i * 0.068
            if abs(event.ydata - y) < 0.034:
                self.on_pick(flag, name)
                return

    def disconnect(self):
        self.fig.canvas.mpl_disconnect(self.cid)


class InsetPicker:
    """Правая кнопка по врезке — выбор, что в ней показывать."""

    def __init__(self, fig, on_menu):
        self.fig, self.on_menu = fig, on_menu
        self.ax = getattr(fig, '_inset_ax', None)
        self.cid = fig.canvas.mpl_connect('button_press_event', self.click)

    def click(self, event):
        if event.button != 3 or event.inaxes is not self.ax:
            return
        self.on_menu(event)

    def disconnect(self):
        self.fig.canvas.mpl_disconnect(self.cid)


def attach_interaction(fig, prof, on_change, on_parcel, on_inset_menu=None):
    """Подключает правку кривых, масштабирование, выбор частицы и врезки."""
    ed = attach_editor(fig, prof, on_change)
    zm = Zoomer(fig, [(getattr(fig, '_skew_ax', None), 'skew'),
                      (getattr(fig, '_hodo_ax', None), 'hodo')])
    pp = ParcelPicker(fig, on_parcel)
    ip = InsetPicker(fig, on_inset_menu) if on_inset_menu else None
    return tuple(x for x in (ed, zm, pp, ip) if x is not None)


# ------------------------------------------------------------ главная сборка
# флаги частиц в params.parcelx
PARCELS = [('SFC', 1), ('ML', 4), ('FCST', 2), ('MU', 3)]


def get_parcel(prof, res, flag):
    """Частица по флагу. Готовая MU лежит в res, остальные считаем."""
    if flag == 3:
        p = res.get('parcel')
        if p is not None:
            return p
    return _q(lambda: __import__('sharppy.sharptab.params',
                                 fromlist=['params']).parcelx(prof, flag=flag))


def _clip_texts(fig):
    """Подписи внутри панелей обрезаются рамкой.

    В matplotlib текст по умолчанию не обрезается: при приближении
    подписи колец годографа и уровней Skew-T уходили за край, а при
    сохранении растягивали картинку. Заголовки над панелями — это
    тексты фигуры, а не осей, их это не касается.
    """
    for ax in fig.get_axes():
        for t in ax.texts:
            if getattr(t, '_noclip', False):
                continue          # подпись намеренно стоит под рамкой
            t.set_clip_on(True)
            t.set_clip_path(ax.patch)


def _embolden(fig):
    """Утолщает весь текст фигуры.

    Тонкий моноширинный шрифт на чёрном фоне при сглаживании теряет
    яркость и выглядит серым, хотя цвет белый. В SHARPpy текст рисует
    Qt без такого эффекта, поэтому для сходства берём полужирное.
    """
    import matplotlib.text as mtext
    for t in fig.findobj(mtext.Text):
        if t.get_text():
            t.set_fontweight('bold')


def draw(prof, res, title, parcel_flag=3, inset='stp'):
    """Собирает фигуру в компоновке окна SHARPpy."""
    fig = plt.figure(figsize=(11.8, 8.35), facecolor=BG)
    fig._parcel_flag = parcel_flag
    fig._inset = inset
    fig._pcl = get_parcel(prof, res, parcel_flag)

    # Геометрия панелей снята с окна SHARPpy 1179x835 и переведена
    # в доли фигуры, поэтому пропорции совпадают с оригиналом.
    # --- Skew-T и колонки справа от него
    ax = fig.add_axes([0.025, 0.329, 0.424, 0.647], facecolor=BG)
    core_draw_skew(ax, prof, res, fig._pcl, winter=(inset == 'winter'))
    fig._skew_ax = ax
    _barbs(fig, [0.450, 0.329, 0.047, 0.647], prof)
    _wind_speed(fig, [0.500, 0.329, 0.051, 0.647], prof)
    _temp_adv(fig, [0.556, 0.329, 0.030, 0.647], prof)

    # --- годограф
    def _motion():
        from sharppy.sharptab import winds
        a, b, _, _ = winds.non_parcel_bunkers_motion(prof)
        return float(a), float(b)
    rstu, rstv = _q(_motion, (None, None))

    ax_h = fig.add_axes([0.588, 0.491, 0.408, 0.485], facecolor=BG)
    fig._hodo_ax = ax_h
    try:
        _draw_hodo(ax_h, prof, rstu, rstv)
    except Exception as e:
        import traceback
        print('[hodo] свой годограф не нарисовался:', e, flush=True)
        traceback.print_exc()
        ax_h.cla()
        ax_h.set_facecolor(BG)
        _q(lambda: core._draw_hodograph(ax_h, prof, rstu, rstv))
    ax_h.set_facecolor(BG)
    for s in ax_h.spines.values():
        s.set_color(FRAME)
    if ax_h.get_title():
        ax_h.title.set_color(FG)
    lg = ax_h.get_legend()
    if lg is not None:
        lg.get_frame().set_facecolor('#101010')
        lg.get_frame().set_edgecolor(FRAME)
        for t in lg.get_texts():
            t.set_color(FG)

    # --- четыре врезки под годографом
    _slinky(fig, [0.588, 0.327, 0.091, 0.160], prof, fig._pcl)
    _theta_e(fig, [0.679, 0.327, 0.076, 0.160], prof)
    _sr_wind(fig, [0.755, 0.327, 0.093, 0.160], prof)
    _hazard(fig, [0.848, 0.327, 0.148, 0.160], prof, res)

    # --- нижние блоки
    fig._pcl_ax = _pcl_block(fig, [0.004, 0.066, 0.250, 0.242], prof, res,
                             parcel_flag)
    kin_ax = _kin_block(fig, [0.254, 0.066, 0.242, 0.242], prof, rstu, rstv)
    sars_ax = _sars_block(fig, [0.496, 0.066, 0.254, 0.242], prof, res)
    fig._inset_ax = draw_inset(fig, [0.751, 0.066, 0.245, 0.242],
                               inset, prof, res)

    # в оригинале нижний ряд обрамлён голубым #3399CC — цвет из стилей
    # самих панелей SHARPpy; верхние врезки остаются белыми
    for a in (fig._pcl_ax, kin_ax, sars_ax, fig._inset_ax):
        if a is None:
            continue
        for s in a.spines.values():
            s.set_color(INSET)
            s.set_linewidth(1.5)

    _embolden(fig)
    _clip_texts(fig)
    fig.text(0.025, 0.982, title, color=FG, fontsize=11, fontweight='bold')
    fig.text(0.996, 0.982, 'SHARPpy Fix v0.0.1', color='#7a7a7a',
             fontsize=8, ha='right')
    verdict = (res.get('verdict') or res.get('summary') or '')
    if verdict:
        fig.text(0.5, 0.030, str(verdict), color=FG, fontsize=9, ha='center')
    return fig


def _qc(v):
    """Значение годное: не маска, не пропуск SHARPpy, конечное."""
    try:
        if np.ma.is_masked(v):
            return False
        v = float(v)
    except (TypeError, ValueError):
        return False
    return np.isfinite(v) and v > -9000


def _draw_effective_layer(ax, prof):
    """Эффективный слой притока — голубая скобка у земли, как в SHARPpy.

    Повторяет draw_effective_layer из sharppy/viz/skew.py: вертикальная
    черта на изотерме -20° у 1000 гПа от основания слоя до вершины,
    засечки на концах. Снизу — «SFC», если слой начинается у земли,
    иначе высота основания; сверху — высота вершины над землёй и ESRH.
    Нет эффективного слоя (нет плавучести) — нет и скобки.
    """
    COL = '#00FFFF'
    pbot = _q(lambda: prof.ebottom)
    ptop = _q(lambda: prof.etop)
    if not (_qc(pbot) and _qc(ptop)):
        got = _q(lambda: __import__('sharppy.sharptab.params', fromlist=['params'])
                 .effective_inflow_layer(prof))
        if got:
            pbot, ptop = got[0], got[1]
    if not (_qc(pbot) and _qc(ptop)):
        return
    pbot, ptop = float(pbot), float(ptop)

    p = np.asarray(prof.pres, float)
    h = np.asarray(prof.hght, float)
    ok = np.isfinite(p) & np.isfinite(h) & (p > 0) & (h > -9000)
    if ok.sum() < 3:
        return
    pp, hh = p[ok], h[ok]
    order = np.argsort(pp)
    lp, hs = np.log(pp[order]), hh[order]
    hat = lambda pr: float(np.interp(np.log(pr), lp, hs))
    psfc = float(pp.max())
    sfc_h = hat(psfc)

    x1 = float(core._sx(-20.0, 1000.0))
    x2 = float(core._sx(-33.0, 1000.0))
    tick = 2.7                    # полдлины засечки: 15 px из оригинала
    y1, y2 = core._sy(pbot), core._sy(ptop)
    kw = dict(color=COL, lw=1.6, zorder=9, solid_capstyle='butt')
    ax.plot([x1 - tick, x1 + tick], [y1, y1], **kw)
    ax.plot([x1 - tick, x1 + tick], [y2, y2], **kw)
    ax.plot([x1, x1], [y1, y2], **kw)

    bot = 'SFC' if abs(pbot - psfc) < 0.5 else f'{hat(pbot) - sfc_h:.0f}m'
    top = f'{hat(ptop) - sfc_h:.0f}m'
    esrh = _q(lambda: float(prof.right_esrh[0]))
    lab = dict(color=COL, fontsize=7.8, zorder=9)
    # отступы в экранных точках, как прямоугольники подписей у оригинала
    b = ax.annotate(bot, (x2, y1), xytext=(0, -3), textcoords='offset points',
                    ha='left', va='top', annotation_clip=False, **lab)
    b._noclip = True              # у земли подпись может уйти под рамку
    ax.annotate(top, (x2, y2), xytext=(0, 3), textcoords='offset points',
                ha='left', va='bottom', **lab)
    if esrh is not None and np.isfinite(esrh):
        ax.annotate(f'{esrh:.0f} m2s2', (x1, y2), xytext=(-6, 3),
                    textcoords='offset points', ha='left', va='bottom', **lab)


def _height_levels(p, h, kms=(1, 3, 6, 9, 12, 15)):
    """Давление на круглых высотах над землёй, интерполяцией.

    Раньше бралась ближайшая точка зонда: если профиль обрывался
    на 11 км, то и «12 км», и «15 км» ложились на его верхний уровень
    одна поверх другой. Теперь высоты вне профиля просто не подписываются.
    """
    p = np.asarray(p, float)
    h = np.asarray(h, float)
    ok = np.isfinite(p) & np.isfinite(h) & (p > 0)
    if ok.sum() < 3:
        return []
    p, h = p[ok], h[ok]
    order = np.argsort(h)
    p, h = p[order], h[order]
    agl = h - h[0]
    out = []
    for km in kms:
        z = km * 1000.0
        if z > agl[-1]:
            break
        pk = float(np.exp(np.interp(z, agl, np.log(p))))
        if pk >= core.P_TOP:
            out.append((km, pk))
    return out


def core_draw_skew(ax, prof, res, pcl=None, winter=False):
    """Skew-T в оформлении окна SHARPpy.

    Фон намеренно обесцвечен: изотермы и адиабаты серым пунктиром, чтобы
    не спорить с данными. Цветом выделено только то, что выделено
    в оригинале — две кривые, семь линий отношения смеси, две изотермы
    0 и -20 с высотой, уровни LCL/LFC/EL и лапс-рейт.
    """
    p_line = np.arange(core.P_BOT, core.P_TOP - 1, -5.0)
    GRID = '#7d7d7d'

    for t0 in range(-110, 61, 10):
        ax.plot(core._sx(np.full_like(p_line, t0), p_line), core._sy(p_line),
                color=GRID, lw=0.5, ls='--', zorder=1)
    for th in range(-40, 201, 10):
        t_dry = (th + 273.15) * (p_line / 1000.0) ** 0.2854 - 273.15
        ax.plot(core._sx(t_dry, p_line), core._sy(p_line),
                color=GRID, lw=0.5, ls='--', zorder=1)
    thermo = getattr(core, 'thermo', None)
    if thermo is not None and hasattr(thermo, 'wetlift'):
        p_m = np.arange(1000.0, core.P_TOP - 1, -25.0)
        for t0 in range(-20, 41, 10):
            tm = _q(lambda t0=t0: [thermo.wetlift(1000.0, float(t0), float(pp))
                                   for pp in p_m])
            if tm:
                ax.plot(core._sx(tm, p_m), core._sy(p_m), color='#6a6a6a',
                        lw=0.5, ls=':', zorder=1)

    p = np.asarray(prof.pres, float)
    t = np.asarray(prof.tmpc, float)
    td = np.asarray(prof.dwpc, float)
    h = np.asarray(prof.hght, float)

    # горизонтальные линии круглых высот через всё поле
    # горизонтальные линии круглых высот через всё поле
    for km, pk in _height_levels(p, h):
        ax.axhline(core._sy(pk), color='#a0a0a0', lw=0.9, zorder=2)

    # семь линий отношения смеси — только в нижней части, как в оригинале
    p_w = np.arange(1000.0, 699.0, -10.0)
    for w in (10, 14, 18, 22, 26, 30, 34):
        e = w * p_w / (622.0 + w)
        lg = np.log(e / 6.112)
        tdw = 243.5 * lg / (17.67 - lg)
        x = core._sx(tdw, p_w)
        y = core._sy(p_w)
        ax.plot(x, y, color='#3fa34d', lw=0.8, zorder=3)
        ax.text(x[-1], y[-1] + 0.006, str(w), color='#3fa34d', fontsize=6.5,
                ha='center', va='bottom', zorder=3)

    # изотермы 0 и -20 с высотой уровня в футах
    for t0, col in ((0, '#3b7dd8'), (-20, '#3b7dd8')):
        ax.plot(core._sx(np.full_like(p_line, t0), p_line), core._sy(p_line),
                color=col, lw=1.3, zorder=3)
        ok = np.isfinite(p) & np.isfinite(t) & np.isfinite(h)
        pz, zft = None, None
        if ok.sum() > 2:
            tt, hh, pp = t[ok], h[ok], p[ok]
            idx = np.where(np.diff(np.sign(tt - t0)) != 0)[0]
            if len(idx):
                i = idx[0]
                dt = tt[i + 1] - tt[i]
                frac = (t0 - tt[i]) / dt if dt else 0.0
                zft = (hh[i] + frac * (hh[i + 1] - hh[i])) * 3.28084
                pz = pp[i] + frac * (pp[i + 1] - pp[i])
        if pz is None:
            # профиль изотерму не пересекает — подписываем на краю поля
            pz = 500.0 if t0 == -20 else 850.0
        lab = f"{t0} C={zft:.0f}'" if zft is not None else f'{t0} C'
        ax.text(core._sx(t0, pz) + 1.5, core._sy(pz), lab, color=col,
                fontsize=7, va='center', zorder=4)

    m = np.isfinite(p) & np.isfinite(t) & (p >= core.P_TOP)
    m2 = np.isfinite(p) & np.isfinite(td) & (p >= core.P_TOP)
    wb = _q(lambda: np.asarray(prof.wetbulb, float))
    if wb is not None:
        mw = np.isfinite(p) & np.isfinite(wb) & (p >= core.P_TOP)
        ax.plot(core._sx(wb[mw], p[mw]), core._sy(p[mw]), color='#7fb3d5',
                lw=0.8, zorder=5)
    ax.plot(core._sx(t[m], p[m]), core._sy(p[m]), color='#ff3b30', lw=2.4,
            zorder=6)
    ax.plot(core._sx(td[m2], p[m2]), core._sy(p[m2]), color='#34c759', lw=2.4,
            zorder=6)

    if pcl is None:
        pcl = res.get('parcel')
    if pcl is not None and getattr(pcl, 'ptrace', None) is not None:
        pt = np.asarray(pcl.ptrace, float)
        tt2 = np.asarray(pcl.ttrace, float)
        ok = np.isfinite(pt) & np.isfinite(tt2) & (pt >= core.P_TOP)
        ax.plot(core._sx(tt2[ok], pt[ok]), core._sy(pt[ok]), color='#e0e0e0',
                lw=1.1, ls='--', zorder=7)

    # Уровни как в оригинале: короткая черта стоит ровно на высоте уровня,
    # а подпись рядом с ней. У LCL черта над подписью, у LFC — под ней:
    # так при близких LCL и LFC подписи расходятся и не слипаются.
    for nm, val, col, side in (
            ('LCL', getattr(pcl, 'lclpres', None) if pcl else None,
             '#00ff00', 'below'),
            ('LFC', getattr(pcl, 'lfcpres', None) if pcl else None,
             '#ffff00', 'above'),
            ('EL', getattr(pcl, 'elpres', None) if pcl else None,
             '#ff00ff', 'above')):
        if val and np.isfinite(val) and core.P_TOP <= val <= core.P_BOT:
            y = core._sy(val)
            ax.plot([39.5, 47.5], [y, y], color=col, lw=1.6, zorder=8,
                    solid_capstyle='butt')
            # подпись сдвигаем в точках экрана, а не в данных: так отступ
            # одинаковый на любой высоте и при любом масштабе
            ax.annotate(nm, (43.5, y), xytext=(0, -3 if side == 'below' else 3),
                        textcoords='offset points', ha='center',
                        va='top' if side == 'below' else 'bottom',
                        color=col, fontsize=8.5, fontweight='bold', zorder=8,
                        annotation_clip=True)

    # лапс-рейт 700-500, как подпись у оригинала
    lr = _q(lambda: float(res.get('lr75')))
    if lr is not None and np.isfinite(lr):
        ax.text(18, core._sy(600.0), f'{lr:.1f} C/km', color='#ffb066',
                fontsize=8, zorder=8)

    if winter:
        # уровни, которые SHARPpy показывает в зимнем режиме:
        # слой дендритного роста и высоты нулевых изотерм
        for attr, col, lab in (('dgz_pbot', '#ffff00', None),
                               ('dgz_ptop', '#ffff00', None)):
            pv = _q(lambda a=attr: float(getattr(prof, a)))
            if pv and np.isfinite(pv) and core.P_TOP <= pv <= core.P_BOT:
                ax.axhline(core._sy(pv), color=col, lw=1.0, zorder=5)
        for name, arr, col in (('FRZ', t, '#ffb066'), ('WBZ', wb, '#ffb066')):
            if arr is None:
                continue
            a = np.asarray(arr, float)
            ok = np.isfinite(p) & np.isfinite(a)
            if ok.sum() < 3:
                continue
            aa, pp2, hh2 = a[ok], p[ok], h[ok]
            idx = np.where(np.diff(np.sign(aa)) != 0)[0]
            if not len(idx):
                continue
            i = idx[0]
            d = aa[i + 1] - aa[i]
            fr = (0 - aa[i]) / d if d else 0.0
            pz = pp2[i] + fr * (pp2[i + 1] - pp2[i])
            zf = (hh2[i] + fr * (hh2[i + 1] - hh2[i])) * 3.28084
            ax.text(24, core._sy(pz), f"{name}={zf:.0f}'", color=col,
                    fontsize=7.5, va='center', zorder=8)

    _draw_effective_layer(ax, prof)

    # подписи высот — на тех же высотах, что и серые линии; у земли
    # стоит только SFC, без «0 км» поверх неё
    for km, pk in _height_levels(p, h):
        ax.text(-49, core._sy(pk), f'{km} км', color='#ff6b6b',
                fontsize=7.5, va='center', zorder=8)

    ax.set_xlim(-50, 50)
    ax.set_ylim(core._sy(core.P_BOT), core._sy(core.P_TOP))
    ticks = [1000, 925, 850, 700, 600, 500, 400, 300, 250, 200, 150, 100]
    ax.set_yticks([core._sy(x) for x in ticks])
    ax.set_yticklabels([str(x) for x in ticks], color=FG, fontsize=7)
    ax.set_xticks(range(-50, 51, 10))
    ax.set_xticklabels([str(x) for x in range(-50, 51, 10)], color=FG,
                       fontsize=7)
    for s in ax.spines.values():
        s.set_color(FRAME)
        s.set_linewidth(1.5)
    ax.tick_params(colors=FG)
    ax.grid(False)

"""
Язык интерфейса: русский или английский.

По умолчанию язык берётся из системы: русская Windows — русский,
любая другая — английский. В меню его можно выбрать вручную, выбор
хранится в настройках.

Русский текст остаётся в коде как есть и служит ключом: _('Выход')
на английском вернёт 'Exit'. Если перевода нет, строка останется
русской — пропуск виден сразу, но ничего не ломается.
"""
import json
import locale
import os
import re

LANG = 'ru'          # действующий язык: 'ru' или 'en'
MODE = 'auto'        # выбор пользователя: 'auto', 'ru', 'en'


# ------------------------------------------------------------ язык системы
def system_lang():
    """'ru', если система на русском, иначе 'en'.

    На Windows смотрим язык интерфейса пользователя — именно он виден
    в меню и окнах. Код 0x19 в младших битах — русский. На других
    системах — локаль и переменные окружения.
    """
    try:
        # Android: в приложении на Chaquopy есть мост в Java, и язык
        # интерфейса телефона отдаёт системная локаль
        from java import jclass
        lang = str(jclass('java.util.Locale').getDefault().getLanguage())
        return 'ru' if lang.lower().startswith('ru') else 'en'
    except Exception:
        pass
    try:
        import ctypes
        lid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        return 'ru' if (lid & 0x3FF) == 0x19 else 'en'
    except Exception:
        pass
    for v in (os.environ.get('LANG', ''), os.environ.get('LC_ALL', ''),
              (locale.getlocale()[0] or '')):
        if v.lower().startswith(('ru', 'russian')):
            return 'ru'
    return 'en'


def init(cfg_path):
    """Выставляет язык по настройкам или по системе. Вызывать до
    построения интерфейса и до определения списков с подписями."""
    global LANG, MODE
    MODE = 'auto'
    try:
        MODE = json.load(open(cfg_path, encoding='utf-8')).get('lang', 'auto')
    except Exception:
        pass
    LANG = system_lang() if MODE == 'auto' else MODE
    if LANG not in ('ru', 'en'):
        LANG = 'en'
    return LANG


def set_mode(mode):
    """Выбор языка: 'auto', 'ru' или 'en'. Возвращает действующий язык."""
    global LANG, MODE
    MODE = mode if mode in ('auto', 'ru', 'en') else 'auto'
    LANG = system_lang() if MODE == 'auto' else MODE
    return LANG


def _(s):
    """Перевод строки интерфейса."""
    if LANG == 'ru':
        return s
    return EN.get(s, s)


# ------------------------------------------------------------ названия
_TR = dict(zip('абвгдеёжзийклмнопрстуфхцчшщъыьэюя',
               ['a', 'b', 'v', 'g', 'd', 'e', 'yo', 'zh', 'z', 'i', 'y',
                'k', 'l', 'm', 'n', 'o', 'p', 'r', 's', 't', 'u', 'f',
                'kh', 'ts', 'ch', 'sh', 'shch', '', 'y', '', 'e', 'yu', 'ya']))


def translit(s):
    out = []
    for ch in s:
        low = ch.lower()
        if low in _TR:
            t = _TR[low]
            out.append(t.capitalize() if ch.isupper() else t)
        else:
            out.append(ch)
    return ''.join(out)


def N(name):
    """Название станции или города: готовый перевод или транслитерация."""
    if LANG == 'ru' or not re.search('[а-яА-ЯёЁ]', name or ''):
        return name
    return NAMES_EN.get(name) or translit(name)


# ------------------------------------------------------------ подписи на диаграмме
# Подписи рисует общее с ботом ядро, и они по-русски. Для английского
# интерфейса переводим готовую фигуру заменой известных фрагментов.
FIG_EN = [
    ('Годограф (узлы)', 'Hodograph (kt)'),
    ('нет траектории', 'no trajectory'),
    ('врезка недоступна', 'inset unavailable'),
    ('Эфф.слой', 'Eff Inflow'),
    ('ГрадSFC-3км', 'LR SFC-3km'), ('Град700-500', 'LR 700-500'),
    ('Град850-500', 'LR 850-500'), ('3CAPE 0-3км', '3CAPE 0-3km'),
    ('Дж/кг', 'J/kg'), ('°C/км', '°C/km'), ('м²/с²', 'm²/s²'),
    ('н/д', '--'), ('совп.', 'match.'),
    ('Конвекция маловероятна', 'Convection unlikely'),
    ('осадки: Снег', 'precip: Snow'), ('осадки: Дождь', 'precip: Rain'),
    ('осадки:', 'precip:'),
    ('Град (знач.)', 'Hail (sig.)'), ('Торнадо (знач.)', 'Tornado (sig.)'),
    # колонка адвекции температуры
    ('Адв.', 'Adv.'), ('°C/ч', '°C/h'),
    # обрезанные многоточием хвосты: обрезка идёт раньше перевода
    ('Дж/', 'J/'), ('°C/к', '°C/k'), ('Дж', 'J'),
    ('км', 'km'), (' мм', ' mm'), (' м/с', ' m/s'),
]


def translate_figure(fig):
    """Переводит подписи уже нарисованной фигуры на английский."""
    if LANG == 'ru':
        return
    import matplotlib.text as mtext
    for t in fig.findobj(mtext.Text):
        s = t.get_text()
        if not s or not re.search('[а-яА-ЯёЁ]', s):
            continue
        for ru, en in FIG_EN:
            s = s.replace(ru, en)
        t.set_text(s)


# ------------------------------------------------------------ словари
NAMES_EN = {
    'Якутск': 'Yakutsk', 'Москва': 'Moscow',
    'Москва (Долгопрудный)': 'Moscow (Dolgoprudny)',
    'Санкт-Петербург': 'Saint Petersburg', 'Ростов-на-Дону': 'Rostov-on-Don',
    'Нижний Новгород': 'Nizhny Novgorod', 'Петропавловск-Камчатский':
    'Petropavlovsk-Kamchatsky', 'Южно-Сахалинск': 'Yuzhno-Sakhalinsk',
    'Малые Кармакулы': 'Malye Karmakuly', 'Нерюнгри (Чульман)':
    'Neryungri (Chulman)', 'Москва (Шереметьево)': 'Moscow (Sheremetyevo)',
    'Оймякон': 'Oymyakon', 'Олёкминск': 'Olyokminsk',
    'Ытык-Кюёль': 'Ytyk-Kyuyol', 'Черский': 'Chersky',
    # США
    'Норман, Оклахома': 'Norman, OK', 'Даллас, Техас': 'Dallas, TX',
    'Хьюстон, Техас': 'Houston, TX', 'Амарилло, Техас': 'Amarillo, TX',
    'Лаббок, Техас': 'Lubbock, TX', 'Мидленд, Техас': 'Midland, TX',
    'Додж-Сити, Канзас': 'Dodge City, KS', 'Топика, Канзас': 'Topeka, KS',
    'Омаха, Небраска': 'Omaha, NE', 'Су-Фолс, Юж. Дакота': 'Sioux Falls, SD',
    'Бисмарк, Сев. Дакота': 'Bismarck, ND', 'Денвер, Колорадо': 'Denver, CO',
    'Альбукерке, Нью-Мексико': 'Albuquerque, NM',
    'Финикс, Аризона': 'Phoenix, AZ', 'Солт-Лейк-Сити, Юта': 'Salt Lake City, UT',
    'Лас-Вегас, Невада': 'Las Vegas, NV',
    'Лос-Анджелес, Калифорния': 'Los Angeles, CA',
    'Сан-Франциско, Калифорния': 'San Francisco, CA',
    'Сиэтл, Вашингтон': 'Seattle, WA', 'Бойсе, Айдахо': 'Boise, ID',
    'Миннеаполис, Миннесота': 'Minneapolis, MN', 'Чикаго, Иллинойс': 'Chicago, IL',
    'Сент-Луис, Миссури': 'St. Louis, MO', 'Канзас-Сити, Миссури': 'Kansas City, MO',
    'Литл-Рок, Арканзас': 'Little Rock, AR', 'Джэксон, Миссисипи': 'Jackson, MS',
    'Новый Орлеан, Луизиана': 'New Orleans, LA',
    'Бирмингем, Алабама': 'Birmingham, AL', 'Нэшвилл, Теннесси': 'Nashville, TN',
    'Луисвилл, Кентукки': 'Louisville, KY', 'Индианаполис, Индиана': 'Indianapolis, IN',
    'Детройт, Мичиган': 'Detroit, MI', 'Атланта, Джорджия': 'Atlanta, GA',
    'Таллахасси, Флорида': 'Tallahassee, FL', 'Тампа, Флорида': 'Tampa, FL',
    'Майами, Флорида': 'Miami, FL', 'Шарлотт, Сев. Каролина': 'Charlotte, NC',
    'Вашингтон, округ Колумбия': 'Washington, DC',
    'Питтсбург, Пенсильвания': 'Pittsburgh, PA', 'Нью-Йорк': 'New York, NY',
    'Бостон, Массачусетс': 'Boston, MA', 'Анкоридж, Аляска': 'Anchorage, AK',
}

MONTHS_EN = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
             'August', 'September', 'October', 'November', 'December']
DAYS_EN = ['M', 'T', 'W', 'T', 'F', 'S', 'S']

EN = {
    # ошибки загрузки
    'Нужен requests:  conda install -c conda-forge requests':
        'requests is required:  conda install -c conda-forge requests',
    'Вайоминг не вернул профиль на этот срок.':
        'Wyoming returned no sounding for this time.',
    'Не разобрал заголовок таблицы.': 'Could not parse the table header.',
    'Профиль пустой.': 'The profile is empty.',
    'Open-Meteo не вернул данные.': 'Open-Meteo returned no data.',
    'нет': 'none',
    'Не похоже на файл .snd': 'This does not look like an .snd file',
    'В файле меньше пяти уровней': 'The file has fewer than five levels',
    'Нет срока {stamp} в ответе модели.': 'Time {stamp} is missing in the model response.',
    'Модель вернула {n} уровней (нужно 5+).\nМодель: {model}, дней назад: {age}':
        'The model returned {n} levels (5+ needed).\nModel: {model}, days ago: {age}',
    'Нет полей: {fields}\n': 'Missing fields: {fields}\n',
    'Для дат старше 92 дней доступен только архив ERA5, и выбор модели там не действует.':
        'Only the ERA5 archive is available for dates older than 92 days, '
        'and model choice has no effect there.',
    'Архив модельных прогонов Open-Meteo начинается с 2021 года.\n\n'
    'Для более ранних дат бери "Наблюдения (Вайоминг)" — там архив с 1970-х.':
        'The Open-Meteo archive of model runs starts in 2021.\n\n'
        'For earlier dates use "Observed (Wyoming)" — its archive goes back to the 1970s.',
    'Уровни с температурой: {got}': 'Levels with temperature: {got}',
    # виды карты
    'Якутия': 'Yakutia', 'Сибирь': 'Siberia', 'Россия': 'Russia',
    'Северное полушарие': 'Northern Hemisphere', 'США': 'USA',
    'Береговая линия не загружена\nФайл → Загрузить карту':
        'Coastline not loaded\nFile → Download map',
    # окно профиля
    'Кеш: —': 'Cache: —',
    'Сохранить PNG': 'Save PNG', 'Тёмная схема': 'Dark scheme',
    'Правка кривых': 'Edit curves', 'Сбросить правки': 'Reset edits',
    'Считаю профиль...': 'Computing profile...',
    'Нет sharppy_core.py': 'sharppy_core.py not found', 'Нет модуля': 'Module missing',
    '[layout] не удалось:': '[layout] failed:',
    'Компоновка SHARPpy недоступна': 'SHARPpy layout unavailable',
    'Готово': 'Done', 'Ошибка': 'Error', 'Не получилось': 'Failed',
    'Пересчитываю...': 'Recomputing...',
    'Положи sharppy_core.py рядом с оболочкой и запускай из окружения, где установлен SHARPpy.':
        'Put sharppy_core.py next to the launcher and run it from the environment where SHARPpy is installed.',
    'Рисую обычную диаграмму ядра.\nПодробности в консоли.':
        'Drawing the plain core diagram.\nDetails are in the console.',
    'Частица: {name}': 'Parcel: {name}', 'Сохранено: {p}': 'Saved: {p}',
    # меню
    'Открыть файл...': 'Open file...',
    'Указать программу просмотра...': 'Set viewer program...',
    'Загрузить карту': 'Download map', 'Очистить кеш': 'Clear cache',
    'Выход': 'Exit', 'Файл': 'File',
    'Встроенный просмотр': 'Built-in viewer', 'Внешний SHARPpy': 'External SHARPpy',
    'Вид': 'View', 'О программе': 'About', 'Справка': 'Help',
    'Язык': 'Language', 'Как в системе': 'System default',
    # главное окно
    'Источник зондирования': 'Sounding source', 'Выбор даты': 'Select date',
    'Выбор срока': 'Select time', 'Построить профиль': 'Build profile',
    'Только скачать': 'Download only', 'Выбор станции': 'Select station',
    'Карта': 'Map', 'Список': 'List', 'Найти': 'Find',
    'Файл уже есть. Скачать заново?': 'The file already exists. Download again?',
    'Качаю береговую линию...': 'Downloading coastline...',
    'Можно положить любой GeoJSON с береговой линией вручную:\n{path}':
        'You can place any coastline GeoJSON manually:\n{path}',
    'Карта загружена: {n} линий': 'Map loaded: {n} lines',
    'Закрыть': 'Close',
    'Исполняемый файл SHARPpy': 'SHARPpy executable',
    'Все файлы': 'All files', 'Программы': 'Programs',
    'Кеш: {n} файлов, {mb:.1f} МБ': 'Cache: {n} files, {mb:.1f} MB',
    'Код WMO, например 24959': 'WMO code, e.g. 24959',
    'ICAO (UEEE) или координаты (62.0, 129.7)': 'ICAO (UEEE) or coordinates (62.0, 129.7)',
    'Для моделей введи ICAO-код (например UEEE) или координаты (62.0, 129.7).':
        'For models enter an ICAO code (e.g. UEEE) or coordinates (62.0, 129.7).',
    'Поиск': 'Search', 'Ищу...': 'Searching...', 'Найдено: {name}': 'Found: {name}',
    'Зондирования': 'Soundings',
    'Выбери станцию в списке справа.': 'Pick a station in the list on the right.',
    'Станция': 'Station', 'Выбери срок.': 'Pick a time.', 'Срок': 'Time',
    'Модель недоступна': 'Model unavailable',
    'Загружаю...': 'Downloading...', 'Из кеша: {name}': 'From cache: {name}',
    'Готово: {name} — {n} уровней': 'Done: {name} — {n} levels',
    '[launcher] запускаю:': '[launcher] launching:',
    'SHARPpy не запустился': 'SHARPpy failed to start',
    'Открываю: {name}': 'Opening: {name}',
    'Команда: {cmd}\n\nФайл готов, открой его вручную:\n{path}':
        'Command: {cmd}\n\nThe file is ready, open it manually:\n{path}',
    'Язык изменится после перезапуска. Перезапустить сейчас?':
        'The language will change after a restart. Restart now?',
    # сведения
    'Источники:': 'Sources:',
    '   наблюдения — архив Университета Вайоминга':
        '   observations — University of Wyoming archive',
    '   модели — Open-Meteo (Arpege, ICON, GFS, ECMWF, GEM)':
        '   models — Open-Meteo (Arpege, ICON, GFS, ECMWF, GEM)',
    'Модельные профили доступны с 2021 года, фактические — с 1970-х.':
        'Model profiles are available from 2021, observed ones from the 1970s.',
    'Кеш: {path}': 'Cache: {path}',
    'Автор фикса и оболочки: Henich, 2026': 'Fix and launcher by Henich, 2026',
    # приложение для телефона
    'Загружаю и считаю...': 'Downloading and computing...',
    'ICAO (UEEE) или (62.0, 129.7)': 'ICAO (UEEE) or (62.0, 129.7)',
    'Станция не найдена': 'Station not found', 'Не найдено': 'Not found',
    'Источник': 'Source', 'Дата': 'Date', 'Срок UTC': 'Time UTC',
    '\u2039 Назад': '\u2039 Back', 'Частица': 'Parcel', 'Врезка': 'Inset',
    'Сохранить': 'Save', 'Сохранено': 'Saved',
}

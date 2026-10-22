# Как загрузить проект на GitHub

Три способа — от самого простого к ручному. Для первого нужен только Windows.

## 1. Скрипт: двойной клик

1. Создайте пустой репозиторий: <https://github.com/new>  
   Имя любое, например `yakutia-radar`. Галочку «Add a README» можно не ставить.
2. В папке проекта запустите **`publish.bat`**.
3. Если Git не установлен, скрипт предложит поставить его через winget.
4. Вставьте адрес репозитория, например:
   ```
   https://github.com/ЛОГИН/yakutia-radar.git
   ```
5. Скрипт сам сделает `git init`, коммит и `git push`.

Повторная загрузка — снова `publish.bat` (адрес запоминается).

Можно и из консоли:

```powershell
.\publish.ps1 -RepoUrl https://github.com/ЛОГИН/yakutia-radar.git
.\publish.ps1 -Message "обновил радар"
.\publish.ps1 -InstallGit
```

## 2. GitHub Desktop — без командной строки

1. Установите <https://desktop.github.com/> и войдите в аккаунт.
2. **File → Add local repository** → выберите папку проекта.
3. Нажмите **Publish repository**.
4. Снимите галочку «Keep this code private», если сайт должен быть публичным.

Дальше изменения загружаются кнопкой **Push origin** после коммита.

## 3. Через сайт GitHub — только для мелких правок

На странице репозитория: **Add file → Upload files**.  
Важно: веб-загрузка не принимает папки целиком, а тайлов радара около 2500 —
для первой публикации этот способ не подходит. Используйте способ 1 или 2.

## После загрузки

- **Render** → New → Blueprint → выбрать репозиторий: настройки возьмутся из `render.yaml`.
- В `client/config.js` вписать адрес Render:
  ```js
  window.API_BASE = "https://ваш-сервис.onrender.com";
  ```
  и снова запустить `publish.bat`.
- **GitHub → Settings → Pages → Source: GitHub Actions**.
- Сайт: `https://ЛОГИН.github.io/ИМЯ/`, SharpPy: `.../sharppy.html`.

## Что не попадёт в репозиторий

В `.gitignore` уже исключены кеши и тяжёлые архивы: `data/cache/`, `data/igra/`,
`data/probe/`, логи. Снимок радара (`client/tiles/`, `client/data.js`) наоборот
нужен — он публикуется на Pages.

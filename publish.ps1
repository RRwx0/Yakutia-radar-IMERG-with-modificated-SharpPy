param(
    [string]$RepoUrl = "",
    [string]$Message = "update site",
    [switch]$InstallGit,
    [switch]$Help
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

function Info($text) { Write-Host $text }
function Has-Git { return [bool](Get-Command git -ErrorAction SilentlyContinue) }

if ($Help) {
    Info "Публикация проекта на GitHub"
    Info ""
    Info "  publish.bat                         — спросит адрес репозитория и запушит"
    Info "  publish.bat https://github.com/USER/REPO.git"
    Info "  publish.bat -Message ""новый текст"" "
    Info "  publish.bat -InstallGit             — сначала поставить Git через winget"
    Info ""
    Info "Перед первым запуском создайте пустой репозиторий: https://github.com/new"
    exit 0
}

if (-not (Has-Git)) {
    Info "Git не найден."
    if (-not $InstallGit) {
        $answer = Read-Host "Установить Git сейчас через winget? (y/n)"
        if ($answer -match '^[yYдД]') { $InstallGit = $true }
    }
    if ($InstallGit) {
        Info "Устанавливаю Git через winget…"
        winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements
        $machine = [Environment]::GetEnvironmentVariable("Path", "Machine")
        $user = [Environment]::GetEnvironmentVariable("Path", "User")
        $env:Path = "$machine;$user"
    }
    if (-not (Has-Git)) {
        Info ""
        Info "Git всё ещё недоступен. Варианты:"
        Info "  1) перезапустить это окно после установки;"
        Info "  2) поставить GitHub Desktop: https://desktop.github.com/"
        Info "  3) установить Git вручную: https://git-scm.com/download/win"
        exit 1
    }
}

if (-not (Test-Path -LiteralPath ".git")) {
    Info "Создаю локальный репозиторий…"
    git init | Out-Null
    git branch -M main
}

if ($RepoUrl) {
    $remotes = @(git remote)
    if ($remotes -contains "origin") {
        git remote set-url origin $RepoUrl
    } else {
        git remote add origin $RepoUrl
    }
}

$remotes = @(git remote)
if (-not ($remotes -contains "origin")) {
    Info "Репозиторий GitHub ещё не привязан."
    Info "1) Создайте пустой репозиторий: https://github.com/new"
    Info "2) Запустите: publish.bat https://github.com/ЛОГИН/ИМЯ.git"
    Start-Process "https://github.com/new"
    exit 1
}

$name = git config user.name
if (-not $name) {
    $name = Read-Host "Имя для коммитов"
    if ($name) { git config user.name $name }
}
$email = git config user.email
if (-not $email) {
    $email = Read-Host "Email для коммитов"
    if ($email) { git config user.email $email }
}

Info "Добавляю файлы…"
git add -A

git commit -m $Message
if ($LASTEXITCODE -ne 0) {
    Info "Новых изменений нет — отправляю текущую версию."
}

Info "Отправляю на GitHub…"
git push -u origin main
if ($LASTEXITCODE -ne 0) {
    Info ""
    Info "Пуш не прошёл. Обычно помогает:"
    Info "  • войти через GitHub Desktop (https://desktop.github.com/);"
    Info "  • или создать Personal Access Token и ввести его как пароль;"
    Info "  • проверить, что репозиторий создан и пуст."
    exit 1
}

Info ""
Info "Готово. Дальше:"
Info "  • Render: New → Blueprint → выбрать репозиторий (render.yaml уже в проекте);"
Info "  • client/config.js: вписать адрес Render;"
Info "  • GitHub → Settings → Pages → Source: GitHub Actions."


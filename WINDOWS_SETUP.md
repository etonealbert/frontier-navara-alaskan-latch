# WINDOWS_SETUP.md — настройка Windows для build123d

Агент должен выполнить эти команды **сам** в терминале Windows, если получил разрешение на запуск и установку ПО. Проверяй результаты каждой команды. Инсталляция требует интернета. Не запускать скрипты из непроверенных репозиториев с правами администратора.

## 1. Найти подходящий Python

Официальный build123d в актуальном README заявляет поддержку Python 3.11–3.14. Для предсказуемой совместимости на Windows начни с **Python 3.12 64-bit**.

```powershell
py -3.12 --version
```

Если нет Python 3.12 и `winget` доступен, согласуй установку и выполни:

```powershell
winget install --id Python.Python.3.12 --exact --source winget
```

После установки может потребоваться **новый терминал**. Альтернативно установи Python 3.12 с https://www.python.org/downloads/windows/ и снова проверь `py -3.12 --version`.

## 2. Создать отдельное окружение в папке проекта

PowerShell в корне распакованного проекта:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install build123d
.\.venv\Scripts\python.exe -c "import build123d; print('build123d OK:', getattr(build123d, '__version__', 'version metadata unavailable'))"
```

**Никакая активация `.venv` не требуется**, вызывай Python по пути `\.venv\Scripts\python.exe`. Не меняй PowerShell ExecutionPolicy ради активации. Команды pip должны завершиться успешно; зафиксируй фактические версии пакетов в отчёте, можно использовать `\.venv\Scripts\python.exe -m pip freeze > reports\pip-freeze.txt`.

Если `py -3.12` отсутствует, но есть другая поддерживаемая версия Python, проверь её совместимость и явно отрази выбор в отчёте. Не устанавливай несовместимые wheel-файлы вручную.

## 3. Где брать API и как экспортировать

- GitHub: https://github.com/gumyr/build123d
- Документация: https://build123d.readthedocs.io/en/latest/
- Стабильная установка: `pip install build123d` (**не** обязательна установка из git branch `dev`).
- Примеры в официальном README показывают `export_stl(part, "file.stl")` и `export_step(part, "file.step")`.

Для визуального просмотра STL/STEP по желанию поставить **FreeCAD** из https://www.freecad.org/downloads.php, но он **не нужен** для автоматического создания STEP/STL через build123d. Если нет прав установки, сначала всё равно создай CAD через Python.

## 4. Запуск модели (после создания агентом)

```powershell
.\.venv\Scripts\python.exe src\model.py
.\.venv\Scripts\python.exe src\validate.py
```

Эти файлы **не предустановлены**, агент должен сначала написать их под данную деталь. В каждом скрипте используй стабильный способ указания путей относительно корня проекта, а не текущего каталога, если иначе скрипт ломается.

## 5. Что НЕ устанавливать

Не требуется Blender, платная лицензия Fusion, slicer, Git, Docker или установка всего `build123d` GitHub-репозитория для выполнения этой задачи. G-code без настроек конкретного принтера не делай. Если после построения потребуется просмотр — согласуй отдельно установку FreeCAD.

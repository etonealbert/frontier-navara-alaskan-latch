# Среда выполнения V01

Фактическая среда, в которой построена и проверена модель (ноябрь 2026).

| Компонент | Версия / значение |
|---|---|
| ОС | macOS 26.7.1 (сборка 25G241), Darwin 25.6.0, **arm64 (Apple Silicon)** |
| Python | 3.13.7 (python.org framework build), виртуальное окружение `.venv` в корне проекта |
| build123d | **0.13.0** (stable, требование пакета: Python ≥ 3.11, < 3.15) |
| OCP / OpenCascade | cadquery-ocp-novtk **8.0.1.1.0** (привязки к OpenCascade 8.0.1; вариант без VTK) |
| numpy | 2.5.4 |
| trimesh | 4.7.0 (проверка STL, сечения для чертежа) |
| manifold3d | 3.5.4 (независимая проверка многообразия STL) |
| matplotlib | 3.11.2 (чертёж-схема) |
| pypdfium2 | 5.15.2 (рендер страниц и извлечение фото из PDF-атласа) |
| Pillow | 13.0.0 (изображения) |
| scipy | 1.18.1 (зависимость build123d/trimesh) |
| pip | 25.2 |

Полный список пакетов: [pip-freeze.txt](./pip-freeze.txt).

## Отличия от инструкций для Windows

- `WINDOWS_SETUP.md` рассчитан на Windows и Python 3.12. Работа выполнена на **macOS arm64**; команды те же,
  но интерпретатор вызывается как `.venv/bin/python` вместо `.\.venv\Scripts\python.exe`.
- Использован уже существующий `.venv` на **Python 3.13.7**: версия входит в поддерживаемый диапазон
  build123d 0.13.0 (3.11–3.14), для неё есть готовые колёса OCP под macOS arm64. Python 3.12 не устанавливался.
- FreeCAD не устанавливался (не требуется для генерации; рендеры сделаны собственным скриптом `src/render.py`).

## Источник пакетов

Прямой доступ к pypi.org в сети организации закрыт политикой веб-фильтра. Пакеты устанавливались через
**корпоративный прокси-репозиторий Nexus** (санкционированный канал организации), без обхода блокировки и без
сборки из git:

```bash
.venv/bin/python -m pip install --index-url https://nexus-dev.onefiserv.net/repository/pypi-proxy/simple \
    build123d==0.13.0 trimesh manifold3d matplotlib pypdfium2
```

- `pymupdf` в прокси недоступен → для работы с PDF использован `pypdfium2`.
- `networkx` не устанавливался → сечения сетки в `src/drawing.py` строятся через `trimesh.intersections.mesh_plane`.

Список прямых зависимостей с версиями: [`requirements.txt`](../requirements.txt).

## Воспроизведение

Из корня проекта (на Windows — `.\.venv\Scripts\python.exe` вместо `.venv/bin/python`):

```bash
.venv/bin/python src/model.py            # перестроение → output/armrest_latch_v01.step + .stl, reports/build_info.json
.venv/bin/python src/validate.py         # проверки → reports/validation.md, reports/validation_results.json
.venv/bin/python src/render.py           # виды → output/armrest_latch_v01_{iso,iso_rear,side,rear,back,front,top}.png
.venv/bin/python src/drawing.py          # чертёж-схема → output/armrest_latch_v01_drawing.{png,svg}
.venv/bin/python src/compare_photos.py   # сопоставление с фото → reports/figures/compare_*.png
# или всё сразу:
.venv/bin/python src/run_all.py
```

Время на этой машине: построение ≈ 3 с, полная проверка с вариантами ≈ 60 с, рендеры ≈ 15 с.

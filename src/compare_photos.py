"""Визуальное сопоставление V01 с фотографиями из input/cad-photo-atlas.pdf.

Запуск: .venv/bin/python src/compare_photos.py  (после model.py)
Фото извлекаются из PDF только для чтения (исходник не изменяется). Результаты —
reports/figures/compare_*.png. Фото перспективные: совпадение контуров — качественная
проверка топологии и ориентации, а не измерение.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_raw
from PIL import Image, ImageDraw, ImageFont

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent
sys.path.insert(0, str(SRC))
import model as M  # noqa: E402
import render as R  # noqa: E402

FIG = ROOT / "reports" / "figures"
# В пакете для Windows файл называется «cad-photo-atlas(1).pdf», здесь — без «(1)».
ATLAS = min((ROOT / "input").glob("cad-photo-atlas*.pdf"))
# Страница PDF (1-based) → исходный кадр (подписи атласа).
PAGES = {"IMG_6558": 2, "IMG_6559": 3, "IMG_4391": 4, "IMG_6560": 5, "IMG_6561": 6, "IMG_4397": 7,
         "IMG_4393": 8, "IMG_4394": 9, "IMG_4395": 10, "IMG_4396": 11}
# Привязка бокового кадра IMG_4396 (1170×1490 px, система координат ТЗ §10.1), измерено по снимку:
# столбец оси C — центр окружности, вписанной в обод отверстия (±2 px); макушка и низ фланца — по силуэту.
# Высота центра отверстия под фото НЕ подгоняется: модель ставится по макушке и масштабу H1.
X_C_PHOTO = 776.0
Y_TOP_PHOTO = 399.0
Y_BOTTOM_PHOTO = 1164.0
PX_PER_MM = (Y_BOTTOM_PHOTO - Y_TOP_PHOTO) / M.p.H1_OVERALL  # 765 px = 33,5 мм
ROLL_DEG = math.degrees(math.atan2(711 - 695, 891 - 680))  # наклон площадки A на снимке (ТЗ §10.1)


def font(size):
    try:
        return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def photo(name: str) -> Image.Image:
    pdf = pdfium.PdfDocument(str(ATLAS))
    page = pdf[PAGES[name] - 1]
    obj = next(iter(page.get_objects(filter=(pdfium_raw.FPDF_PAGEOBJ_IMAGE,))))
    return obj.get_bitmap(render=False).to_pil().convert("RGB")


def side_overlay(verts, tris):
    ph = photo("IMG_4396")
    if ph.size != (1170, 1490):
        raise RuntimeError(f"unexpected IMG_4396 size {ph.size}")
    W, H = 1800, 2000
    hz = M.p.derived()["LUG_HOLE_Z"]
    anchor = (X_C_PHOTO, Y_TOP_PHOTO + (M.p.H3_LUG - hz) * PX_PER_MM)  # куда на фото попадает ось C модели
    _, info = R.render(verts, tris, (-1, 0, 0), (0, 0, 1), size=(W, H), scale=PX_PER_MM, center=(0.0, hz))
    mask, edge = info["mask"], info["edge"]
    ov = np.zeros((H, W, 4), np.uint8)
    ov[mask] = (0, 170, 255, 60)
    thick = edge.copy()
    for dy, dx in ((0, 1), (1, 0), (0, -1), (-1, 0)):
        thick |= np.roll(np.roll(edge, dy, 0), dx, 1)
    ov[thick] = (0, 255, 120, 255)
    layer = Image.fromarray(ov, "RGBA").rotate(ROLL_DEG, center=(W / 2, H / 2), resample=Image.BICUBIC)
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    x0 = int(round(W / 2 - anchor[0]))
    y0 = int(round(H / 2 - anchor[1]))
    canvas.paste(ph.convert("RGBA"), (x0, y0))
    canvas.alpha_composite(layer)
    out = canvas.crop((x0 + 150, y0 + 300, x0 + 1150, y0 + 1300)).convert("RGB")
    d = ImageDraw.Draw(out)
    d.rectangle([0, 0, 1000, 92], fill=(255, 255, 255))
    d.text((10, 6), f"IMG_4396 + контур V01 (зелёный), масштаб H1: 33,5 мм = {Y_BOTTOM_PHOTO - Y_TOP_PHOTO:.0f} px; привязка по макушке "
                    "и столбцу оси C,", fill=(0, 0, 0), font=font(19))
    d.text((10, 32), f"поворот кадра {ROLL_DEG:.1f}° по площадке A. Фото перспективное: ближняя проушина крупнее;", fill=(0, 0, 0), font=font(19))
    d.text((10, 58), "зуб на фото сломан (виден остаток) — V01 показывает восстановленный клин 10 мм.", fill=(0, 0, 0), font=font(19))
    return out


def side_by_side(left: Image.Image, right: Image.Image, title: str, height=900):
    def fit(im):
        k = height / im.height
        return im.resize((int(im.width * k), height), Image.LANCZOS)
    a, b = fit(left), fit(right)
    out = Image.new("RGB", (a.width + b.width + 30, height + 60), "white")
    out.paste(a, (0, 60))
    out.paste(b, (a.width + 30, 60))
    ImageDraw.Draw(out).text((10, 15), title, fill=(0, 0, 0), font=font(24))
    return out


def crop_to_content(im: Image.Image, pad=20) -> Image.Image:
    arr = np.asarray(im.convert("L"))
    ys, xs = np.nonzero(arr < 250)
    return im.crop((max(xs.min() - pad, 0), max(ys.min() - pad, 0), min(xs.max() + pad, im.width), min(ys.max() + pad, im.height)))


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    verts, tris = R.mesh_from_step(M.STEP_PATH)
    c = M.config()
    d = M.directions(c)
    n3 = np.array([0, d["N"][0], d["N"][1]])
    f3 = np.array([0, d["F"][0], d["F"][1]])
    written = []

    out = side_overlay(verts, tris)
    path = FIG / "compare_side_overlay_IMG_4396.png"
    out.save(path)
    written.append(path)

    rear, _ = R.render(verts, tris, tuple(-n3), tuple(f3), size=(1400, 900))
    ph = photo("IMG_4397").crop((0, 750, 1536, 1550))
    path = FIG / "compare_rear_IMG_4397.png"
    side_by_side(ph, crop_to_content(rear), "IMG_4397 (тыл фланца, перспектива) ↔ V01 по нормали к фланцу").save(path)
    written.append(path)

    tooth_view, _ = R.render(verts, tris, (0, -0.45, 1.0), (0, 1, 0), size=(1400, 1100))
    ph = photo("IMG_4393").crop((150, 600, 1400, 1800))
    path = FIG / "compare_tooth_side_IMG_4393.png"
    side_by_side(ph, crop_to_content(tooth_view), "IMG_4393 (снизу со стороны зуба, вдоль фланца) ↔ V01 в похожем ракурсе (зуб V01 — восстановленный клин)").save(path)
    written.append(path)

    front, _ = R.render(verts, tris, (-0.55, 0.45, -1.0), (0, 1, 0), size=(1100, 1300))
    ph = photo("IMG_6558").crop((200, 250, 1450, 1900))
    path = FIG / "compare_front_IMG_6558.png"
    side_by_side(ph, crop_to_content(front), "IMG_6558 (лицевая сторона лопатки) ↔ V01 (похожий ракурс)").save(path)
    written.append(path)
    for w in written:
        print("wrote", w)


if __name__ == "__main__":
    main()

"""Рендеры для осмотра: изометрии, боковой, тыльный, лицевой и верхний виды (PNG).

Запуск: .venv/bin/python src/render.py  (после src/model.py)
Источник геометрии — экспортированный output/armrest_latch_v03.step (тот же файл,
что передаётся владельцу), триангулируется здесь только для визуализации.
Рендер — ортографический, собственный z-буфер на numpy (без OpenGL).
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent
sys.path.insert(0, str(SRC))

from build123d import import_step  # noqa: E402

import model  # noqa: E402

OUT = ROOT / "output"


def mesh_from_step(path: Path, tol=0.02, ang=0.15):
    shape = import_step(str(path))
    verts, tris = shape.tessellate(tol, ang)
    v = np.array([[q.X, q.Y, q.Z] for q in verts], dtype=float)
    t = np.array(tris, dtype=np.int64)
    return v, t


def _basis(forward, up):
    f = np.asarray(forward, float)
    f /= np.linalg.norm(f)
    r = np.cross(f, np.asarray(up, float))
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    return f, r, u


def render(verts, tris, forward, up, size=(1400, 1050), margin=40, base_rgb=(150, 170, 195),
           scale=None, center=None):
    f, r, u = _basis(forward, up)
    px, py, pz = verts @ r, verts @ u, verts @ f
    W, H = size
    if scale is None:
        span_x, span_y = px.max() - px.min(), py.max() - py.min()
        scale = min((W - 2 * margin) / span_x, (H - 2 * margin) / span_y)
    if center is None:
        center = ((px.max() + px.min()) / 2, (py.max() + py.min()) / 2)
    sx = (px - center[0]) * scale + W / 2
    sy = H / 2 - (py - center[1]) * scale
    tri_n = np.cross(verts[tris[:, 1]] - verts[tris[:, 0]], verts[tris[:, 2]] - verts[tris[:, 0]])
    norms = np.linalg.norm(tri_n, axis=1)
    keep = norms > 1e-12
    tri_n[keep] /= norms[keep, None]

    depth = np.full((H, W), np.inf)
    index = np.full((H, W), -1, dtype=np.int64)
    X0, Y0, Z0 = sx[tris[:, 0]], sy[tris[:, 0]], pz[tris[:, 0]]
    X1, Y1, Z1 = sx[tris[:, 1]], sy[tris[:, 1]], pz[tris[:, 1]]
    X2, Y2, Z2 = sx[tris[:, 2]], sy[tris[:, 2]], pz[tris[:, 2]]
    xmin = np.clip(np.floor(np.minimum(np.minimum(X0, X1), X2)).astype(int), 0, W - 1)
    xmax = np.clip(np.ceil(np.maximum(np.maximum(X0, X1), X2)).astype(int), 0, W - 1)
    ymin = np.clip(np.floor(np.minimum(np.minimum(Y0, Y1), Y2)).astype(int), 0, H - 1)
    ymax = np.clip(np.ceil(np.maximum(np.maximum(Y0, Y1), Y2)).astype(int), 0, H - 1)
    for i in np.nonzero(keep)[0]:
        x_lo, x_hi, y_lo, y_hi = xmin[i], xmax[i], ymin[i], ymax[i]
        if x_hi < x_lo or y_hi < y_lo:
            continue
        gx, gy = np.meshgrid(np.arange(x_lo, x_hi + 1) + 0.5, np.arange(y_lo, y_hi + 1) + 0.5)
        x0, y0, x1, y1, x2, y2 = X0[i], Y0[i], X1[i], Y1[i], X2[i], Y2[i]
        den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(den) < 1e-12:
            continue
        a = ((y1 - y2) * (gx - x2) + (x2 - x1) * (gy - y2)) / den
        b = ((y2 - y0) * (gx - x2) + (x0 - x2) * (gy - y2)) / den
        g = 1.0 - a - b
        inside = (a >= -1e-9) & (b >= -1e-9) & (g >= -1e-9)
        if not inside.any():
            continue
        z = a * Z0[i] + b * Z1[i] + g * Z2[i]
        sub_d = depth[y_lo:y_hi + 1, x_lo:x_hi + 1]
        sub_i = index[y_lo:y_hi + 1, x_lo:x_hi + 1]
        closer = inside & (z < sub_d)
        sub_d[closer] = z[closer]
        sub_i[closer] = i

    mask = index >= 0
    n = np.zeros((H, W, 3))
    n[mask] = tri_n[index[mask]]
    view = -f
    n_view = n.copy()
    flip = (n_view @ view) < 0
    n_view[flip] *= -1
    lights = [(_unit(view * 0.6 + u * 0.6 + r * 0.3), 0.65), (_unit(view * 0.7 - r * 0.6 - u * 0.2), 0.35)]
    shade = np.full((H, W), 0.28)
    for ldir, w in lights:
        shade += w * np.clip(n_view @ ldir, 0, 1)
    shade = np.clip(shade, 0, 1.15)
    img = np.ones((H, W, 3)) * 255
    img[mask] = np.clip(np.array(base_rgb)[None, :] * shade[mask][:, None], 0, 255)

    # Контуры: границы силуэта, разрывы глубины и изломы нормалей.
    edge = np.zeros((H, W), bool)
    dep = np.where(mask, depth, np.nan)
    for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
        sa = (slice(0, H - dy), slice(max(0, -dx), W - max(0, dx)))
        sb = (slice(dy, H), slice(max(0, dx), W - max(0, -dx)))
        ma, mb = mask[sa], mask[sb]
        jump = ma & mb & (np.abs(dep[sa] - dep[sb]) > 0.6)
        crease = ma & mb & (np.einsum("ijk,ijk->ij", n_view[sa], n_view[sb]) < math.cos(math.radians(35)))
        edge[sa] |= (ma != mb) | jump | crease
    img[edge] = (35, 40, 50)
    return Image.fromarray(img.astype(np.uint8)), dict(scale=scale, center=center, mask=mask, edge=edge)


def _unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def annotate(im: Image.Image, title: str, scale_px_per_mm: float, lines=()):
    d = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 22)
        small = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 17)
    except OSError:
        font = small = ImageFont.load_default()
    d.text((20, 15), title, fill=(20, 20, 20), font=font)
    for k, line in enumerate(lines):
        d.text((20, 46 + 22 * k), line, fill=(60, 60, 60), font=small)
    W, H = im.size
    bar = 10 * scale_px_per_mm
    d.line([(W - 40 - bar, H - 35), (W - 40, H - 35)], fill=(20, 20, 20), width=4)
    d.text((W - 40 - bar, H - 30), "10 mm", fill=(20, 20, 20), font=small)
    return im


VIEWS = {
    "iso": dict(forward=(-0.9, 1.0, -0.8), up=(0, 0, 1), title="Изометрия (лицевая сторона, сверху)"),
    "iso_rear": dict(forward=(-0.8, -1.0, 0.45), up=(0, 0, 1), title="Изометрия (тыльная сторона, снизу): зуб, рёбра, углубление"),
    "side": dict(forward=(-1, 0, 0), up=(0, 0, 1), title="Боковой вид вдоль оси C (−X), как фото 03/08/09/10"),
    "rear": None,  # нормально к тыльной плоскости фланца, как IMG_4397 (заполняется ниже)
    "back": dict(forward=(0, -1, 0), up=(0, 0, 1), title="Вид с тыльной стороны (+Y → −Y)"),
    "front": dict(forward=(0, 1, 0), up=(0, 0, 1), title="Вид с лицевой стороны (−Y → +Y)"),
    "top": dict(forward=(0, 0, -1), up=(0, 1, 0), title="Вид сверху (+Z), лопатка внизу"),
}


def main(views=None):
    step = model.STEP_PATH
    if not step.exists():
        raise SystemExit("run src/model.py first")
    verts, tris = mesh_from_step(step)
    c = model.config()
    d = model.directions(c)
    n3 = np.array([0, d["N"][0], d["N"][1]])
    f3 = np.array([0, d["F"][0], d["F"][1]])
    VIEWS["rear"] = dict(forward=tuple(-n3), up=tuple(f3),
                         title="Тыльный вид по нормали к фланцу (как фото 06 / IMG_4397)")
    OUT.mkdir(exist_ok=True)
    written = []
    for name, spec in VIEWS.items():
        if views and name not in views:
            continue
        im, info = render(verts, tris, spec["forward"], spec["up"])
        annotate(im, f"armrest_latch_v03 — {spec['title']}", info["scale"],
                 [f"{len(tris)} треугольников визуализации (STL печати: отдельный файл)"])
        path = OUT / f"armrest_latch_v03_{name}.png"
        im.save(path)
        written.append(path)
        print("wrote", path)
    return written


if __name__ == "__main__":
    main(sys.argv[1:] or None)

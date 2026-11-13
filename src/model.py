"""Параметрическая модель ручки-защёлки V01 на build123d.

Запуск из корня проекта:  .venv/bin/python src/model.py
Результат: output/armrest_latch_v01.step, output/armrest_latch_v01.stl,
           reports/build_info.json (расчётные величины построения).

Все связи вычисляются из src/params.py. Боковое сечение строится в плоскости
(Y, Z); векторы направлений — пары (Y, Z).
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path
from types import SimpleNamespace

from build123d import (
    Axis, Circle, Face, GeomType, Keep, Line, Plane, Pos, SlotOverall, Solid, Spline,
    ThreePointArc, Vector, Wire, export_step, export_stl, extrude, fillet, split,
)
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
from OCP.TopExp import TopExp
from OCP.TopoDS import TopoDS

try:  # OCP ≥ 8: шаблонные коллекции OCCT вынесены в OCP.collections
    from OCP.collections import IndexedDataMap_TopoDS_Shape_List_TopoDS_Shape_TopTools_ShapeMapHasher as _EdgeFaceMap
except ImportError:  # OCP 7.x
    from OCP.TopTools import TopTools_IndexedDataMapOfShapeListOfShape as _EdgeFaceMap

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent
sys.path.insert(0, str(SRC))
import params as p  # noqa: E402

OUT_DIR = ROOT / "output"
REPORT_DIR = ROOT / "reports"
STEP_PATH = OUT_DIR / "armrest_latch_v01.step"
STL_PATH = OUT_DIR / "armrest_latch_v01.stl"
X_AXIS = (1.0, 0.0, 0.0)


# --- Векторная алгебра в боковой плоскости (Y, Z) ------------------------------
def add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def mul(a, k):
    return (a[0] * k, a[1] * k)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def rot90(a):
    """Поворот на +90° (от +Y к +Z)."""
    return (-a[1], a[0])


def solve2(a, b, c):
    """Решение s·a + t·b = c для двумерных векторов."""
    det = a[0] * b[1] - a[1] * b[0]
    if abs(det) < 1e-12:
        raise ValueError("parallel directions in solve2")
    return ((c[0] * b[1] - c[1] * b[0]) / det, (a[0] * c[1] - a[1] * c[0]) / det)


def v3(pt_yz, x=0.0) -> Vector:
    return Vector(x, pt_yz[0], pt_yz[1])


def yz_prism(points_yz, x0: float, width: float) -> Solid:
    """Призма из замкнутого многоугольника в плоскости (Y, Z), выдавленная вдоль +X от x0."""
    pts = [v3(q, x0) for q in points_yz]
    edges = [Line(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]
    return extrude(Face(Wire(edges)), amount=width, dir=X_AXIS)


def config(overrides: dict | None = None) -> SimpleNamespace:
    values = {name: param.value for name, param in p.PARAMS.items()}
    for key, val in (overrides or {}).items():
        if key not in values:
            raise KeyError(f"unknown parameter override: {key}")
        values[key] = val
    return SimpleNamespace(**values)


def contour_points(c) -> tuple[tuple[float, float], ...]:
    pts = {"v01": c.FLANGE_CONTOUR_V01, "spec": c.FLANGE_CONTOUR_SPEC}.get(c.FLANGE_CONTOUR_SOURCE)
    if pts is None:
        raise ValueError(f"FLANGE_CONTOUR_SOURCE must be 'v01' or 'spec', got {c.FLANGE_CONTOUR_SOURCE!r}")
    if abs(pts[0][0]) > 1e-9 or abs(pts[0][1] - c.H2_FLANGE) > 1e-9:
        raise ValueError("first contour point must be the apex (0, H2_FLANGE)")
    if abs(pts[-1][1]) > 1e-9:
        raise ValueError("last contour point must be the wing tip on V=0")
    return pts


# --- Базовые направления ----------------------------------------------------------
def directions(c) -> dict:
    u_neck = p.unit(-c.BETA_DEG)                       # от площадки к фланцу по шейке
    f_dir = p.unit(-(c.ALPHA_DEG + c.DELTA_DEG))        # F: от прямой V=0 к выпуклой кромке
    if math.dist(u_neck, f_dir) > 1e-9:
        raise NotImplementedError(
            "V01 строит шейку и фланец одной пластиной: требуется BETA_DEG == ALPHA_DEG + DELTA_DEG. "
            "Для разных углов нужен излом шейки (не реализован в V01).")
    n_dir = rot90(f_dir)                                # N: нормаль пластины, лицевая → тыльная
    p_dir = p.unit(180.0 - c.DELTA_DEG)                 # вдоль P к свободному концу лопатки
    w_p = (p_dir[1], -p_dir[0])                         # нормаль P (к +Z при δ=0)
    t_dir = p.unit(c.GAMMA_DEG - c.DELTA_DEG)           # направление зуба к его концу
    t_w = rot90(t_dir)                                  # нормаль зуба (к +Z при δ=γ=0)
    return dict(u_neck=u_neck, F=f_dir, N=n_dir, p_dir=p_dir, w_P=w_p, t_dir=t_dir, t_w=t_w)


def flange_plane(origin_yz, d) -> Plane:
    return Plane(origin=v3(origin_yz), x_dir=X_AXIS, z_dir=(0.0, d["N"][0], d["N"][1]))


# --- Контур и пластина фланца с шейкой --------------------------------------------
def flange_outline(c, s_neck: float, x_tip: float):
    half = list(contour_points(c))
    half[-1] = (x_tip, 0.0)
    full = [(-x, v) for x, v in reversed(half[1:])] + half
    spline = Spline(*[Vector(x, v, 0) for x, v in full])
    hw0 = c.NECK_WIDTH_AT_FLANGE / 2.0
    hwp = c.NECK_WIDTH_AT_PAD / 2.0
    v_end = -(s_neck + c.NECK_PAD_OVERLAP)
    hw_end = hw0 + (hwp - hw0) * (s_neck + c.NECK_PAD_OVERLAP) / s_neck
    edges = [
        spline,
        Line((x_tip, 0), (hw0, 0)),
        Line((hw0, 0), (hw_end, v_end)),
        Line((hw_end, v_end), (-hw_end, v_end)),
        Line((-hw_end, v_end), (-hw0, 0)),
        Line((-hw0, 0), (-x_tip, 0)),
    ]
    face = Face(Wire(edges))
    tips = [v for v in face.vertices() if abs(abs(v.X) - x_tip) < 1e-6 and abs(v.Y) < 1e-6]
    face = fillet(tips, c.FLANGE_TIP_RADIUS)
    side = (hwp - hw0, -s_neck)
    theta_void = math.acos(side[0] / math.hypot(*side))
    r_junction = (c.NECK_JUNCTION_WIDTH / 2.0 - hw0) * math.tan(theta_void / 2.0)
    corners = [v for v in face.vertices() if abs(abs(v.X) - hw0) < 1e-6 and abs(v.Y) < 1e-6]
    face = fillet(corners, r_junction)
    return face, r_junction


def flange_plate_local(c, s_neck: float):
    """Пластина (фланец + шейка) в локальных координатах: x=X, y=V, z=N (0 — лицевая)."""
    target = c.FLANGE_WIDTH / 2.0
    x_prev, x_tip = None, target
    xmax_prev = None
    for _ in range(25):
        face, r_junction = flange_outline(c, s_neck, x_tip)
        xmax = face.bounding_box().max.X
        if abs(target - xmax) < 1e-6:
            break
        gain = 1.0 if x_prev is None else (xmax - xmax_prev) / (x_tip - x_prev)
        x_prev, xmax_prev = x_tip, xmax
        x_tip += (target - xmax) / gain
    else:
        raise RuntimeError("flange tip iteration did not converge")
    plate = extrude(face, amount=c.FLANGE_THICKNESS, dir=(0, 0, 1))
    plate = fillet(plate.faces().sort_by(Axis.Z)[0].edges(), c.FLANGE_EDGE_FILLET_FRONT)
    plate = fillet(plate.faces().sort_by(Axis.Z)[-1].edges(), c.FLANGE_EDGE_FILLET_BACK)
    slot = (Plane.XY.offset(c.FLANGE_THICKNESS - c.GROOVE_DEPTH) * Pos(0, c.GROOVE_CENTER_V)
            * SlotOverall(c.GROOVE_LENGTH, c.GROOVE_WIDTH))
    plate = plate - extrude(slot, amount=c.GROOVE_DEPTH + 1.0)
    return plate, dict(x_tip_sharp=x_tip, r_junction=r_junction, outline_face=face)


def placed_plate(c, d, s_neck: float):
    pad_corner = (-c.LUG_HOLE_FROM_FRONT_END, -c.PAD_THICKNESS)
    origin = add(add(pad_corner, mul(d["u_neck"], s_neck)), mul(d["N"], c.FLANGE_FRONT_OFFSET))
    plate_local, info = flange_plate_local(c, s_neck)
    plate = flange_plane(origin, d).from_local_coords(plate_local)
    plate = split(plate, bisect_by=Plane.XY.offset(-c.PAD_THICKNESS), keep=Keep.BOTTOM)
    info.update(origin=origin, pad_corner=pad_corner)
    return plate, info


# --- Остальные элементы ----------------------------------------------------------------
def make_pad(c):
    y_f = -c.LUG_HOLE_FROM_FRONT_END
    y_b = y_f + c.PAD_LENGTH
    hn, hh = c.PAD_WIDTH_NECK_END / 2.0, c.PAD_WIDTH_HORN_END / 2.0
    z0 = -c.PAD_THICKNESS
    pts = [Vector(-hn, y_f, z0), Vector(hn, y_f, z0), Vector(hh, y_b, z0), Vector(-hh, y_b, z0)]
    edges = [Line(pts[i], pts[(i + 1) % 4]) for i in range(4)]
    return extrude(Face(Wire(edges)), amount=c.PAD_THICKNESS, dir=(0, 0, 1))


def lug_profile_points(c, der):
    """Опорные точки профиля проушины в (Y, Z): углы основания, точки касания, макушка."""
    center = (0.0, der["LUG_HOLE_Z"])
    r = der["LUG_TOP_RADIUS"]
    if r >= c.LUG_BASE_LENGTH / 2.0:
        raise ValueError(f"lug top arc R{r:.3f} is not narrower than the lug base {c.LUG_BASE_LENGTH}")
    y_f = -c.LUG_HOLE_FROM_FRONT_END
    y_b = y_f + c.LUG_BASE_LENGTH

    def tangent(q, sign):
        dq = sub(q, center)
        dist = math.hypot(*dq)
        phi = math.acos(r / dist)
        ang = math.atan2(dq[1], dq[0]) + sign * phi
        return (center[0] + r * math.cos(ang), center[1] + r * math.sin(ang))

    return dict(front=(y_f, 0.0), back=(y_b, 0.0), t_back=tangent((y_b, 0.0), +1),
                t_front=tangent((y_f, 0.0), -1), top=(center[0], center[1] + r), center=center)


def make_lug(c, der, x0: float):
    lp = lug_profile_points(c, der)
    z_in = -1.0
    a = v3((lp["front"][0], z_in), x0)
    b = v3((lp["back"][0], z_in), x0)
    edges = [
        Line(a, b),
        Line(b, v3(lp["back"], x0)),
        Line(v3(lp["back"], x0), v3(lp["t_back"], x0)),
        ThreePointArc(v3(lp["t_back"], x0), v3(lp["top"], x0), v3(lp["t_front"], x0)),
        Line(v3(lp["t_front"], x0), v3(lp["front"], x0)),
        Line(v3(lp["front"], x0), a),
    ]
    return extrude(Face(Wire(edges)), amount=c.LUG_THICKNESS, dir=X_AXIS)


def make_horn(c, x_center: float):
    """Рожок: сечение X–Z со скруглёнными углами (продольные кромки), вытянутое вдоль +Y;
    торец скруглён одной гладкой петлёй — без трёхрёберных угловых сопряжений."""
    y_b = -c.LUG_HOLE_FROM_FRONT_END + c.PAD_LENGTH
    x0, x1 = x_center - c.HORN_WIDTH / 2.0, x_center + c.HORN_WIDTH / 2.0
    y0, y1 = y_b - 1.0, y_b + c.HORN_PROTRUSION
    z0, z1 = -c.PAD_THICKNESS, -c.PAD_THICKNESS + c.HORN_THICKNESS
    pts = [Vector(x0, y0, z0), Vector(x1, y0, z0), Vector(x1, y0, z1), Vector(x0, y0, z1)]
    section = Face(Wire([Line(pts[i], pts[(i + 1) % 4]) for i in range(4)]))
    if c.HORN_EDGE_FILLET > 0:
        section = fillet(section.vertices(), c.HORN_EDGE_FILLET)
    horn = extrude(section, amount=y1 - y0, dir=(0, 1, 0)).solids()[0]
    if c.HORN_EDGE_FILLET > 0:
        tip_face = horn.faces().sort_by(Axis.Y)[-1]
        horn = horn.fillet(c.HORN_EDGE_FILLET * 0.75, tip_face.edges())
    return horn


def rib_profile(c, d, origin):
    """Профиль ребра в (Y, Z) во внутреннем углу между низом площадки и тыльной гранью шейки."""
    z_pad = -c.PAD_THICKNESS
    back_pt = add(origin, mul(d["N"], c.FLANGE_THICKNESS))
    s, _ = solve2(d["F"], (-1.0, 0.0), sub((back_pt[0], z_pad), back_pt))
    corner = add(back_pt, mul(d["F"], s))
    corner = (corner[0], z_pad)
    leg_pad = add(corner, (c.RIB_LEG_ALONG_PAD, 0.0))
    leg_neck = add(corner, mul(d["F"], c.RIB_LEG_ALONG_NECK))
    inner = add(add(corner, mul(d["N"], -0.8)), (0.0, 0.8))
    pts = [leg_pad, add(leg_pad, (0.0, 1.0)), inner, add(leg_neck, mul(d["N"], -1.0)), leg_neck]
    return pts, corner, leg_pad, leg_neck


def make_paddle(c, d, origin):
    s_pt = add(origin, mul(d["F"], c.PADDLE_S_V))
    y_s, z_s = s_pt
    hw_r, hw_t = c.PADDLE_WIDTH_ROOT / 2.0, c.PADDLE_WIDTH_TIP / 2.0
    length = c.L1_PADDLE
    u_back = 6.0
    hw_back = hw_r + (hw_r - hw_t) * u_back / length
    z_low = z_s - 12.0
    pts = [Vector(-hw_back, y_s + u_back, z_low), Vector(hw_back, y_s + u_back, z_low),
           Vector(hw_t, y_s - length, z_low), Vector(-hw_t, y_s - length, z_low)]
    plan = Face(Wire([Line(pts[i], pts[(i + 1) % 4]) for i in range(4)]))
    tip_vertices = [v for v in plan.vertices() if abs(v.Y - (y_s - length)) < 1e-6]
    plan = fillet(tip_vertices, c.PADDLE_CORNER_RADIUS)
    body = extrude(plan, amount=z_s - z_low, dir=(0, 0, 1))
    slope = (c.PADDLE_THICKNESS_ROOT - c.PADDLE_THICKNESS_TIP) / length
    n_bottom = (slope, 1.0)
    taper_plane = Plane(origin=(0, y_s, z_s - c.PADDLE_THICKNESS_ROOT), x_dir=X_AXIS,
                        z_dir=(0, n_bottom[0], n_bottom[1]))
    body = split(body, bisect_by=taper_plane, keep=Keep.TOP).solids()[0]
    if c.PADDLE_EDGE_FILLET > 0:
        top = body.faces().sort_by(Axis.Z)[-1]
        body = body.fillet(c.PADDLE_EDGE_FILLET, top.edges())
        nb = Vector(0, n_bottom[0], n_bottom[1]).normalized()
        bottom = max((f for f in body.faces() if f.geom_type == GeomType.PLANE),
                     key=lambda f: -f.normal_at().dot(nb))
        body = body.fillet(c.PADDLE_EDGE_FILLET, bottom.edges())
    if abs(c.DELTA_DEG) > 0:
        body = body.rotate(Axis(v3(s_pt), X_AXIS), -c.DELTA_DEG)
    cut_origin = add(origin, mul(d["N"], c.PADDLE_EMBED_DEPTH))
    body = split(body, bisect_by=flange_plane(cut_origin, d), keep=Keep.BOTTOM).solids()[0]
    return body, s_pt


def tooth_profile(c, d, origin):
    v_root = c.H2_FLANGE - c.TOOTH_ROOT_EDGE_OFFSET
    r0 = add(add(origin, mul(d["F"], v_root)), mul(d["N"], c.FLANGE_THICKNESS))
    t_dir, t_w, f_dir, n_dir = d["t_dir"], d["t_w"], d["F"], d["N"]
    h_root, h_tip = c.TOOTH_THICKNESS_ROOT, c.TOOTH_THICKNESS_TIP
    r1 = add(r0, mul(n_dir, -c.TOOTH_EMBED_DEPTH))
    if c.TOOTH_FLAT_FACE == "top":
        top_line = add(r0, mul(t_w, h_root))
        lam, mu = solve2(t_dir, mul(f_dir, -1.0), sub(r0, top_line))
        flat_root = add(top_line, mul(t_dir, lam))                  # T0: корень прямой грани
        tip_flat = add(flat_root, mul(t_dir, c.TOOTH_LENGTH))
        tip_other = add(tip_flat, mul(t_w, -h_tip))
        lam2, _ = solve2(t_dir, mul(f_dir, -1.0), sub(r1, top_line))
        r2 = add(top_line, mul(t_dir, lam2))
        pts = [r0, tip_other, tip_flat, r2, r1]
        upper_root, flat_sign = flat_root, -1.0
    elif c.TOOTH_FLAT_FACE == "bottom":
        flat_root = r0
        top_root = add(r0, mul(f_dir, h_root / dot(f_dir, t_w)))
        tip_flat = add(r0, mul(t_dir, c.TOOTH_LENGTH))
        tip_other = add(tip_flat, mul(t_w, h_tip))
        pts = [r0, tip_flat, tip_other, top_root, add(top_root, mul(n_dir, -c.TOOTH_EMBED_DEPTH)), r1]
        upper_root, flat_sign = top_root, 1.0
    else:
        raise ValueError("TOOTH_FLAT_FACE must be 'top' or 'bottom'")
    return dict(points=pts, r0=r0, flat_root=flat_root, tip_flat=tip_flat, tip_other=tip_other,
                upper_root=upper_root, flat_sign=flat_sign, v_root=v_root)


def make_tooth(c, d, origin):
    tp = tooth_profile(c, d, origin)
    x0 = -c.TOOTH_WIDTH / 2.0
    tooth = yz_prism(tp["points"], x0, c.TOOTH_WIDTH).solids()[0]
    if c.TOOTH_STEP_ENABLED:
        t_dir, t_w = d["t_dir"], d["t_w"]
        inward = mul(t_w, tp["flat_sign"])          # от прямой грани внутрь тела зуба
        outward = mul(inward, -1.0)
        cot = 1.0 / math.tan(math.radians(c.TOOTH_STEP_WALL_DEG))
        wall_top = add(tp["flat_root"], mul(t_dir, c.TOOTH_STEP_FROM_ROOT))
        wall_bot = add(add(wall_top, mul(t_dir, c.TOOTH_STEP_DEPTH * cot)), mul(inward, c.TOOTH_STEP_DEPTH))
        far = c.TOOTH_LENGTH + 2.0
        notch = [add(add(wall_top, outward), mul(t_dir, -cot)), wall_bot,
                 add(wall_bot, mul(t_dir, far)), add(add(wall_top, mul(t_dir, far)), outward)]
        tooth = (tooth - yz_prism(notch, x0 - 1.0, c.TOOTH_WIDTH + 2.0)).solids()[0]
    if c.TOOTH_TIP_FILLET > 0:
        tv = Vector(0, d["t_dir"][0], d["t_dir"][1])
        end_face = max((f for f in tooth.faces() if f.geom_type == GeomType.PLANE
                        and f.normal_at().dot(tv) > 0.999), key=lambda f: f.center().dot(tv))
        tooth = tooth.fillet(c.TOOTH_TIP_FILLET, end_face.edges())
    return tooth, tp


# --- Выбор рёбер после объединения ---------------------------------------------------------
_to_edge = getattr(TopoDS, "Edge_s", None) or TopoDS.Edge
_to_face = getattr(TopoDS, "Face_s", None) or TopoDS.Face


def edge_face_pairs(shape):
    emap = _EdgeFaceMap()
    TopExp.MapShapesAndAncestors_s(shape.wrapped, TopAbs_EDGE, TopAbs_FACE, emap)
    from build123d import Edge
    pairs = []
    for i in range(1, emap.Extent() + 1):
        edge = Edge(_to_edge(emap.FindKey(i)))
        faces = [Face(_to_face(f)) for f in emap.FindFromIndex(i)]
        pairs.append((edge, faces))
    return pairs


def is_plane_with_normal(face, normal, tol=1e-6):
    return face.geom_type == GeomType.PLANE and (face.normal_at() - Vector(normal)).length < tol


def single_solid(shape, label: str) -> Solid:
    solids = shape.solids()
    if len(solids) != 1:
        raise RuntimeError(f"{label}: expected exactly one solid, got {len(solids)}")
    return solids[0]


def apply_fillet(solid: Solid, radius: float, edges, label: str, log: list) -> Solid:
    edges = list(edges)
    if radius <= 0:
        log.append({"fillet": label, "radius": radius, "edges": 0, "status": "disabled by parameter"})
        return solid
    if not edges:
        raise RuntimeError(f"fillet '{label}': no edges selected")
    result = solid.fillet(radius, edges)
    if not result.is_valid:
        raise RuntimeError(f"fillet '{label}' produced an invalid solid")
    log.append({"fillet": label, "radius": radius, "edges": len(edges), "status": "applied"})
    return result


# --- Сборка ------------------------------------------------------------------------------------
def build(overrides: dict | None = None):
    t0 = time.time()
    c = config(overrides)
    der = p.derived(c)
    d = directions(c)
    z_target = c.H3_LUG - c.H1_OVERALL

    # Замыкание H1: положение пластины вдоль шейки так, чтобы низ фланца был на Z = H3 − H1.
    s0 = c.NECK_LENGTH_START
    plate0, _ = placed_plate(c, d, s0)
    zmin0 = plate0.bounding_box(optimal=True).min.Z
    s_neck = s0 + (z_target - zmin0) / d["u_neck"][1]
    if s_neck <= 0.5:
        raise RuntimeError(f"H1 closure gives a degenerate neck length {s_neck:.3f}")
    plate, pinfo = placed_plate(c, d, s_neck)
    plate_zmin = plate.bounding_box(optimal=True).min.Z
    origin = pinfo["origin"]

    pad = make_pad(c)
    lug_pos = make_lug(c, der, der["LUG_INNER_X"])
    lug_neg = make_lug(c, der, -der["LUG_OUTER_X"])
    horns = [make_horn(c, sx * der["HORN_CENTER_X"]) for sx in (1, -1)]
    rib_pts, rib_corner, rib_leg_pad, rib_leg_neck = rib_profile(c, d, origin)
    rib_xs = [0.0, c.RIB_OUTER_X, -c.RIB_OUTER_X]
    ribs = [yz_prism(rib_pts, x - c.RIB_THICKNESS / 2.0, c.RIB_THICKNESS) for x in rib_xs]
    paddle, s_pt = make_paddle(c, d, origin)
    tooth, tp = make_tooth(c, d, origin)

    part = plate + pad + lug_pos + lug_neg
    for extra in [*horns, *ribs, paddle, tooth]:
        part = part + extra
    hole = extrude(Plane.YZ.offset(-30) * Pos(0, der["LUG_HOLE_Z"]) * Circle(c.LUG_HOLE_D / 2.0), amount=60)
    solid = single_solid(part - hole, "union")
    if not solid.is_valid:
        raise RuntimeError("union produced an invalid solid")

    log: list = []
    n3 = Vector(0, d["N"][0], d["N"][1])
    y_axis = Vector(0, 1, 0)

    # Галтели корня проушин: рёбра между A и боковыми гранями проушин.
    lug_x = {round(x, 6) for x in (der["LUG_INNER_X"], der["LUG_OUTER_X"])}
    sel = []
    for e, fs in edge_face_pairs(solid):
        if len(fs) != 2 or e.geom_type != GeomType.LINE:
            continue
        a, b = e.position_at(0), e.position_at(1)
        if abs(a.Z) > 1e-6 or abs(b.Z) > 1e-6 or abs(a.X - b.X) > 1e-6 or round(abs(a.X), 6) not in lug_x:
            continue
        if any(is_plane_with_normal(f, (0, 0, 1)) for f in fs):
            sel.append(e)
    solid = apply_fillet(solid, c.LUG_ROOT_FILLET, sel, "lug roots", log)

    # Корневая галтель зуба по верхней линии корня (дальней от кромки фланца; в варианте 'top' — корень прямой грани).
    root_pt = v3(tp["upper_root"])
    sel = [e for e in solid.edges() if e.geom_type == GeomType.LINE
           and abs(abs((e.position_at(1) - e.position_at(0)).normalized().X) - 1) < 1e-6
           and (Vector(0, e.center().Y, e.center().Z) - root_pt).length < 1e-4]
    solid = apply_fillet(solid, c.TOOTH_ROOT_FILLET, sel, "tooth upper root", log)

    # Галтель примыкания лопатки к лицевой плоскости фланца: только рёбра в пятне корня лопатки.
    front_plane_pt = v3(origin)
    f3 = Vector(0, d["F"][0], d["F"][1])
    v_lo = c.PADDLE_S_V - 1.5
    v_hi = c.PADDLE_S_V + c.PADDLE_THICKNESS_ROOT / abs(dot(d["F"], d["w_P"])) + 1.5
    sel = []
    for e, fs in edge_face_pairs(solid):
        if len(fs) != 2:
            continue
        in_front_plane = [is_plane_with_normal(f, -n3) and abs((f.center() - front_plane_pt).dot(n3)) < 1e-6
                          for f in fs]
        if sum(in_front_plane) != 1:
            continue
        other = fs[in_front_plane.index(False)]
        ev = (e.center() - front_plane_pt).dot(f3)
        if ((other.center() - front_plane_pt).dot(n3) < -2.0 and v_lo <= ev <= v_hi
                and abs(e.center().X) <= c.PADDLE_WIDTH_ROOT / 2.0 + 1.5):
            sel.append(e)
    solid = apply_fillet(solid, c.PADDLE_ROOT_FILLET, sel, "paddle root", log)

    # Галтели примыкания рёбер к низу площадки и тыльной грани шейки.
    rib_side_x = {round(x + s * c.RIB_THICKNESS / 2.0, 6) for x in rib_xs for s in (-1, 1)}
    sel = []
    for e, fs in edge_face_pairs(solid):
        if len(fs) != 2:
            continue
        sides = [f for f in fs if f.geom_type == GeomType.PLANE and abs(abs(f.normal_at().X) - 1) < 1e-6
                 and round(f.center().X, 6) in rib_side_x]
        bases = [f for f in fs if is_plane_with_normal(f, (0, 0, -1)) or is_plane_with_normal(f, n3)]
        if len(sides) == 1 and len(bases) == 1 and e.center().Z < -c.PAD_THICKNESS + 1e-6:
            sel.append(e)
    solid = apply_fillet(solid, c.RIB_ROOT_FILLET, sel, "rib roots", log)

    # Притупление кромок отверстий.
    hole_edges = [e for e in solid.edges() if e.geom_type == GeomType.CIRCLE
                  and abs(e.radius - c.LUG_HOLE_D / 2.0) < 1e-6
                  and abs(e.arc_center.Y) < 1e-6 and abs(e.arc_center.Z - der["LUG_HOLE_Z"]) < 1e-6]
    if c.LUG_HOLE_CHAMFER > 0:
        rim_length = sum(e.length for e in hole_edges)
        if abs(rim_length - 4 * math.pi * c.LUG_HOLE_D) > 1e-4:
            raise RuntimeError(f"hole rims: expected 4 full circles, got total length {rim_length:.4f}")
        solid = solid.chamfer(c.LUG_HOLE_CHAMFER, None, hole_edges)
        if not solid.is_valid:
            raise RuntimeError("hole chamfer produced an invalid solid")
        log.append({"chamfer": "hole edges", "length": c.LUG_HOLE_CHAMFER, "edges": len(hole_edges),
                    "status": "applied (4 rims)"})

    lp = lug_profile_points(c, der)
    neck_back_len = math.dist(rib_corner, add(origin, mul(d["N"], c.FLANGE_THICKNESS)))
    info = {
        "build_seconds": round(time.time() - t0, 2),
        "overrides": overrides or {},
        "directions_YZ": {k: [round(v[0], 9), round(v[1], 9)] for k, v in d.items()},
        "z_target_min": z_target,
        "neck_length_front_face_s": s_neck,
        "neck_length_back_face": neck_back_len,
        "neck_length_start_reference": c.NECK_LENGTH_START,
        "flange_origin_Of_YZ": list(origin),
        "flange_plate_zmin": plate_zmin,
        "flange_tip_x_before_rounding": pinfo["x_tip_sharp"],
        "neck_junction_fillet_radius": pinfo["r_junction"],
        "lug_hole_d": c.LUG_HOLE_D,
        "lug_hole_center_z": der["LUG_HOLE_Z"],
        "lug_top_radius": der["LUG_TOP_RADIUS"],
        "lug_bridge_above_hole": der["LUG_BRIDGE"],
        "lug_tangent_point_front_YZ": list(lp["t_front"]),
        "lug_tangent_point_back_YZ": list(lp["t_back"]),
        "lug_side_flare_deg": math.degrees(math.atan2(lp["front"][0] - lp["t_front"][0],
                                                      lp["t_front"][1] - lp["front"][1])) * -1.0,
        "S_point_YZ": list(s_pt),
        "rib_corner_YZ": list(rib_corner),
        "rib_leg_pad_end_YZ": list(rib_leg_pad),
        "rib_leg_neck_end_YZ": list(rib_leg_neck),
        "rib_x": rib_xs,
        "tooth_lower_root_R0_YZ": list(tp["r0"]),
        "tooth_flat_root_YZ": list(tp["flat_root"]),
        "tooth_tip_flat_YZ": list(tp["tip_flat"]),
        "tooth_tip_other_YZ": list(tp["tip_other"]),
        "tooth_root_v": tp["v_root"],
        "feature_zmin": {
            "flange_plate": plate_zmin,
            "paddle": paddle.bounding_box(optimal=True).min.Z,
            "tooth": tooth.bounding_box(optimal=True).min.Z,
        },
        "fillets": log,
    }
    return solid, info, c


def export(solid, c):
    OUT_DIR.mkdir(exist_ok=True)
    if not export_step(solid, STEP_PATH):
        raise RuntimeError("STEP export failed")
    if not export_stl(solid, STL_PATH, tolerance=c.STL_TOLERANCE, angular_tolerance=c.STL_ANGULAR_TOLERANCE):
        raise RuntimeError("STL export failed")


def main():
    solid, info, c = build()
    bb = solid.bounding_box(optimal=True)
    info["volume_mm3"] = solid.volume
    info["bbox"] = {"min": [bb.min.X, bb.min.Y, bb.min.Z], "max": [bb.max.X, bb.max.Y, bb.max.Z]}
    info["is_valid"] = solid.is_valid
    export(solid, c)
    REPORT_DIR.mkdir(exist_ok=True)
    (REPORT_DIR / "build_info.json").write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"valid={solid.is_valid} volume={solid.volume:.3f} mm3 build={info['build_seconds']} s")
    print(f"bbox X[{bb.min.X:.3f},{bb.max.X:.3f}] Y[{bb.min.Y:.3f},{bb.max.Y:.3f}] Z[{bb.min.Z:.3f},{bb.max.Z:.3f}]")
    print(f"neck front-face length (H1 closure) = {info['neck_length_front_face_s']:.3f} mm")
    print(f"lug holes: D={info['lug_hole_d']} centre Z={info['lug_hole_center_z']:.3f} top arc R={info['lug_top_radius']:.3f} "
          f"bridge={info['lug_bridge_above_hole']:.3f} mm")
    for item in info["fillets"]:
        print("  ", item)
    print(f"STEP -> {STEP_PATH}\nSTL  -> {STL_PATH}")


if __name__ == "__main__":
    main()

"""Проверка V01: перестроение, валидность BREP, размеры по базам ТЗ, экспорт STEP/STL.

Запуск из корня проекта:  .venv/bin/python src/validate.py
Предварительно: .venv/bin/python src/model.py (создаёт проверяемые STEP/STL).
Результаты: reports/validation_results.json, reports/validation.md.
"""

from __future__ import annotations

import hashlib
import json
import math
import platform
import re
import sys
import time
from importlib.metadata import version
from pathlib import Path

import manifold3d
import numpy as np
import trimesh
from build123d import Axis, Box, Face, GeomType, Plane, Vector, import_step
from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepAlgoAPI import BRepAlgoAPI_Check
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.GeomAbs import GeomAbs_Cylinder

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent
sys.path.insert(0, str(SRC))
import model as M  # noqa: E402
import params as p  # noqa: E402

REPORTS = ROOT / "reports"
CHECKS: list[dict] = []


def check(group, item, method, measured, expected=None, tol=None, unit="мм", status=None, note=""):
    if status is None:
        if expected is None:
            status = "INFO"
        elif isinstance(expected, bool):
            status = "PASS" if measured == expected else "FAIL"
        else:
            status = "PASS" if abs(measured - expected) <= tol else "FAIL"
    CHECKS.append(dict(group=group, item=item, method=method, measured=measured, expected=expected,
                       tol=tol, unit=unit, status=status, note=note))
    return measured


# --- Измерительные помощники ------------------------------------------------------------
def _vec(v) -> Vector:
    return v if isinstance(v, Vector) else Vector(*v)


def intervals(solid, origin, direction):
    """Отрезки луча origin + t·dir (t ≥ 0, мм вдоль единичного dir), лежащие внутри тела.

    Axis в build123d — бесконечная прямая, поэтому точки позади начала луча отбрасываются;
    начало луча обязано лежать вне тела."""
    o, dvec = _vec(origin), _vec(direction).normalized()
    if solid.is_inside(o):
        raise ValueError(f"ray origin {o} is inside the solid")
    ts = sorted({round((pt - o).dot(dvec), 9) for pt, _ in solid.find_intersection_points(Axis(o, dvec))})
    ts = [t for t in ts if t >= -1e-9]
    out = []
    for a, b in zip(ts, ts[1:]):
        if b - a > 1e-7 and solid.is_inside(o + dvec * ((a + b) / 2)):
            if out and abs(out[-1][1] - a) < 1e-7:
                out[-1] = (out[-1][0], b)
            else:
                out.append((a, b))
    return out


def extreme_point(solid, plane_point, normal):
    """Ближайшая к плоскости точка тела (плоскость вне тела) и расстояние до неё."""
    pl = Plane(origin=plane_point, z_dir=normal)
    face = Face.make_rect(400, 400, pl)
    ext = BRepExtrema_DistShapeShape(solid.wrapped, face.wrapped)
    ext.Perform()
    q = ext.PointOnShape1(1)
    return Vector(q.X(), q.Y(), q.Z()), ext.Value()


def angle_deg(a, b):
    c = max(-1.0, min(1.0, a.normalized().dot(b.normalized())))
    return math.degrees(math.acos(c))


def in_plane_ray(face_normal: Vector, toward: Vector) -> Vector:
    """Луч в плоскости грани, перпендикулярный X, направленный в сторону toward."""
    r = face_normal.cross(Vector(1, 0, 0)).normalized()
    return r if r.dot(toward) > 0 else -r


def planar_faces_with_normal(solid, normal, tol=1e-6):
    n = Vector(*normal).normalized() if not isinstance(normal, Vector) else normal.normalized()
    return [f for f in solid.faces() if f.geom_type == GeomType.PLANE and (f.normal_at() - n).length < tol]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dec(v) -> str:
    """Число для подписи с десятичной запятой: 3.1 → «3,1»."""
    return f"{v:g}".replace(".", ",")


# --- Проверки -----------------------------------------------------------------------------
def run(do_variants: bool = True) -> dict:
    t_start = time.time()
    results: dict = {"started": time.strftime("%Y-%m-%d %H:%M:%S")}

    # 0. Исходники
    expected_hashes = dict(re.findall(r"`(input/[^`]+)`: `([0-9a-f]{64})`",
                                      (ROOT / "INPUT_SHA256.md").read_text(encoding="utf-8")))
    actual = {f"input/{f.name}": sha256(f) for f in sorted((ROOT / "input").iterdir()) if f.is_file()}
    for exp_name, exp_hash in expected_hashes.items():
        match = [name for name, h in actual.items() if h == exp_hash]
        check("Источники", f"SHA-256 {exp_name}", "sha256 файлов input/ против INPUT_SHA256.md",
              bool(match), True, status=None,
              note=f"совпадает с {match[0]}" + (" (имя файла без «(1)»)" if match and match[0] != exp_name else "")
              if match else "нет файла с таким хешем")

    # 1. Перестроение из исходника
    solid, info, c = M.build()
    d = M.directions(c)
    der = p.derived(c)
    results["build_info"] = {k: v for k, v in info.items()}
    check("Построение", "build123d-скрипт выполнен без ошибок", "model.build() в этом процессе", True, True,
          note=f"{info['build_seconds']} с")
    for item in info["fillets"]:
        check("Построение", f"Скругление/фаска: {item.get('fillet') or item.get('chamfer')}",
              "журнал build(): операция выполнена, тело валидно после неё",
              item["status"].startswith("applied"), True,
              note=f"R/фаска {item.get('radius', item.get('length'))}, рёбер {item['edges']}")

    # 2. Топология и валидность
    check("Топология", "Число твёрдых тел", "len(solids())", len(solid.solids()), 1, 0, unit="шт")
    check("Топология", "Число оболочек (нет внутренних пустот)", "len(shells())", len(solid.shells()), 1, 0, unit="шт")
    check("Топология", "BRepCheck_Analyzer", "OCCT BRepCheck_Analyzer.IsValid", BRepCheck_Analyzer(solid.wrapped).IsValid(), True)
    chk = BRepAlgoAPI_Check(solid.wrapped, True, True)
    check("Топология", "Нет самопересечений/малых рёбер (BRepAlgoAPI_Check)",
          "OCCT BRepAlgoAPI_Check(тест малых рёбер, тест самопересечений)", chk.IsValid(), True)
    pairs = M.edge_face_pairs(solid)
    free = sum(1 for e, fs in pairs if len(fs) == 1 and not BRep_Tool.IsClosed_s(e.wrapped, fs[0].wrapped))
    seams = sum(1 for e, fs in pairs if len(fs) == 1 and BRep_Tool.IsClosed_s(e.wrapped, fs[0].wrapped))
    nonman = sum(1 for _, fs in pairs if len(fs) > 2)
    check("Топология", "Свободные рёбра (щели в оболочке)", "рёбра с одной смежной гранью, кроме швов замкнутых "
          "поверхностей", free, 0, 0, unit="шт", note=f"швов цилиндров/конусов: {seams}")
    check("Топология", "Неманифолдные рёбра", "рёбра с >2 смежными гранями", nonman, 0, 0, unit="шт")
    vol = solid.volume
    check("Топология", "Объём положительный", "solid.volume", vol, unit="мм³", status="PASS" if vol > 0 else "FAIL")
    min_edge = min(e.length for e in solid.edges())
    min_face = min(f.area for f in solid.faces())
    check("Топология", "Минимальная длина ребра", "min(edge.length)", min_edge, unit="мм",
          status="PASS" if min_edge > 0.01 else "FAIL", note="порог 0,01 мм")
    check("Топология", "Минимальная площадь грани", "min(face.area)", min_face, unit="мм²",
          status="PASS" if min_face > 0.001 else "FAIL", note="порог 0,001 мм²")
    check("Топология", "Граней / рёбер", "подсчёт", len(solid.faces()), unit="шт", note=f"рёбер {len(solid.edges())}")

    # 3. Главные размеры по базам
    bb = solid.bounding_box(optimal=True)
    z_top_pt, _ = extreme_point(solid, (0, 0, bb.max.Z + 1), (0, 0, 1))
    z_low_pt, _ = extreme_point(solid, (0, 0, bb.min.Z - 1), (0, 0, -1))
    h1 = z_top_pt.Z - z_low_pt.Z
    check("Главные размеры", "H1 = 33,5: макушка проушины → нижняя кромка фланца вдоль H (=Z)",
          "BRepExtrema: точки тела, ближайшие к касательным плоскостям Z=max и Z=min", h1, c.H1_OVERALL, 0.005,
          note=f"верх ({z_top_pt.X:.2f}; {z_top_pt.Y:.2f}; {z_top_pt.Z:.3f}) на проушине; "
               f"низ ({z_low_pt.X:.2f}; {z_low_pt.Y:.2f}; {z_low_pt.Z:.3f}) на тыльно-нижней кромке фланца")
    lug_x_ok = der["LUG_INNER_X"] - 1e-3 <= abs(z_top_pt.X) <= der["LUG_OUTER_X"] + 1e-3
    check("Главные размеры", "Верхняя точка H1 — макушка проушины", "X верхней точки в пределах проушины",
          lug_x_ok, True)
    fz = info["feature_zmin"]
    low_is_flange = fz["flange_plate"] <= min(fz["paddle"], fz["tooth"]) - 0.1
    check("Главные размеры", "Нижняя точка H1 — фланец, не лопатка и не зуб",
          "сравнение минимумов Z отдельных элементов до объединения", low_is_flange, True,
          note=f"фланец {fz['flange_plate']:.3f}; зуб {fz['tooth']:.3f}; лопатка {fz['paddle']:.3f}")

    origin_on_a = Vector(0, 0, 0)
    a_faces = [f for f in planar_faces_with_normal(solid, (0, 0, 1))
               if abs(f.center().Z) < 1e-6 and f.bounding_box().min.X <= 0 <= f.bounding_box().max.X
               and f.bounding_box().min.Y <= 0 <= f.bounding_box().max.Y]
    a_face = max(a_faces, key=lambda f: f.area)
    z_a = a_face.center().Z
    check("Главные размеры", "H3 = 11,3: от A до макушки проушины по нормали к A",
          "Z макушки − Z плоской грани A (нормаль +Z, содержит начало координат под C)", z_top_pt.Z - z_a,
          c.H3_LUG, 0.005, note=f"Z(A) = {z_a:.6f}; расстояние A до начала координат "
                                f"{a_face.distance_to(origin_on_a):.2e}")

    origin = info["flange_origin_Of_YZ"]
    fp = M.flange_plane(origin, d)
    o3 = M.v3(origin)
    f3 = Vector(0, d["F"][0], d["F"][1])
    n3 = Vector(0, d["N"][0], d["N"][1])
    x3 = Vector(1, 0, 0)

    def fl(x, v, n):
        return o3 + x3 * x + f3 * v + n3 * n

    local = fp.to_local_coords(solid)
    slab_full = Box(90, 30, c.FLANGE_THICKNESS).translate((0, 12, c.FLANGE_THICKNESS / 2))
    in_slab = local & slab_full
    v_max = in_slab.bounding_box(optimal=True).max.Y
    wings = local & Box(18, 30, c.FLANGE_THICKNESS).translate((28, 12, c.FLANGE_THICKNESS / 2))
    v_min_wing = wings.bounding_box(optimal=True).min.Y
    check("Главные размеры", "H2 = 16,5: собственная высота фланца вдоль F",
          "тело переведено в локальную систему фланца (x=X, y=V вдоль F, z=N); экстремумы V в слое пластины; "
          "низ — вершина выпуклой кромки, верх — прямая кончиков крылышек (X 19…37)",
          v_max - v_min_wing, c.H2_FLANGE, 0.005, note=f"V_max={v_max:.4f}, V_min(крылышко)={v_min_wing:.4f}")

    s_pt = info["S_point_YZ"]
    s3 = M.v3(s_pt)
    p_dir3 = Vector(0, d["p_dir"][0], d["p_dir"][1])
    tip_pt, _ = extreme_point(solid, s3 + p_dir3 * (c.L1_PADDLE + 5), p_dir3)
    l1 = (tip_pt - s3).dot(p_dir3)
    check("Главные размеры", "L1 = 30,0: от S до крайней точки свободного торца вдоль P",
          "S — линия выхода верхней грани лопатки (P) из лицевой плоскости фланца (виртуальная острая кромка); "
          "крайняя точка — BRepExtrema к плоскости ⟂P", l1, c.L1_PADDLE, 0.005,
          note=f"S=(Y {s_pt[0]:.3f}; Z {s_pt[1]:.3f}); крайняя точка X={tip_pt.X:.3f}")

    # 4. Проушины и отверстия
    hz, dia = der["LUG_HOLE_Z"], c.LUG_HOLE_D
    z_above = hz + (der["LUG_TOP_RADIUS"] + dia / 2) / 2  # середина перемычки над отверстием
    iv = intervals(solid, (-50, 0, z_above), (1, 0, 0))
    check("Проушины", "Сечение по X над отверстием: два интервала", f"прямая вдоль X при Y=0, Z={z_above:.2f}",
          len(iv), 2, 0, unit="шт", note=str([(round(a - 50, 3), round(b - 50, 3)) for a, b in iv]))
    if len(iv) == 2:
        (a0, a1), (b0, b1) = [(a - 50, b - 50) for a, b in iv]
        check("Проушины", "Чистый зазор между внутренними гранями 21,8", "b0 − a1 по той же прямой",
              b0 - a1, c.LUG_INNER_GAP, 0.002)
        check("Проушины", "Толщина проушины (−X) 3,0", "a1 − a0", a1 - a0, c.LUG_THICKNESS, 0.002)
        check("Проушины", "Толщина проушины (+X) 3,0", "b1 − b0", b1 - b0, c.LUG_THICKNESS, 0.002)
        check("Проушины", "Наружный размах 27,8 (Р)", "b1 − a0", b1 - a0, der["LUG_OUTER_SPAN"], 0.002)
        check("Проушины", "Средние плоскости ±12,4 (Р)", "(a0+a1)/2, (b0+b1)/2", (b0 + b1) / 2,
              der["LUG_MID_X"], 0.002, note=f"−X: {(a0 + a1) / 2:.3f}")
    through = intervals(solid, (-50, 0, hz), (1, 0, 0))
    check("Проушины", "Отверстия сквозные по оси C", f"прямая вдоль X по оси Y=0, Z={hz:.2f} не пересекает тело",
          len(through), 0, 0, unit="интервалов")
    cyl = []
    for f in solid.faces():
        ad = BRepAdaptor_Surface(f.wrapped)
        if ad.GetType() == GeomAbs_Cylinder:
            cy = ad.Cylinder()
            ax = cy.Axis()
            dirv = Vector(ax.Direction().X(), ax.Direction().Y(), ax.Direction().Z())
            if abs(abs(dirv.X) - 1) < 1e-9:
                loc = ax.Location()
                q = f.position_at(0.5, 0.5)
                concave = f.normal_at(q).dot(Vector(0, q.Y - loc.Y(), q.Z - loc.Z())) < 0
                cyl.append((cy.Radius(), loc.Y(), loc.Z(), f.center().X, concave))
    # Отбор по положению (в пределах толщины проушин) и вогнутости (нормаль к оси — отверстие, а не выпуклая
    # дуга вершины ушка), а не по ожидаемому радиусу — иначе проверка диаметра была бы круговой.
    holes = [q for q in cyl if q[4] and der["LUG_INNER_X"] - 1e-6 <= abs(q[3]) <= der["LUG_OUTER_X"] + 1e-6]
    sides = sorted({int(np.sign(q[3])) for q in holes})
    check("Проушины", "Отверстия: по одной цилиндрической грани в каждой проушине",
          "вогнутые грани-цилиндры с осью ∥X в пределах толщин проушин", len(holes), 2, 0, unit="шт",
          note=f"стороны X: {sides}; выпуклых дуг вершины ушка: "
               f"{sum(1 for q in cyl if not q[4] and der['LUG_INNER_X'] - 1e-6 <= abs(q[3]) <= der['LUG_OUTER_X'] + 1e-6)}")
    if len(holes) == 2 and sides == [-1, 1]:
        d_faces = max((2 * q[0] for q in holes), key=lambda v: abs(v - dia))
        check("Проушины", f"Диаметр отверстий Ø{dec(dia)} (грани-цилиндры, обе проушины)", "2 × радиус граней",
              d_faces, dia, 1e-6, note="исправленный замер владельца (ранее Ø2,5)")
        coax = max(math.hypot(q[1], q[2] - hz) for q in holes)
        check("Проушины", "Соосность отверстий (отклонение осей от C)",
              f"расстояние осей цилиндров до линии Y=0, Z={hz:.2f}", coax, 0.0, 1e-6)
        check("Проушины", f"Центр отверстия над A = {dec(round(hz, 3))} (Р)", "Z оси цилиндров − Z(A)",
              holes[0][2] - z_a, hz, 1e-6, note="H3 − (перемычка + Ø/2)" if c.LUG_HOLE_CENTER_Z_FIXED is None
              else "задан LUG_HOLE_CENTER_Z_FIXED")
        check("Проушины", f"Перемычка над отверстием {dec(round(der['LUG_BRIDGE'], 3))}", "Z макушки − (Z оси + R)",
              z_top_pt.Z - (holes[0][2] + holes[0][0]), der["LUG_BRIDGE"], 0.002)
    gaps = []
    for sx in (-1, 1):
        xm = sx * der["LUG_MID_X"]
        for origin_, direction_ in (((xm, 0, 50), (0, 0, -1)), ((xm, -50, hz), (0, 1, 0))):
            ivh = intervals(solid, origin_, direction_)
            gaps.append(ivh[1][0] - ivh[0][1] if len(ivh) >= 2 else float("nan"))
    check("Проушины", f"Диаметр отверстий Ø{dec(dia)} (лучи в средних плоскостях проушин)",
          "просвет между интервалами тела вдоль Z и вдоль Y через ось C, X = ±12,4", max(gaps, key=lambda v: abs(v - dia)),
          dia, 0.002, note="; ".join(f"{g:.4f}" for g in gaps))
    iv = intervals(solid, (der["LUG_MID_X"], -50, 0.05), (0, 1, 0))
    flare = math.tan(math.radians(info["lug_side_flare_deg"]))
    check("Проушины", "Основание ушка вдоль Y (у A, Z=0,05)", "прямая вдоль Y в средней плоскости проушины",
          iv[0][1] - iv[0][0] if iv else float("nan"), c.LUG_BASE_LENGTH - 2 * 0.05 * flare, 0.002,
          note=f"Д: касательные к дуге R{der['LUG_TOP_RADIUS']:.2f}, развал боковин {info['lug_side_flare_deg']:.2f}°")

    # 5. Площадка и рожки
    y_f, y_b = der["PAD_FRONT_Y"], der["PAD_BACK_Y"]
    for label, y, expected in (("у торца рожков 30,8", y_b - 0.05, c.PAD_WIDTH_HORN_END),
                               ("у перехода к шейке 32,68", y_f + 0.05, c.PAD_WIDTH_NECK_END)):
        iv = intervals(solid, (-50, y, -c.PAD_THICKNESS / 2), (1, 0, 0))
        frac = (y - y_f) / c.PAD_LENGTH
        exp = c.PAD_WIDTH_NECK_END + (c.PAD_WIDTH_HORN_END - c.PAD_WIDTH_NECK_END) * frac
        width = (iv[-1][1] - iv[0][0]) if iv else float("nan")
        check("Площадка", f"Ширина площадки {label}", f"прямая вдоль X при Y={y:.2f}, середина толщины",
              width, exp, 0.002, note=f"номинал {expected} на самом торце")
    iv = intervals(solid, (5, -50, -1.25), (0, 1, 0))
    check("Площадка", "Длина площадки 10,5 в плоскости A", "прямая вдоль Y при X=5, Z=−1,25",
          iv[0][1] - iv[0][0], c.PAD_LENGTH, 0.002)
    iv = intervals(solid, (5, 0, 50), (0, 0, -1))
    check("Площадка", "Толщина площадки 2,5", "прямая вдоль Z при X=5, Y=0 (первый интервал)",
          iv[0][1] - iv[0][0], c.PAD_THICKNESS, 0.002)
    iv = intervals(solid, (-50, y_b + c.HORN_PROTRUSION / 2, -c.PAD_THICKNESS / 2), (1, 0, 0))
    widths = [b - a for a, b in iv]
    centers = [(a + b) / 2 - 50 for a, b in iv]
    check("Рожки", "Количество рожков", "прямая вдоль X через рожки", len(iv), 2, 0, unit="шт")
    if len(iv) == 2:
        check("Рожки", "Межцентровое расстояние 18,0", "разность центров интервалов", centers[1] - centers[0],
              c.HORN_PITCH, 0.002)
        check("Рожки", "Ширина рожка 2,2", "длина интервала", widths[0], c.HORN_WIDTH, 0.002)
    iv = intervals(solid, (der["HORN_CENTER_X"], -50, -c.PAD_THICKNESS / 2), (0, 1, 0))
    check("Рожки", "Вылет рожков за торец 2,0", "конец интервала по Y − Y торца площадки", iv[-1][1] - 50 - y_b,
          c.HORN_PROTRUSION, 0.002)

    # 6. Шейка
    s_neck = info["neck_length_front_face_s"]
    check("Шейка", "Итоговая длина шейки по лицевой грани (Р, из H1)",
          "от нижнего лицевого угла площадки до прямой V=0 вдоль шейки", s_neck,
          note=f"стартовое значение исходника {c.NECK_LENGTH_START} подчинено H1 (ТЗ §10.2)")
    check("Шейка", "Длина шейки по тыльной грани (Р)", "от низа площадки до прямой V=0", info["neck_length_back_face"])
    hw0, hwp = c.NECK_WIDTH_AT_FLANGE / 2, c.NECK_WIDTH_AT_PAD / 2
    for label, v_at in (("у площадки", -s_neck + 0.05), ("над переходом к фланцу", -info["neck_junction_fillet_radius"] - 0.05)):
        iv = intervals(solid, fl(-50, v_at, c.FLANGE_THICKNESS / 2), (1, 0, 0))
        exp = 2 * (hw0 + (hwp - hw0) * (-v_at) / s_neck)
        check("Шейка", f"Ширина шейки {label}", f"прямая вдоль X в середине толщины, V={v_at:.3f}",
              iv[-1][1] - iv[0][0], exp, 0.002, note="линейный переход 32,68 → 34,0 (И)")
    rj = info["neck_junction_fillet_radius"]
    v_j = -0.02
    iv = intervals(solid, fl(-50, v_j, c.FLANGE_THICKNESS / 2), (1, 0, 0))
    exp = 2 * (c.NECK_JUNCTION_WIDTH / 2 - math.sqrt(rj ** 2 - (rj + v_j) ** 2))
    check("Шейка", "Вогнутый переход шейки к прямой V=0 (ширина сопряжения 36)",
          f"ширина при V={v_j} против расчёта дуги R{rj:.3f}, касательной к V=0 в X=±18",
          iv[-1][1] - iv[0][0], exp, 0.005)
    inside_front = solid.is_inside(fl(0, -s_neck / 2, 0.01)) and not solid.is_inside(fl(0, -s_neck / 2, -0.01))
    check("Шейка", "Лицевая грань шейки в одной плоскости с лицевой гранью фланца",
          "точки ±0,01 мм от лицевой плоскости фланца в середине шейки: внутри/снаружи", inside_front, True)

    # 7. Рёбра
    corner, lpad, lneck = info["rib_corner_YZ"], info["rib_leg_pad_end_YZ"], info["rib_leg_neck_end_YZ"]
    cen = ((corner[0] + lpad[0] + lneck[0]) / 3, (corner[1] + lpad[1] + lneck[1]) / 3)
    iv = intervals(solid, (-50, cen[0], cen[1]), (1, 0, 0))
    got = [((a + b) / 2 - 50, b - a) for a, b in iv]
    check("Рёбра", "Количество рёбер (раздельные, в центре треугольника профиля)", "прямая вдоль X через центр профиля",
          len(iv), 3, 0, unit="шт", note="; ".join(f"X={x:.2f} t={t:.3f}" for x, t in got))
    if len(got) == 3:
        check("Рёбра", "Толщина рёбер 2,0", "максимальное отклонение длины интервала",
              max(abs(t - c.RIB_THICKNESS) for _, t in got), 0.0, 0.002)
        check("Рёбра", "Положение рёбер X = −13 / 0 / +13", "центры интервалов",
              max(abs(x - e) for (x, _), e in zip(got, sorted(info["rib_x"]))), 0.0, 0.002)
    check("Рёбра", "Рёбра объединены с телом (не висят)", "одно тело + наличие материала в центре каждого ребра",
          len(solid.solids()) == 1 and len(iv) == 3, True)

    # 8. Фланец
    check("Фланец", "Полная ширина 70 (после скругления кончиков R1)", "габарит по X (BRepExtrema/bbox)",
          bb.max.X - bb.min.X, c.FLANGE_WIDTH, 0.002)
    iv = intervals(solid, fl(30, 2.0, -20), (n3))
    check("Фланец", "Толщина пластины 3,2", "прямая вдоль N в крылышке (X=30, V=2)", iv[0][1] - iv[0][0],
          c.FLANGE_THICKNESS, 0.002)
    contour = M.contour_points(c)
    for x_i, v_i in contour[:-1]:
        iv = intervals(solid, fl(x_i, -40, 1.6), (f3))
        check("Фланец", f"Контур проходит через опорную точку (X={x_i}; V={v_i})",
              "прямая вдоль F в середине толщины; крайний V = выпуклая кромка", iv[-1][1] - 40, v_i, 0.002)
    xs = np.arange(-33.0, 33.01, 1.0)
    ve = []
    for x in xs:
        iv = intervals(solid, fl(float(x), -40, 1.6), (f3))
        ve.append(iv[-1][1] - 40)
    ve = np.array(ve)
    d2 = ve[2:] - 2 * ve[1:-1] + ve[:-2]
    check("Фланец", "Выпуклая кромка без перегибов и волн", "вторые разности V(X) на шаге 1 мм, X∈[−33;33]",
          float(d2.max()), unit="мм", status="PASS" if d2.max() < 0 else "FAIL",
          note=f"все вторые разности < 0; диапазон {d2.min():.4f}…{d2.max():.4f}")
    check("Фланец", "Симметрия контура относительно B", "max |V(X) − V(−X)|", float(np.max(np.abs(ve - ve[::-1]))),
          0.0, 1e-4)
    r_apex = 1.0 / abs((ve[34] - 2 * ve[33] + ve[32]) / 1.0)
    check("Фланец", "Нет общего R27: радиус кривизны у вершины", "1/|V''| в вершине", r_apex, unit="мм",
          status="PASS" if r_apex > 27.0 else "FAIL", note="сплайн по точкам ТЗ §12.1; R27 не задан ни на одном участке")
    iv = intervals(solid, fl(25, -40, 1.6), (f3))
    check("Фланец", "Противоположная кромка — прямая V=0", "начало интервала вдоль F при X=±25",
          iv[0][0] - 40, 0.0, 0.002)
    iv = intervals(solid, fl(0, c.GROOVE_CENTER_V, -20), (n3))
    back = iv[-1][1] - 20
    check("Углубление", "Глубина 1,5 (дно 1,7)", "прямая вдоль N через центр углубления: тыльная граница",
          c.FLANGE_THICKNESS - back, c.GROOVE_DEPTH, 0.002, note=f"остаток стенки {back:.3f}")
    iv = intervals(solid, fl(-50, c.GROOVE_CENTER_V, c.FLANGE_THICKNESS - 0.3), (1, 0, 0))
    gaps = [(iv[k + 1][0] - iv[k][1]) for k in range(len(iv) - 1)]
    check("Углубление", "Длина 48 с закрытыми концами", "прямая вдоль X внутри углубления: длина разрыва",
          max(gaps) if gaps else float("nan"), c.GROOVE_LENGTH, 0.002, note="материал по обе стороны — концы закрыты")
    iv = intervals(solid, fl(0, -40, c.FLANGE_THICKNESS - 0.3), (f3))
    gaps = [(iv[k][1] - 40, iv[k + 1][0] - 40) for k in range(len(iv) - 1)]
    g = [b - a for a, b in gaps if a < c.GROOVE_CENTER_V < b]
    check("Углубление", "Ширина 2,5", "прямая вдоль F внутри углубления", g[0] if g else float("nan"),
          c.GROOVE_WIDTH, 0.002)

    # 9. Лопатка
    w3 = Vector(0, d["w_P"][0], d["w_P"][1])
    for u in (5.0, 15.0, 25.0):
        t_exp = c.PADDLE_THICKNESS_ROOT - (c.PADDLE_THICKNESS_ROOT - c.PADDLE_THICKNESS_TIP) * u / c.L1_PADDLE
        base = s3 + p_dir3 * u
        iv = intervals(solid, base + w3 * 30, -w3)
        check("Лопатка", f"Толщина при u={u:g} от S (6 → 3 линейно)", "прямая по нормали к P при X=0",
              iv[0][1] - iv[0][0], t_exp, 0.002)
    for u in (5.0, 15.0, 20.0):
        t_exp = c.PADDLE_THICKNESS_ROOT - (c.PADDLE_THICKNESS_ROOT - c.PADDLE_THICKNESS_TIP) * u / c.L1_PADDLE
        mid = s3 + p_dir3 * u - w3 * (t_exp / 2)
        iv = intervals(solid, (mid.X - 60, mid.Y, mid.Z), (1, 0, 0))
        w_exp = c.PADDLE_WIDTH_ROOT - (c.PADDLE_WIDTH_ROOT - c.PADDLE_WIDTH_TIP) * u / c.L1_PADDLE
        check("Лопатка", f"Ширина при u={u:g} (52 у S → 40 у конца)", "прямая вдоль X в середине толщины "
              "(до начала дуг R10)", iv[-1][1] - iv[0][0], w_exp, 0.002)
    end_u = c.L1_PADDLE - 0.5
    end_pt = s3 + p_dir3 * end_u - w3 * ((c.PADDLE_THICKNESS_ROOT - (c.PADDLE_THICKNESS_ROOT - c.PADDLE_THICKNESS_TIP)
                                          * end_u / c.L1_PADDLE) / 2)
    iv = intervals(solid, (end_pt.X - 60, end_pt.Y, end_pt.Z), (1, 0, 0))
    r_c = c.PADDLE_CORNER_RADIUS
    corner = math.pi / 2 + math.atan((c.PADDLE_WIDTH_ROOT - c.PADDLE_WIDTH_TIP) / 2 / c.L1_PADDLE)
    x_center = c.PADDLE_WIDTH_TIP / 2 - r_c / math.tan(corner / 2)
    w_exp = 2 * (x_center + math.sqrt(r_c ** 2 - (r_c - 0.5) ** 2))
    check("Лопатка", "Углы свободного конца R10 в плане", "ширина в 0,5 мм от торца против расчёта дуги R10, "
          "касательной к торцу и боковине", iv[-1][1] - iv[0][0], w_exp, 0.01)
    front_faces = [f for f in planar_faces_with_normal(solid, -n3) if abs((f.center() - o3).dot(n3)) < 1e-6]
    front = max(front_faces, key=lambda f: f.area)
    # Кромка фланца V_edge(X) в середине толщины, затем сечение сетки чуть перед лицевой плоскостью.
    x_grid = np.arange(-34.5, 34.51, 0.25)
    v_edge = np.array([intervals(solid, fl(float(x), -40, 1.6), f3)[-1][1] - 40 for x in x_grid])
    tau = math.radians(c.ALPHA_DEG + c.DELTA_DEG - 90.0)
    slope = (c.PADDLE_THICKNESS_ROOT - c.PADDLE_THICKNESS_TIP) / c.L1_PADDLE
    lam = c.PADDLE_THICKNESS_ROOT / (math.cos(tau) + slope * math.sin(tau))  # от S вдоль F до нижней линии корня
    hw_bottom = c.PADDLE_WIDTH_ROOT / 2 - (c.PADDLE_WIDTH_ROOT - c.PADDLE_WIDTH_TIP) / 2 / c.L1_PADDLE * lam * math.sin(tau)
    v_bottom = c.PADDLE_S_V + lam
    margin_bare = float(np.interp(hw_bottom, x_grid, v_edge)) - v_bottom
    check("Лопатка", "Голый корень лопатки (без галтели) внутри контура фланца",
          "V кромки фланца при X = полуширине корня − V нижней линии корня (≈ без скругления R1,4)", margin_bare,
          unit="мм", status="PASS" if margin_bare > 0 else "FAIL",
          note=f"угол корня X=±{hw_bottom:.2f}, V={v_bottom:.2f}")
    mesh_for_sec = trimesh.load(str(M.STL_PATH), force="mesh")
    excess = []
    for n_off in (-0.05, -0.3, -0.8):
        segs = trimesh.intersections.mesh_plane(mesh_for_sec, plane_normal=list(n3), plane_origin=list(o3 + n3 * n_off))
        pts3 = segs.reshape(-1, 3)
        xs_, vs_ = pts3[:, 0], (pts3 - np.array(list(o3))) @ np.array(list(f3))
        near = np.abs(xs_) <= 34.5
        excess.append(float(np.max(vs_[near] - np.interp(xs_[near], x_grid, v_edge))))
    check("Лопатка", "Галтель корня лопатки не выходит за контур фланца",
          "сечения STL плоскостями ∥ лицевой на 0,05/0,3/0,8 мм перед ней: max(V − V_кромки)", max(excess),
          unit="мм", status="PASS" if max(excess) <= 0.02 else "FAIL",
          note="у нижних углов корня (|X|>23,5) галтель R1 сливается со скруглением кромки R0,5 — допущение V01")

    # 10. Углы (по реальным граням)
    p_top = max((f for f in planar_faces_with_normal(solid, w3) if (f.center() - s3).dot(p_dir3) > 5),
                key=lambda f: f.area)
    ray_p = in_plane_ray(p_top.normal_at(), p_dir3)
    ray_f_up = in_plane_ray(front.normal_at(), -f3)
    alpha = angle_deg(ray_p, ray_f_up)
    check("Углы", "α лопатка–фланец ≈110°", "луч по верхней грани P к свободному концу ↔ луч по лицевой грани фланца "
          "к его верхней кромке (нормали реальных граней)", alpha, c.ALPHA_DEG, 1e-6, unit="°",
          note=f"сторона: верх фланца наклонён к +Y (к рожкам); δ={c.DELTA_DEG}")
    ray_pad = in_plane_ray(a_face.normal_at(), Vector(0, 1, 0))
    ray_neck = in_plane_ray(front.normal_at(), f3)
    beta = angle_deg(ray_pad, ray_neck)
    check("Углы", "β площадка–шейка ≈110°", "луч по A к рожкам ↔ луч по лицевой грани шейки к фланцу",
          beta, c.BETA_DEG, 1e-6, unit="°", note="тупой угол, шейка уходит вниз-к лопатке (−Y)")
    check("Углы", "Наклон F к H", "угол между лучом шейки/фланца вниз и −Z", angle_deg(ray_neck, Vector(0, 0, -1)),
          c.ALPHA_DEG + c.DELTA_DEG - 90.0, 1e-6, unit="°", note="Р: α + δ − 90°")
    tp_flat = Vector(0, info["tooth_flat_root_YZ"][0], info["tooth_flat_root_YZ"][1])
    t3 = Vector(0, d["t_dir"][0], d["t_dir"][1])
    tw3 = Vector(0, d["t_w"][0], d["t_w"][1])
    tooth_faces = [f for f in solid.faces() if f.geom_type == GeomType.PLANE
                   and abs((f.center() - tp_flat).dot(tw3)) < 1e-6 and (f.center() - tp_flat).dot(t3) > 1]
    tooth_flat = max(tooth_faces, key=lambda f: f.area)
    gamma = angle_deg(tooth_flat.normal_at(), p_top.normal_at())
    check("Углы", "γ зуб–P = 0° (зуб не загнут)", "угол между нормалями прямой грани зуба и верхней грани лопатки",
          gamma, c.GAMMA_DEG, 1e-6, unit="°")
    delta = angle_deg(a_face.normal_at(), p_top.normal_at())
    check("Углы", "δ A–P = 0°", "угол между нормалями A и P", delta, c.DELTA_DEG, 1e-6, unit="°")

    # 11. Зуб
    tip = info["tooth_tip_flat_YZ"]
    iv = intervals(solid, (-50, tp_flat.Y + 5, tp_flat.Z - 0.5), (1, 0, 0))
    check("Зуб", "Ширина 17,5, симметрично B", "прямая вдоль X через тело зуба", iv[0][1] - iv[0][0],
          c.TOOTH_WIDTH, 0.002, note=f"центр X={(iv[0][0] + iv[0][1]) / 2 - 50:.4f}")
    line_o = tp_flat - tw3 * (c.TOOTH_THICKNESS_TIP / 2)
    iv = intervals(solid, (line_o - t3 * 30), (t3))
    tip_t = iv[-1][1] - 30
    check("Зуб", "Вылет 10,0 вдоль направления зуба", "от линии корня прямой грани до торца (прямая ∥ зубу)",
          tip_t, c.TOOTH_LENGTH, 0.002, note="отсчёт от тыльной плоскости фланца на уровне прямой грани")
    r0 = Vector(0, info["tooth_lower_root_R0_YZ"][0], info["tooth_lower_root_R0_YZ"][1])
    span = (tp_flat + t3 * c.TOOTH_LENGTH - tw3 * c.TOOTH_THICKNESS_TIP - r0)
    for dist in (3.0, 6.0, c.TOOTH_LENGTH - 0.5):
        q = tp_flat + t3 * dist
        iv = intervals(solid, (q + tw3 * 5), (-tw3))
        thick_exp = c.TOOTH_THICKNESS_ROOT - (c.TOOTH_THICKNESS_ROOT - c.TOOTH_THICKNESS_TIP) * max(0.0, (q - r0).dot(t3) / span.dot(t3))
        check("Зуб", f"Толщина в {dist:g} мм от корня прямой грани", "прямая по нормали к P",
              iv[0][1] - iv[0][0], thick_exp, 0.002, note="клин 5,2 у нижней линии корня → 2,0 у конца")
    check("Зуб", "Отступ корня от выпуклой кромки вдоль F (X=0)", "H2 − V нижней линии корня",
          c.H2_FLANGE - info["tooth_root_v"], c.TOOTH_ROOT_EDGE_OFFSET, 1e-9)
    c_pt = (0.0, der["LUG_HOLE_Z"])
    check("Зуб", "Положение корня прямой грани относительно C", "ΔY, ΔZ от оси C",
          tp_flat.Y - c_pt[0], unit="мм",
          note=f"ΔY={tp_flat.Y - c_pt[0]:.2f} (к лопатке <0), ΔZ={tp_flat.Z - c_pt[1]:.2f}; конец ΔY={tip[0]:.2f}")
    mid_root = ((r0.Y + tp_flat.Y) / 2, (r0.Z + tp_flat.Z) / 2)
    check("Зуб", "Сверка с фото-оценкой ТЗ §12.3 (≈26 ниже C; 5–6 к лопатке; ± несколько мм)",
          "середина корня относительно C", c_pt[1] - mid_root[1], unit="мм",
          note=f"ниже C на {c_pt[1] - mid_root[1]:.1f}; к лопатке на {-(mid_root[0] - c_pt[0]):.1f} — в пределах заявленной неопределённости фото")
    check("Зуб", "Удерживающая ступенька", "параметр TOOTH_STEP_ENABLED", c.TOOTH_STEP_ENABLED, False,
          status="NOT CONFIRMED", note="форма/положение не измерены ('?'); механизм параметрический, по умолчанию выключен")

    # 12. Экспорт: STEP
    step_path, stl_path = M.STEP_PATH, M.STL_PATH
    step_shape = import_step(str(step_path))
    s_solids = step_shape.solids()
    check("STEP", "Файл не пустой", "размер файла", step_path.stat().st_size, unit="байт",
          status="PASS" if step_path.stat().st_size > 10000 else "FAIL")
    check("STEP", "Обратный импорт: одно твёрдое тело", "import_step → solids()", len(s_solids), 1, 0, unit="шт")
    ss = s_solids[0]
    check("STEP", "Обратный импорт: валидность", "BRepCheck_Analyzer", BRepCheck_Analyzer(ss.wrapped).IsValid(), True)
    check("STEP", "Объём совпадает с построением", "|V_step − V_build| / V_build", abs(ss.volume - vol) / vol,
          0.0, 1e-5, unit="отн.", note=f"V_step={ss.volume:.3f} мм³")
    sbb = ss.bounding_box(optimal=True)
    dbb = max(abs(a - b) for a, b in zip((sbb.min.X, sbb.min.Y, sbb.min.Z, sbb.max.X, sbb.max.Y, sbb.max.Z),
                                         (bb.min.X, bb.min.Y, bb.min.Z, bb.max.X, bb.max.Y, bb.max.Z)))
    check("STEP", "Габариты совпадают с построением", "max |Δ bbox|", dbb, 0.0, 1e-4)
    head = step_path.read_text(errors="ignore")[:4000]
    check("STEP", "Единицы — миллиметры", "SI_UNIT(.MILLI.,.METRE.) в заголовке STEP",
          ".MILLI." in step_path.read_text(errors="ignore"), True)
    check("STEP", "Схема STEP", "FILE_SCHEMA", re.search(r"FILE_SCHEMA\s*\(\s*\(\s*'([^']+)'", head).group(1)
          if re.search(r"FILE_SCHEMA\s*\(\s*\(\s*'([^']+)'", head) else "?", unit="", status="INFO")

    # 13. Экспорт: STL
    mesh = trimesh.load(str(stl_path), force="mesh")
    check("STL", "Файл не пустой", "число треугольников", len(mesh.faces), unit="шт",
          status="PASS" if len(mesh.faces) > 1000 else "FAIL",
          note=f"триангуляция: допуск {c.STL_TOLERANCE} мм, угловой {c.STL_ANGULAR_TOLERANCE} рад")
    check("STL", "Замкнутость (watertight)", "trimesh.is_watertight", bool(mesh.is_watertight), True)
    _, edge_use = np.unique(mesh.edges_sorted, axis=0, return_counts=True)
    check("STL", "Граничные рёбра сетки (дыры)", "рёбра, принадлежащие одному треугольнику", int((edge_use == 1).sum()),
          0, 0, unit="шт")
    check("STL", "Неманифолдные рёбра сетки", "рёбра, принадлежащие >2 треугольникам", int((edge_use > 2).sum()),
          0, 0, unit="шт")
    check("STL", "Согласованная ориентация треугольников", "trimesh.is_winding_consistent",
          bool(mesh.is_winding_consistent), True)
    check("STL", "Нормали наружу (положительный объём)", "trimesh.volume > 0", float(mesh.volume), unit="мм³",
          status="PASS" if mesh.volume > 0 else "FAIL")
    bodies = mesh.split(only_watertight=False)
    check("STL", "Одно связное тело", "trimesh.split", len(bodies), 1, 0, unit="шт")
    check("STL", "Объём STL ≈ объём CAD", "|V_stl − V_cad| / V_cad", abs(mesh.volume - vol) / vol, 0.0, 0.002,
          unit="отн.", note=f"V_stl={mesh.volume:.2f} мм³")
    mb = mesh.bounds
    dbb = max(abs(a - b) for a, b in zip(list(mb[0]) + list(mb[1]),
                                         (bb.min.X, bb.min.Y, bb.min.Z, bb.max.X, bb.max.Y, bb.max.Z)))
    check("STL", "Габариты STL ≈ CAD (единицы мм)", "max |Δ bbox|", dbb, 0.0, 0.02,
          note=f"X {mb[1][0] - mb[0][0]:.3f} × Y {mb[1][1] - mb[0][1]:.3f} × Z {mb[1][2] - mb[0][2]:.3f} мм")
    check("STL", "Эйлерова характеристика", "V − E + F (2 − 2·род)", int(mesh.euler_number), unit="",
          status="INFO", note="ожидается −2: два сквозных отверстия (род 2)")
    mm = manifold3d.Manifold(manifold3d.Mesh(vert_properties=np.asarray(mesh.vertices, dtype=np.float32),
                                             tri_verts=np.asarray(mesh.faces, dtype=np.uint32)))
    check("STL", "manifold3d: многообразная сетка", "Manifold(mesh).status() == NoError", str(mm.status()), unit="",
          status="PASS" if "NoError" in str(mm.status()) else "FAIL", note=f"род {mm.genus()}, объём {mm.volume():.2f}")

    # 14. Варианты параметров (механизм редактирования)
    variants = {}
    if do_variants:
        for name, ov in {"удерживающая ступенька включена (значения-заглушки)": {"TOOTH_STEP_ENABLED": True},
                         "прямая грань зуба снизу": {"TOOTH_FLAT_FACE": "bottom"},
                         "контур фланца по исходной таблице §12.1 (S поднята до 2,5)":
                             {"FLANGE_CONTOUR_SOURCE": "spec", "PADDLE_S_V": 2.5},
                         "γ = 3°": {"GAMMA_DEG": 3.0},
                         "центр C зафиксирован на 7,15 (как до исправления Ø)": {"LUG_HOLE_CENTER_Z_FIXED": 7.15}}.items():
            try:
                sv, iv_info, _ = M.build(ov)
                ok = sv.is_valid and len(sv.solids()) == 1
                variants[name] = dict(ok=ok, volume=sv.volume, overrides=ov)
                note = f"V={sv.volume:.1f} мм³"
                if ov.get("TOOTH_STEP_ENABLED"):
                    q = tp_flat + t3 * (c.TOOTH_STEP_FROM_ROOT + 1.5)
                    ivs = intervals(sv, (q + tw3 * 5), (-tw3))
                    drop = ivs[0][0] - 5.0 if ivs else float("nan")
                    ok = ok and abs(drop - c.TOOTH_STEP_DEPTH) < 0.002
                    note += f"; прямая грань за стенкой понижена на {drop:.3f} (задано {c.TOOTH_STEP_DEPTH})"
                if ov.get("LUG_HOLE_CENTER_Z_FIXED") is not None:
                    ivs = intervals(sv, (der["LUG_MID_X"], 0, 50), (0, 0, -1))
                    bridge_v = ivs[0][1] - ivs[0][0] if ivs else float("nan")
                    gap_v = ivs[1][0] - ivs[0][1] if len(ivs) >= 2 else float("nan")
                    bridge_exp = c.H3_LUG - ov["LUG_HOLE_CENTER_Z_FIXED"] - c.LUG_HOLE_D / 2
                    ok = ok and abs(bridge_v - bridge_exp) < 0.002 and abs(gap_v - c.LUG_HOLE_D) < 0.002
                    note += (f"; перемычка {bridge_v:.3f} (ожидается {bridge_exp:.3f}), Ø по лучу {gap_v:.3f}, "
                             f"центр Z={iv_info['lug_hole_center_z']:.2f}")
                check("Варианты", f"Перестроение: {name}", f"model.build({ov})", ok, True, note=note)
            except Exception as exc:  # noqa: BLE001 — вариант фиксируется как FAIL с текстом ошибки
                variants[name] = dict(ok=False, error=str(exc), overrides=ov)
                check("Варианты", f"Перестроение: {name}", f"model.build({ov})", False, True, note=str(exc)[:200])

    results.update(
        checks=CHECKS,
        variants=variants,
        volume_mm3=vol,
        bbox=dict(min=[bb.min.X, bb.min.Y, bb.min.Z], max=[bb.max.X, bb.max.Y, bb.max.Z]),
        environment=dict(python=sys.version.split()[0], platform=platform.platform(),
                         build123d=version("build123d"), ocp=version("cadquery-ocp-novtk"),
                         trimesh=version("trimesh"), manifold3d=version("manifold3d"), numpy=version("numpy")),
        seconds=round(time.time() - t_start, 1),
    )
    return results


def fmt(v):
    if isinstance(v, bool):
        return "да" if v else "нет"
    if isinstance(v, float):
        if v != 0 and (abs(v) < 1e-3):
            return f"{v:.2e}"
        return f"{v:.4f}".rstrip("0").rstrip(".") if abs(v) < 1000 else f"{v:.1f}"
    return str(v)


MANUAL_SECTION = (ROOT / "reports" / "validation_manual.md")

# Пункты ACCEPTANCE_CHECKLIST.md → автоматические проверки (группа, начало названия) и/или ручной осмотр.
ACCEPTANCE = [
    ("Прочитан полный ТЗ; использованы §12 (допущения) и §13 (требования)", [],
     "вручную — «Ручные проверки → Источники»; итог в src/params.py и assumptions.md"),
    ("Просмотрен PDF с изображениями, не только текст; сопоставлены боковой и задний виды, разметка H1/H2 и углы", [],
     "вручную — все 12 страниц отрендерены, 10 фото извлечены; reports/figures/compare_*.png"),
    ("Статусы У/И/О/Д/Р/? сохранены в параметрах и таблице допущений", [],
     "поле status каждого параметра в src/params.py; reports/parameters.md; reports/assumptions.md"),
    ("Полная модель: две проушины, отверстия, рожки, шейка, 3 ребра, фланец с крылышками, лопатка, тыльное углубление, зуб",
     [("Проушины", "Сечение по X над отверстием"), ("Проушины", "Отверстия сквозные"), ("Рожки", "Количество рожков"),
      ("Шейка", "Ширина шейки у площадки"), ("Рёбра", "Количество рёбер"), ("Фланец", "Полная ширина 70"),
      ("Углубление", "Длина 48"), ("Лопатка", "Толщина при u=15"), ("Зуб", "Ширина 17,5")], ""),
    ("H1 = 33,5 от макушки ушка до нижнего края фланца вдоль H, без лопатки",
     [("Главные размеры", "H1 = 33,5"), ("Главные размеры", "Верхняя точка H1"), ("Главные размеры", "Нижняя точка H1")], ""),
    ("H2 = 16,5 вдоль F фланца, а не по общему габариту", [("Главные размеры", "H2 = 16,5")], ""),
    ("H3 = 11,3 от A до вершины ушка", [("Главные размеры", "H3 = 11,3")], ""),
    ("L1 = 30,0 от S до края лопатки вдоль P", [("Главные размеры", "L1 = 30,0")], ""),
    ("Ø у обеих проушин (по исправленному замеру владельца " + dec(p.LUG_HOLE_D) + "; в ТЗ — Ø2,5); соосность; "
     "две толщины 3,0; внутренний зазор 21,8",
     [("Проушины", "Диаметр отверстий"), ("Проушины", "Соосность"), ("Проушины", "Толщина проушины (−X)"),
      ("Проушины", "Толщина проушины (+X)"), ("Проушины", "Чистый зазор")], ""),
    ("Ширина фланца 70; непрерывная симметричная кромка без ложного общего R27",
     [("Фланец", "Полная ширина 70"), ("Фланец", "Выпуклая кромка без перегибов"), ("Фланец", "Симметрия контура"),
      ("Фланец", "Нет общего R27")], ""),
    ("Оба угла 110° с правильным знаком и лучами (§10)",
     [("Углы", "α лопатка–фланец"), ("Углы", "β площадка–шейка"), ("Углы", "Наклон F к H")],
     "сторона наклона дополнительно сверена наложением на IMG_4396"),
    ("Зуб не загнут (основное направление ∥ P); рабочая ступенька не выдана за подтверждённый факт",
     [("Углы", "γ зуб–P"), ("Зуб", "Удерживающая ступенька")], "ступенька — статус NOT CONFIRMED"),
    ("Шейка замыкает H1 (итоговая длина записана); все рёбра объединены с деталью",
     [("Шейка", "Итоговая длина шейки"), ("Рёбра", "Рёбра объединены")], ""),
    ("В основной выдаче ровно одно связное твёрдое тело",
     [("Топология", "Число твёрдых тел"), ("STEP", "Обратный импорт: одно твёрдое тело"), ("STL", "Одно связное тело")], ""),
    ("build123d/Python-скрипт выполнен без ошибок", [("Построение", "build123d-скрипт выполнен")],
     "на macOS arm64 (машина пользователя); на Windows не запускался"),
    ("Положительный объём, валидный BREP, нет пересечений и щелей; методы записаны",
     [("Топология", "Объём положительный"), ("Топология", "BRepCheck_Analyzer"), ("Топология", "Нет самопересечений"),
      ("Топология", "Свободные рёбра"), ("Топология", "Неманифолдные рёбра")], ""),
    ("STEP не пустой, обратный импорт даёт ожидаемое твёрдое тело",
     [("STEP", "Файл не пустой"), ("STEP", "Обратный импорт: валидность"), ("STEP", "Единицы — миллиметры")], ""),
    ("STL не пустой, ориентирован, замкнут и многообразен (проверено инструментально); мм отмечены для печатника",
     [("STL", "Файл не пустой"), ("STL", "Замкнутость"), ("STL", "Согласованная ориентация"), ("STL", "Нормали наружу"),
      ("STL", "manifold3d")], "единицы мм — reports/print_handoff.md"),
    ("STEP и STL из одной геометрии; записаны габариты, объём, число тел, параметры триангуляции",
     [("STEP", "Объём совпадает"), ("STEP", "Габариты совпадают"), ("STL", "Объём STL"), ("STL", "Габариты STL")], ""),
    ("Деталь визуально сопоставлена с основными фотографиями", [],
     "вручную — reports/figures/compare_*.png; расхождения перечислены в «Ручные проверки»"),
    ("Рабочее зацепление не объявлено подтверждённым без ответной части или испытания", [("Зуб", "Удерживающая ступенька")],
     "статус NOT CONFIRMED; также в assumptions.md и print_handoff.md"),
]


def acceptance_lines(checks: list[dict]) -> list[str]:
    lines = ["## Чек-лист приёмки (ACCEPTANCE_CHECKLIST.md)", "",
             "`[x]` — пункт подтверждён перечисленными проверками этого отчёта (PASS; INFO — значение записано; "
             "NOT CONFIRMED — честно помечено неподтверждённым) или выполненным ручным осмотром.", ""]
    for text, refs, note in ACCEPTANCE:
        found, ok = [], True
        for group, prefix in refs:
            match = [ch for ch in checks if ch["group"] == group and ch["item"].startswith(prefix)]
            if not match:
                ok = False
                found.append(f"«{prefix}» — проверка не найдена")
                continue
            for ch in match:
                ok &= ch["status"] in ("PASS", "INFO", "NOT CONFIRMED")
                found.append(f"{group}: «{ch['item']}» — {ch['status']}")
        detail = "; ".join(found + ([note] if note else []))
        lines.append(f"- [{'x' if ok else ' '}] {text}. _{detail}_")
    return lines + [""]


def write_markdown(results: dict):
    counts = {}
    for ch in results["checks"]:
        counts[ch["status"]] = counts.get(ch["status"], 0) + 1
    failed = [ch for ch in results["checks"] if ch["status"] == "FAIL"]
    env = results["environment"]
    lines = [
        "# Отчёт о проверке V01 — ручка-защёлка подлокотника",
        "",
        "> Файл сгенерирован `src/validate.py` " + results["started"] + ". Все числа ниже — результаты реальных",
        "> измерений тела, перестроенного из `src/`, и обратного импорта выданных файлов. Посадка и работа зуба",
        "> **не проверены** (нет ответной детали и примерки).",
        "",
        f"**Итог автоматических проверок:** {', '.join(f'{k}: {v}' for k, v in sorted(counts.items()))}. "
        + ("**Есть FAIL — см. таблицу.**" if failed else "Провалов нет."),
        "",
        f"Среда: Python {env['python']}, build123d {env['build123d']}, OCP {env['ocp']}, trimesh {env['trimesh']}, "
        f"manifold3d {env['manifold3d']}, {env['platform']}. Время проверки {results['seconds']} с.",
        "",
        f"Объём тела: **{results['volume_mm3']:.2f} мм³**. Габариты (мм): X {results['bbox']['min'][0]:.3f}…{results['bbox']['max'][0]:.3f}, "
        f"Y {results['bbox']['min'][1]:.3f}…{results['bbox']['max'][1]:.3f}, Z {results['bbox']['min'][2]:.3f}…{results['bbox']['max'][2]:.3f}.",
        "",
        "Базы: X — ось C, Z — нормаль к A (H = Z), +Y — тыльная сторона; начало — на A под осью C в плоскости B.",
        "",
        *acceptance_lines(results["checks"]),
    ]
    group = None
    for ch in results["checks"]:
        if ch["group"] != group:
            group = ch["group"]
            lines += ["", f"## {group}", "", "| Проверка | Способ | Измерено | Ожидается | Допуск | Статус | Примечание |",
                      "|---|---|---:|---:|---:|---|---|"]
        exp = "" if ch["expected"] is None else fmt(ch["expected"])
        tol = "" if ch["tol"] is None else fmt(ch["tol"])
        unit = f" {ch['unit']}" if ch["unit"] and not isinstance(ch["measured"], (bool, str)) else ""
        lines.append(f"| {ch['item']} | {ch['method']} | {fmt(ch['measured'])}{unit} | {exp} | {tol} | "
                     f"**{ch['status']}** | {ch['note']} |")
    lines += ["", "## Ручные проверки и осмотр", ""]
    if MANUAL_SECTION.exists():
        lines.append(MANUAL_SECTION.read_text(encoding="utf-8").strip())
    else:
        lines.append("_Раздел ручного осмотра не заполнен._")
    (REPORTS / "validation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_parameters(results: dict):
    """reports/parameters.md — полный список параметров со статусами из src/params.py и расчётные величины."""
    info = results["build_info"]
    der = p.derived()
    lines = ["# Параметры V01 (сгенерировано из `src/params.py` скриптом `src/validate.py`)", "",
             "Статусы ТЗ: **У** — владелец; **И** — исходное описание; **О** — оценка; **Д** — допущение; "
             "**Р** — расчёт; **?** — неизвестно. Изменять значения — только в `src/params.py`, затем "
             "`src/run_all.py`.", "",
             "| Параметр | Значение | Статус | Источник | Описание |", "|---|---|---|---|---|"]
    for name, prm in p.PARAMS.items():
        val = prm.value
        if isinstance(val, tuple):
            val = "; ".join(f"({x:g}, {v:g})" for x, v in val)
        elif val is None:
            val = "не задано"
        lines.append(f"| `{name}` | {val} | {prm.status} | {prm.source} | {prm.description} |")
    lines += ["", "## Расчётные величины (Р)", "", "| Величина | Значение, мм/° | Как получена |", "|---|---:|---|"]
    hz = der["LUG_HOLE_Z"]
    rows = [
        ("Центр отверстия C над A", hz, "H3 − (перемычка 2,9 + Ø/2)" if p.LUG_HOLE_CENTER_Z_FIXED is None
         else "задан LUG_HOLE_CENTER_Z_FIXED"),
        ("Радиус дуги вершины ушка", der["LUG_TOP_RADIUS"], "H3 − Z_C (дуга с центром в отверстии через макушку, Д)"),
        ("Перемычка над отверстием", der["LUG_BRIDGE"], "R − Ø/2"),
        ("Внутренние грани проушин X", der["LUG_INNER_X"], "±зазор/2"),
        ("Средние плоскости проушин X", der["LUG_MID_X"], "±(зазор + толщина)/2"),
        ("Наружный размах проушин", der["LUG_OUTER_SPAN"], "зазор + 2·толщина"),
        ("Нижний край отверстия над A", der["LUG_HOLE_BOTTOM_Z"], "центр − Ø/2"),
        ("Остаток площадки за проушинами", der["PAD_MARGIN_BEYOND_LUGS"], "(30,8 − 27,8)/2"),
        ("Целевой низ фланца Z", der["Z_TARGET_MIN"], "H3 − H1"),
        ("Длина шейки по лицевой грани", info["neck_length_front_face_s"], "замыкание H1 (вместо стартовых 5,1)"),
        ("Длина шейки по тыльной грани", info["neck_length_back_face"], "от низа площадки до прямой V=0"),
        ("Радиус вогнутого перехода шейки", info["neck_junction_fillet_radius"], "ширина сопряжения 36 при V=0"),
        ("X острого кончика до скругления R1", info["flange_tip_x_before_rounding"], "итерация: габарит 70,000 после R1"),
        ("Развал боковин проушины", info["lug_side_flare_deg"],
         f"касательные от углов основания к дуге R{dec(round(der['LUG_TOP_RADIUS'], 3))}"),
        ("S: Y", info["S_point_YZ"][0], "лицевая плоскость фланца на V = PADDLE_S_V"),
        ("S: Z (= плоскость P)", info["S_point_YZ"][1], "то же"),
        ("Корень прямой грани зуба T0: Y", info["tooth_flat_root_YZ"][0], "от оси C (Y=0)"),
        ("Корень прямой грани зуба T0: Z", info["tooth_flat_root_YZ"][1], f"Z оси C = {dec(round(hz, 3))}"),
        ("Нижняя линия корня зуба R0: Y", info["tooth_lower_root_R0_YZ"][0], "0,5 вдоль F от выпуклой кромки"),
        ("Нижняя линия корня зуба R0: Z", info["tooth_lower_root_R0_YZ"][1], ""),
        ("Конец зуба: Y", info["tooth_tip_flat_YZ"][0], "T0 + 10 вдоль P"),
        ("Объём тела, мм³", results["volume_mm3"], "build123d"),
    ]
    for name, val, how in rows:
        lines.append(f"| {name} | {val:.3f} | {how} |")
    (REPORTS / "parameters.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    do_variants = "--no-variants" not in sys.argv
    results = run(do_variants)
    REPORTS.mkdir(exist_ok=True)

    def default(o):
        if isinstance(o, (np.floating, np.integer)):
            return o.item()
        if isinstance(o, np.bool_):
            return bool(o)
        return str(o)

    (REPORTS / "validation_results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False, default=default),
                                                     encoding="utf-8")
    write_markdown(results)
    write_parameters(results)
    failed = [ch for ch in results["checks"] if ch["status"] == "FAIL"]
    for ch in results["checks"]:
        flag = "!!" if ch["status"] == "FAIL" else "  "
        print(f"{flag} [{ch['status']:>13}] {ch['group']}: {ch['item']} = {fmt(ch['measured'])} {ch['note']}")
    print(f"\n{len(results['checks'])} checks, {len(failed)} FAIL, {results['seconds']} s")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()

"""Чертёж-схема V01 (ТЗ §13.7): боковое сечение, вид фланца, профиль проушины, таблица параметров.

Запуск: .venv/bin/python src/drawing.py  (после model.py и validate.py)
Сечения берутся из выданного STL (output/armrest_latch_v03.stl), подписи — из
reports/validation_results.json (измеренные значения) и reports/build_info.json.
Это поясняющая схема для владельца и печатника, а не чертёж по ЕСКД.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent
sys.path.insert(0, str(SRC))
import model as M  # noqa: E402
import params as p  # noqa: E402

plt.rcParams.update({"font.size": 8, "font.family": "DejaVu Sans"})


def measured(results, item_prefix):
    for ch in results["checks"]:
        if ch["item"].startswith(item_prefix):
            return ch["measured"]
    raise KeyError(item_prefix)


def section(mesh, origin, normal):
    """Отрезки сечения сетки плоскостью: массив (n, 2, 3)."""
    return trimesh.intersections.mesh_plane(mesh, plane_normal=normal, plane_origin=origin)


def draw_segments(ax, segs, xy, **style):
    from matplotlib.collections import LineCollection
    if len(segs):
        ax.add_collection(LineCollection([[xy(a), xy(b)] for a, b in segs], **style))


def dec(v) -> str:
    return f"{v:g}".replace(".", ",")


def dim_line(ax, a, b, text, offset, color="#b00", fs=8, text_shift=(0, 0)):
    a, b = np.asarray(a, float), np.asarray(b, float)
    dvec = b - a
    n = np.array([-dvec[1], dvec[0]]) / np.linalg.norm(dvec)
    a2, b2 = a + n * offset, b + n * offset
    ax.plot([a[0], a2[0]], [a[1], a2[1]], color=color, lw=0.5)
    ax.plot([b[0], b2[0]], [b[1], b2[1]], color=color, lw=0.5)
    ax.annotate("", xy=b2, xytext=a2, arrowprops=dict(arrowstyle="<->", color=color, lw=0.8, shrinkA=0, shrinkB=0))
    mid = (a2 + b2) / 2 + n * 0.8 + np.asarray(text_shift)
    ang = math.degrees(math.atan2(dvec[1], dvec[0]))
    if ang > 90:
        ang -= 180
    if ang < -90:
        ang += 180
    ax.text(mid[0], mid[1], text, color=color, fontsize=fs, rotation=ang, ha="center", va="center",
            bbox=dict(fc="white", ec="none", alpha=0.8, pad=0.5))


def main():
    results = json.loads((ROOT / "reports" / "validation_results.json").read_text(encoding="utf-8"))
    info = results["build_info"]
    c = M.config()
    d = M.directions(c)
    der = p.derived(c)
    mesh = trimesh.load(str(M.STL_PATH), force="mesh")

    fig = plt.figure(figsize=(16.5, 11.7))
    fig.suptitle("Ручка-защёлка подлокотника — V01 (предварительная модель для примерки). Все размеры в мм. "
                 "Подписи — измерения тела V01 (src/validate.py), а не замеры оригинала.", fontsize=10, x=0.01, ha="left")
    gs = fig.add_gridspec(2, 3, width_ratios=[1.6, 1.0, 0.72], height_ratios=[1.15, 1.0], wspace=0.18, hspace=0.18,
                          left=0.03, right=0.99, top=0.94, bottom=0.03)

    # --- 1. Боковое сечение X = 0 ------------------------------------------------------------
    ax = fig.add_subplot(gs[:, 0])
    ax.set_title("Боковое сечение по плоскости B (X = 0); серым — сечение через проушину X = 12,4", loc="left")
    yz = lambda q: (q[1], q[2])  # noqa: E731
    draw_segments(ax, section(mesh, (12.4, 0, 0), (1, 0, 0)), yz, colors="0.6", linewidths=0.8, linestyles="--")
    draw_segments(ax, section(mesh, (0, 0, 0), (1, 0, 0)), yz, colors="k", linewidths=1.1)
    hz = der["LUG_HOLE_Z"]
    ax.plot([0], [hz], marker="+", color="b", ms=14, mew=1.2)
    ax.text(0.6, hz + 0.6, f"C (ось Ø{dec(c.LUG_HOLE_D)})", color="b")
    ax.axhline(0, color="g", lw=0.6, ls="-.")
    ax.text(-40, 0.4, "A (Z=0)", color="g")
    z_top, z_low = 11.3, c.H3_LUG - c.H1_OVERALL
    dim_line(ax, (9, z_top), (9, z_low), f"H1 = {measured(results, 'H1 = 33,5'):.2f} (вдоль H=Z)", -6)
    dim_line(ax, (6, 0), (6, z_top), f"H3 = {measured(results, 'H3 = 11,3'):.2f}", -2.5)
    o = np.array(info["flange_origin_Of_YZ"])
    F, N = np.array(d["F"]), np.array(d["N"])
    apex = o + F * c.H2_FLANGE
    dim_line(ax, o, apex, f"H2 = {measured(results, 'H2 = 16,5'):.2f} вдоль F", 11.0)
    s_pt = np.array(info["S_point_YZ"])
    tip = s_pt + np.array(d["p_dir"]) * c.L1_PADDLE
    dim_line(ax, s_pt, tip, f"L1 = {measured(results, 'L1 = 30,0'):.2f} от S вдоль P", -4.5)
    ax.plot(*s_pt, "o", color="#b00", ms=4)
    ax.text(s_pt[0] - 3.2, s_pt[1] + 0.6, "S", color="#b00", fontsize=9)
    ax.text(s_pt[0] - 15, s_pt[1] + 1.2, f"α = {measured(results, 'α'):.1f}° (P к концу ↔ фланец к верху)",
            color="#b00", fontsize=7)
    pc = np.array([-c.LUG_HOLE_FROM_FRONT_END, -c.PAD_THICKNESS])
    ax.text(pc[0] + 1.0, pc[1] - 2.6, f"β = {measured(results, 'β'):.1f}°", color="#b00")
    ax.text(-41, -25.0, f"Шейка (зависимая длина, замыкание H1): {info['neck_length_front_face_s']:.2f} по лицевой грани, "
            f"{info['neck_length_back_face']:.2f} по тыльной;\nстарт исходника {c.NECK_LENGTH_START} — справочно.",
            fontsize=7.5)
    t0 = np.array(info["tooth_flat_root_YZ"])
    tt = np.array(info["tooth_tip_flat_YZ"])
    r0 = np.array(info["tooth_lower_root_R0_YZ"])
    for q, lab in ((t0, "T0"), (tt, "конец"), (r0, "R0")):
        ax.plot(*q, "s", color="#060", ms=3)
        ax.text(q[0] + 0.4, q[1] + 0.5, lab, color="#060", fontsize=7)
    ax.text(-41, -28.6, f"Зуб: прямая грань ∥ P (γ = {measured(results, 'γ'):.1f}°), вылет {measured(results, 'Вылет 10,0'):.2f}, "
            f"толщина 5,2 (у R0) → 2,0 (у конца).\nОт C: T0 ΔY={t0[0]:.2f}, ΔZ={t0[1] - hz:.2f}; конец ΔY={tt[0]:.2f}, "
            f"ΔZ={tt[1] - hz:.2f}.", fontsize=7.5, color="#060")
    ax.text(-41, -31.2, "Удерживающая ступенька зуба НЕ ЗАДАНА (нет замеров ответной части) —\nв V01 это клиновая оболочка.",
            fontsize=7.5, color="#a00")
    ax.set_aspect("equal")
    ax.set_xlim(-42, 20)
    ax.set_ylim(-32.5, 14)
    ax.grid(True, lw=0.2)
    ax.set_xlabel("Y, мм (−Y — лицевая сторона/лопатка; +Y — тыл/зуб)")
    ax.set_ylabel("Z = H, мм")

    # --- 2. Вид фланца (по нормали, как IMG_4397) ------------------------------------------
    ax = fig.add_subplot(gs[0, 1:])
    ax.set_title("Фланец по нормали к пластине (локальные X, V; V от прямой кончиков к выпуклой кромке)", loc="left")
    o3 = np.array([0, o[0], o[1]])
    n3, f3 = np.array([0, N[0], N[1]]), np.array([0, F[0], F[1]])

    xv = lambda q: ((q - o3)[0], (q - o3) @ f3)  # noqa: E731
    for n_off, style in ((1.6, dict(colors="k", linewidths=1.0)),
                         (c.FLANGE_THICKNESS - 0.3, dict(colors="#a50", linewidths=0.9)),
                         (c.FLANGE_THICKNESS + 0.6, dict(colors="#060", linewidths=0.9)),
                         (-0.4, dict(colors="#06c", linewidths=0.7, linestyles="--"))):
        draw_segments(ax, section(mesh, tuple(o3 + n3 * n_off), tuple(n3)), xv, **style)
    pts = M.contour_points(c)
    for x_i, v_i in pts:
        for sx in ((1, -1) if x_i else (1,)):
            ax.plot(sx * x_i, v_i, "o", color="#b00", ms=3)
            ax.text(sx * x_i, v_i + 0.7, f"({sx * x_i:g}; {v_i:g})", color="#b00", fontsize=6.5, ha="center")
    dim_line(ax, (-35, 0), (35, 0), f"70,00 (после R1 кончиков)", -3.5)
    dim_line(ax, (38.5, 0), (38.5, 16.5), "H2 16,50", -1.5)
    ax.text(0, 2.0, f"переход шейки: ширина 34 → 36 у V=0 (вогнутые R{info['neck_junction_fillet_radius']:.2f})",
            ha="center", fontsize=7)
    ax.text(0, 6.6, "тыльное углубление 48 × 2,5 × 1,5 (V=5), концы R1,25", ha="center", fontsize=7, color="#a50")
    ax.text(0, 18.2, "зуб 17,5 (сечение за тыльной плоскостью)", ha="center", fontsize=7, color="#060")
    ax.text(-34, 12.5, "синий пунктир — корень лопатки\nна лицевой плоскости (с галтелью)", fontsize=7, color="#06c")
    ax.text(-34, 16.5, f"контур: сплайн по точкам V01\n(ТЗ §12.1, ±18/±26 уточнены по IMG_4397); R27 не применён",
            fontsize=7)
    ax.set_aspect("equal")
    ax.set_xlim(-40, 42)
    ax.set_ylim(-6.0, 20.5)
    ax.grid(True, lw=0.2)

    # --- 3. Профиль проушины ---------------------------------------------------------------------
    ax = fig.add_subplot(gs[1, 1])
    ax.set_title("Профиль проушины (сечение X = 12,4) и площадка", loc="left")
    segs = section(mesh, (12.4, 0, 0), (1, 0, 0))
    segs = segs[(segs[:, :, 2] > -2.6).all(axis=1)] if len(segs) else segs
    draw_segments(ax, segs, lambda q: (q[1], q[2]), colors="k", linewidths=1.0)
    r_top = der["LUG_TOP_RADIUS"]
    circ = plt.Circle((0, hz), r_top, fill=False, ls=":", color="0.5")
    ax.add_patch(circ)
    ax.plot([0], [hz], "+", color="b", ms=10)
    dim_line(ax, (-5.25, -2.5), (5.25, -2.5), "основание 10,50 (= длина площадки)", 1.6)
    dim_line(ax, (6.5, 0), (6.5, 11.3), "11,30", -1.2)
    dim_line(ax, (-6.6, 0), (-6.6, hz), f"{dec(round(hz, 2))}", 1.2)
    ax.text(-8.2, -3.6, f"Ø{dec(c.LUG_HOLE_D)} (исправлено владельцем; было Ø2,5), фаска 0,2; "
            f"перемычка {dec(round(der['LUG_BRIDGE'], 2))}", fontsize=7, color="b")
    ax.text(-4.8, 12.0, f"R{dec(round(r_top, 2))} от центра отверстия (Д); боковины — касательные, развал "
            f"{info['lug_side_flare_deg']:.1f}°", fontsize=7)
    ax.text(-8.2, -4.7, f"толщина 3,0 ×2; зазор 21,8; наружный размах 27,8; корень R{c.LUG_ROOT_FILLET}", fontsize=7)
    ax.set_aspect("equal")
    ax.set_xlim(-8.5, 9.5)
    ax.set_ylim(-5.5, 13)
    ax.grid(True, lw=0.2)

    # --- 4. Таблица параметров -------------------------------------------------------------------
    ax = fig.add_subplot(gs[1, 2])
    ax.axis("off")
    ax.set_title("Ключевые параметры (все — reports/assumptions.md)", loc="left")
    keys = ["H1_OVERALL", "H2_FLANGE", "H3_LUG", "L1_PADDLE", "ALPHA_DEG", "BETA_DEG", "GAMMA_DEG", "DELTA_DEG",
            "LUG_HOLE_D", "LUG_INNER_GAP", "LUG_TOP_TO_HOLE_EDGE", "FLANGE_THICKNESS", "PADDLE_S_V", "PADDLE_THICKNESS_TIP",
            "TOOTH_LENGTH", "TOOTH_THICKNESS_ROOT", "TOOTH_THICKNESS_TIP", "TOOTH_ROOT_EDGE_OFFSET", "TOOTH_FLAT_FACE",
            "TOOTH_STEP_ENABLED", "RIB_OUTER_X", "FLANGE_EDGE_FILLET_BACK"]
    rows = [[k, str(p.PARAMS[k].value), p.PARAMS[k].status] for k in keys]
    rows.append(["Центр C над A (Р)", f"{hz:.2f}", "Р"])
    rows.append(["Шейка (Р, из H1)", f"{info['neck_length_front_face_s']:.2f} / {info['neck_length_back_face']:.2f}", "Р"])
    tbl = ax.table(cellText=rows, colLabels=["параметр", "значение", "статус"], loc="upper left",
                   colWidths=[0.58, 0.24, 0.18], cellLoc="left")
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(6.6)
    tbl.scale(1, 1.13)

    out_png = ROOT / "output" / "armrest_latch_v03_drawing.png"
    out_svg = ROOT / "output" / "armrest_latch_v03_drawing.svg"
    fig.savefig(out_png, dpi=150)
    fig.savefig(out_svg)
    print("wrote", out_png, "and", out_svg)


if __name__ == "__main__":
    main()

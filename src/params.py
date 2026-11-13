"""Редактируемые параметры ручки-защёлки V01 (все размеры в мм, углы в градусах).

Статусы по ТЗ (input/cad-latch-spec.md, раздел 1):
  У — задано/уточнено владельцем;  И — из исходного описания;  О — оценка;
  Д — рабочее допущение;  Р — расчёт;  ? — неизвестно.

Система координат (ТЗ §2): X — вдоль оси отверстий C, Z — нормаль к площадке A
к макушкам проушин (H = Z в V01), Y — дополняет до правой тройки (+Y — тыльная
сторона: рожки, рёбра, зуб; −Y — лицевая сторона: лопатка). Начало — проекция
пересечения C и B на A.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from types import SimpleNamespace


@dataclass(frozen=True)
class Param:
    value: object
    status: str
    source: str
    description: str


PARAMS: dict[str, Param] = {}


def _p(name: str, value, status: str, source: str, description: str):
    PARAMS[name] = Param(value, status, source, description)
    return value


# --- Главные размеры (ТЗ §3) -------------------------------------------------
H1_OVERALL = _p("H1_OVERALL", 33.5, "У", "ТЗ §3, IMG_4394",
                "Габарит вдоль H(=Z): макушка проушины → самая нижняя кромка фланца; лопатка не входит; ведущий размер")
H2_FLANGE = _p("H2_FLANGE", 16.5, "У", "ТЗ §3, §7, IMG_4395",
               "Собственная высота фланца вдоль F: прямая V=0 кончиков крылышек → вершина выпуклой кромки")
H3_LUG = _p("H3_LUG", 11.3, "У", "ТЗ §3, §4", "Высота проушины от A до макушки по нормали к A")
L1_PADDLE = _p("L1_PADDLE", 30.0, "У/Д", "ТЗ §2, §3, §8",
               "Длина лопатки вдоль P от линии S до крайней точки свободного торца")

# --- Углы (ТЗ §10.1) ---------------------------------------------------------
ALPHA_DEG = _p("ALPHA_DEG", 110.0, "О", "ТЗ §10.1, IMG_4396",
               "α: луч вдоль P к свободному концу лопатки ↔ луч вдоль фланца к его верхней кромке (тупой)")
BETA_DEG = _p("BETA_DEG", 110.0, "О", "ТЗ §10.1, IMG_4396",
              "β: луч по площадке к рожкам ↔ луч по шейке к фланцу (тупой)")
GAMMA_DEG = _p("GAMMA_DEG", 0.0, "Д (У — качественно)", "ТЗ §9, §10.1",
               "γ: основное направление зуба ↔ P; >0 — конец зуба поднимается к +Z")
DELTA_DEG = _p("DELTA_DEG", 0.0, "Д", "ТЗ §2, §10.1",
               "δ: A ↔ P; >0 — свободный конец лопатки поднимается к +Z")

# --- Проушины (ТЗ §4, §12.2) -------------------------------------------------
LUG_HOLE_D = _p("LUG_HOLE_D", 3.1, "У", "владелец, исправленный замер 13.11.2026 (в ТЗ §4: Ø2,5 «И» — ошибочно)",
                "Диаметр соосных сквозных отверстий под ось C")
LUG_THICKNESS = _p("LUG_THICKNESS", 3.0, "И", "ТЗ §4", "Толщина каждой проушины вдоль X")
LUG_INNER_GAP = _p("LUG_INNER_GAP", 21.8, "И", "ТЗ §4", "Чистый зазор между внутренними плоскими гранями проушин")
LUG_TOP_TO_HOLE_EDGE = _p("LUG_TOP_TO_HOLE_EDGE", 2.9, "И", "ТЗ §4",
                          "Перемычка: от макушки до ближайшего края отверстия; задаёт высоту центра C (Р, ТЗ §4/§10.2)")
LUG_HOLE_CENTER_Z_FIXED = _p("LUG_HOLE_CENTER_Z_FIXED", None, "Д", "—",
                             "None — центр C по цепи ТЗ: Z = H3 − (перемычка + Ø/2). Число — центр C жёстко на этой "
                             "высоте над A (напр. 7.15 — положение до исправления Ø); перемычка тогда = H3 − Z − Ø/2")
LUG_BASE_LENGTH = _p("LUG_BASE_LENGTH", 10.5, "И/?", "ТЗ §4, §12.2",
                     "Длина основания ушка вдоль Y; основание заподлицо с торцами площадки (Д)")
LUG_HOLE_FROM_FRONT_END = _p("LUG_HOLE_FROM_FRONT_END", 5.25, "Д", "ТЗ §12.2",
                             "Центр отверстия от лицевого торца основания (середина основания)")
# Дуга вершины ушка (Д, ТЗ §12.2): центр в отверстии, проходит через макушку → R = H3 − Z_C (см. derived()).
LUG_ROOT_FILLET = _p("LUG_ROOT_FILLET", 0.5, "Д", "ТЗ §12.2", "Галтель корня проушин (на A)")
LUG_HOLE_CHAMFER = _p("LUG_HOLE_CHAMFER", 0.2, "Д", "ТЗ §12.2", "Притупление кромок отверстий 0,2×45°")

# --- Площадка и рожки (ТЗ §5, §12.2) ------------------------------------------
PAD_WIDTH_HORN_END = _p("PAD_WIDTH_HORN_END", 30.8, "И", "ТЗ §5", "Ширина площадки (X) у торца со стороны рожков")
PAD_WIDTH_NECK_END = _p("PAD_WIDTH_NECK_END", 32.68, "И", "ТЗ §5", "Ширина площадки (X) у перехода к шейке")
PAD_LENGTH = _p("PAD_LENGTH", 10.5, "И", "ТЗ §5", "Расстояние между торцами площадки в плоскости A (Y)")
PAD_THICKNESS = _p("PAD_THICKNESS", 2.5, "И", "ТЗ §5", "Толщина площадки по нормали к A (под A)")
HORN_PITCH = _p("HORN_PITCH", 18.0, "И", "ТЗ §5", "Межцентровое расстояние рожков по X (центры ±9 — Р)")
HORN_PROTRUSION = _p("HORN_PROTRUSION", 2.0, "И (направление Д)", "ТЗ §5, §12.2",
                     "Вылет рожков за торец площадки в плоскости A (+Y)")
HORN_WIDTH = _p("HORN_WIDTH", 2.2, "О", "ТЗ §5", "Ширина рожка по X")
HORN_THICKNESS = _p("HORN_THICKNESS", 2.5, "О", "ТЗ §5", "Толщина рожка (в пределах толщины площадки)")
HORN_EDGE_FILLET = _p("HORN_EDGE_FILLET", 0.4, "Д", "ТЗ §12.2",
                      "Скругление открытых продольных кромок рожков; торец — одной гладкой петлёй 0,75×R (0,3), "
                      "чтобы не было трёхрёберных угловых сопряжений")

# --- Шейка (ТЗ §6, §12.1, §12.2) ----------------------------------------------
NECK_WIDTH_AT_PAD = _p("NECK_WIDTH_AT_PAD", 32.68, "И", "ТЗ §6", "Ширина шейки у площадки")
NECK_WIDTH_AT_FLANGE = _p("NECK_WIDTH_AT_FLANGE", 34.0, "И", "ТЗ §6", "Ширина шейки у фланца (на прямой V=0)")
NECK_LENGTH_START = _p("NECK_LENGTH_START", 5.1, "И/Д", "ТЗ §6, §10.2",
                       "Справочная стартовая длина; итоговая длина — Р из замыкания H1 (см. отчёт)")
NECK_THICKNESS_SPEC = _p("NECK_THICKNESS_SPEC", 3.0, "И", "ТЗ §6",
                         "Толщина стенки шейки по исходнику; в V01 шейка — продолжение пластины фланца (см. FLANGE_THICKNESS)")
NECK_JUNCTION_WIDTH = _p("NECK_JUNCTION_WIDTH", 36.0, "И/Д", "ТЗ §12.1",
                         "Ширина центрального сопряжения шейки с прямой кромкой V=0 (вогнутые переходы)")
NECK_PAD_OVERLAP = _p("NECK_PAD_OVERLAP", 2.5, "Д (техн.)", "—",
                      "Технический запас контура шейки выше угла площадки перед подрезкой плоскостью низа площадки")

# --- Рёбра (ТЗ §6, §12.2) -----------------------------------------------------
RIB_THICKNESS = _p("RIB_THICKNESS", 2.0, "О", "ТЗ §6", "Толщина каждого ребра по X")
RIB_LEG_ALONG_PAD = _p("RIB_LEG_ALONG_PAD", 4.5, "О", "ТЗ §6", "Катет ребра вдоль низа площадки")
RIB_LEG_ALONG_NECK = _p("RIB_LEG_ALONG_NECK", 4.5, "О", "ТЗ §6", "Катет ребра вдоль тыльной грани шейки")
RIB_OUTER_X = _p("RIB_OUTER_X", 13.0, "О", "IMG_4397, IMG_6560 (ТЗ §12.2: «у боковых краёв»)",
                 "Положение средних плоскостей крайних рёбер ±X; среднее ребро по B")
RIB_ROOT_FILLET = _p("RIB_ROOT_FILLET", 0.5, "Д", "ТЗ §12.2", "Галтели примыкания рёбер")

# --- Фланец (ТЗ §7, §12.1, §12.2) ---------------------------------------------
FLANGE_WIDTH = _p("FLANGE_WIDTH", 70.0, "И", "ТЗ §7", "Полная ширина от кончика до кончика (после скругления кончиков)")
FLANGE_THICKNESS = _p("FLANGE_THICKNESS", 3.2, "И", "ТЗ §7", "Толщина пластины фланца (и шейки в V01) по нормали")
FLANGE_CONTOUR_SPEC = _p("FLANGE_CONTOUR_SPEC", ((0, 16.5), (9, 16.2), (18, 13.8), (26, 8.5), (35, 0)), "О/Д",
                         "ТЗ §12.1", "Исходная таблица опорных точек выпуклой кромки (X, V)")
FLANGE_CONTOUR_V01 = _p("FLANGE_CONTOUR_V01", ((0, 16.5), (9, 16.2), (18, 14.3), (26, 9.8), (35, 0)), "О/Д",
                        "ТЗ §12.1 + повторная нормировка силуэта IMG_4397",
                        "Опорные точки V01: промежуточные (±18, ±26) скорректированы по фото, габариты 70/16,5 сохранены")
FLANGE_CONTOUR_SOURCE = _p("FLANGE_CONTOUR_SOURCE", "v01", "Д", "—", "Какой набор точек применять: 'v01' или 'spec'")
FLANGE_TIP_RADIUS = _p("FLANGE_TIP_RADIUS", 1.0, "Д", "ТЗ §12.2", "Скругление кончиков крылышек в контуре")
FLANGE_EDGE_FILLET_FRONT = _p("FLANGE_EDGE_FILLET_FRONT", 0.5, "Д", "ТЗ §12.2", "Скругление наружных кромок лицевой стороны")
FLANGE_EDGE_FILLET_BACK = _p("FLANGE_EDGE_FILLET_BACK", 0.4, "Д", "ТЗ §12.2 (0,5 → 0,4)",
                             "Скругление кромок тыльной стороны; уменьшено, чтобы не совпадать с линией корня зуба (отступ 0,5)")
FLANGE_FRONT_OFFSET = _p("FLANGE_FRONT_OFFSET", 0.0, "Д", "IMG_4391/4396",
                         "Смещение лицевой плоскости фланца от лицевой грани шейки по N (0 — соосны, как на фото)")
GROOVE_LENGTH = _p("GROOVE_LENGTH", 48.0, "О", "ТЗ §7, §12.2", "Длина тыльного углубления (с полукруглыми концами)")
GROOVE_WIDTH = _p("GROOVE_WIDTH", 2.5, "О", "ТЗ §7, §12.2", "Ширина углубления (концы R1,25)")
GROOVE_DEPTH = _p("GROOVE_DEPTH", 1.5, "О", "ТЗ §7, §12.2", "Глубина углубления от тыльной плоскости (дно 1,7)")
GROOVE_CENTER_V = _p("GROOVE_CENTER_V", 5.0, "О/Д", "ТЗ §12.2", "Центр углубления по V от прямой кончиков крылышек")

# --- Лопатка (ТЗ §8, §12.2) ---------------------------------------------------
PADDLE_WIDTH_ROOT = _p("PADDLE_WIDTH_ROOT", 52.0, "И", "ТЗ §8", "Ширина у основания (на линии S)")
PADDLE_WIDTH_TIP = _p("PADDLE_WIDTH_TIP", 40.0, "И/Д", "ТЗ §8, §12.2", "Ширина трапециевидной заготовки у конца до скруглений")
PADDLE_CORNER_RADIUS = _p("PADDLE_CORNER_RADIUS", 10.0, "И/Д", "ТЗ §8", "Радиус двух углов свободного конца в плане")
PADDLE_THICKNESS_ROOT = _p("PADDLE_THICKNESS_ROOT", 6.0, "И", "ТЗ §8", "Толщина у основания (у S) по нормали к P")
PADDLE_THICKNESS_TIP = _p("PADDLE_THICKNESS_TIP", 3.0, "Д", "ТЗ §8, §12.2", "Толщина свободного торца")
PADDLE_EDGE_FILLET = _p("PADDLE_EDGE_FILLET", 1.4, "Д", "ТЗ §12.2 (R1,5 → 1,4)",
                        "Скругление кромок лопатки по толщине; 1,4 вместо 1,5 — при торце 3,0 R1,5×2 вырождает торец")
PADDLE_S_V = _p("PADDLE_S_V", 3.5, "О", "IMG_4396, IMG_4391",
                "Положение S: расстояние вдоль F от прямой V=0 до линии выхода верхней грани лопатки из лицевой плоскости фланца")
PADDLE_ROOT_FILLET = _p("PADDLE_ROOT_FILLET", 1.0, "Д", "—", "Галтель примыкания лопатки к лицевой плоскости фланца")
PADDLE_EMBED_DEPTH = _p("PADDLE_EMBED_DEPTH", 1.2, "Д (техн.)", "—", "Заглубление корня лопатки в пластину для надёжного объединения")

# --- Зуб-защёлка (ТЗ §9, §12.3) ------------------------------------------------
TOOTH_WIDTH = _p("TOOTH_WIDTH", 17.5, "И", "ТЗ §9", "Полная ширина зуба по X, симметрично B")
TOOTH_LENGTH = _p("TOOTH_LENGTH", 10.0, "И", "ТЗ §9, §12.3",
                  "Вылет вдоль направления зуба от тыльной плоскости фланца (линия корня прямой грани) до конца")
TOOTH_THICKNESS_ROOT = _p("TOOTH_THICKNESS_ROOT", 5.2, "И/Д", "ТЗ §9, §12.3", "Максимальная толщина у корня по нормали к P")
TOOTH_THICKNESS_TIP = _p("TOOTH_THICKNESS_TIP", 2.0, "И", "ТЗ §9", "Толщина свободного конца")
TOOTH_FLAT_FACE = _p("TOOTH_FLAT_FACE", "top", "Д", "ТЗ §12.3 п.2, IMG_4391",
                     "Какая продольная грань прямая и параллельна P: 'top' (к +Z) или 'bottom'; противоположная — скос")
TOOTH_ROOT_EDGE_OFFSET = _p("TOOTH_ROOT_EDGE_OFFSET", 0.5, "Д", "ТЗ §12.3 п.1",
                            "Отступ вдоль F от выпуклой кромки (X=0) до ближайшей границы корня зуба")
TOOTH_ROOT_FILLET = _p("TOOTH_ROOT_FILLET", 1.0, "Д", "ТЗ §12.3 п.5", "Корневая галтель у прямой грани (вне зоны контакта)")
TOOTH_TIP_FILLET = _p("TOOTH_TIP_FILLET", 0.3, "Д", "ТЗ §9, §12.3 п.5", "Притупление кромок свободного конца")
TOOTH_EMBED_DEPTH = _p("TOOTH_EMBED_DEPTH", 1.0, "Д (техн.)", "—", "Заглубление тела зуба в пластину для объединения")
TOOTH_SOLID = _p("TOOTH_SOLID", True, "Д", "ТЗ §9, §12.3 п.4", "Сплошной зуб; две полости оригинала не воспроизводятся")
# Удерживающая ступенька: форма и положение не измерены ('?'). Механизм оставлен
# параметрическим; значения ниже — заглушки только для проверки механизма.
TOOTH_STEP_ENABLED = _p("TOOTH_STEP_ENABLED", False, "?", "ТЗ §9, §12.3 п.3",
                        "Включить удерживающую ступеньку на прямой грани (по умолчанию выключено)")
TOOTH_STEP_FROM_ROOT = _p("TOOTH_STEP_FROM_ROOT", 6.0, "?", "заглушка", "Положение стенки ступеньки от линии корня вдоль зуба")
TOOTH_STEP_DEPTH = _p("TOOTH_STEP_DEPTH", 0.8, "?", "заглушка", "Глубина ступеньки от прямой грани")
TOOTH_STEP_WALL_DEG = _p("TOOTH_STEP_WALL_DEG", 90.0, "?", "заглушка", "Угол стенки ступеньки к P (90 — перпендикулярно)")

# --- Экспорт ---------------------------------------------------------------------
STL_TOLERANCE = _p("STL_TOLERANCE", 0.01, "Д", "—", "Линейный допуск триангуляции STL, мм")
STL_ANGULAR_TOLERANCE = _p("STL_ANGULAR_TOLERANCE", 0.1, "Д", "—", "Угловой допуск триангуляции STL, рад")


# --- Производные величины, не зависящие от построения (Р) ------------------------
def derived(c=None) -> dict[str, float]:
    """Расчётные величины. c — конфигурация model.config() с учётом переопределений; None — значения модуля."""
    g = c if c is not None else SimpleNamespace(**{name: prm.value for name, prm in PARAMS.items()})
    if g.LUG_HOLE_CENTER_Z_FIXED is None:
        hole_z = g.H3_LUG - (g.LUG_TOP_TO_HOLE_EDGE + g.LUG_HOLE_D / 2.0)
    else:
        hole_z = float(g.LUG_HOLE_CENTER_Z_FIXED)
    top_radius = g.H3_LUG - hole_z
    bridge = top_radius - g.LUG_HOLE_D / 2.0
    if bridge <= 0 or hole_z - g.LUG_HOLE_D / 2.0 <= 0:
        raise ValueError(f"hole Ø{g.LUG_HOLE_D} at Z={hole_z:.3f} does not fit between A and the lug top")
    lug_inner_x = g.LUG_INNER_GAP / 2.0
    pad_front_y = -g.LUG_HOLE_FROM_FRONT_END
    return {
        "LUG_HOLE_Z": hole_z,
        "LUG_TOP_RADIUS": top_radius,
        "LUG_BRIDGE": bridge,
        "LUG_INNER_X": lug_inner_x,
        "LUG_OUTER_X": lug_inner_x + g.LUG_THICKNESS,
        "LUG_MID_X": lug_inner_x + g.LUG_THICKNESS / 2.0,
        "LUG_OUTER_SPAN": g.LUG_INNER_GAP + 2.0 * g.LUG_THICKNESS,
        "LUG_HOLE_BOTTOM_Z": hole_z - g.LUG_HOLE_D / 2.0,
        "PAD_FRONT_Y": pad_front_y,
        "PAD_BACK_Y": pad_front_y + g.PAD_LENGTH,
        "HORN_CENTER_X": g.HORN_PITCH / 2.0,
        "Z_TARGET_MIN": g.H3_LUG - g.H1_OVERALL,
        "PAD_MARGIN_BEYOND_LUGS": (g.PAD_WIDTH_HORN_END - (g.LUG_INNER_GAP + 2.0 * g.LUG_THICKNESS)) / 2.0,
    }


def flange_contour() -> tuple[tuple[float, float], ...]:
    if FLANGE_CONTOUR_SOURCE == "spec":
        return FLANGE_CONTOUR_SPEC
    if FLANGE_CONTOUR_SOURCE == "v01":
        return FLANGE_CONTOUR_V01
    raise ValueError(f"FLANGE_CONTOUR_SOURCE must be 'v01' or 'spec', got {FLANGE_CONTOUR_SOURCE!r}")


def unit(angle_deg: float) -> tuple[float, float]:
    """Единичный вектор (Y, Z) по углу, отсчитанному от +Y против часовой стрелки (к +Z)."""
    a = math.radians(angle_deg)
    return (math.cos(a), math.sin(a))

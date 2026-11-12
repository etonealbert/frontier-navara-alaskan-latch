"""Editable V01 nominal dimensions, mm/degrees; source spec revision 2.
У owner; И inherited; О estimate; Д assumption; Р derived; ? unknown.
No fit compensation is applied. Unknown retaining ledge is disabled by default.
"""
from dataclasses import dataclass, field, fields


def dim(value, status, source):
    return field(default=value, metadata={"status": status, "source": source})


@dataclass(frozen=True)
class Parameters:
    h1: float = dim(33.5, 'У', '§3 crown to lowest flange surface along H=Z')
    h2: float = dim(16.5, 'У', '§3 flange extent along F')
    h3: float = dim(11.3, 'У', '§3 ear crown above A')
    paddle_length: float = dim(30.0, 'У/Д', '§3 S to free end along P')
    alpha: float = dim(110.0, 'О', '§10 paddle forward ray to flange upward ray')
    beta: float = dim(110.0, 'О', '§10 platform horn ray to descending neck ray')
    delta: float = dim(0.0, 'Д', '§12 signed A/P angle')
    gamma: float = dim(0.0, 'У/Д', '§12 tooth straight face relative to P')
    ear_thickness: float = dim(3.0, 'И', '§4 along X')
    ear_gap: float = dim(21.8, 'И', '§4 clear planar gap')
    hole_diameter: float = dim(2.5, 'И', '§4 true coaxial through bores')
    crown_hole_land: float = dim(2.9, 'И', '§4 crown to upper bore edge')
    ear_crown_radius: float = dim(4.15, 'Д', '§12 concentric crown approximation')
    hole_chamfer: float = dim(0.2, 'Д', '§12 45 degree bore chamfer')
    ear_root_radius: float = dim(0.5, 'Д', '§12 OUTSIDE roots only to preserve clear gap')
    platform_length: float = dim(10.5, 'И/Д', '§5; ear bases flush at both ends')
    platform_horn_width: float = dim(30.8, 'И', '§5 horn-side width')
    platform_neck_width: float = dim(32.68, 'И', '§5 neck-side width')
    platform_thickness: float = dim(2.5, 'И', '§5 below A')
    horn_spacing: float = dim(18.0, 'И', '§5 center to center along X')
    horn_length: float = dim(2.0, 'И/Д', '§12 extends beyond platform in +Y')
    horn_width: float = dim(2.2, 'О', '§12')
    horn_radius: float = dim(0.4, 'Д', '§12 open edges')
    neck_width: float = dim(34.0, 'И', '§6 at flange')
    neck_thickness: float = dim(3.0, 'И', '§6 normal to neck')
    neck_reference_length: float = dim(5.1, 'И/Д', '§10 reference only; solve actual length from H1')
    rib_thickness: float = dim(2.0, 'О', '§6 three ribs')
    rib_leg: float = dim(4.5, 'О', '§6 side-profile legs, not perpendicular')
    rib_radius: float = dim(0.5, 'Д', '§12 rib roots')
    flange_width: float = dim(70.0, 'И', '§7 finished tip-to-tip extent')
    flange_thickness: float = dim(3.2, 'И', '§7 along rear normal N')
    flange_junction_width: float = dim(36.0, 'И/Д', '§12 central transition at V=0')
    flange_edge_radius: float = dim(0.5, 'Д', '§12 perimeter front/rear rounds')
    wing_radius: float = dim(1.0, 'Д', '§12 planar tip rounds')
    groove_length: float = dim(48.0, 'О', '§12 capsule overall length')
    groove_width: float = dim(2.5, 'О', '§12 capsule width')
    groove_depth: float = dim(1.5, 'О', '§12 from rear surface along N')
    groove_v: float = dim(5.0, 'Д', '§12 center from wing-tip baseline')
    paddle_root_width: float = dim(52.0, 'И', '§8 at S')
    paddle_end_width: float = dim(40.0, 'И/Д', '§12 unrounded trapezoid width')
    paddle_corner_radius: float = dim(10.0, 'И/Д', '§12 two plan-view end corners')
    paddle_root_thickness: float = dim(6.0, 'И', '§8 local root envelope')
    paddle_end_thickness: float = dim(3.0, 'Д', '§12 free-end envelope')
    paddle_end_radius: float = dim(1.5, 'Д', '§12 rounded free-end side profile')
    paddle_s_v: float = dim(4.0, 'Д', 'Photo side view: S on FRONT flange surface at V=4')
    tooth_width: float = dim(17.5, 'И', '§9')
    tooth_length: float = dim(10.0, 'И/Д', '§12 from rear root lower datum to end')
    tooth_root_thickness: float = dim(5.2, 'И/Д', '§12 maximum envelope')
    tooth_end_thickness: float = dim(2.0, 'И', '§12 pre-rounding end envelope')
    tooth_edge_offset: float = dim(0.5, 'Д', '§12 lower root boundary setback along F')
    tooth_root_radius: float = dim(1.0, 'Д', '§12 lateral noncontact root blends')
    tooth_tip_radius: float = dim(0.3, 'Д', '§12 free-end rounds')
    retaining_face_from_root: float | None = dim(None, '?', '§9 unknown; no retaining ledge in V01')
    retaining_ledge_depth: float = dim(0.0, '?/Д', 'Disabled. Set only after mating-part measurement')
    retaining_face_angle: float = dim(90.0, '?/Д', 'Editing default only; unused when ledge disabled')
    fusion_overlap: float = dim(0.3, 'Д', 'CAD overlap inside mating material; no external fit allowance')
    stl_linear_tolerance: float = dim(0.01, 'Д', 'Export chordal deflection mm')
    stl_angular_tolerance: float = dim(0.1, 'Д', 'Export angular deflection radians')

    @property
    def hole_z(self):
        return self.h3 - self.crown_hole_land - self.hole_diameter / 2

    @property
    def ear_center_x(self):
        return (self.ear_gap + self.ear_thickness) / 2

    def table(self):
        return [{"name": f.name, "value": getattr(self, f.name), **f.metadata} for f in fields(self)]

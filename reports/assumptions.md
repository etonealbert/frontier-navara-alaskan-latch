# V01 reconstruction assumptions and provenance

This is a full preliminary fit prototype, made under the approximations explicitly allowed in §12 of the supplied specification. It is not a metrological copy or a verified functional replacement.

## Sources

The entire revision-2 specification and all 12 photo-atlas pages were reviewed. Only the two supplied files were available; separate original JPEG files were not present. The actual input names omit `(1)`, unlike stale references in the project instructions. The recorded SHA256 hashes match, and neither input was edited.

Status legend: **У** owner nominal; **И** inherited source dimension; **О** estimate; **Д** construction assumption; **Р** calculated; **?** unknown. Retaining a number to two decimals does not imply that its measurement accuracy is 0.01 mm.

## Feature map

| Feature | Placement / construction | Source / status | Purpose and unresolved risk |
|---|---|---|---|
| Two ears | Inner faces X=±10.9, outer X=±13.9; A Z=0; C Z=7.15 | §4, §12; У/И/Д/Р | Pivot fit; Ø2.5 and actual shaft still need physical checking |
| Crown and roots | Concentric R4.15 arc with tangent straight flanks to the 10.5 base; exterior R0.5 only | §12; Д | Preserves height and seating gap; exact molded contour unknown |
| Platform and horns | A top; thickness below A; narrower end and two horns toward +Y | §5, §12; И/О/Д | Stops/clearance; horn rounding R0.4 is assumed |
| Neck | Starts at center of platform's neck-side thickness; separate beta parameter | §6, §10; И/О/Д/Р | Exact thickness retained; effective length solved from finished H1 |
| Three ribs | One at B, two at transition sides, true fused triangles and R0.5 underside root rounds | §6, §12; О/Д | Reinforcement; exact section and strength not known |
| Flange | Curved symmetric plate, V toward convex edge, N rearward; no spatial bow | §7, §12.1; У/И/О/Д | 70 × 16.5 × 3.2; silhouette approximate |
| Central shoulders | R1 concave transitions from neck width 34 to the 36 mm central joining region | §12.1; И/Д | Makes an explicit joining region rather than inventing a trapezoid's short side |
| Rear groove | Capsule centered at V=5, 48 × 2.5 × 1.5, 1.7 residual flange wall | §7, §12; О/Д | Represents the visible elongated recess; molded framing not reproduced |
| Paddle | S on front flange plane at V=4; -Y projection; 52→40 trapezoid blank, R10 end corners | §8, §12; У/И/Д | Finger lever; S placement is a documented interpretation |
| Paddle section | Flat top reference P; smooth cubic lower taper 6→3; R1.5 semicircular free end | §12; И/Д | No invented deep finger cavity; extreme tangent tip is rounded |
| Tooth | Rear lower-root reference 0.5 from convex edge along F; +Y projection; upper face straight | §9, §12.3; И/Д | The missing retaining face is unknown and intentionally disabled |
| Tooth reinforcement | Two analytic R1 lateral strips, terminating inside the root height span | §12.3; Д | Outside the straight contact face; local root transition clearance must be checked |

## Coordinate and dimension decisions

- X follows the pivot axis. A is Z=0; B is X=0; H is Z. Horns project +Y, paddle -Y, tooth +Y.
- F points down and toward the paddle. N points to the rear. Alpha is measured between P toward the free end and -F toward the ears. Beta is measured between +Y toward the horns and the descending neck. Both are 110°; they are stored separately.
- P and A have separate definitions, with delta=0° for V01. Tooth gamma=0° preserves its main straight upper face parallel to P. A local wedge taper does not turn it into a hook.
- S is the upper paddle departure line on the nominal front flange surface, at V=4.0. Its precise original molded location is not measured. L1 extends from S to the outermost rounded tip. The tiny buried construction overlap is excluded from L1.
- H1 uses actual external support planes after the flange edge rounds. H2 is measured in local V along F, not by world-Z projection. H3 is from A; the paddle is excluded from H1.
- The 3 mm ear walls are planar in the seating region. R0.5 root fillets are on the outside only; there is no fillet encroachment into the 21.8 mm interior gap.

## Flange silhouette and blends

The §12.1 stations (0,16.5), (±9,16.2), (±18,13.8), (±26,8.5), (±35,0) define a starting silhouette. Piecewise cubic Bezier segments interpolate their nominal V values, with a horizontal center tangent and monotonically descending slopes. Adjacent segments share tangents. This preserves a smooth convex silhouette without imposing a fictitious global R27.

R1 tip rounding would reduce the finished width. The upstream X station coordinates are therefore scaled by **1.03930631**, solved numerically before rounding so that the finished width remains exactly 70. The intermediate stations are estimates and are allowed to move; H2 remains exactly 16.5. R0.5 thickness-edge rounds preserve the middle-wall width and V extent. No extra spatial bending is introduced.

The neck has actual centerline length **5.362068 mm**, rather than treating the old 5.1 estimate as an independent constraint. Its thickness remains 3 normal to its own plane. The platform-thickness midpoint is the chosen start datum; small internal overlaps prevent zero-thickness Boolean joints.

## Tooth: limitations that must accompany the files

The tooth is a **solid straight wedge**, not a validated copy of the damaged molded catch. No two internal cavities, retaining step, or damaged rim were inferred from shadows. The full nominal body width is 17.5; its length is 10 from the agreed lower rear-root datum. The upper face stays straight; thickness tapers from the 5.2 root envelope to the 2.0 end envelope. R0.3 tip rounds mean the outermost tangent end has less than the pre-round 2.0 thickness.

The R1 flange-side root fillets extend beyond the constant-width tooth body, making the local transition up to **19.5 mm** wide. This is the assumed reinforcement transition, not a change to the 17.5 mm free tooth body. It needs a clearance check. Continuous full-edge R1 filleting failed in OpenCascade near the 0.5 mm edge setback; the delivered geometry uses explicit circular-section lateral strips terminated 1 mm inside the root-height limits. No requested fillet failure was silently ignored.

Lower root datum: (X,Y,Z)=(0.000, -11.053, -21.871) mm. Upper root datum: (0.000, -9.160, -16.671) mm. Their midpoint is Y=-10.106, Z=-19.271, or **26.421 mm below C**. These are CAD results (Р), not recovered measurements.

The photo-based estimate (~26 mm below C and 5–6 mm toward the paddle) is used only as a rough orientation check, not an extra constraint. The root-height midpoint is consistent with the approximate 26 mm drop. Its computed Y position lies about 4.6 mm farther toward the paddle than the rough 5.5 mm photo estimate. The owner-defined dimension chain was preserved instead of shifting geometry to match a perspective estimate. This placement, especially the tooth's eventual retaining face, must be checked against the mating part.

`retaining_face_from_root=None` and `retaining_ledge_depth=0` suppress the unknown ledge. The source includes an explicit optional parameterized relief face for measured future revisions; its inactive 90° editing default is not a claimed original angle.

## Omitted features and scope

Microscopic texture, lettering, molding witnesses, damage, unmeasured cavities and a deep paddle recess are omitted per the allowed V01 assumptions. No material, shrink compensation, printer orientation, G-code, load qualification, hot-cabin qualification or fatigue validation is supplied.

## Editable parameter ledger

| Parameter | V01 value | Status | Origin / interpretation |
|---|---:|---|---|
| `h1` | 33.5 | У | §3 crown to lowest flange surface along H=Z |
| `h2` | 16.5 | У | §3 flange extent along F |
| `h3` | 11.3 | У | §3 ear crown above A |
| `paddle_length` | 30.0 | У/Д | §3 S to free end along P |
| `alpha` | 110.0 | О | §10 paddle forward ray to flange upward ray |
| `beta` | 110.0 | О | §10 platform horn ray to descending neck ray |
| `delta` | 0.0 | Д | §12 signed A/P angle |
| `gamma` | 0.0 | У/Д | §12 tooth straight face relative to P |
| `ear_thickness` | 3.0 | И | §4 along X |
| `ear_gap` | 21.8 | И | §4 clear planar gap |
| `hole_diameter` | 2.5 | И | §4 true coaxial through bores |
| `crown_hole_land` | 2.9 | И | §4 crown to upper bore edge |
| `ear_crown_radius` | 4.15 | Д | §12 concentric crown approximation |
| `hole_chamfer` | 0.2 | Д | §12 45 degree bore chamfer |
| `ear_root_radius` | 0.5 | Д | §12 OUTSIDE roots only to preserve clear gap |
| `platform_length` | 10.5 | И/Д | §5; ear bases flush at both ends |
| `platform_horn_width` | 30.8 | И | §5 horn-side width |
| `platform_neck_width` | 32.68 | И | §5 neck-side width |
| `platform_thickness` | 2.5 | И | §5 below A |
| `horn_spacing` | 18.0 | И | §5 center to center along X |
| `horn_length` | 2.0 | И/Д | §12 extends beyond platform in +Y |
| `horn_width` | 2.2 | О | §12 |
| `horn_radius` | 0.4 | Д | §12 open edges |
| `neck_width` | 34.0 | И | §6 at flange |
| `neck_thickness` | 3.0 | И | §6 normal to neck |
| `neck_reference_length` | 5.1 | И/Д | §10 reference only; solve actual length from H1 |
| `rib_thickness` | 2.0 | О | §6 three ribs |
| `rib_leg` | 4.5 | О | §6 side-profile legs, not perpendicular |
| `rib_radius` | 0.5 | Д | §12 rib roots |
| `flange_width` | 70.0 | И | §7 finished tip-to-tip extent |
| `flange_thickness` | 3.2 | И | §7 along rear normal N |
| `flange_junction_width` | 36.0 | И/Д | §12 central transition at V=0 |
| `flange_edge_radius` | 0.5 | Д | §12 perimeter front/rear rounds |
| `wing_radius` | 1.0 | Д | §12 planar tip rounds |
| `groove_length` | 48.0 | О | §12 capsule overall length |
| `groove_width` | 2.5 | О | §12 capsule width |
| `groove_depth` | 1.5 | О | §12 from rear surface along N |
| `groove_v` | 5.0 | Д | §12 center from wing-tip baseline |
| `paddle_root_width` | 52.0 | И | §8 at S |
| `paddle_end_width` | 40.0 | И/Д | §12 unrounded trapezoid width |
| `paddle_corner_radius` | 10.0 | И/Д | §12 two plan-view end corners |
| `paddle_root_thickness` | 6.0 | И | §8 local root envelope |
| `paddle_end_thickness` | 3.0 | Д | §12 free-end envelope |
| `paddle_end_radius` | 1.5 | Д | §12 rounded free-end side profile |
| `paddle_s_v` | 4.0 | Д | Photo side view: S on FRONT flange surface at V=4 |
| `tooth_width` | 17.5 | И | §9 |
| `tooth_length` | 10.0 | И/Д | §12 from rear root lower datum to end |
| `tooth_root_thickness` | 5.2 | И/Д | §12 maximum envelope |
| `tooth_end_thickness` | 2.0 | И | §12 pre-rounding end envelope |
| `tooth_edge_offset` | 0.5 | Д | §12 lower root boundary setback along F |
| `tooth_root_radius` | 1.0 | Д | §12 lateral noncontact root blends |
| `tooth_tip_radius` | 0.3 | Д | §12 free-end rounds |
| `retaining_face_from_root` | None | ? | §9 unknown; no retaining ledge in V01 |
| `retaining_ledge_depth` | 0.0 | ?/Д | Disabled. Set only after mating-part measurement |
| `retaining_face_angle` | 90.0 | ?/Д | Editing default only; unused when ledge disabled |
| `fusion_overlap` | 0.3 | Д | CAD overlap inside mating material; no external fit allowance |
| `stl_linear_tolerance` | 0.01 | Д | Export chordal deflection mm |
| `stl_angular_tolerance` | 0.1 | Д | Export angular deflection radians |

Derived (Р): C height 7.15; ear midplanes ±12.4; outer ear span 27.8; retained flange web 1.7; solved neck length above. See validation.json for full datum vectors.

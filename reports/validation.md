# V01 geometric validation

**PASS: nominal geometry and export checks. Physical fit remains UNVERIFIED.**

| Check | Measured | Expected | Tolerance | Result | Method |
|---|---:|---:|---:|---|---|
| CAD valid | True | true | - | PASS | OpenCascade BRepCheck through build123d is_valid |
| Connected CAD solids | 1 | 1.0 | 0 | PASS | CAD boundary measurement |
| Positive CAD volume | True | true | - | PASS | OpenCascade mass properties |
| H1 crown to flange along Z | 33.5 | 33.5 | 1e-05 | PASS | CAD boundary measurement |
| H2 flange extent along F | 16.5 | 16.5 | 1e-05 | PASS | CAD boundary measurement |
| H3 crown above A | 11.3 | 11.3 | 1e-05 | PASS | CAD boundary measurement |
| L1 S to free end along P | 30 | 30.0 | 1e-05 | PASS | CAD boundary measurement |
| Flange width | 70 | 70.0 | 1e-05 | PASS | CAD boundary measurement |
| Flange normal thickness | 3.2000002 | 3.2 | 1e-05 | PASS | CAD boundary measurement |
| Ear spans on final body | 2 | 2.0 | 0 | PASS | CAD line-solid intersection Y=0 Z=5 |
| Clear ear gap | 21.8 | 21.8 | 1e-05 | PASS | Final body line intersection, not center spacing |
| Ear 1 thickness | 3 | 3.0 | 1e-05 | PASS | CAD boundary measurement |
| Ear 2 thickness | 3 | 3.0 | 1e-05 | PASS | CAD boundary measurement |
| True cylindrical bore faces | 2 | 2.0 | 0 | PASS | CAD boundary measurement |
| Bore 1 diameter | 2.5 | 2.5 | 1e-05 | PASS | CAD boundary measurement |
| Bore 1 axis Y | 0 | 0.0 | 1e-05 | PASS | CAD boundary measurement |
| Bore 1 axis Z | 7.15 | 7.15 | 1e-05 | PASS | CAD boundary measurement |
| Bore 2 diameter | 2.5 | 2.5 | 1e-05 | PASS | CAD boundary measurement |
| Bore 2 axis Y | 0 | 0.0 | 1e-05 | PASS | CAD boundary measurement |
| Bore 2 axis Z | 7.15 | 7.15 | 1e-05 | PASS | CAD boundary measurement |
| Pivot axis passes unobstructed | True | true | - | PASS | Final CAD intersection with full common bore axis is empty |
| Alpha oriented rays | 110 | 110.0 | 1e-05 | PASS | P toward free end vs -F toward ears |
| Beta oriented rays | 110 | 110.0 | 1e-05 | PASS | +Y toward horns vs descending neck |
| Tooth parallel to paddle | 0 | 0.0 | 1e-05 | PASS | Opposite projecting directions; straight longitudinal upper face |
| A/P angle | 0 | 0.0 | 1e-05 | PASS | CAD boundary measurement |
| Groove residual flange wall | 1.7 | 1.7000000000000002 | 1e-05 | PASS | CAD boundary measurement |
| Groove width | 2.5 | 2.5 | 1e-05 | PASS | CAD boundary measurement |
| Groove overall length | 48 | 48.0 | 1e-05 | PASS | CAD boundary measurement |
| Tooth nominal body width | 17.5 | 17.5 | 1e-05 | PASS | CAD boundary measurement |
| Tooth projection from root datum | 10 | 10.0 | 1e-05 | PASS | CAD boundary measurement |
| Tooth maximum thickness | 5.2 | 5.2 | 1e-05 | PASS | CAD boundary measurement |
| Unmeasured retaining ledge absent | True | true | - | PASS | Default configuration; no guessed catch step |
| Rib count | 3 | 3.0 | 0 | PASS | CAD boundary measurement |
| Each rib adds joined material | True | true | - | PASS | Per-feature fuse validation; positive stage volume increments recorded |
| Symmetry difference volume mm3 | 0 | 0.0 | 0.001 | PASS | Symmetric-difference BREP volume against B-plane mirror |
| STEP round-trip valid | True | true | - | PASS | Reimport exported STEP with OpenCascade |
| Exported BREP has no self-interference | True | true | - | PASS | BOPAlgo_CheckerSI level 5 on reimported STEP: completed without errors or interference pairs |
| STEP symmetric-difference volume mm3 | 0 | 0.0 | 0.001 | PASS | Two BREP Boolean differences: source minus STEP and STEP minus source |
| STEP solid count | 1 | 1.0 | 0 | PASS | CAD boundary measurement |
| STEP volume difference mm3 | 1.4347424e-06 | 0.0 | 0.001 | PASS | CAD boundary measurement |
| STEP bounds max error mm | 1.0000026e-07 | 0.0 | 0.0001 | PASS | CAD boundary measurement |
| STL watertight | True | true | - | PASS | trimesh edge incidence after duplicate vertex indexing; no hole filling |
| STL winding consistent | True | true | - | PASS | trimesh shared-edge winding |
| STL connected components | 1 | 1.0 | 0 | PASS | CAD boundary measurement |
| STL Euler characteristic | -2 | -2.0 | 0 | PASS | One closed shell with two pivot through-bores (genus 2) |
| STL degenerate triangles | 0 | 0.0 | 0 | PASS | CAD boundary measurement |
| STL positive volume | True | true | - | PASS | Signed triangle volume |
| STL/CAD relative volume error | 0.0007704765 | 0.0 | 0.0015 | PASS | CAD boundary measurement |
| STL/CAD bounding error mm | 0.0012958527 | 0.0 | 0.02 | PASS | CAD boundary measurement |
| Input unchanged: cad-latch-spec.md | True | true | - | PASS | SHA256 vs INPUT_SHA256.md |
| Input unchanged: cad-photo-atlas.pdf | True | true | - | PASS | SHA256 vs INPUT_SHA256.md |

Raw in-memory self-interference diagnostic: {'errors': 'BOPAlgo_AlertIntersectionFailed', 'pairs': 0}. An algorithm error is inconclusive. The delivered STEP is independently checked and must complete without errors; source/STEP geometry equivalence is checked above.

CAD volume: 10938.688065 mm³. Global XYZ extents: 70.000000, 47.205524, 33.500000 mm.
STEP: 755,116 bytes. STL: 65,934 triangles, 32,965 indexed vertices, 3,296,784 bytes.
STL volume: 10930.260063 mm³. Tessellation deflection 0.01 mm / 0.1 radians.

## Datum interpretation

A: platform top Z=0. B: X=0. C: (0,0,7.15), parallel X. H: Z. Horns point +Y; paddle points -Y; tooth points +Y.
S: intersection of the paddle upper plane with the nominal front flange plane at V=4.0. L1 is the maximum projection from S to the rounded free end, not the buried fusion overlap.
Neck reference centerline begins at platform edge Y=-5.25, Z=-1.25. Its solved length is **5.362068 mm**, versus the non-binding source estimate 5.1 mm.
H1 is solved after the flange rounds, using its actual lowest external surface. H2 is measured after transforming that flange back to (X,V,N).
Ear gap/thickness are measured on the final solid at Y=0, Z=5, away from bore chamfers and exterior root fillets.
Tooth tip thickness 2.0 and paddle tip thickness 3.0 denote pre-round envelopes; the extreme tangent end is rounded. The 0.3 mm buried overlap is a Boolean construction allowance, not print compensation.

## Scope and visual review

All 12 photo-atlas pages were rendered and inspected. Pages 2–3 guide ears/paddle, 4 and 9–11 side orientation and dimension rays, 5–8 ribs/groove/tooth/flange. The two supplied files have their original hashes; their actual filenames omit the stale `(1)` suffix in the instructions.
See `visual_review.md` for final image inspection. No load, thermal, fatigue, slicer/printer or mating-part test was performed. CAD validity and mesh closure do not establish functional engagement.

## Feature construction log

| Stage | Volume mm³ | Connected solids | Valid |
|---|---:|---:|---|
| platform | 833.175000 | 1 | True |
| horn_0 | 843.620404 | 1 | True |
| horn_1 | 854.065808 | 1 | True |
| ear_0 | 1137.873478 | 1 | True |
| ear_1 | 1421.681149 | 1 | True |
| external ear root R0.5 | 1422.804273 | 1 | True |
| coaxial through holes | 1393.351842 | 1 | True |
| bore chamfers | 1392.690013 | 1 | True |
| flange with blind recess | 2568.164113 | 1 | True |
| neck | 1931.440450 | 1 | True |
| flange | 4470.669852 | 1 | True |
| neck to 36 mm shoulder 0 | 4471.628809 | 1 | True |
| neck to 36 mm shoulder 1 | 4472.587765 | 1 | True |
| rib_0 | 4480.883960 | 1 | True |
| rib_1 | 4488.952513 | 1 | True |
| rib_2 | 4497.248708 | 1 | True |
| rib root fillets | 4497.852036 | 1 | True |
| tapered rounded paddle | 10401.979785 | 1 | True |
| straight reconstructed tooth | 10937.171297 | 1 | True |
| analytic tooth lateral R1 blend 0 | 10937.929678 | 1 | True |
| analytic tooth lateral R1 blend 1 | 10938.688065 | 1 | True |
| final solid | 10938.688065 | 1 | True |

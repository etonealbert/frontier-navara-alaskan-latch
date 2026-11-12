# Visual review of the delivered V01

All 12 pages of `input/cad-photo-atlas.pdf` were rendered with Poppler and inspected. All four final PNG views and the dimensioned PNG drawing were then opened and inspected after the successful build. The SVG drawing is generated from the same figure as the inspected PNG.

| Reference | Observed relationship | Model review |
|---|---|---|
| Page 2, paddle-side overview | Wide paddle narrows toward rounded end; ears above support; wings beyond paddle root | Present in front isometric; R10 rounded end corners and tapered thickness visible |
| Page 3, ears/platform | Two separate ear walls, coaxial holes, small horns beyond platform | Present; the photographed perspective size difference was not copied |
| Page 4, side view | Paddle left, ears above, flange tilted down-left, tooth projecting right at lower rear | Present in side render; straight tooth upper face parallel to paddle |
| Pages 5–6, underside/rear | Three ribs; long recess; central damaged tooth with two cavities | Three ribs and recess present; tooth is deliberately solid per the permitted reconstruction |
| Page 7, flange silhouette | Symmetric convex crown and wings, central transition; no global constant-radius arc | Present in rear render and flange drawing; intermediate spline stations adjusted for finished tip width |
| Page 8, tooth-side overview | Tooth near convex flange edge; paddle behind flange; rounded outer silhouette | Same topology; missing ledge and cavities remain unclaimed |
| Pages 9–10, marked 33.5/16.5 | H1 external height excludes paddle; H2 along inclined flange | Correct bases in drawing and numerical measurements |
| Page 11 and page 12 angle explanation | Paddle-to-upward-flange and horns-to-downward-neck rays both obtuse | Correct sign; numerical vector angles both 110° |

The side, rear and front views show one complete part with no visibly floating components. The drawing includes a real central CAD section, near-ear profile drawn dashed, local flange view, ear profile, H1/H2/H3/L1, solved neck length, tooth position relative to C and an assumptions table. Titles, dimensions and notes are legible with no clipped labels or overlapping table text.

The source photographs are perspective views and not orthographic calibration data. No pixel-perfect overlay or dimensional accuracy beyond the specified nominals is claimed. In particular, tooth-root Y differs from the rough photo position estimate as documented in `assumptions.md`. Cosmetic texture, molding witness marks and damage are absent intentionally.

Images use a deterministic orthographic software z-buffer with mesh-surface shading, generated from the same validated STL. The initial centroid-sorted preview showed false triangular occlusion artifacts; these were corrected in the renderer before delivery. Final views contain no such artifacts.

Functional fit, contact face position and strength remain unverified.

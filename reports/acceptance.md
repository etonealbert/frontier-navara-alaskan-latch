# Acceptance checklist disposition

Completed against `ACCEPTANCE_CHECKLIST.md`. PASS means the preliminary geometric deliverable is complete; it does not imply working engagement.

- [x] Entire specification read; all 12 photo-atlas pages visually inspected. Sources retain the manifest SHA256 hashes.
- [x] Source-status tags retained in `src/params.py` and `assumptions.md`.
- [x] Complete feature set: two ears/bores, two horns, platform, dependent neck, three ribs, curved flange/wings, paddle, rear groove and reconstructed tooth.
- [x] H1/H2/H3/L1 measured from the specified distinct datums; 33.5/16.5/11.3/30.0 mm pass.
- [x] Ø2.5 coaxial bores, 3 mm ear walls and 21.8 clear gap verified on real CAD.
- [x] Finished flange width 70; smooth symmetric contour; no unsupported global R27.
- [x] Both 110° angles use the specified rays and correct sign; tooth remains straight and parallel to P.
- [x] Neck solved from actual rounded flange bounds; length 5.362068 mm is shown on the drawing and in reports.
- [x] Each feature fusion validated; final shape has one connected valid solid and positive volume.
- [x] Delivered STEP reimported: one valid solid; independent self-interference check completes with no pairs. Source/STEP symmetric-difference volume is zero at check tolerance.
- [x] Raw in-memory self-interference checker error disclosed as inconclusive; not misrepresented as a pass. See `validation.md`.
- [x] Delivered STL has one component, closed manifold edge incidence, consistent winding, positive volume and no degenerate triangles. Only eight zero-area raw mesh facets removed, without vertex movement or hole filling.
- [x] Same final CAD used for STEP and STL; bounds, volumes, tessellation settings and file sizes recorded in `validation.json`.
- [x] Working rebuild source, environment record, assumptions, validation, print handoff, four inspection views and dimensioned SVG/PNG drawing delivered.
- [x] Final inspection views compared to the source atlas; limitations recorded in `visual_review.md`.
- [x] Functional tooth engagement, physical fit and strength explicitly remain unverified.

Reproduce the automated evidence with `.venv/bin/python src/build.py`. Fifty-one checks must pass. `reports/validation.md` lists each check's method and result; `reports/validation.json` is the machine-readable record.

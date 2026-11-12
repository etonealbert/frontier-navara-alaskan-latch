# V01 handoff to owner and printer

**Preliminary fit prototype. Engagement, load capacity and vehicle-temperature performance are not verified.**

## Files and scale

- `output/armrest_latch_v01.stl`: closed triangulated print geometry. Import as **millimetres**, scale **100%**. STL itself has no unit metadata.
- `output/armrest_latch_v01.step`: the same solid as CAD exchange, in mm. Prefer this for engineering changes and measurement.
- `output/armrest_latch_v01_drawing.svg` / `.png`: engineering review sheet, with datum definitions. Do not measure a screenshot as a scale template.
- Four rendered views accompany the model. Code and editable nominal dimensions are in `src/`.
- `reports/validation.md` / `.json`: actual geometric checks; `assumptions.md`: provenance and approximations.

The maximum width is 70 mm. H1=33.5 mm runs from the ear crown to the flange bottom; it excludes the paddle. The paddle is 30 mm from S. Neither value should be used alone as the total XYZ bounding box. Read the measured full bounds in the validation report.

## Before producing a functional replacement

1. Select a printer/process, material and profile appropriate to the actual cabin temperature, required load, wear and repeated cycling. None was supplied, so no material-specific shrinkage, extrusion settings, strength claim or G-code is included.
2. Select orientation and support placement in the actual slicer, examining layer direction at the tooth root and the two ears. Keep support damage away from the pivot bores and eventual contact face. The supplied CAD orientation is a measurement frame, not an approved build orientation.
3. Treat the nominal Ø2.5 holes, 21.8 clear gap and tooth location as first-fit values. Establish the printer's dimensional compensation separately with test features; do not force an undersized hole onto the shaft or force the latch closed.
4. Inspect the printed part for cracks, incomplete layers and support damage before placing it in the mechanism.

## Fit checklist for the first prototype

- Measure both holes and their coaxial alignment; verify free rotation with the actual pivot.
- Check the 21.8 mm inner ear gap and the 3 mm ear thicknesses against the receiving mechanism.
- Check both small horns, the neck, flange wings and paddle through the complete free travel.
- Observe the tooth and mating catch together. Record the required retaining-face position relative to C, face angle, ledge height/depth and release clearance.
- The reconstructed tooth is straight and solid. The two original cavities and damaged retaining step were deliberately not guessed. Its stiffness and strength can differ from the original part.
- The nominal tooth body is 17.5 mm wide; the R1 flange-side root reinforcement occupies a wider local transition (up to 19.5 mm). Check clearance at that transition.
- Record any interference before revising `src/params.py`. `retaining_face_from_root=None` and `retaining_ledge_depth=0` intentionally disable a catch ledge. Enable it only using measured mating-part geometry.
- After geometry fits, establish retention/release force, hot-cabin behavior, wear and repeated-cycle performance by appropriate physical tests before treating the part as a working replacement.

## Scope

This is a complete geometric reconstruction for fit evaluation, not an exact metrological copy, a strength-qualified part, or a guarantee that the lid will remain latched. The original damaged tooth cannot establish the missing contact profile.

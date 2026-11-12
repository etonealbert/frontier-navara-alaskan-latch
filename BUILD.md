# Rebuild the V01 latch

The `codex` branch contains the complete preliminary build123d reconstruction. Generated CAD, mesh and inspection views are in `output/`; evidence and limitations are in `reports/`.

## macOS / Linux

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python src/build.py
```

## Windows

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe src\build.py
```

The build resolves paths relative to the project, so it can also be invoked from another directory. Python 3.12 on macOS arm64 was actually tested; Windows commands are provided for reproducibility, not claimed as tested on this machine. `requirements-lock.txt` records the complete installed environment, including the PDF-inspection dependencies; `requirements.txt` lists the pinned model/runtime requirements.

## Editing

- `src/params.py`: nominal dimensions and У/И/О/Д/Р/? source metadata. The specification's reference neck length is not an independent constraint; the effective length is solved from H1 after flange rounding.
- `src/model.py`: CAD construction, named features, frame transformations and per-stage solid checks. Source geometry is build123d/OpenCascade, not a mesh reconstruction.
- `src/validate.py`: actual boundary, line-intersection, self-interference, symmetry, STEP and STL checks. Fails the build when acceptance fails.
- `src/render.py`: orthographic z-buffer views and a dimensioned CAD-section drawing.
- `src/build.py`: reconstruct, export both formats, validate, render and record environment.

Adjust geometrically related dimensions together. For example, the default circular ear crown must close H3 with the derived hole center; the rounded paddle end uses a radius equal to half its thickness. Grossly incompatible parameter combinations fail explicitly rather than silently dropping features. This is a V01 reconstruction, not a general-purpose configurable latch family.

The drawing and validation regenerate automatically. Manually authored `assumptions.md`, `visual_review.md` and `print_handoff.md` describe the delivered nominal configuration; review and update them after changing dimensions. No holes are filled and no mesh vertices are moved during export: only zero-area tessellation facets at horn-fillet poles are removed, with a recorded count and volume comparison.

The original input files are unchanged. Their actual names are `input/cad-latch-spec.md` and `input/cad-photo-atlas.pdf`, although the original project instructions refer to names with `(1)`. SHA256 checks prove that the supplied contents match the original manifest.

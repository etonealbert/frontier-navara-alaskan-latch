"""One command: .venv/bin/python src/build.py; run from any working directory."""
from pathlib import Path
import platform
import sys
import json
from importlib.metadata import version
import trimesh
from build123d import export_step, export_stl
from params import Parameters
from model import build_model
from validate import validate
from render import render_all

ROOT=Path(__file__).resolve().parents[1]


def main():
    out=ROOT/'output';reports=ROOT/'reports';work=ROOT/'work'
    for folder in (out,reports,work):folder.mkdir(exist_ok=True)
    p=Parameters();model=build_model(p)
    step=out/'armrest_latch_v01.step';stl=out/'armrest_latch_v01.stl'
    assert export_step(model.part,step)
    # Preserve the direct OCC tessellation as diagnostic input, then remove only
    # zero-area collapsed facets at spherical horn fillet poles. No repair,
    # remeshing, hole filling, scaling, smoothing or vertex movement occurs.
    raw=work/'armrest_latch_v01_raw.stl'
    assert export_stl(model.part,raw,tolerance=p.stl_linear_tolerance,angular_tolerance=p.stl_angular_tolerance)
    mesh=trimesh.load_mesh(raw,process=True)
    keep=mesh.nondegenerate_faces(height=1e-8)
    removed=int((~keep).sum());before=mesh.volume
    mesh.update_faces(keep);mesh.remove_unreferenced_vertices()
    assert abs(mesh.volume-before)<1e-6
    mesh.export(stl)
    (reports/'mesh_cleanup.json').write_text(json.dumps(dict(removed_collapsed_facets=removed,vertex_motion_mm=0,
        hole_filling=False,remeshing=False,volume_change_mm3=mesh.volume-before),indent=2)+'\n')
    verified_mesh,data=validate(model,step,stl,ROOT)
    render_all(model,verified_mesh,out)
    env=['# Actual build environment','',f'- OS: {platform.platform()}',f'- Architecture: {platform.machine()}',
         f'- Python: {sys.version.split()[0]}',f'- Interpreter: {sys.executable}',
         f'- build123d: {version("build123d")} (stable PyPI release)',f'- OpenCascade Python package: {version("cadquery-ocp-novtk")}',
         f'- trimesh: {version("trimesh")}',f'- matplotlib: {version("matplotlib")}',
         '- Installation: local `.venv` using Homebrew Python 3.12; no administrator privileges required.',
         '- Host is macOS arm64; the Windows-specific setup directions were adapted to the actual host.',
         '- Full dependency versions: `requirements-lock.txt`. Minimal pinned build requirements: `requirements.txt`.',
         '- Official API references: https://build123d.readthedocs.io/en/latest/installation.html and https://build123d.readthedocs.io/en/latest/introductory_examples.html',
         '- All CAD coordinates and STEP units are mm. STL does not store a unit declaration.',
         f'- Removed {removed} collapsed zero-area tessellation facets; no geometry was moved and no holes were filled. See `mesh_cleanup.json`.']
    (reports/'environment.md').write_text('\n'.join(env)+'\n')
    print(f'PASS: {len(data["checks"])} checks; {len(verified_mesh.faces)} triangles; volume {model.part.volume:.3f} mm3',flush=True)


if __name__=='__main__':main()

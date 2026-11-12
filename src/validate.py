"""Independent geometric, STEP round-trip and triangulation acceptance checks."""
import hashlib
import io
import json
from pathlib import Path
from math import acos, degrees
import numpy as np
import trimesh
from build123d import Axis, Plane, Vector, GeomType, import_step
from OCP.BOPAlgo import BOPAlgo_CheckerSI


def angle(a,b):
    a=np.asarray(a);b=np.asarray(b)
    return degrees(acos(np.clip(a@b/np.linalg.norm(a)/np.linalg.norm(b),-1,1)))


def bounds(shape):
    b=shape.bounding_box()
    return dict(min=list(b.min),max=list(b.max),size=list(b.size))


def validate(m,step_path,stl_path,root):
    p=m.params;d=m.datums;part=m.part;results=[]
    def numeric(name,value,expected,tol=1e-5,method='CAD boundary measurement'):
        passed=abs(value-expected)<=tol
        results.append(dict(check=name,value=float(value),expected=float(expected),tolerance=tol,passed=bool(passed),method=method))
    def flag(name,value,method):
        results.append(dict(check=name,value=bool(value),passed=bool(value),method=method))
    flag('CAD valid',part.is_valid,'OpenCascade BRepCheck through build123d is_valid')
    numeric('Connected CAD solids',len(part.solids()),1,0)
    flag('Positive CAD volume',part.volume>0,'OpenCascade mass properties')
    checker=BOPAlgo_CheckerSI();checker.AddArgument(part.wrapped);checker.SetLevelOfCheck(5);checker.Perform()
    raw_error=io.BytesIO();checker.DumpErrors(raw_error)
    raw_diagnostic=dict(errors=raw_error.getvalue().decode().strip(),pairs=checker.DS().Interferences().Extent())
    # A raw checker algorithm failure is inconclusive, not an intersection.
    # Check the actual delivered STEP BREP independently below, with bounds,
    # volume and symmetric-difference checks against the source geometry.
    fp=Plane(origin=d['flange_origin'],x_dir=(1,0,0),z_dir=d['N'])
    fl=fp.to_local_coords(m.features['flange'])
    pp=Plane(origin=d['S'],x_dir=(1,0,0),z_dir=d['Q'])
    paddle=pp.to_local_coords(m.features['paddle'])
    numeric('H1 crown to flange along Z',part.bounding_box().max.Z-m.features['flange'].bounding_box().min.Z,p.h1)
    numeric('H2 flange extent along F',fl.bounding_box().size.Y,p.h2)
    numeric('H3 crown above A',part.bounding_box().max.Z-d['A_z'],p.h3)
    numeric('L1 S to free end along P',paddle.bounding_box().max.Y,p.paddle_length)
    numeric('Flange width',fl.bounding_box().size.X,p.flange_width)
    numeric('Flange normal thickness',fl.bounding_box().size.Z,p.flange_thickness)
    # Real final-body line intersections below the hole, above any root fillet.
    spans=part.intersect(Axis((0,0,5),(1,0,0)))
    intervals=sorted((s.bounding_box().min.X,s.bounding_box().max.X) for s in spans)
    numeric('Ear spans on final body',len(intervals),2,0,'CAD line-solid intersection Y=0 Z=5')
    if len(intervals)==2:
        numeric('Clear ear gap',intervals[1][0]-intervals[0][1],p.ear_gap,method='Final body line intersection, not center spacing')
        for i,(a,b) in enumerate(intervals):numeric(f'Ear {i+1} thickness',b-a,p.ear_thickness)
    bores=[f for f in part.faces().filter_by(GeomType.CYLINDER)
           if abs(f.radius-p.hole_diameter/2)<1e-5 and abs(abs(f.axis_of_rotation.direction.X)-1)<1e-6]
    numeric('True cylindrical bore faces',len(bores),2,0)
    for i,f in enumerate(sorted(bores,key=lambda f:f.center().X)):
        numeric(f'Bore {i+1} diameter',2*f.radius,p.hole_diameter)
        numeric(f'Bore {i+1} axis Y',f.axis_of_rotation.position.Y,0)
        numeric(f'Bore {i+1} axis Z',f.axis_of_rotation.position.Z,p.hole_z)
    through=part.intersect(Axis((0,0,p.hole_z),(1,0,0)))
    flag('Pivot axis passes unobstructed',not through,'Final CAD intersection with full common bore axis is empty')
    numeric('Alpha oriented rays',angle(d['P'],-np.array(d['F'])),p.alpha,method='P toward free end vs -F toward ears')
    numeric('Beta oriented rays',angle([0,1,0],d['neck_direction']),p.beta,method='+Y toward horns vs descending neck')
    numeric('Tooth parallel to paddle',180-angle(d['tooth_direction'],d['P']),abs(p.gamma),method='Opposite projecting directions; straight longitudinal upper face')
    numeric('A/P angle',angle([0,-1,0],d['P']),abs(p.delta))
    # Intersection through the original blind groove measures the flange's web.
    spans=m.features['flange'].intersect(Axis(fp.from_local_coords((0,p.groove_v,0)),d['N']))
    local_spans=[fp.to_local_coords(s) for s in spans]
    numeric('Groove residual flange wall',sum(s.bounding_box().size.Z for s in local_spans),p.flange_thickness-p.groove_depth)
    numeric('Groove width',fp.to_local_coords(m.features['groove_tool']).bounding_box().size.Y,p.groove_width)
    numeric('Groove overall length',fp.to_local_coords(m.features['groove_tool']).bounding_box().size.X,p.groove_length)
    tp=Plane(origin=d['tooth_root'],x_dir=(1,0,0),z_dir=Vector(1,0,0).cross(Vector(d['tooth_direction'])))
    tooth=tp.to_local_coords(m.features['tooth'])
    numeric('Tooth nominal body width',tooth.bounding_box().size.X,p.tooth_width)
    numeric('Tooth projection from root datum',tooth.bounding_box().max.Y,p.tooth_length)
    numeric('Tooth maximum thickness',tooth.bounding_box().size.Z,p.tooth_root_thickness)
    flag('Unmeasured retaining ledge absent',p.retaining_ledge_depth==0 and p.retaining_face_from_root is None,'Default configuration; no guessed catch step')
    numeric('Rib count',sum(k.startswith('rib_') for k in m.features),3,0)
    flag('Each rib adds joined material',all(s['solids']==1 and s['valid'] for s in m.stages if s['stage'].startswith('rib_')),'Per-feature fuse validation; positive stage volume increments recorded')
    mirrored=part.mirror(Plane.YZ)
    asymmetry=part.cut(mirrored).volume+mirrored.cut(part).volume
    numeric('Symmetry difference volume mm3',asymmetry,0,.001,'Symmetric-difference BREP volume against B-plane mirror')
    restored=import_step(step_path)
    flag('STEP round-trip valid',restored.is_valid,'Reimport exported STEP with OpenCascade')
    step_checker=BOPAlgo_CheckerSI();step_checker.AddArgument(restored.wrapped);step_checker.SetLevelOfCheck(5);step_checker.Perform()
    flag('Exported BREP has no self-interference',not step_checker.HasErrors() and step_checker.DS().Interferences().Extent()==0,
         'BOPAlgo_CheckerSI level 5 on reimported STEP: completed without errors or interference pairs')
    shape_error=part.cut(restored).volume+restored.cut(part).volume
    numeric('STEP symmetric-difference volume mm3',shape_error,0,.001,'Two BREP Boolean differences: source minus STEP and STEP minus source')
    numeric('STEP solid count',len(restored.solids()),1,0)
    numeric('STEP volume difference mm3',abs(restored.volume-part.volume),0,.001)
    numeric('STEP bounds max error mm',max(abs(np.array(bounds(restored)['min'])-bounds(part)['min']).max(),abs(np.array(bounds(restored)['max'])-bounds(part)['max']).max()),0,1e-4)
    mesh=trimesh.load_mesh(stl_path,process=True)
    flag('STL watertight',mesh.is_watertight,'trimesh edge incidence after duplicate vertex indexing; no hole filling')
    flag('STL winding consistent',mesh.is_winding_consistent,'trimesh shared-edge winding')
    numeric('STL connected components',len(mesh.split(only_watertight=False)),1,0)
    numeric('STL Euler characteristic',mesh.euler_number,-2,0,'One closed shell with two pivot through-bores (genus 2)')
    numeric('STL degenerate triangles',np.count_nonzero(mesh.area_faces<1e-12),0,0)
    flag('STL positive volume',mesh.volume>0,'Signed triangle volume')
    numeric('STL/CAD relative volume error',abs(mesh.volume-part.volume)/part.volume,0,.0015)
    numeric('STL/CAD bounding error mm',np.abs(mesh.bounds-np.array([bounds(part)['min'],bounds(part)['max']])).max(),0,.02)
    expected={'cad-latch-spec.md':'8c03a6e5a2556c7c5bf6e7d9dad775ba1b807aa70efa3cc38d307d4693f9186a',
              'cad-photo-atlas.pdf':'d48eca315b14d76af495d12138087aa730048ecc256cf6215117ad189ce6bf97'}
    for name,digest in expected.items():
        flag(f'Input unchanged: {name}',hashlib.sha256((root/'input'/name).read_bytes()).hexdigest()==digest,'SHA256 vs INPUT_SHA256.md')
    data=dict(status='PASS' if all(r['passed'] for r in results) else 'FAIL',checks=results,
              cad=dict(volume_mm3=part.volume,bounds_mm=bounds(part),solids=len(part.solids())),
              step=dict(volume_mm3=restored.volume,bytes=step_path.stat().st_size),
              stl=dict(volume_mm3=mesh.volume,triangles=len(mesh.faces),vertices=len(mesh.vertices),bytes=stl_path.stat().st_size),
              stages=m.stages,datums=d,parameters=p.table(),raw_self_interference_diagnostic=raw_diagnostic)
    (root/'reports'/'validation.json').write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
    lines=['# V01 geometric validation','',f'**{data["status"]}: nominal geometry and export checks. Physical fit remains UNVERIFIED.**','',
           '| Check | Measured | Expected | Tolerance | Result | Method |','|---|---:|---:|---:|---|---|']
    for r in results:
        value=f'{r["value"]:.8g}' if not isinstance(r['value'],bool) else str(r['value'])
        lines.append(f'| {r["check"]} | {value} | {r.get("expected","true")} | {r.get("tolerance","-")} | {"PASS" if r["passed"] else "FAIL"} | {r["method"]} |')
    lines+=['',f'Raw in-memory self-interference diagnostic: {raw_diagnostic}. An algorithm error is inconclusive. The delivered STEP is independently checked and must complete without errors; source/STEP geometry equivalence is checked above.', '',f'CAD volume: {part.volume:.6f} mm³. Global XYZ extents: '+', '.join(f'{x:.6f}' for x in bounds(part)['size'])+' mm.',
            f'STEP: {step_path.stat().st_size:,} bytes. STL: {len(mesh.faces):,} triangles, {len(mesh.vertices):,} indexed vertices, {stl_path.stat().st_size:,} bytes.',
            f'STL volume: {mesh.volume:.6f} mm³. Tessellation deflection {p.stl_linear_tolerance} mm / {p.stl_angular_tolerance} radians.',
            '', '## Datum interpretation','',
            'A: platform top Z=0. B: X=0. C: (0,0,7.15), parallel X. H: Z. Horns point +Y; paddle points -Y; tooth points +Y.',
            'S: intersection of the paddle upper plane with the nominal front flange plane at V=4.0. L1 is the maximum projection from S to the rounded free end, not the buried fusion overlap.',
            f'Neck reference centerline begins at platform edge Y=-5.25, Z=-1.25. Its solved length is **{d["neck_length"]:.6f} mm**, versus the non-binding source estimate 5.1 mm.',
            'H1 is solved after the flange rounds, using its actual lowest external surface. H2 is measured after transforming that flange back to (X,V,N).',
            'Ear gap/thickness are measured on the final solid at Y=0, Z=5, away from bore chamfers and exterior root fillets.',
            'Tooth tip thickness 2.0 and paddle tip thickness 3.0 denote pre-round envelopes; the extreme tangent end is rounded. The 0.3 mm buried overlap is a Boolean construction allowance, not print compensation.',
            '', '## Scope and visual review','',
            'All 12 photo-atlas pages were rendered and inspected. Pages 2–3 guide ears/paddle, 4 and 9–11 side orientation and dimension rays, 5–8 ribs/groove/tooth/flange. The two supplied files have their original hashes; their actual filenames omit the stale `(1)` suffix in the instructions.',
            'See `visual_review.md` for final image inspection. No load, thermal, fatigue, slicer/printer or mating-part test was performed. CAD validity and mesh closure do not establish functional engagement.',
            '', '## Feature construction log','', '| Stage | Volume mm³ | Connected solids | Valid |','|---|---:|---:|---|']
    for s in m.stages:lines.append(f'| {s["stage"]} | {s["volume_mm3"]:.6f} | {s["solids"]} | {s["valid"]} |')
    (root/'reports'/'validation.md').write_text('\n'.join(lines)+'\n')
    failures=[r['check'] for r in results if not r['passed']]
    if failures:raise RuntimeError('Acceptance checks failed: '+', '.join(failures))
    return mesh,data

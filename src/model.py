"""Deterministic build123d solid reconstruction. Run via src/build.py.
Frames: X pivot axis; A Z=0; B X=0; horns +Y; paddle -Y; H=Z.
Flange local (X,V,N), V from wing baseline to convex edge; N points rearward.
"""
from dataclasses import dataclass
from math import sin, cos, radians, sqrt, tan
from build123d import (Vector, Plane, Axis, Edge, Wire, Face, Solid, Part,
                      Box, Pos, SlotOverall, extrude, fillet, chamfer)
from scipy.optimize import brentq
from params import Parameters


def polygon(points):
    return Face(Wire.make_polygon(points))


def prism(points, vector):
    return Solid.extrude(polygon(points), vector)


def rounded_solid(shape, edges, radius, label):
    edges = list(edges)
    if not edges:
        raise RuntimeError(f'{label}: empty edge selection')
    result = fillet(edges, radius)
    if not result.is_valid or len(result.solids()) != 1:
        raise RuntimeError(f'{label}: invalid fillet')
    return result


@dataclass
class Model:
    part: Part
    features: dict
    datums: dict
    stages: list
    params: Parameters


def flange_outline(p):
    # Piecewise cubic Beziers: interpolation at all §12.1 stations; C1 joins.
    # Slopes chosen monotonically decreasing; convex, no wavy interpolating spline.
    stations = [(0,16.5),(9,16.2),(18,13.8),(26,8.5),(35,0)]
    slopes = [0,-0.075,-0.45,-0.85,-1.1]
    def outline(xscale):
        right=[]
        for i in range(4):
            x0,y0=stations[i]; x1,y1=stations[i+1]; dx=x1-x0
            controls=[(x0,y0),(x0+dx/3,y0+slopes[i]*dx/3),
                      (x1-dx/3,y1-slopes[i+1]*dx/3),(x1,y1)]
            right.append(Edge.make_bezier(*[(x*xscale,y*p.h2/16.5,0) for x,y in controls]))
        left=[e.mirror(Plane.YZ) for e in right]
        face=Face(Wire(right+left+[Edge.make_line((-35*xscale,0,0),(35*xscale,0,0))]))
        return face.fillet_2d(p.wing_radius,[v for v in face.vertices() if abs(v.X)>34*xscale])
    # Solve upstream spline width, retaining exact R1 AND finished 70 mm envelope.
    factor=brentq(lambda k:outline(k).bounding_box().size.X-p.flange_width,0.9,1.3,xtol=1e-11)
    return outline(factor),factor


def build_model(p=Parameters()):
    stages=[]; features={}
    def checked(label,shape):
        assert shape.is_valid, f'{label}: invalid BREP'
        assert len(shape.solids())==1, f'{label}: {len(shape.solids())} solids'
        assert shape.volume>0
        stages.append(dict(stage=label,valid=True,solids=1,volume_mm3=shape.volume))
        print(f'{label}: {shape.volume:.3f} mm3',flush=True)
        return shape
    def fuse(label,a,b):
        return checked(label,a.fuse(b).clean())

    # Ear-support platform: its upper face is datum A exactly.
    l=p.platform_length/2; t=p.platform_thickness
    platform=prism([(-p.platform_neck_width/2,-l,-t),(p.platform_neck_width/2,-l,-t),
                    (p.platform_horn_width/2,l,-t),(-p.platform_horn_width/2,l,-t)],(0,0,t))
    part=checked('platform',platform);features['platform']=platform
    for i,x in enumerate([-p.horn_spacing/2,p.horn_spacing/2]):
        h=Pos(x,l+p.horn_length/2-p.fusion_overlap/2,-t/2)*Box(p.horn_width,p.horn_length+p.fusion_overlap,t)
        h=rounded_solid(h,[e for e in h.edges() if e.center().Y>l+0.05],p.horn_radius,'horn rounds')
        features[f'horn_{i}']=h;part=fuse(f'horn_{i}',part,h)

    # Circular crown with exact tangent straight flanks to the full 10.5 mm base.
    r=p.ear_crown_radius; cz=p.hole_z
    assert abs(cz+r-p.h3)<1e-7, 'Crown radius must close H3 with bore position'
    # Tangency from (l,0) to circle center (0,cz) in ear's (Y,Z) plane.
    d2=l*l+cz*cz
    ty=r*r*l/d2 + r*sqrt(d2-r*r)*cz/d2
    tz=cz-r*r*cz/d2 + r*sqrt(d2-r*r)*l/d2
    for i,xc in enumerate([-p.ear_center_x,p.ear_center_x]):
        x=xc-p.ear_thickness/2
        a=(x,-l,0);b=(x,l,0);c=(x,ty,tz);d=(x,-ty,tz)
        face=Face(Wire([Edge.make_line(a,b),Edge.make_line(b,c),
                        Edge.make_three_point_arc(c,(x,0,cz+r),d),Edge.make_line(d,a)]))
        ear=Solid.extrude(face,(p.ear_thickness,0,0))
        features[f'ear_{i}']=ear;part=fuse(f'ear_{i}',part,ear)
    # External root radii only: no material added inside the 21.8 mm seating gap.
    root_edges=[e for e in part.edges() if abs(e.center().Z)<1e-6 and
                abs(abs(e.center().X)-(p.ear_gap/2+p.ear_thickness))<1e-5 and e.length>5]
    part=checked('external ear root R0.5',rounded_solid(part,root_edges,p.ear_root_radius,'ear root'))
    bore=Solid.make_cylinder(p.hole_diameter/2,p.ear_gap+2*p.ear_thickness+4,
        Plane(origin=(-p.ear_gap/2-p.ear_thickness-2,0,cz),x_dir=(0,1,0),z_dir=(1,0,0)))
    part=checked('coaxial through holes',part.cut(bore).clean())
    circles=[e for e in part.edges() if e.geom_type.name=='CIRCLE' and abs(e.radius-p.hole_diameter/2)<1e-6]
    assert len(circles)==4
    part=checked('bore chamfers',chamfer(circles,p.hole_chamfer))

    # Construct flange including finish rounds BEFORE closing H1 to its real surface.
    outline,flange_xscale=flange_outline(p)
    flange_local=Solid.extrude(outline,(0,0,p.flange_thickness)).translate((0,0,-p.flange_thickness/2))
    flange_local=rounded_solid(flange_local,[e for e in flange_local.edges() if e.bounding_box().size.Z<1e-6],p.flange_edge_radius,'flange perimeter')
    a=radians(p.alpha+p.delta);b=radians(p.beta);d=radians(p.delta)
    F=Vector(0,cos(a),-sin(a)); N=Vector(0,sin(a),cos(a))
    D=Vector(0,cos(b),-sin(b)); NN=Vector(0,sin(b),cos(b))
    P=Vector(0,-cos(d),sin(d)); Q=Vector(0,-sin(d),-cos(d))
    oriented=Plane(origin=(0,0,0),x_dir=(1,0,0),z_dir=N).from_local_coords(flange_local)
    target_z=p.h3-p.h1
    flange_z=target_z-oriented.bounding_box().min.Z
    neck_start=Vector(0,-l,-t/2)
    neck_length=(flange_z-neck_start.Z)/D.Z
    assert neck_length>0
    O=neck_start+D*neck_length
    fp=Plane(origin=O,x_dir=(1,0,0),z_dir=N)
    flange=fp.from_local_coords(flange_local)
    features['flange_uncut']=flange;features['flange_outline']=outline
    # Capsule blind recess: real 1.7 mm residual wall, no false through slot.
    slot=Pos(0,p.groove_v,p.flange_thickness/2-p.groove_depth)*extrude(SlotOverall(p.groove_length,p.groove_width),amount=p.groove_depth+1)
    groove=fp.from_local_coords(slot)
    flange=checked('flange with blind recess',flange.cut(groove).clean())
    features['flange']=flange;features['groove_tool']=groove
    # Neck is normal-thickness trapezoid, with overlap at both buried joints.
    np=Plane(origin=neck_start,x_dir=(1,0,0),z_dir=NN)
    ov=p.fusion_overlap
    neck_local=prism([(-p.platform_neck_width/2,-ov,-p.neck_thickness/2),
                     (p.platform_neck_width/2,-ov,-p.neck_thickness/2),
                     (p.neck_width/2,neck_length+ov,-p.neck_thickness/2),
                     (-p.neck_width/2,neck_length+ov,-p.neck_thickness/2)],(0,0,p.neck_thickness))
    neck=np.from_local_coords(neck_local);features['neck']=neck
    part=fuse('neck',part,neck);part=fuse('flange',part,flange)
    # R1 concave shoulders make the 34 mm neck expand to the specified
    # 36 mm central joining region, without treating the whole flange as a trapezoid.
    shoulder_r=(p.flange_junction_width-p.neck_width)/2
    assert shoulder_r>0
    for i,sign in enumerate([-1,1]):
        x0=sign*p.neck_width/2;r=shoulder_r;n=-p.neck_thickness/2
        q0=(x0-sign*ov,-r,n);q1=(x0,-r,n)
        qm=(x0+sign*r*(1-1/sqrt(2)),-r*(1-1/sqrt(2)),n)
        q2=(x0+sign*r,0,n);q3=(x0+sign*r,ov,n);q4=(x0-sign*ov,ov,n)
        shoulder_face=Face(Wire([Edge.make_line(q0,q1),Edge.make_three_point_arc(q1,qm,q2),
                                Edge.make_line(q2,q3),Edge.make_line(q3,q4),Edge.make_line(q4,q0)]))
        shoulder=fp.from_local_coords(Solid.extrude(shoulder_face,(0,0,p.neck_thickness)))
        features[f'neck_shoulder_{i}']=shoulder
        part=fuse(f'neck to 36 mm shoulder {i}',part,shoulder)

    # Three triangular underside gussets at center and near both neck edges.
    # Actual included angle beta: platform underside leg +Y, neck leg D.
    root=Vector(0,-l,-t)
    ra=root+Vector(0,p.rib_leg,0);rb=root+D*p.rib_leg
    for i,x in enumerate([-(p.platform_neck_width-p.rib_thickness)/2,0,(p.platform_neck_width-p.rib_thickness)/2]):
        verts=[Vector(x-p.rib_thickness/2,v.Y,v.Z) for v in [root+Vector(0,-ov,ov),ra+Vector(0,0,ov),rb-NN*ov]]
        rib=prism(verts,(p.rib_thickness,0,0))
        features[f'rib_{i}']=rib;part=fuse(f'rib_{i}',part,rib)
    # Radius the concave platform/rib intersection lines (exclude neck seams).
    rib_roots=[e for e in part.edges() if abs(e.center().Z+t)<1e-5 and
               -l+0.1<e.center().Y<-l+p.rib_leg-0.1 and e.length>1 and
               any(abs(e.center().X-x)<1e-5 for x in
                   [-p.platform_neck_width/2,-p.platform_neck_width/2+p.rib_thickness,-p.rib_thickness/2,p.rib_thickness/2,p.platform_neck_width/2-p.rib_thickness,p.platform_neck_width/2])]
    part=checked('rib root fillets',rounded_solid(part,rib_roots,p.rib_radius,'rib root'))

    # Paddle: S is the FRONT surface at V=4, upper-face departure line.
    S=O+F*p.paddle_s_v-N*p.flange_thickness/2
    pp=Plane(origin=S,x_dir=(1,0,0),z_dir=Q)
    length=p.paddle_length; thick=p.paddle_root_thickness; end=p.paddle_end_thickness; rr=p.paddle_end_radius
    assert abs(2*rr-end)<1e-7, 'V01 circular end requires diameter equal to end thickness'
    # F·P is positive here: root moves forward as it descends.
    front_slope=F.dot(P)/F.dot(Q)
    root_u=front_slope*thick-ov
    x=-p.paddle_root_width/2
    top=(x,-ov,0);bottom=(x,root_u,thick)
    tipbottom=(x,length-rr,end);tiptop=(x,length-rr,0)
    edges=[Edge.make_line(top,bottom),
           Edge.make_bezier(bottom,(x,root_u+(length-rr-root_u)/3,thick),
                            (x,length-rr-(length-rr-root_u)/3,end),tipbottom),
           Edge.make_three_point_arc(tipbottom,(x,length,rr),tiptop),Edge.make_line(tiptop,top)]
    side=Solid.extrude(Face(Wire(edges)),(p.paddle_root_width,0,0))
    plan=polygon([(-p.paddle_root_width/2,-ov,0),(p.paddle_root_width/2,-ov,0),
                  (p.paddle_root_width/2,0,0),(p.paddle_end_width/2,length,0),
                  (-p.paddle_end_width/2,length,0),(-p.paddle_root_width/2,0,0)])
    plan=plan.fillet_2d(p.paddle_corner_radius,[v for v in plan.vertices() if abs(v.Y-length)<1e-5])
    paddle_local=Part(side.intersect(Solid.extrude(plan,(0,0,thick+1)))).clean()
    paddle=pp.from_local_coords(paddle_local);features['paddle']=paddle;features['paddle_plan']=plan
    part=fuse('tapered rounded paddle',part,paddle)

    # Tooth: straight upper longitudinal face parallel P, opposite projecting direction.
    # Bottom rear-root point is set back 0.5 along F; embed into flange by overlap.
    root=O+F*(p.h2-p.tooth_edge_offset)+N*p.flange_thickness/2
    tooth_dir=-P
    if p.gamma:
        tooth_dir=tooth_dir.rotate(Axis.X,p.gamma)
    up=Vector(1,0,0).cross(tooth_dir)
    tp=Plane(origin=root,x_dir=(1,0,0),z_dir=up)
    # local y = projecting tooth direction, z = up, angled flange root follows -F.
    root_shift=(-F).dot(tooth_dir)/(-F).dot(up)*p.tooth_root_thickness
    tw=p.tooth_width;tl=p.tooth_length;tr=p.tooth_root_thickness;te=p.tooth_end_thickness
    tooth_local=prism([(-tw/2,-ov,0),(-tw/2,tl,tr-te),(-tw/2,tl,tr),
                       (-tw/2,root_shift-ov,tr)],(tw,0,0))
    tooth_local=rounded_solid(tooth_local,[e for e in tooth_local.edges() if e.center().Y>tl-1e-5],p.tooth_tip_radius,'tooth tip')
    # Optional measured retaining-face relief, intentionally absent from default V01.
    if p.retaining_ledge_depth:
        if p.retaining_face_from_root is None or not 0<p.retaining_face_from_root<tl:
            raise ValueError('Measure and set retaining_face_from_root before enabling a ledge')
        ledge=p.retaining_ledge_depth;at=p.retaining_face_from_root
        shift=ledge/tan(radians(p.retaining_face_angle))
        cut=prism([(-tw,at,tr-ledge),(-tw,tl+1,tr-ledge),(-tw,tl+1,tr+1),
                   (-tw,at-shift,tr+1)],(tw*2,0,0))
        tooth_local=tooth_local.cut(cut)
    tooth=tp.from_local_coords(tooth_local);features['tooth']=tooth
    part=fuse('straight reconstructed tooth',part,tooth)
    # Analytic R1 lateral blends, terminated inside the root's height span.
    # Full-edge OCC fillets run into the 0.5 mm edge setback. These short
    # quarter-circle fillet strips keep R1 outside the unknown contact zone.
    root_v=p.h2-p.tooth_edge_offset
    upper_v=root_v-tr/(-F).dot(up)
    blend_v0=upper_v+p.tooth_root_radius
    blend_v1=root_v-p.tooth_root_radius
    assert blend_v1>blend_v0
    rr=p.tooth_root_radius
    for i,sign in enumerate([-1,1]):
        # Coordinates in flange frame: X lateral, V downward, N rearward.
        x0=sign*tw/2; n0=p.flange_thickness/2
        q0=(x0,blend_v0,n0-ov)
        q1=(x0+sign*rr,blend_v0,n0-ov)
        q2=(x0+sign*rr,blend_v0,n0)
        qm=(x0+sign*rr*(1-1/sqrt(2)),blend_v0,n0+rr*(1-1/sqrt(2)))
        q3=(x0,blend_v0,n0+rr)
        face=Face(Wire([Edge.make_line(q0,q1),Edge.make_line(q1,q2),
                        Edge.make_three_point_arc(q2,qm,q3),Edge.make_line(q3,q0)]))
        blend=fp.from_local_coords(Solid.extrude(face,(0,blend_v1-blend_v0,0)))
        features[f'tooth_root_blend_{i}']=blend
        part=fuse(f'analytic tooth lateral R1 blend {i}',part,blend)
    part=checked('final solid',part.clean())
    datums=dict(A_z=0.0,C=[0,0,cz],F=list(F),N=list(N),P=list(P),Q=list(Q),neck_direction=list(D),
                flange_origin=list(O),S=list(S),tooth_root=list(root),tooth_direction=list(tooth_dir),
                tooth_upper_root=list(root+tooth_dir*root_shift+up*tr),neck_length=neck_length,
                flange_xscale=flange_xscale,flange_min_z=flange.bounding_box().min.Z)
    return Model(part,features,datums,stages,p)

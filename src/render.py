"""Headless orthographic renders and dimensioned SVG/PNG drawing from real CAD."""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from build123d import Plane, Vector, section

BG='#f3f6f8'; INK='#183344'; ACCENT='#187a86'


def projected_render(mesh, path, camera, title, subtitle):
    view=np.asarray(camera,dtype=float);view/=np.linalg.norm(view)
    right=np.cross([0,0,1],view);right/=np.linalg.norm(right)
    up=np.cross(view,right)
    basis=np.array([right,up,view]).T
    vertices=mesh.vertices@basis
    triangles=vertices[mesh.faces]
    normals=mesh.face_normals
    light=np.array([-.3,.1,.95]);light/=np.linalg.norm(light)
    shade=.43+.42*np.maximum(normals@light,0)+.12*np.maximum(normals@view,0)
    base=np.array([.13,.43,.48])
    colors=np.clip(base[None,:]*shade[:,None]*1.8,0,1)
    # Orthographic z-buffer rasterization: correct occlusion even for large
    # planar CAD triangles whose centroids cannot be painter-sorted reliably.
    lower=vertices[:,:2].min(axis=0)-1;upper=vertices[:,:2].max(axis=0)+1
    pixels=1500;scale=pixels/max(upper-lower)
    width,height=np.ceil((upper-lower)*scale).astype(int)
    depth=np.full((height,width),-np.inf)
    canvas=np.ones((height,width,4));canvas[:,:,:3]=[243/255,246/255,248/255]
    canvas[:,:,3]=0
    for ti in np.flatnonzero(normals@view>1e-9):
        t=triangles[ti];screen=(t[:,:2]-lower)*scale
        x0,y0=np.maximum(np.floor(screen.min(axis=0)).astype(int),0)
        x1,y1=np.minimum(np.ceil(screen.max(axis=0)).astype(int),[width-1,height-1])
        if x1<x0 or y1<y0:continue
        xx,yy=np.meshgrid(np.arange(x0,x1+1)+.5,np.arange(y0,y1+1)+.5)
        a,b,c=screen
        den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(den)<1e-12:continue
        w0=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den
        w1=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den
        w2=1-w0-w1;z=w0*t[0,2]+w1*t[1,2]+w2*t[2,2]
        target=depth[y0:y1+1,x0:x1+1]
        mask=(w0>=-1e-7)&(w1>=-1e-7)&(w2>=-1e-7)&(z>target)
        target[mask]=z[mask]
        chunk=canvas[y0:y1+1,x0:x1+1];chunk[mask,:3]=colors[ti];chunk[mask,3]=1
    fig,ax=plt.subplots(figsize=(12,8),dpi=160,facecolor=BG)
    ax.set_facecolor(BG)
    ax.imshow(canvas,origin='lower',extent=[lower[0],upper[0],lower[1],upper[1]],interpolation='bilinear')
    lo=vertices[:,:2].min(axis=0);hi=vertices[:,:2].max(axis=0)
    center=(lo+hi)/2;extent=max((hi-lo)[0]/1.45,(hi-lo)[1])*1.27
    ax.set_xlim(center[0]-extent*.77,center[0]+extent*.77)
    ax.set_ylim(center[1]-extent*.5,center[1]+extent*.5)
    ax.set_aspect('equal');ax.axis('off')
    fig.text(.07,.92,'ARMREST LATCH / V01',fontsize=11,color=ACCENT,weight='bold')
    fig.text(.07,.875,title,fontsize=23,color=INK,weight='bold')
    fig.text(.07,.06,subtitle,fontsize=10,color=INK)
    fig.text(.93,.06,'mm · FIT PROTOTYPE',fontsize=10,color=ACCENT,ha='right')
    fig.savefig(path,dpi=160,facecolor=BG);plt.close(fig)


def edge_points(edge,n=70):
    return np.array([list(edge.position_at(t)) for t in np.linspace(0,1,n)])


def dimension(ax,a,b,offset,label,color=ACCENT):
    a=np.asarray(a);b=np.asarray(b);off=np.asarray(offset);aa=a+off;bb=b+off
    ax.plot([a[0],aa[0]],[a[1],aa[1]],color=color,lw=.65)
    ax.plot([b[0],bb[0]],[b[1],bb[1]],color=color,lw=.65)
    ax.annotate('',xy=aa,xytext=bb,arrowprops=dict(arrowstyle='<->',lw=.8,color=color,shrinkA=0,shrinkB=0))
    mid=(aa+bb)/2
    ax.text(mid[0],mid[1],label,color=color,fontsize=8,ha='center',va='center',bbox=dict(facecolor='white',edgecolor='none',pad=1.5))


def drawing(m,path):
    p=m.params;d=m.datums
    fig,axs=plt.subplots(2,2,figsize=(15,10),dpi=180)
    fig.patch.set_facecolor('white')
    for ax in axs.flat:
        ax.set_aspect('equal');ax.axis('off')
    ax=axs[0,0]
    cross=section(m.part,Plane.YZ)
    for e in cross.edges():
        v=edge_points(e);ax.plot(v[:,1],v[:,2],color=INK,lw=1)
    # Near ear section, not falsely included in center section.
    ear_section=section(m.part,Plane(origin=(p.ear_center_x,0,0),x_dir=(0,1,0),z_dir=(1,0,0)))
    for e in ear_section.edges():
        v=edge_points(e)
        if v[:,2].max()>0:ax.plot(v[:,1],v[:,2],color='#7b8d97',lw=.8,ls='--')
    s=np.array(d['S']);o=np.array(d['flange_origin']);f=np.array(d['F']);P=np.array(d['P'])
    ax.axhline(0,lw=.7,ls='--',color='#9baeb5');ax.text(8,0.6,'A / Z=0',fontsize=8,color=ACCENT)
    dimension(ax,[0,p.h3],[0,d['flange_min_z']],[16,0],'H1 33.50')
    dimension(ax,s[1:],(s+P*p.paddle_length)[1:],[0,7],'L1 30.00 from S')
    ax.scatter([s[1]],[s[2]],s=12,color=ACCENT);ax.text(s[1]+1,s[2]+1,'S',fontsize=9,color=ACCENT)
    rt=np.array(d['tooth_root']);ax.scatter([rt[1]],[rt[2]],s=12,color=ACCENT)
    ax.text(-43,-29,f'Neck centerline: {d["neck_length"]:.3f} (derived)\nTooth lower root Y={rt[1]:.3f}, Z={rt[2]:.3f} relative to A\nC=(0, 0, {p.hole_z:.2f}); root is {p.hole_z-rt[2]:.3f} below C',fontsize=8,color=INK,va='top')
    ax.set_title('01  SIDE SECTION B / NEAR EAR DASHED',loc='left',fontsize=11,color=INK,pad=16)
    ax.set_xlim(-47,21);ax.set_ylim(-39,20)
    ax=axs[0,1]
    outline=m.features['flange_outline']
    for e in outline.edges():
        v=edge_points(e);ax.plot(v[:,0],v[:,1],color=INK,lw=1.2)
    fp=Plane(origin=o,x_dir=(1,0,0),z_dir=d['N'])
    fl=fp.to_local_coords(m.features['flange'])
    for e in fl.edges():
        v=edge_points(e)
        if abs(v[:,2].mean()-p.flange_thickness/2)<.02:
            ax.plot(v[:,0],v[:,1],color=INK,lw=.6)
    dimension(ax,[-35,0],[35,0],[0,-5],'70.00')
    dimension(ax,[0,0],[0,p.h2],[39,0],'H2 16.50')
    ax.text(-35,24,'Flange coordinates X / V; looking at rear surface\nR1 wing tips · R0.5 thickness edges · groove 48 × 2.5 × 1.5',fontsize=8,color=INK)
    ax.text(-35,-12,f'Central joining region 36; neck 34\nSpline station X values × {d["flange_xscale"]:.5f} before tip rounds',fontsize=8,color=INK)
    ax.set_title('02  FLANGE / LOCAL PLANE F',loc='left',fontsize=11,color=INK,pad=16)
    ax.set_xlim(-42,47);ax.set_ylim(-16,29)
    ax=axs[1,0]
    ear=m.features['ear_1']
    for e in ear.edges():
        v=edge_points(e)
        if np.ptp(v[:,0])<1e-6:ax.plot(v[:,1],v[:,2],color=INK,lw=.8)
    circle=plt.Circle((0,p.hole_z),p.hole_diameter/2,fill=False,color=INK,lw=1);ax.add_patch(circle)
    ax.plot([-7,7],[0,0],color='#9baeb5',ls='--',lw=.7)
    dimension(ax,[0,0],[0,p.h3],[8,0],'H3 11.30')
    dimension(ax,[-p.platform_length/2,0],[p.platform_length/2,0],[0,-2.5],'10.50')
    ax.annotate('2 × Ø2.50 THRU\n0.2 × 45° chamfers',xy=(0,p.hole_z),xytext=(-19,9),fontsize=8,color=INK,arrowprops=dict(arrowstyle='-',color=ACCENT,lw=.7))
    ax.text(-19,-6,'Ear thickness 3.00 each; clear gap 21.80\nOuter span 27.80; midplanes X=±12.40\nOutside root R0.5; gap remains clear',fontsize=8,color=INK)
    ax.set_title('03  PIVOT EAR / PROFILE AND FIT',loc='left',fontsize=11,color=INK,pad=16)
    ax.set_xlim(-22,13);ax.set_ylim(-10,15)
    ax=axs[1,1];ax.set_aspect('auto')
    ax.set_title('04  V01 ASSUMPTIONS / NOT FIT-VALIDATED',loc='left',fontsize=11,color=INK,pad=16)
    rows=[['Feature','Nominal / status'],['α / β','110° / 110° · estimate'],['γ / δ','0° / 0° · assumption'],['Paddle','52 → 40 blank; R10 corners; 6 → 3'],['Tooth','17.5 wide × 10 projection; 5.2 → 2'],['Tooth ledge','Unknown; disabled pending mating-part fit'],['Root blends','R1 lateral strips; end rounds R0.3'],['Reconstruction','Solid tooth; original cavities not inferred'],['Manufacture','Nominal mm; no shrink or hole compensation']]
    table=ax.table(cellText=rows,loc='upper left',cellLoc='left',colWidths=[.27,.73],bbox=[0,.12,1,.83])
    table.auto_set_font_size(False);table.set_fontsize(8)
    for (row,col),cell in table.get_celld().items():
        cell.set_edgecolor('#d5e0e5');cell.set_linewidth(.6);cell.PAD=.09
        cell.set_facecolor('#e7f1f3' if row==0 else ('#f5f8fa' if row%2==0 else 'white'))
        if row==0:cell.set_text_props(weight='bold',color=INK)
    ax.text(0,0,'Status: У owner · И inherited · О estimate · Д assumption · Р derived · ? unknown',fontsize=8,color=INK,transform=ax.transAxes)
    fig.suptitle('ARMREST LATCH  /  V01 ENGINEERING REVIEW',fontsize=18,color=INK,x=.06,ha='left')
    fig.text(.06,.025,'All dimensions in mm. Screen drawing is not a scale template. Nominal CAD geometry only; verify tooth engagement and free motion on the mating mechanism.',fontsize=9,color=INK)
    fig.subplots_adjust(left=.06,right=.96,top=.90,bottom=.08,wspace=.2,hspace=.32)
    fig.savefig(path.with_suffix('.svg'));fig.savefig(path.with_suffix('.png'),dpi=180);plt.close(fig)


def render_all(m,mesh,out):
    for name,cam,title,caption in [
        ('iso',(1,-1.4,.9),'Complete reconstructed latch','Front isometric · paddle, pivot ears and curved flange'),
        ('rear_iso',(-1,1.5,-.1),'Tooth, ribs and rear recess','Rear isometric · solid preliminary tooth; retaining ledge remains undefined'),
        ('side',(1,0,0),'Side profile','Paddle left · tooth right · H1 excludes the paddle'),
        ('rear',(0,1,.364),'Rear flange view','Three joined ribs · blind capsule recess · symmetric wing contour')]:
        projected_render(mesh,out/f'armrest_latch_v01_{name}.png',cam,title,caption)
    drawing(m,out/'armrest_latch_v01_drawing')

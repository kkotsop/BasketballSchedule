"""Renders the background basketball (numpy + Pillow): tilted 8-panel seams, pebbled leather, studio lighting.
Usage: python tools/render_ball.py [size=1000]   ->   assets/ball.webp"""
import numpy as np, sys, os
from pathlib import Path
from PIL import Image
OUT = Path(__file__).resolve().parent.parent / 'assets' / 'ball.webp'
N=int(sys.argv[1]) if len(sys.argv)>1 else 1000
R=0.485*N
rng=np.random.default_rng(11)
yy,xx=np.mgrid[0:N,0:N].astype(np.float64)
x=(xx+0.5-N/2)/R; y=-(yy+0.5-N/2)/R
r=np.sqrt(x*x+y*y); z=np.sqrt(np.clip(1-r*r,0,1))
alpha=np.clip((1.0-r)*R+0.5,0,1)*(r<=1.0)
def smooth(a,b,v):
    t=np.clip((v-a)/(b-a),0,1); return t*t*(3-2*t)
def nrm(v): v=np.array(v,float); return v/np.linalg.norm(v)

# ---- object frame (tilted so the 8-panel seams wrap the sphere) ----
ca,sa=np.cos(np.radians(-26)),np.sin(np.radians(-26)); cb,sb=np.cos(np.radians(30)),np.sin(np.radians(30))
Rz=np.array([[ca,-sa,0],[sa,ca,0],[0,0,1]]); Rx=np.array([[1,0,0],[0,cb,-sb],[0,sb,cb]]); M=Rz@Rx
xo=M[0,0]*x+M[1,0]*y+M[2,0]*z; yo=M[0,1]*x+M[1,1]*y+M[2,1]*z; zo=M[0,2]*x+M[1,2]*y+M[2,2]*z
cx,rr=1.55,1.25
d=np.minimum.reduce([np.abs(xo),np.abs(yo),np.abs(np.hypot(xo+cx,yo)-rr),np.abs(np.hypot(xo-cx,yo)-rr)])
w=0.030*(0.30+0.70*np.abs(zo))
groove=1-smooth(w*0.70,w*1.05,d)
hs=-(1-smooth(0,w*1.15,d))*0.9                      # recessed channel
pillow=smooth(0.0,0.34,d)                            # panels bulge away from the seams
ao=1-0.70*np.exp(-(d/(w*3.6))**2)*(1-groove)         # dark creases beside the channels

# ---- leather pebbles ----
def pebble(N,s,seed):
    g=np.random.default_rng(seed); n=int(np.ceil(N/s))+3
    jx=g.random((n,n)); jy=g.random((n,n)); sz=0.7+0.6*g.random((n,n))
    py,px=np.mgrid[0:N,0:N].astype(np.float64)
    ci=(px/s).astype(int)+1; cj=(py/s).astype(int)+1
    best=np.full((N,N),1e9); bsz=np.ones((N,N))
    for oj in (-1,0,1):
        for oi in (-1,0,1):
            ii=ci+oi; jj=cj+oj
            dd=np.hypot(px-(ii-1+jx[jj,ii])*s, py-(jj-1+jy[jj,ii])*s)
            m=dd<best; best=np.where(m,dd,best); bsz=np.where(m,sz[jj,ii],bsz)
    return np.clip(1-best/(0.62*s*bsz),0,1)**1.25
h=pebble(N,N/132.0,3)*(0.30+0.70*z)**1.4
h_peb=h*smooth(w*0.8,w*1.6,d)

# ---- normals ----
pgy,pgx=np.gradient(h_peb); sgy,sgx=np.gradient(hs); qgy,qgx=np.gradient(pillow)
sc=N/900.0
SP,SG,SQ=4.4*sc,9.0*sc,2.3*sc*R/ (0.34*R)*0.0+ 260.0*sc*(1.0/N)*N/900.0
nx=x-pgx*SP-sgx*SG-qgx*SQ; ny=y+pgy*SP+sgy*SG+qgy*SQ; nz=z.copy()
l=np.sqrt(nx*nx+ny*ny+nz*nz)+1e-9; nx,ny,nz=nx/l,ny/l,nz/l
def dot(v): return nx*v[0]+ny*v[1]+nz*v[2]
def dot0(v): return x*v[0]+y*v[1]+z*v[2]     # smooth sphere normal, for the overall form

# ---- lights: warm key (top-left), cool fill (right), warm floor bounce, back rim ----
Lk=nrm((-0.52,0.62,0.58)); Lf=nrm((0.85,0.15,0.5)); Lb=nrm((0.25,-0.92,0.30)); Lr=nrm((0.8,-0.2,-0.45))
key_form=np.clip(dot0(Lk)*1.0+0.02,0,1.25)**1.55
key=np.clip(key_form+(dot(Lk)-dot0(Lk))*0.85,0,1.4)
fill=np.clip(dot0(Lf),0,1)**1.5*(1-key_form*0.6)
bounce=np.clip(dot0(Lb),0,1)**2.0
rim=np.clip(dot(Lr),0,1)*(1-z)**2.2
# leather albedo (linear), darker valleys / lighter pebble tops, soft mottling
lin=lambda c: np.array(c,float)**2.2
base=lin((0.86,0.39,0.09))
lf=np.zeros((N,N))
for f,a in ((3,0.5),(7,0.3),(15,0.2)):
    g=rng.random((f+2,f+2)); im=Image.fromarray((g*255).astype(np.uint8)).resize((N,N),Image.BICUBIC)
    lf+=np.asarray(im,float)/255*a
lf=(lf-lf.mean())*0.22
alb=(1+lf)*(0.80+0.22*h)*ao*(0.72+0.28*z**0.7)
col=np.zeros((N,N,3))
warm=np.array([1.00,0.93,0.82]); cool=np.array([0.62,0.72,1.0]); bnc=np.array([1.0,0.55,0.22])
for c in range(3):
    col[...,c]=base[c]*alb*(0.045+key*1.35*warm[c]+fill*0.07*cool[c]+bounce*0.20*bnc[c])
# specular: broad leather sheen + a softbox reflection, both broken up by the pebbles
V=np.array([0,0,1.0]); Hk=nrm(Lk+V)
ndh=np.clip(dot(Hk),0,1)
sheen=ndh**16*0.09+ndh**80*0.22
Rx_=2*nz*nx; Ry_=2*nz*ny; Rz_=2*nz*nz-1            # reflection of the view vector
Wd=nrm((-0.42,0.62,0.66))
soft=smooth(0.93,0.99,Rx_*Wd[0]+Ry_*Wd[1]+Rz_*Wd[2])*0.20
spec=(sheen+soft)*(1-groove)
col+=spec[...,None]*np.array([1.0,0.95,0.86])
col+=rim[...,None]*np.array([1.0,0.62,0.28])*0.55
# channel: dark rubber, only faintly lit
gcol=lin((0.04,0.024,0.017))
gl=(0.30+0.85*key)[...,None]
col=col*(1-groove[...,None])+gcol*gl*groove[...,None]
# filmic-ish tone curve, then sRGB
col=1-np.exp(-col*1.15)
col=np.clip(col,0,1)**(1/2.2)
out=np.zeros((N,N,4)); out[...,:3]=col; out[...,3]=alpha
img=Image.fromarray((np.clip(out,0,1)*255).astype(np.uint8),'RGBA')
img.save(OUT, quality=78, method=6)
print('wrote', OUT, os.path.getsize(OUT)//1024, 'KB')

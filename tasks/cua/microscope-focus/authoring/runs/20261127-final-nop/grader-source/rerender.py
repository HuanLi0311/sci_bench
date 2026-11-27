"""Trusted image-plane comparison, independent of candidate reports."""
import base64,io
import numpy as np
from PIL import Image

def decode(data):
    return np.asarray(Image.open(io.BytesIO(base64.b64decode(data.split(',',1)[1]))).convert('RGB'),dtype=float)

def expected_image(sample,total):
    out=Image.new('RGB',(1280,720),(16,24,32))
    if total is None: return np.asarray(out,dtype=float)
    width=abs(total)*.006*1024
    # Canvas nearest-neighbour pixel centres, including clipping and 180 degree rotation.
    yy,xx=np.indices((720,1280)); sx=(xx+.5-640)/width+0.5; sy=(yy+.5-360)/width+.5
    if total<0: sx=1-sx;sy=1-sy
    mask=(sx>=0)&(sx<1)&(sy>=0)&(sy<1)
    tex=np.asarray(Image.open(sample).convert('RGB'))
    a=np.asarray(out).copy();a[mask]=tex[np.minimum(1023,(sy[mask]*1024).astype(int)),np.minimum(1023,(sx[mask]*1024).astype(int))]
    return a.astype(float)

def similarity(a,b):
    # Local-window structural similarity with luminance and contrast.
    if a.shape!=b.shape:return 0.
    a=a[:704,:1280].reshape(44,16,80,16,3).transpose(0,2,1,3,4).reshape(-1,768)
    b=b[:704,:1280].reshape(44,16,80,16,3).transpose(0,2,1,3,4).reshape(-1,768)
    ma=a.mean(1);mb=b.mean(1);va=a.var(1);vb=b.var(1);cov=((a-ma[:,None])*(b-mb[:,None])).mean(1)
    return float(np.mean((2*ma*mb+6.5025)*(2*cov+58.5225)/((ma*ma+mb*mb+6.5025)*(va+vb+58.5225))))

def mapping_ok(a,b,width):
    """Evaluate foreground as well as full frame; small samples cannot be blank."""
    if a.shape!=b.shape:return False
    bg=np.array([16,24,32]);ma=np.max(abs(a-bg),axis=2)>10;mb=np.max(abs(b-bg),axis=2)>10
    if ma.sum()<4 or mb.sum()<4:return False
    ya,xa=np.where(ma);yb,xb=np.where(mb)
    centroid=abs(xa.mean()-xb.mean())<=.02*1280 and abs(ya.mean()-yb.mean())<=.02*720
    def coverage_extent(row,reference):
        ids=np.where(np.max(abs(row-bg),axis=1)>10)[0];refids=np.where(np.max(abs(reference-bg),axis=1)>10)[0]
        if len(ids)<2 or len(refids)<2:return 0
        # Canvas antialiases fractional rectangle boundaries even with smoothing off.
        # Recover fractional coverage using the corresponding opaque edge colour.
        weights=[]
        for i,j in [(ids[0],refids[0]),(ids[-1],refids[-1])]:
            delta=reference[j]-bg
            weights.append(float(np.clip(np.dot(row[i]-bg,delta)/max(1,np.dot(delta,delta)),0,1)))
        return ids[-1]-ids[0]-1+sum(weights)
    measured=[coverage_extent(a[360],b[360]),coverage_extent(a[:,640],b[:,640])]
    target=min(width,1280),min(width,720)
    scale=all(abs(m/t-1)<=.02 for m,t in zip(measured,target))
    # Nearest-neighbour colour agreement catches wrong orientation and wrong sample.
    return centroid and scale and float(abs(a-b)[mb].mean())<6

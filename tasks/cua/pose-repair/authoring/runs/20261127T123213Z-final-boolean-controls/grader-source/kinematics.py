"""Independent world-space replay (Python Euler matrices, no submitted JS)."""
import math
import numpy as np

def replay(p, u):
    q = np.array(p['matrix']) @ np.array(u) + np.array(p['bias']) + .12*np.sin(u)
    positions, rotations = [], []
    for i in range(8):
        x,y,z=q[3*i:3*i+3]
        cx,sx,cy,sy,cz,sz=math.cos(x),math.sin(x),math.cos(y),math.sin(y),math.cos(z),math.sin(z)
        rx=np.array([[1,0,0],[0,cx,-sx],[0,sx,cx]])
        ry=np.array([[cy,0,sy],[0,1,0],[-sy,0,cy]])
        rz=np.array([[cz,-sz,0],[sz,cz,0],[0,0,1]])
        parent=p['parents'][i]
        rotations.append((np.eye(3) if parent<0 else rotations[parent]) @ rz @ ry @ rx)
        positions.append(np.array([0,0,.9]) if parent<0 else positions[parent]+rotations[parent]@p['offsets'][i])
    return np.array(positions), np.array(rotations)

def errors(p,u,v):
    a,ar=replay(p,u);b,br=replay(p,v)
    position=np.linalg.norm(a-b,axis=1)
    angles=np.degrees(np.arccos(np.clip((np.trace(ar@br.transpose(0,2,1),axis1=1,axis2=2)-1)/2,-1,1)))
    return float(position.max()),float(angles.max())

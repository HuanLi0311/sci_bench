"""CC0 synthetic choreography; also prints the public bone/rest/stance tables.

Coordinates are metres, Z up. Character-local forward is +X; width is Y.
No candidate grading imports this trajectory generator.
"""
import math
from mathutils import Vector,Matrix

EVENTS=[(65,'L','hand.L'),(105,'R','hand.R'),(145,'L','hand.L'),(185,'R','chest')]
KEYS=(48,65,235,300)
PARENTS={'root':None,'spine':'root','chest':'spine','neck':'chest','head':'neck'}
# 5 axial + 1 pelvis + 8 arm + 8 leg = 22 bones.
PARENTS['pelvis']='root'
for side in ['L','R']:
    for n,p in [('clavicle','chest'),('upper_arm','clavicle.'+side),('forearm','upper_arm.'+side),('hand','forearm.'+side),('thigh','pelvis'),('shin','thigh.'+side),('foot','shin.'+side),('toe','foot.'+side)]: PARENTS[n+'.'+side]=p

def smooth(x):
    x=max(0,min(1,x));return x*x*(3-2*x)
def pulse(f,c,width=12):return max(0,1-abs(f-c)/width)**2
def ik(a,b,l1,l2,pole):
    d=b-a;dist=min(d.length,l1+l2-1e-6);direction=d.normalized()
    x=(l1*l1-l2*l2+dist*dist)/(2*dist)
    v=Vector(pole)-direction*Vector(pole).dot(direction)
    if v.length<1e-6:v=direction.cross(Vector((0,0,1)))
    return a+direction*x+v.normalized()*math.sqrt(max(0,l1*l1-x*x))
def foot_x(side,f):
    start=-1.2;end=-.53
    lo,hi=(5,20) if side=='L' else (22,37)
    v=start+(end-start)*smooth((f-lo)/(hi-lo))
    lo,hi=(265,280) if side=='L' else (282,297)
    return v+(start-end)*smooth((f-lo)/(hi-lo))
def stance(side,f):
    return not ((5<f<20 if side=='L' else 22<f<37) or (265<f<280 if side=='L' else 282<f<297) or (side=='L' and 215<f<253))
def pose(which,f):
    scale=1 if which=='left' else 1.9/1.7;direction=1 if which=='left' else -1
    def V(x,y,z):return Vector((direction*x,y*scale,z*scale))
    feet={s:V(foot_x(s,f),(.15 if s=='L' else -.15),.07) for s in ['L','R']}
    x=(feet['L'].x+feet['R'].x)/2
    root=Vector((x,0,.86*scale))
    attack=max(pulse(f,c,9) for c,_,_ in EVENTS)
    root.x+=.20*attack
    if which=='left':
        body=pulse(f,185,9)
        root.x+=.12*attack+.24*body
        root.z-=.05*attack+.15*body
    x=root.x
    duck=.35*pulse(f,235,20) if which=='right' else 0
    root.z-=.62*duck
    lean=Vector((direction*.12*duck,0,-.25*duck))
    b={}
    b['root']=(root,root+V(0,0,.1))
    b['pelvis']=(root,root+V(0,.06,0))
    a=b['root'][1];b['spine']=(a,a+V(-.21*scale*math.sin(duck),0,.21*math.cos(duck)))
    a=b['spine'][1];b['chest']=(a,a+V(-.24*scale*math.sin(duck),0,.24*math.cos(duck)))
    a=b['chest'][1];b['neck']=(a,a+V(0,0,.12))
    a=b['neck'][1];b['head']=(a,a+V(0,0,.12))
    for s,sgn in [('L',1),('R',-1)]:
        shoulder=b['chest'][1]+V(0,sgn*.18,0)
        b['clavicle.'+s]=(b['chest'][1]+V(0,sgn*.025,0),shoulder)
        wrist=Vector((x+direction*.25,sgn*.22*scale,1.28*scale))
        if which=='right':
            wrist=Vector((x-direction*.04,sgn*.22*scale,1.28*scale))
            for c,attack,target in EVENTS:
                if target=='hand.'+s:
                    p=pulse(f,c,9)
                    wrist.x-=.27*p
                    wrist.z-=.08*p
            wrist.z-=duck*.5
        else:
            for c,attack,target in EVENTS:
                if attack==s:
                    p=pulse(f,c,12)
                    target_pose=pose('right',f)
                    ta,tb=target_pose[target];center=(ta+tb)/2
                    # Fist center stops just short of the target's convex surface.
                    center.x-= .074 if target.startswith('hand') else .18
                    desired=center-V(.04,0,0)
                    wrist=wrist.lerp(desired,p)
        elbow=ik(shoulder,wrist,.31*scale,.29*scale,(0,sgn*.8,-.7))
        b['upper_arm.'+s]=(shoulder,elbow);b['forearm.'+s]=(elbow,wrist)
        b['hand.'+s]=(wrist,wrist+V(.08,0,0))
        ankle=feet[s].copy()
        if not stance(s,f):
            if 5<f<20 or 22<f<37 or 265<f<280 or 282<f<297: ankle.z+=.11*math.sin(math.pi*((f-(5 if s=='L' and f<100 else 22 if s=='R' and f<100 else 265 if s=='L' else 282))/15))
        if which=='left' and s=='L':
            p=pulse(f,235,18);theta=2*math.pi*smooth((f-215)/38)-math.pi
            ankle=ankle.lerp(Vector((x+.48*math.cos(theta),.35+.18*math.sin(theta),1.40)),p)
        hip=root+V(0,sgn*.17,0)
        knee=ik(hip,ankle,.42*scale,.41*scale,(direction,0,0))
        b['thigh.'+s]=(hip,knee);b['shin.'+s]=(knee,ankle)
        b['foot.'+s]=(ankle,ankle+V(.15,0,0));b['toe.'+s]=(b['foot.'+s][1],ankle+V(.21,0,0))
    if which=='left' and 215<f<253:
        spin=Matrix.Rotation(2*math.pi*smooth((f-215)/38),3,'Z')
        for n in list(b):
            if n not in ['root','pelvis'] and not n.startswith(('thigh','shin','foot','toe')):
                b[n]=tuple(root+spin@(point-root) for point in b[n])
    return b

def radius(name):
    if name=='head':return .05
    if name in ['root','pelvis']:return .07
    if name in ['spine','chest']:return .12
    if name.startswith('hand'):return .05
    if name.startswith(('foot','toe')):return .07
    return .035

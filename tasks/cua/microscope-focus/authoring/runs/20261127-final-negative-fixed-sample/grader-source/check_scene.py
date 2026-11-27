"""Independent Cartesian thin-lens oracle; never imports submission code."""
import math

def lens(s, f):
    if abs(s) < 1e-10:
        return dict(kind='no-finite-image',s=s,v=None,m=None)
    if abs(s+f) < 1e-9:
        return dict(kind='infinity',s=s,v=None,m=None)
    # Independent reciprocal form (the reference JS uses rational form).
    v=1.0/(1.0/f+1.0/s)
    return dict(kind='real' if v>0 else 'virtual',s=s,v=v,m=v/s)

def optical(stage, objective, eye):
    a=lens(stage-objective,4.)
    b=lens(objective+a['v']-eye,25.) if a['v'] is not None else dict(kind='no-finite-image',s=None,v=None,m=None)
    m=a['m']*b['m'] if b['m'] is not None else None
    return dict(objective=a,eyepiece=b,total=m,height=None if m is None else .05*m,orientation='undefined' if m is None else 'inverted' if m<0 else 'upright')

def selftest():
    a=optical(-8,0,160)
    assert abs(a['objective']['v']-8)<1e-10 and a['objective']['m']==-1
    assert optical(-4,0,160)['objective']['kind']=='infinity'
    assert lens(-25,25)['kind']=='infinity'
    assert optical(-4.12,0,160)['eyepiece']['kind']=='virtual'
    assert optical(-4.16,0,161)['eyepiece']['kind']=='real'
    for s in [-4.01,-4.5,-9,3]:
        r=lens(s,4); assert math.isclose(1/r['v']-1/s,.25,abs_tol=1e-12)

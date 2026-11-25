import subprocess, re
WSL='cd "/mnt/d/迅雷下载/ic-bench/tasks/engineering-sciences/electrical-engineering/datapath-debug" && '
base=open("environment/rtl/axis_source.v").read()
def run(b,g,extra=""):
    s=re.sub(r"parameter integer BURST  = \d+","parameter integer BURST  = %d"%b,base)
    s=re.sub(r"parameter integer GAP    = \d+","parameter integer GAP    = %d"%g,s)
    open(".scratch/as.v","w").write(s)
    cmd=WSL+"iverilog -g2012 -o /tmp/dp/sim tests/tb_top.v .scratch/as.v $(ls environment/rtl/*.v | grep -v axis_source) "+extra+" && /tmp/dp/sim"
    out=subprocess.run(["wsl","-e","bash","-lc",cmd],capture_output=True,text=True,errors="replace").stdout
    m=re.search(r"TOP_OK=(\d+) TOP_ERR=(\d+) TOP_BEATS=(\d+) TOP_CYCLES=(\d+) TOP_FIRSTBAD=(\d+)",out)
    return m.groups() if m else out.strip()[:200]
for b,g in [(1000,0),(200,0),(64,32),(48,48),(32,64),(24,96),(40,120),(16,64)]:
    print("burst=%d gap=%d ->"% (b,g), run(b,g))

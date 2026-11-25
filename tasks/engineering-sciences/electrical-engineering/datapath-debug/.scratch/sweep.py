import subprocess, re, os, shutil
base = "environment/rtl/axis_source.v"
src = open(base).read()
WSL = 'cd "/mnt/d/迅雷下载/ic-bench/tasks/engineering-sciences/electrical-engineering/datapath-debug" && '
def run(burst, gap, depth):
    s = open(base).read()
    s2 = re.sub(r"parameter integer NBEATS = \d+", "parameter integer NBEATS = 5200", s)
    s2 = s2.replace("    reg [15:0] n;", "    parameter integer BURST = %d;\n    parameter integer GAP = %d;\n    reg [15:0] n;\n    reg [7:0] ph;\n    wire want = (ph < BURST);" % (burst, gap))
    s2 = s2.replace("if (!valid) begin", "if (!valid && want) begin")
    s2 = s2.replace("            end else if (retire) begin", "            end else if (retire) begin")
    s2 = s2.replace("                end\n            end\n        end\n    end", "                end\n            end\n            ph <= (ph == BURST+GAP-1) ? 8'd0 : ph + 8'd1;\n        end\n    end")
    s2 = s2.replace("            credit <= 1'b0;\n            done   <= 1'b0;", "            credit <= 1'b0;\n            done   <= 1'b0;\n            ph     <= 8'd0;")
    open("/tmp/as.v","w").write(s2)
    shutil.copy("/tmp/as.v", ".scratch/as.v")
    cmd = WSL + "iverilog -g2012 -o /tmp/dp/sim tests/tb_top.v .scratch/as.v $(ls environment/rtl/*.v | grep -v axis_source) && /tmp/dp/sim"
    out = subprocess.run(["wsl","-e","bash","-lc",cmd],capture_output=True,text=True).stdout
    m = re.search(r"TOP_OK=(\d+) TOP_ERR=(\d+) TOP_BEATS=(\d+)", out)
    return m.groups() if m else out
for b,g in [(96,64),(48,64),(32,96),(24,128),(200,32)]:
    print(b,g,run(b,g,16))

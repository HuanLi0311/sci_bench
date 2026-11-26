"""Package the full booth task/evidence without other tasks or credentials."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import zipfile


def main():
    repo = Path(__file__).resolve().parents[3]
    cua = repo / "tasks/cua"
    task = cua / "booth-clearance"
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d_%H%M%S")
    target = repo.parent / f"booth-clearance_task-and-traces_{stamp}.zip"
    partial = target.with_suffix(".zip.partial")
    assert not target.exists() and not partial.exists()
    entries, directories, generated = {}, set(), {}

    def include(path):
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            return
        if path.is_symlink():
            raise RuntimeError(f"Unexpected symlink: {path}")
        name = "ic-bench/" + path.relative_to(repo).as_posix()
        if path.is_dir():
            directories.add(name.rstrip("/") + "/")
        elif path.is_file():
            entries[name] = path

    include(task)
    for path in task.rglob("*"):
        include(path)
    for path in (cua / "tools").rglob("*"):
        include(path)
    include(cua / "crate-lookdev/authoring/base-image.md")
    for folder in (cua / "evaluation").iterdir():
        if not folder.is_dir():
            continue
        if ("final-booth-clearance" in folder.name or "codex-runtime-smoke" in folder.name
                or folder.name == "20261126T105010Z-all-tasks-final-qc"):
            include(folder)
            for path in folder.rglob("*"):
                include(path)
        elif "scene-probes" in folder.name:
            for path in folder.rglob("*"):
                parts = path.relative_to(folder).parts
                if (len(parts) == 1 or parts[0].startswith("booth-")
                        or (parts[0] == "grader-source" and len(parts) > 1 and parts[1] == "booth-clearance")):
                    include(path)
    include(cua / "evaluation/credential-audit-final.json")

    def derived(name, data):
        generated[name] = data.encode("utf-8") if isinstance(data, str) else data

    def derived_json(name, value):
        derived("ic-bench/tasks/cua/" + name, json.dumps(value, indent=2) + "\n")

    calibration = json.loads((cua / "evaluation/gradient-calibration.json").read_text(encoding="utf-8"))
    calibration["measurements"] = [r for r in calibration["measurements"] if r["task"] == "booth-clearance"]
    derived_json("evaluation/gradient-calibration.json", calibration)
    regression = json.loads((cua / "evaluation/gradient-regression.json").read_text(encoding="utf-8"))
    regression["checks"] = [r for r in regression["checks"] if r["trusted"].startswith("booth-clearance/")]
    derived_json("evaluation/gradient-regression.json", regression)
    index = [r for r in json.loads((cua / "run-index.json").read_text(encoding="utf-8")) if r["task"] == "booth-clearance"]
    derived_json("run-index.json", index)
    current = json.loads((cua / "current-validation.json").read_text(encoding="utf-8"))
    derived_json("current-validation.json", [r for r in current if r["task"] == "booth-clearance"])
    lines = ["# Booth-clearance captured runs\n",
             "All stored booth runs are included, including failures and superseded snapshots. Only matching current-source records validate the final task.\n",
             "| Run | Kind | Reward | State |", "|---|---|---:|---|"]
    for row in index:
        lines.append(f"| [{Path(row['run']).name}]({row['run']}/run.json) | {row['kind']} | {row['reward']} | {row['classification']} |")
    derived("ic-bench/tasks/cua/RUNS.md", "\n".join(lines) + "\n")
    derived("ic-bench/tasks/cua/EVIDENCE.md", """# Booth evidence

See [current validation](booth-clearance/authoring/calibration/VALIDATION.md),
[raw runs](RUNS.md), [model inventory](booth-clearance/authoring/model-attempts.json),
[hardening audit](booth-clearance/authoring/calibration/HARDENING.md) and
[colour correction](booth-clearance/authoring/calibration/COLOR_SPACE.md).

Original commands, UTC times, exit codes, source/input hashes, stdout/stderr,
metrics and rewards are retained. NOP and negative mutations are separate.
The package-level indices/regression cases are filtered to this task; original
files inside booth-clearance are copied byte-for-byte. The shared base-image
recipe is in crate-lookdev/authoring/base-image.md; no other task data is included.
""")
    derived("README_PACKAGE.md", """# booth-clearance：题目与完整轨迹包

本包包含完整题目、素材、参考成品、评分代码及所有本地展台测评记录。
其他题目数据未打入；crate-lookdev 目录只有共享基础镜像说明。

当前结果：Oracle=1（22/22）、真实 NOP=0、8 个负例全为 0；
同一份模型产物复评=1（22/22）。旧版误判、意外通过、故障及备份全部保留。

先看 ic-bench/tasks/cua/booth-clearance/：

- instruction.md：题面；environment/materials/：全部素材。
- solution/：正式 .blend、两张成品图、manifest 和 Oracle 入口。
- tests/：完整评分器及回归检查。
- authoring/calibration/VALIDATION.md：当前结果和原始日志/metrics/reward 链接。
- authoring/model-attempts.json：两次模型尝试、精确配置、结果、步数口径。
- authoring/runs/20261126T084651Z-model-codex-terminal/raw-rollout/：原始 JSONL。
- 同一 run 的 observations/README.md：13 帧原始观测、SHA、事件行号和缩略图。
- ../RUNS.md：本题全部运行索引。

模型为 Codex CLI 0.172.0 / gpt-6.1-sol / high / 单 agent / 7200 秒预算。
正式尝试包含 88 个 agent item、73 次工具请求、13 帧内嵌图像观测。
它生成了全部产物，最后因 API 429 退出 1；产物通过与进程正常收尾分开记录。
这是 terminal baseline，gui_compliant=false，不宣称严格 GUI/CUA 成功。
第一轮缺 companion host 的环境故障也完整保留，不是 NOP 或模型能力失败。
模型产物未被修改；旧 0 与公平修复后 1 的 .blend SHA 相同。

本次修复包含背景稀释的 SSIM 漏检、真实入口/视锥、尺寸和支撑、
副色实际赋面、未使用材质槽、Empty 误拒及线性 RGB/sRGB 混比。
参考颜色修正前后几何 SHA 不变，旧成品和照片永久备份。

解压后运行 python VERIFY.py，校验全部文件 SHA。
进入 ic-bench 后可运行：

    python tasks/cua/booth-clearance/tests/test_rubric.py
    python tasks/cua/tools/check_render_metric.py

该 ZIP 的图像回归集是展台子集，使用不可变运行输入，不需要其他题目。
WSL 内完整 Docker QC：

    python3 tasks/cua/tools/sanity_check.py booth-clearance

运行需要已有 Docker、blender-bench:gui/对应任务镜像；配方及实际 image ID 已记录。
不含 Docker 镜像、Codex 二进制或任何认证配置。上述校验/QC 不调用模型 API。
重新运行模型需要自备认证；本包不会自动重试受限流影响的模型。

MANIFEST.json 记录每个文件的 SHA、大小和来源。原始题目/证据按字节保留，
只有本包级索引、说明和单题回归清单为便携打包生成的派生文件。
""")
    derived("VERIFY.py", """from pathlib import Path
import hashlib,json,sys
root=Path(__file__).resolve().parent
manifest=json.loads((root/'MANIFEST.json').read_text(encoding='utf-8'))
errors=[]
for item in manifest['files']:
    path=root/item['path']
    if not path.is_file() or path.stat().st_size!=item['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:
        errors.append(item['path'])
print('PASS' if not errors else 'FAIL',len(manifest['files']),'files')
for path in errors: print(path)
sys.exit(bool(errors))
""")
    manifest = []
    with zipfile.ZipFile(partial, "w", zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as archive:
        for name in sorted(directories):
            archive.writestr(name, b"")
        for name, path in sorted(entries.items()):
            if name in generated:
                continue
            content = path.read_bytes()
            archive.writestr(name, content)
            manifest.append({"path": name, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest(), "source": "workspace byte-for-byte"})
        for name, content in sorted(generated.items()):
            archive.writestr(name, content)
            manifest.append({"path": name, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest(), "source": "package-derived"})
        archive.writestr("MANIFEST.json", json.dumps({"created_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "task": "booth-clearance", "file_count": len(manifest), "files": manifest}, indent=2).encode())
    print("ARCHIVE_WRITTEN", partial.name, flush=True)
    with zipfile.ZipFile(partial) as archive:
        assert archive.testzip() is None
        for item in manifest:
            assert hashlib.sha256(archive.read(item["path"])).hexdigest() == item["sha256"], item["path"]
        assert "ic-bench/tasks/cua/booth-clearance/authoring/runs/20261126T103358Z-final-nop/submission/" in archive.namelist()
        assert "ic-bench/tasks/cua/booth-clearance/solution/booth.blend" in archive.namelist()
    os.replace(partial, target)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix(".zip.sha256").write_text(digest + "  " + target.name + "\n", encoding="utf-8")
    report = {"path": str(target), "bytes": target.stat().st_size, "sha256": digest, "files": len(manifest), "archive_crc": "PASS", "every_member_sha256": "PASS", "empty_NOP_submission_directory": "PRESENT"}
    target.with_suffix(".zip.verify.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True), flush=True)


if __name__ == "__main__":
    main()

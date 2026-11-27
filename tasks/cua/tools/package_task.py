"""Create a self-contained ZIP for one or more CUA tasks.

The archive keeps the task layout, Docker build contexts, reference output,
verifier, materials, and QC evidence.  It deliberately omits Python caches,
Blender ``.blend1`` backups, and transient verifier work directories.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import stat
import textwrap
import zipfile


ROOT = Path(__file__).resolve().parents[1]
TASKS = {"skateboard-prop", "spider-gait"}
SKIP_DIRS = {"__pycache__", ".git"}
SKIP_SUFFIXES = {".pyc", ".blend1"}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def should_skip(path: Path, task: Path) -> bool:
    rel = path.relative_to(task)
    if any(part in SKIP_DIRS for part in rel.parts) or path.suffix in SKIP_SUFFIXES:
        return True
    # GUI evidence contains large, disposable X11 and verifier work trees;
    # run.json, raw logs, grader snapshots and metrics stay in the archive.
    if "verifier-tmp" in rel.parts:
        return True
    if "verifier" in rel.parts and any(part.startswith("work-") for part in rel.parts):
        return True
    return False


def zipinfo(name: str, source: Path, data: bytes) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name)
    info.date_time = dt.datetime.now().timetuple()[:6]
    mode = stat.S_IMODE(source.stat().st_mode)
    info.external_attr = (mode or 0o644) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    return info


def package(task_name: str, output_dir: Path) -> Path:
    task = ROOT / task_name
    if not task.is_dir():
        raise SystemExit(f"task directory missing: {task}")
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d_%H%M%S")
    target = output_dir / f"{task_name}_qc_package_{stamp}.zip"
    partial = target.with_suffix(".zip.partial")

    entries: dict[str, bytes] = {}
    sources: dict[str, Path] = {}
    for path in sorted(task.rglob("*")):
        if path.is_file() and not should_skip(path, task):
            name = f"ic-bench/tasks/cua/{task_name}/{path.relative_to(task).as_posix()}"
            entries[name] = path.read_bytes()
            sources[name] = path
    for path in (ROOT / "SANITY_LIST.md", ROOT / "tools" / "sanity_check.py"):
        name = f"ic-bench/tasks/cua/{path.relative_to(ROOT).as_posix()}"
        entries[name] = path.read_bytes()
        sources[name] = path

    readme_name = "README_PACKAGE.md"
    readme = textwrap.dedent(f"""
        # {task_name} 独立质检包

        本包保留任务的 Docker build context、材料、参考解、verifier、
        authoring provenance/calibration 和最终 QC 证据，可在已有
        `blender-bench:gui` 基础镜像的 WSL Docker 中独立运行。

        ```bash
        python3 VERIFY_PACKAGE.py
        python3 ic-bench/tasks/cua/tools/sanity_check.py {task_name}
        docker build -t {task_name}-env ic-bench/tasks/cua/{task_name}/environment
        docker build -t {task_name}-tests ic-bench/tasks/cua/{task_name}/tests
        ```

        参考解验证：`authoring/calibration/VALIDATION.md`；解包后 `solution/solve.sh`
        可把参考产物复制到容器的 `/app/out`。本包不含凭据，瞬态 X11/verifier
        work 目录、Python 缓存和 `.blend1` 备份已剔除。
    """).strip() + "\n"
    entries[readme_name] = readme.encode("utf-8")
    sources[readme_name] = task / "README.md"

    manifest = [
        {"path": name, "bytes": len(data), "sha256": sha256(data),
         "source": str(sources[name]) if name in sources else "package-derived"}
        for name, data in sorted(entries.items())
    ]
    manifest_data = json.dumps({
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "task": task_name,
        "file_count": len(manifest),
        "files": manifest,
    }, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    verifier = textwrap.dedent("""
        from pathlib import Path
        import hashlib, json, sys
        root = Path(__file__).resolve().parent
        manifest = json.loads((root / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
        bad = []
        for item in manifest["files"]:
            p = root / item["path"]
            if not p.is_file() or p.stat().st_size != item["bytes"]:
                bad.append(item["path"])
                continue
            digest = hashlib.sha256(p.read_bytes()).hexdigest()
            if digest != item["sha256"]:
                bad.append(item["path"])
        print("PASS" if not bad else "FAIL", len(manifest["files"]), "files")
        for path in bad:
            print(path)
        sys.exit(bool(bad))
    """).strip() + "\n"

    with zipfile.ZipFile(partial, "w", allowZip64=True) as archive:
        for name, data in sorted(entries.items()):
            archive.writestr(zipinfo(name, sources[name], data), data)
        archive.writestr(zipfile.ZipInfo("PACKAGE_MANIFEST.json"), manifest_data)
        archive.writestr(zipfile.ZipInfo("VERIFY_PACKAGE.py"), verifier.encode("utf-8"))
    with zipfile.ZipFile(partial) as archive:
        assert archive.testzip() is None
        for item in manifest:
            assert sha256(archive.read(item["path"])) == item["sha256"], item["path"]
    partial.replace(target)
    digest = sha256(target.read_bytes())
    target.with_suffix(".zip.sha256").write_text(f"{digest}  {target.name}\n", encoding="utf-8")
    target.with_suffix(".zip.verify.json").write_text(json.dumps({
        "path": str(target), "bytes": target.stat().st_size,
        "sha256": digest, "files": len(manifest),
        "archive_crc": "PASS", "every_member_sha256": "PASS",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"task": task_name, "path": str(target),
                      "bytes": target.stat().st_size, "files": len(manifest),
                      "sha256": digest}, ensure_ascii=False))
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("tasks", nargs="+", choices=sorted(TASKS))
    parser.add_argument("--output-dir", type=Path, default=Path.cwd())
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for task_name in args.tasks:
        package(task_name, args.output_dir)

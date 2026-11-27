# SCI Bench

当前 `branch` 仅保留以下三个 task。保留顺序依据本机 `D:\benchmark`
任务文件夹的创建时间，时区为 Asia/Shanghai。

| Task | 内容 | 本地创建时间 |
|---|---|---|
| [pose-repair](tasks/cua/pose-repair/README.md) | 角色多视角姿态修复（原题 4） | 2026-11-27T20:42:53.971584+08:00 |
| [fight-retarget](tasks/cua/fight-retarget/README.md) | 双人同屏格斗重定向（原题 3） | 2026-11-27T20:42:53.255164+08:00 |
| [microscope-focus](tasks/cua/microscope-focus/README.md) | 显微镜装配与对焦（原题 5） | 2026-11-27T19:45:33.096933+08:00 |

每个 task 的题面、Docker 环境、参考解和独立 verifier 均在对应目录中。
运行方式和 sanity 证据以各 task 自带的 README、`instruction.md`、
`authoring/calibration/` 和 `authoring/runs/` 为准。

通用规范见 [SANITY_LIST.md](SANITY_LIST.md)。本次清理仅删除旧任务包，
三个保留 task 的内容保持原样；通用工具和规范文档保留。
本地创建时间的选择记录见 [RETAINED_TASKS.json](tasks/cua/RETAINED_TASKS.json)。

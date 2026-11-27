# 第 5 题交付与 sanity 记录

日期：2026-11-27（Asia/Shanghai）。正式任务：`tasks/cua/microscope-focus`，对应仓库 README §4.5。

本地实现位于 `D:\benchmark`。该目录检测到其他聊天并行改动，因此发布使用独立 Git 元数据和暂存区；发布基线为远端 main `7d400f8737e322943ac3ac0ffd5978f4a1370f4b`，仅新增显微镜任务及必要的通用 sanity 检查器支持。其他人的分支、暂存区与任务文件未被提交到本次变更。

源码清单：`authoring/source-manifest.json`，SHA-256 `8dff7c267e17428e7eecf33a0d1d827943e8dcd36a012144c0c9c7fef775daf0`。这是逐文件实际字节摘要，不冒称 Harbor 官方注册 manifest。每次运行还保存当前 tests 与 solution 的独立摘要及 grader-source 快照；仓库总检查已验证所有最终记录与当前源码一致。

## 实现与输入

离线 Three.js 0.169.0/OrbitControls，Xfce/Xvfb/noVNC 桌面，1920×1080；实际镜片/载物台运动、两阶段笛卡尔薄透镜成像、真实光线几何、实/虚像与无穷远、任意本地样本映射、三组状态回放及保存重载重置。资料含三张带真实地标投影的 1280×960 参考图、光学 PDF、两个 1024² 原创样本、三张 1280×720 目标图、空白 starter、完整规范和 JSON Schema；全部原始图形为 CC0，Three.js/OrbitControls 为 MIT，使用系统字体。

Agent 镜像仅复制 environment 白名单；参考解在执行时注入，不在镜像中。Verifier 从独立 tests 上下文构建，只接收 `/app/out`，浏览器执行提交代码而 Node/Python 不导入它。实际世界矩阵、光线顶点与画布由可信 driver 提取，独立 reciprocal 形式透镜方程及图像映射进行核验。未知样本服务只允许一个 PNG，不暴露其他 fixture。

## 最终当前源码结果

后端：WSL2 Ubuntu 24.04 内直接 Docker；4 CPU、8192 MiB、512 PIDs，verifier nofile=1024，网络 `none`。正式入口 `/tests/test.sh`；agent 7200 秒、verifier 600 秒，浏览器总时限 240 秒。正常候选失败写唯一二元 reward.txt；可信 fixture/driver 故障非零退出且无 reward。

| 用例 | verifier 退出码 | reward | 用时（秒） |
|---|---:|---:|---:|
| fixture-fault | 1 | absent | 3.44 |
| negative-bool | 0 | 0 | 3.96 |
| negative-duplicate-key | 0 | 0 | 3.68 |
| negative-fixed-sample | 0 | 0 | 23.21 |
| negative-frozen-focus | 0 | 0 | 23.93 |
| negative-nan | 0 | 0 | 3.77 |
| negative-static-optics | 0 | 0 | 25.14 |
| negative-symlink | 0 | 0 | 3.64 |
| negative-wrong-sign | 0 | 0 | 24.16 |
| negative-wrong-version | 0 | 0 | 3.93 |
| nop | 0 | 0 | 4.93 |
| oracle | 0 | 1 | 25.39 |
| oracle-repeat | 0 | 1 | 25.57 |

两次 oracle 都在全新 agent 容器执行 solve.sh，再仅导出 out 到全新 verifier；不是历史正确产物回放。15 项全部通过。NOP 只执行 `/bin/true`，输出为空、求解步骤为零。四个科学负例分别被 R05、R13、R04、R14 拒绝；五个格式/类型/文件负例被 R01 拒绝。可信故障注入预放旧 reward=1 后破坏 truth.json，test.sh 清除旧分数并退出 1，没有生成新 reward。近焦两侧、物镜无穷远、目镜无穷远、零物距、1 mm 光学扰动、额外复合扰动和未知棋盘在两次 oracle 的正式 driver 中运行。

总检查：`python3 tasks/cua/tools/sanity_check.py microscope-focus` 的 14 个检查项全部 PASS，见 `authoring/runs/pack-static.log`。本地执行使用相同定稿 checker 的隔离副本并仅覆盖 ROOT 路径，以免覆盖共享仓库的工具文件。检查器仅增加该任务的负例及 Web3D 入口映射，并用 AST 正确识别 critical 字符串。

默认桌面、X11、HTTP、noVNC 与 WebGL2 已实际冷启动；截图 `authoring/runs/gui-desktop.png`。运行时外网连接被拒绝，见 `isolation.log`。光学 PDF 已用 Poppler 渲染并目检；三视图已目检。

## 镜像与复现

基础镜像固定 `mcr.microsoft.com/playwright:v1.56.1-noble@sha256:f1e7e01021efd65dd1a2c56064be399f3e4de00fd021ac561325f2bfbb2b837a`；Node v22.20.0，Playwright 1.56.1 自带 Chromium；agent 与 verifier 同一浏览器来源。Verifier numpy==2.2.6、Pillow==11.2.1。PyPI 直连下载超时后改用清华镜像，版本未变，仅构建期联网。Python 作者工具的独立依赖版本记在 authoring/requirements.txt。

- `cua-qc-microscope-focus-env`: `sha256:87a588aaf4050c9c17506c399a5f9dac783548c5bbaf215da67620a061247ac4` (4084505036 bytes)
- `cua-qc-microscope-focus-tests`: `sha256:057e6712537cf1b7f3ec238349a1b2a782b56b491d76a379e74055c99d3bde46` (3898109164 bytes)

重跑：在任务目录执行 `python3 authoring/run_sanity.py`。该脚本从独立 contexts 构建并执行上表全部用例。构建日志、镜像 ID、完整 stdout、reward、metrics、CTRF、grader-source 和各产物均在 `authoring/runs`。最终上下文构建复用了已下载依赖缓存；首次本机已从官方 digest 下载并构建依赖。未声明另一台干净机器的构建验证或 apt 包仓库快照锁定。

## 范围与未验证项

结论：本机直接 Docker 的功能、隔离、数值与奖励语义 sanity 通过。未运行正式 Harbor 调度、模型推理、5 次强模型难度标定或 GUI 模型轨迹；不能从本次结果推导目标通过率。尚无独立复核者签字，因此未宣称满足采购流程的独立接收门槛。浏览器观测可检测常见静态/自报答案作弊，不构成对恶意 JavaScript 完全伪造所有浏览器 API 的安全证明。只模拟理想傍轴薄透镜，不含像差/衍射。

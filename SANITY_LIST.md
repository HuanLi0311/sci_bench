# Environment Sanity Checklist

This checklist is the pre-merge sanity pass for Terminal-Bench-Science tasks. It is intended to catch environment, isolation, fixture, and verifier failures before interpreting an agent reward as a scientific result.

Use one checklist per task and record the commit SHA, image digests, command, exit code, and artifact paths. A failed infrastructure check must be reported as an environment error; it must not be converted into a candidate reward of `0`.

## 1. Repository and task structure

- [ ] The task has exactly the expected top-level files: `instruction.md`, `task.toml`, `environment/`, `tests/`, `solution/`, and any documented `authoring/` material.
- [ ] `task.toml` parses with Python `tomllib`.
- [ ] `artifacts` is top-level, uses absolute paths, and names every file the verifier needs.
- [ ] `[verifier].environment_mode = "separate"` is set for a separate verifier task.
- [ ] The instruction, `SPEC.md`, tests, solution, README, and task metadata describe the same interface, limits, and acceptance behavior.
- [ ] The final instruction suffix contains the task timeout and the standard no-cheating text.
- [ ] No generated caches, local credentials, private logs, or unrelated files are included in the task package.

## 2. Network and dependency policy

- [ ] Agent environment declares `network_mode = "public"` when the benchmark policy requires agent internet access.
- [ ] Verifier environment declares `network_mode = "no-network"`; use an explicit allowlist only when a verifier genuinely requires one host.
- [ ] The verifier does not install packages, download data, call APIs, or fetch model weights at runtime.
- [ ] All verifier dependencies are pinned and installed in `tests/Dockerfile` at image-build time.
- [ ] Agent-visible data and verifier-only data come from separate allowlists. No `solution/`, `tests/`, `authoring/`, hidden device data, answer arrays, or reference parameters are copied into `environment/Dockerfile`.
- [ ] Any external dataset or model artifact is repository-owned or from the approved Harbor source, pinned immutably, and checksum-verified.
- [ ] A runtime network probe from the verifier fails as expected; a build-time dependency install is the only permitted network use in the verifier image construction.

## 3. Image and filesystem isolation

- [ ] The agent image builds from `environment/Dockerfile` alone and starts successfully with the declared resources.
- [ ] The verifier image builds from `tests/Dockerfile` alone and starts successfully with the declared resources.
- [ ] The verifier container cannot read the agent worktree, `/solution`, `/authoring`, hidden inputs, or files outside the declared artifact mount.
- [ ] The agent container cannot read verifier scripts, hidden answers, device truth, or test fixtures.
- [ ] The verifier receives only the declared artifact at the exact absolute path expected by `test.sh`.
- [ ] Parent directories for declared artifacts are created in `tests/Dockerfile`.
- [ ] Declared output files are regular files. Any documented symlink restriction is stated in the instruction and tested explicitly.
- [ ] Submission size, archive member count, output size, file descriptor count, process count, CPU time, address space, and wall-clock limits are enforced consistently with the instruction.

## 4. Build and cold-start checks

- [ ] Build each image from a clean cache or record the cache state and image digest.
- [ ] Build succeeds without repository files outside the intended Docker build context.
- [ ] A clean container can import every required package and execute the documented entry point.
- [ ] The first invocation is within the declared timeout and resource budget; do not rely only on a warm interpreter or cached data.
- [ ] Rebuilding the same commit produces the same dependency versions, fixture hashes, and interface behavior.
- [ ] If a package download times out, classify it as a build/repository availability problem and retry with the approved mirror or wheelhouse before judging the scientific task.

## 5. Verifier and reward semantics

- [ ] `test.sh` writes exactly one binary reward: `1` for a passing candidate and `0` for a candidate that fails the stated contract or scientific checks.
- [ ] `reward.json` is absent unless intentionally supported; if both reward files exist, verify which one Harbor reads.
- [ ] Rich metrics and diagnostics use a separate filename such as `metrics.json` or `ctrf.json`.
- [ ] Candidate assertion failures and verifier/fixture/infrastructure failures have different exit paths.
- [ ] Missing, malformed, truncated, or internally inconsistent verifier metrics cause a non-zero infrastructure exit and do not write candidate reward `0`.
- [ ] A failing benchmark-owned fixture test is run before candidate grading or outside the candidate pytest selection.
- [ ] The reward agrees with the detailed report: reward `1` has no failed candidate checks, and reward `0` has an identifiable candidate failure.
- [ ] The no-op submission fails and the oracle/reference submission passes under the same image and verifier.
- [ ] Repeat the oracle at least twice when practical; mixed outcomes are recorded as flakiness rather than averaged away.

## 6. Contract and boundary probes

- [ ] Test empty legal inputs independently: empty point arrays, empty query/radius arrays, and both empty together. Check exact output shapes and dtypes.
- [ ] Test minimum and maximum legal numeric values, finite-value requirements, duplicate keys, wrong versions, malformed shapes, and non-regular output files.
- [ ] Test a legal input that changes one profile or configuration while keeping geometry fixed. The candidate must respond to the changed input.
- [ ] Test at least one additional valid parameterization or held-out packet beyond the visible examples.
- [ ] Test an invalid submission that should be rejected, and confirm that the rejection is attributable to the candidate contract rather than a harness exception.
- [ ] For every public promise in `SPEC.md`, identify at least one executable test. If a promise cannot be tested, either make it observable or remove it from the public contract.

## 7. Scientific and numerical checks

- [ ] Recompute the verifier's pass formula independently from its source, including units, normalization, reference generation, thresholds, and tolerances.
- [ ] Verify that the reference baseline is independent of the candidate and that thresholds were not fitted to a single reference implementation.
- [ ] Check absolute tolerance bands, not only relative tolerances; confirm they are meaningful at zero and near-zero values.
- [ ] Use finite-difference or conservation checks at multiple locations and scales, not only the fixed visible points.
- [ ] Check all required output arrays for finite **real** numeric dtype when the contract says real. `np.number` alone is insufficient because it includes complex dtypes.
- [ ] Check boundary conditions, profile monotonicity, normalization, and any declared symmetry or topology directly.
- [ ] Include negative controls for wrong branches, constant profiles, missing boundary conditions, or other scientifically plausible shortcuts.


## 9. Final execution gate

- [ ] Run the repository static checks relevant to the task, including task fields, structure, Dockerfile sanity, network policy, test-file references, binary reward, and verifier output checks.
- [ ] Run clean Docker build, oracle, and no-op validation on the declared backend.
- [ ] Run adversarial or cheat trials when available; distinguish a successful legitimate solution from a verifier exploit.
- [ ] Inspect `verifier/` artifacts and failing assertions for every non-passing trial.
- [ ] Record the exact commit SHA and confirm all execution artifacts correspond to that SHA.
- [ ] Do not mark the task deliverable until all unresolved items are explicitly classified as candidate failure, infrastructure failure, unverified external dependency, or accepted limitation.

## Required evidence record

For each completed sanity pass, retain:

- task path and commit SHA;
- environment and verifier image identifiers;
- build commands and logs;
- oracle and no-op rewards;
- boundary/negative probe results;
- `ctrf.json`, metrics, reward file, and verifier stdout;
- resource and timing measurements;
- any skipped check with the reason and owner for follow-up.

---

## 10. 通用执行 SOP：RL 环境交付的快速 sanity 验收

本节适用于后续供应方交付的 RL / agent benchmark 环境。前面的 checklist 是检查项库；本节规定实际执行顺序和接收口径。不得因为存在未勾选项，就默认启动耗时的模型评测。

### 10.1 验收范围与停止条件

默认 sanity 只确认：环境能启动、接口契约一致、可信评分流程可执行、已知正例通过、典型错误提交失败、基础设施故障能够与候选失败区分。

- 默认不运行模型推理、模型通过率测试、长时间难度校准或跨随机种子研究。
- 已有可信正确产物时，可以先回放该产物验证评分链路。必须标记为“正确产物回放”，不能写成“本次冷启动 oracle 通过”。
- 参考解本身耗时较长时，记录其未执行状态与已采用的替代证据。只有验收范围明确包含全量求解时才继续运行。
- 当前检查通过后，不再无目的增加或重复测试；新增修改、失败结果或尚未解决的具体疑点才触发追加验证。
- sanity 通过不代表模型难度、科研新颖性、所有合法算法的公平性或跨初始化稳定性已经验证。

### 10.2 第一步：冻结交付范围与版本

1. 列出正式任务名称、目录和 manifest 登记项。CI 故障 fixtures、示例、历史实验和其他项目任务不计入采购数量。
2. 记录基线 commit、工作区未提交修改和实际交付文件。存在未提交修改时，以最终文件内容摘要标识版本，不能只引用 commit。
3. 核对每个正式任务的 instruction、SPEC、task 配置、agent Dockerfile、verifier Dockerfile、参考解和测试入口。
4. 审查工作区是否有其他人的修改；修复和打包只覆盖本次正式范围，不能整体覆盖或混入无关任务。

### 10.3 第二步：静态检查与接口对齐

先执行仓库已有静态检查，保留每项命令、退出码和日志。再人工核对以下关键点：

- 输出路径、产物类型、字段、数组形状、dtype、空输入、数值范围与所有 gating metrics 是否一致。
- agent 和 verifier 的网络策略、文件可见范围及产物传递白名单是否正确。
- verifier 依赖是否在构建期安装，运行时是否需要额外下载或外部服务。
- 开发与评分环境存在差异时，依赖、用户权限、内存/地址空间、CPU、进程、文件描述符和输出限制是否已在题面引用的规范中披露。
- 总验证时限能否覆盖全部调用：不能只检查单次 timeout。增加 probe 后，重新计算总工作量与准备开销。
- Windows 交付的 Linux shell 脚本是否为 LF；需要时用限定任务范围的 `.gitattributes` 固定行尾。
- 保持任务原有预算和评分条件；若与继承的 CI 发布/开发策略冲突，明确记录本地交付策略及理由，不暗改科学门槛来使检查变绿。

### 10.4 第三步：构建与运行容器

1. 优先使用任务声明的基础镜像和锁定依赖，记录镜像 ID、依赖版本、构建日志及是否使用缓存。
2. 下载失败应先归类为构建依赖可用性问题。可以使用镜像源或离线 wheelhouse，但须保持声明版本并记录实际构建方式。
3. 验证运行时禁网要求，并核对实际 Docker 网络配置；不能只检查配置文件中的文字。
4. 按声明的 CPU、内存和 verifier 内部限制运行正式入口。不能通过放宽限制来证明原配置通过。
5. 分离 agent 与 verifier，只传递声明的产物。若为诊断临时挂载源码或替换 verifier，必须与正式正例运行分开记录。
6. 直接 Docker 执行、正式 Harbor 作业调度、历史 CI 记录分别标记；三者不能互相冒称。

### 10.5 第四步：最小功能验证矩阵

| 类别 | 最小动作 | 期望结果 |
|---|---|---|
| 已知正例 | 快速参考解，或可信正确产物回放，运行正式 `test.sh` | reward=1，详细报告无候选失败 |
| 空提交 / NOP | 不生成声明产物 | 合法完成评分并给 reward=0；拒绝原因是候选未提交 |
| 契约边界 | 合法空输入、最小合法形状、主要数值边界 | 正确输入被接受，形状和 dtype 正确 |
| 类型与格式反例 | 按任务选择复数 dtype、NaN/Inf、布尔值、错版本、重复键、错形状等 | 按候选契约拒绝，不能依赖偶然的 harness 崩溃 |
| 输入响应 | 改变一个合法 profile 或配置，保持其他条件不变 | 忽略输入变化或硬编码原答案的提交被拒绝 |
| 科学负例 | 选择一个有代表性的错误分支、常量 profile 或简化解 | 被对应科学检查拒绝 |
| 可信故障注入 | 损坏 benchmark fixture；或让可信 verifier 成功退出但缺失/损坏 metrics | 非零基础设施退出，不新写候选 reward=0，也不能读取残留旧 reward 冒充结果 |

按任务接口选择有意义的 probe，不机械地把所有类型反例应用于所有任务。优先复用真实评分函数和真实入口；不要另外实现一个更宽松的“测试用评分器”。

### 10.6 第五步：检查 reward 与基础设施故障语义

必须区分以下两个边界：

- **候选产物缺失或非法**：属于候选失败，应按任务约定得到 reward=0。
- **可信 fixture、验证程序或其 metrics 缺失/损坏**：属于环境错误，应非零退出，并且不得写成普通候选零分。

仅检查 metrics 文件存在或设备名齐全不够。应检查对象结构、必需指标、类型、有限值及 verdict 自洽性。阈值计算尽量复用可信实现，避免复制门槛后发生漂移。

pytest 的失败数或进程非零退出本身不能说明是候选失败：必须检查具体异常来源。benchmark 自有 fixture 应在候选评分之外预检查；不要把可信期望值计算异常误报为候选未解题。

### 10.7 第六步：修复后做针对性复测与独立验收

1. 修复根因，并保留最小可运行回归检查；不要只删除触发缺陷的 probe 或放宽门槛。
2. 先重跑失败路径，再重跑受影响任务的正式入口和必要静态检查。未受影响的耗时测试不必反复运行。
3. 安排独立复核者或单独的验收智能体，检查最终源码与证据，并至少独立验证正例、NOP 和关键反例。主执行者不能替独立复核者写出“已通过”的结论。
4. 双方发现分歧时，先明确分歧对应的文件、命令和产物，再以可复现结果解决；修复后同步复核。
5. 以最终修订版达成接收结论。旧版本、旧实验或修复前的运行结果不能替代最终版本证据。

### 10.8 第七步：更新版本摘要并打包

- 在所有任务文件定稿后，用框架官方算法刷新 manifest digest；嵌套目录需确认同步命令确实找到任务，不能把“命令成功但没有更新”当作摘要一致。
- 包含正式任务源码、必要运行基础设施、验收报告、独立意见、关键原始日志、reward、metrics/CTRF 和逐文件 SHA-256。
- 排除 `.git`、凭据、生成缓存、未完成实验、无关任务及不应对外传播的宿主日志。
- 校验压缩包可以完整读取，归档文件与定稿源码一致，manifest 与任务内容一致；另写压缩包 SHA-256。
- 原始证据放入包内的相对路径，避免下游依赖验收机器上的绝对路径。

### 10.9 接收判定

| 判定 | 条件 |
|---|---|
| sanity 接收 | 必需正例、NOP、关键反例和故障区分达到预期；相关静态检查通过；版本及证据完整；独立复核意见一致 |
| 需整改后复验 | 正例被误判、错误提交得分、可信异常被计为零分、环境无法启动、隐藏答案泄漏、契约或资源预算冲突等仍未解决 |
| 范围内证据不足 | 必需链路受外部依赖等因素阻断；必须注明未验证项，不能宣称已通过 |

未运行模型推理是默认 sanity 范围，不单独构成失败。若采购另有冷启动、完整 Harbor 调度、科研正确性或模型难度指标，须单独列项，不能把这些项目从 sanity 结果中推导出来。

### 10.10 每次交付的简短记录模板

```text
日期 / 项目：
正式任务数量与名称：
基线 commit / 最终任务 digest：
验收范围：sanity；模型推理未运行 / 其他明确范围
构建平台、基础镜像 ID、依赖版本与缓存/离线安装说明：
本次修复：
正例：参考解实跑 / 产物回放；命令、结果、reward、证据路径
NOP：命令、结果、reward、证据路径
边界 / 负例：
基础设施故障注入：退出码、是否生成 reward、证据路径
静态检查：通过项 / 失败项 / 明确跳过项及原因
独立复核：复核者、独立执行项、结论、分歧处理
最终判定：sanity 接收 / 需整改 / 范围内证据不足
本轮未验证的能力：
交付包路径 / SHA-256 / 报告与原始证据相对路径：
```

## 11. CUA/Blender visual-task delivery gates

These checks apply when the task is sold or accepted as a computer-use/GUI benchmark, or when the deliverable contains a Blender scene plus rendered evidence.

### 11.1 Reproducible build inputs

- [ ] Every `FROM` image is pinned by an immutable OCI digest, and the exact image ID/digest is recorded in the delivery.
- [ ] The pinned base image, Blender binary version/hash, OS package sources, and any offline import procedure are supplied or explicitly excluded from the reproducibility claim.
- [ ] A clean-machine build is tested from the declared Docker contexts alone; cached local images are not the only evidence.
- [ ] Rebuilding after a cache purge yields the same verifier dependencies and fixture hashes.

### 11.2 Agent policy and GUI scope

- [ ] The task metadata, instruction, and container configuration agree on whether the agent may use a terminal, scripts, network, or GUI only.
- [ ] If the task is advertised as GUI/CUA, a successful terminal/script-only artifact is not counted as a GUI success; `gui_compliant` is recorded separately from artifact reward and checked against the allowed tool policy. Require a successful GUI trace only when this is an explicit procurement deliverable; do not launch new model inference as part of default sanity.
- [ ] Agent network access is disabled unless internet access is part of the stated task contract; verifier network access is independently tested as disabled.
- [ ] A terminal baseline is retained only as a separate diagnostic control and cannot satisfy the GUI success gate.

### 11.3 Blender scene and render authenticity

- [ ] Reopen the `.blend` with auto-execution disabled and verify required objects are non-empty meshes in an active scene.
- [ ] Check both delivered renders against independent re-renders from their named cameras, per RGB channel, with a structure/gradient metric that rejects constant or background-only substitutions.
- [ ] Verify camera position, lens/type, and camera direction toward the declared target; include a camera-rotated-away negative case.
- [ ] Verify every required material on an actually used, non-trivial display surface. A material declaration, unused slot, hidden helper face, or unrelated object must not satisfy a visual-brand requirement.
- [ ] For geometry constraints, use world-space evaluated meshes and test fixed reference planes/regions rather than movable helper markers.
- [ ] For applicable visual/geometry requirements, include negatives for resized/floating products, moved markers, closed openings, camera-away scenes, hidden or missing secondary colour, and substituted renders. Do not mechanically apply irrelevant probes to other tasks.

### 11.4 Evidence and package hygiene

- [ ] After any verifier change, rerun Oracle, true NOP, every required negative, and any model regrade against the new test-source hashes.
- [ ] Do not treat empty, malformed, timed-out, cancelled, or infrastructure-error metrics as candidate reward `0`; classify them separately and exclude them from current validation.
- [ ] Separate final current-source evidence from historical failures and temporary X11/verifier directories, or provide an explicit index that marks them non-authoritative.
- [ ] Re-extract the final archive and verify the manifest file count, byte sizes, SHA-256 values, JSON parseability, image/PDF signatures, and `.blend` readability from the extracted copy.
- [ ] The final archive hash, manifest hash, base-image digest, test-source hashes, commands, exit codes, and artifact paths are recorded together.


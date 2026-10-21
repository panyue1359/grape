# Grape CLI Development Record

## Requirement and scope

The traditional PinkViewer GUI has been replaced on the active development line by Grape, a headless INP/NTL command-line tool. The CLI exposes `inspect`, `validate`, `convert`, and `batch`, and writes VTK, VTU, and XDMF/HDF5. It supports Python 3.11–3.13 on Windows and Linux, with a Windows PyInstaller executable named `grape.exe`. Old tools and commands are not compatibility targets.

The first release may read complete files into memory. Streaming and performance optimization are deferred. Core runtime code must not depend on PyQt5, PyWebView, or Tkinter. Node IDs must be explicitly validated and remapped to dense indices; unknown element types must fail with clear diagnostics.

An external local reference project was used during development. Its machine-specific path is intentionally omitted; it is reference-only, and GUI code, `build/`, `dist/`, and large generated artifacts must not be copied.

## Design

### 三分量速度时间序列扩展（2026-10-21）

规范化标题精确等于 `VELOCITY`（忽略大小写）时，将每节点宽度解释为 `3 × 时间步数`，按 `vx0 vy0 vz0 vx1 vy1 vz1 ...` 排列；依据参考转换器 `infer_field_layout` / `reshape_procast_values` 和真实速度样例宽度 327、对应温度 109 步。其余标题按原单分量规则解释，速度模量不会因为包含 VELOCITY 单词而变为向量。

实现范围：`model.py` 的分类、记录解析和时间序列模型；`writers.py` 的 XDMF 向量属性与 HDF5 三列数组；CLI 原 `--ntl` 与 batch 自动路由。单步三分量速度也通过一帧 temporal collection 输出，只支持 XDMF。多文件必须步数一致；保留 ID 映射、命名和覆盖保护。验证包含乱序 ID、非对称三分量、跨行/相邻科学记数值、非法宽度/截断，以及真实样例和发布 EXE 转换。数学操作仅为数据重排，不改变数值、单位或坐标系；时间仍为步索引。内存开销增加至每节点每步三个 float64。

The implementation will separate CLI commands, INP/NTL parsing, an internal mesh/data model, validation/ID mapping, and output writers. Source node IDs remain distinct from output point indices. Connectivity is translated only through a validated deterministic map. Supported element types and output-format cell mappings are explicit; unsupported or unrepresentable types are errors, never silent omissions.

Commands:

- `inspect`: summarize input structure and counts.
- `validate`: parse and check identifiers, connectivity, and supported element semantics.
- `convert`: convert one input to a selected output format.
- `batch`: process multiple inputs with deterministic output naming and per-input results.

### Multiple time-series NTL support (2026-10-21)

`convert --format xdmf` must accept multiple `--ntl` inputs when every input is a scalar time series with the same number of steps and matching mesh node IDs. Each XDMF temporal grid contains every input field at the shared zero-based step index; HDF5 stores one node array per field and step. Single-step NTL fields remain disallowed in a time-series conversion. Unequal time-series lengths fail with a clear error rather than truncating, padding, or misaligning fields. If NTL titles collide, output attribute names are made unique using source filename stems.

Implementation boundary: extend the existing model/writer/CLI only; keep NTL parsing, mesh topology, current single-series behavior, VTK/VTU conversion, and batch manifest shape unchanged. Acceptance: unit tests inspect XDMF field presence and HDF5 values for multiple fields, CLI tests cover automatic routing, mismatched steps and scalar/time-series rejection, existing single-series tests stay green, and the full suite passes.

## Build and use

The distribution is named `grape-mesh-cli`; its import package remains `pinkviewer` for now. Install with `python -m pip install -e .`; add `.[build]` to install PyInstaller. The installed command is `grape` (the Python module entry remains `python -m pinkviewer`):

```text
grape inspect mesh.inp [field.ntl ...]
grape validate mesh.inp [field.ntl ...]
grape convert mesh.inp mesh.vtu --format vtu --ntl field.ntl
grape batch jobs.json
```

Batch manifests are JSON arrays containing `inp`, `output`, `format`, and optional `ntl` (an array), with relative paths resolved from the manifest directory. The Windows one-file build command is `pyinstaller --clean --onefile --name grape cli_entry.py` from the repository root; the resulting executable is `dist/grape.exe`. The maintained spec is `grape.spec`. Use a Windows Python environment for the Windows executable.

## Validation plan

Use TDD. Begin with package/CLI tests, then small INP/NTL fixtures whose node IDs are shuffled and non-contiguous. Prove exact source-ID-to-dense-index and element-connectivity mapping before implementing conversion of real data. Cover duplicate IDs, invalid IDs, missing node references, malformed records, and unknown element types. Test VTK, VTU, and XDMF/HDF5 output, batch behavior, and ensure the core has no GUI dependencies. Run the supported Python/platform matrix where available.

Current test command: `uv run --python 3.11 --with pytest --with h5py --with numpy --with-editable . python -m pytest -q`. Tests cover CLI help/batch, ID remapping, validation, VTK/VTU output, XDMF/HDF5 output and time series, and overwrite protection.

The package's user-facing name is Grape: distribution `grape-mesh-cli`, console command `grape`, and Windows binary `grape.exe`. The Python import namespace intentionally remains `pinkviewer` in this migration increment; it is an implementation detail and not a supported CLI command.

## Supported input subset and limitations

- INP: comma-separated `*NODE` records with exactly three coordinates and `*ELEMENT, TYPE=...` records are parsed. Supported types are `S3`, `CPS3`, `CPE3`, `S4`, `CPS4`, `CPE4`, `C3D4`, `C3D6`, and `C3D8`. Other INP sections are ignored; an unsupported `*ELEMENT` type fails. Continuation records, alternative coordinate dimensions, and arbitrary element families are not supported.
- NTL：规范化标题精确为 `VELOCITY` 时采用上述三分量速度约定（宽度/3 为步数），其余文件宽度 1 为单步标量、宽度 N 为 N 步标量。普通 `--ntl` 和 batch 自动识别。速度与标量时间序列可在实际步数相同时合并；单步标量暂不能与时间序列/速度混用。时间坐标仍是零基步索引。速度允许跨行及相邻科学记数值；无空格相邻格式要求带符号两位指数。其他多分量布局不属于支持范围。
- XDMF/HDF5 要求单一拓扑类型；VTK/VTU 支持混合已知单元但仅支持单步标量。速度（含单步）通过 temporal collection 以节点 Vector 输出，每步 HDF5 形状为 `(nodes, 3)`，标量形状保持 `(nodes,)`。
- NTL 字段名仅去除标题首部的 `ProCAST` 和尾部的 `RESULTS`（忽略大小写），保留中间物理量名称，以单个空格连接；去除后为空时使用文件名主干。单步和时间序列共用该规则。验收须检查发布 EXE 的实际转换产物，而不仅是源码测试；已有输出文件的字段名需单独更新。
- Output files are never overwritten. Source node and element IDs are retained as metadata in VTK/VTU/XDMF-HDF5.
- No Linux runtime/build execution was available in this Windows session; cross-platform support is declared but not yet demonstrated on Linux.

## Risks

- INP and NTL have dialects and optional constructs; only explicitly implemented syntax will be supported and unsupported constructs must produce actionable errors.
- Full in-memory reads limit the initial maximum dataset size.
- XDMF/HDF5 and VTK element conventions must be verified against downstream consumers; current tests validate topology and data arrays, not ParaView GUI rendering.
- INP 集合、材料和边界定义不在当前解析范围内。

## Execution log

- 2026-10-21 三分量速度交付：`model.py` 新增精确 VELOCITY 标题识别，宽度除以 3 获取步数；时间序列模型保存分量数，速度形状 `(steps, nodes, 3)`，支持跨行、E/D 指数及无空格相邻两位指数科学记数值。`writers.py` 输出节点 Vector 和每步三列 HDF5；`--ntl` / batch 保持原参数，支持同时间轴标量+速度合并。29 项测试通过。暂存 EXE 完成真实 `Benchmarkv.ntl` 转换到 `output/grape/Benchmark_velocity.xdmf` / `.h5`（114956 节点、548500 四面体、109 步、3 分量）。独立 `UDF/validate_velocity.py` 对全部帧的节点 1、2（首个非零节点）、114956 逐分量比对源数据通过。实际 Windows `pvpython UDF/validate_velocity_paraview.py output/grape/Benchmark_velocity.xdmf --steps 109 --nodes 114956` 通过，首尾帧均识别为三分量向量；首帧模长范围 `(0, 0.3981134)`，末帧 `(0, 0)`。已更新 `dist/grape.exe` 和同目录手册，旧 EXE 备份 `dist/grape.exe.backup-velocity-20261021-201118`。发布 SHA-256 为 `748EF58BF47D3C05E4CA2F69E905E777F273DE76044942E027FF23DD9D3426FF`。测试样例新增 `tests/fixtures/velocity_timeseries.ntl`；实现计划及验收见 `docs/superpowers/plans/2026-10-21-velocity-timeseries.md`。未验证物理单位/物理时间，未修改现有 GUI 会话。
- 2026-10-21 字段名修复：确认现有 `output/grape/Benchmark_ft.xdmf` 和 `Benchmarkc.vtu` 仍保存完整 ProCAST 标题；旧字段名规则也遗漏两词标题的 `RESULTS`。现改为按首部 `ProCAST`、尾部 `RESULTS` 精确清理（忽略大小写），单步与时间序列共用。24 项测试通过，包括 VTK/VTU/XDMF 转换字段名检查。通过 `python -m PyInstaller --noconfirm --distpath .build-grape-fixed --workpath .build-grape-work-fixed grape.spec` 构建后，实际 EXE 单步 VTU 输出为 `Temperature`，两步 XDMF 每步输出为 `SHRINKAGE POROSITY`，配套 HDF5 存在。已更新 `dist/grape.exe` 和同目录手册，旧 EXE 保存在 `dist/grape.exe.backup-fields-20261021-195642`。现有结果另存为 `Benchmark_ft_clean_names.xdmf`（218 个字段属性更新、引用原 `Benchmark_ft.h5`）和 `Benchmarkc_clean_names.vtu`（1 个字段更新）；核对 XML 数据文本完全一致，原文件保留。验证范围为文件结构与数据，未操作 ParaView GUI。
- 2026-10-21: Created and reviewed the migration plan. Archived legacy GUI revision `5e49da11993f6ded9f9867d4a440ef9aa26f55c6` with local branch `legacy-viewer` and tag `legacy-viewer-v1`; removed legacy GUI modules and assets from the active migration branch after explicit confirmation.
- 2026-10-21: Added package skeleton, INP/NTL model/parser, CLI commands, VTK and VTU writers, and TDD tests. Twelve tests pass on Python 3.11.7. Verified non-contiguous IDs 40, 10, 90 map to point indices 0, 1, 2; element topology maps to (0, 1, 2); NTL values follow IDs as (4, 1, 3). Existing output paths are protected against overwrite.
- 2026-10-21: Parsed the reference 40 MB INP without copying it: 114,956 nodes and 548,500 C3D4 elements.
- 2026-10-21: Created `.venv` with `uv` and installed NumPy, h5py, pytest, and PyInstaller. XDMF/HDF5 round-trip checks pass with exact connectivity/source IDs/field values. PyInstaller one-file Windows build and EXE help smoke test pass. The test suite passes on Python 3.11.7, 3.12.13, and 3.13.5. Linux execution was not available in this session.
- 2026-10-21: Final review documented the supported INP/NTL subset and homogeneous-only XDMF limitation, added VTK source-element IDs, and ignored local environment/build/cache outputs without deleting them.
- 2026-10-21: Renamed the distribution, console command, CLI help, and Windows executable to Grape. Verified `dist/grape.exe --help` reports `usage: grape`; the internal import package remains `pinkviewer`.
- 2026-10-21: Added TDD-tested automatic NTL classification/routing. `inspect` reports kind, scalar component count and steps; `validate` checks mapping; `convert --ntl` and batch automatically route width 1 to scalar output and wider records to temporal XDMF/HDF5 (multiple same-length time-series NTLs per job; XDMF only). Converted benchmark as `output/Benchmarkg_temperature_timeseries_auto.xdmf` and `.h5`: 114,956 nodes, 548,500 tetrahedra, 109 steps. Full suite: 21 tests passed before final binary rebuild.
- 2026-10-21: Extended CLI and XDMF/HDF5 writer to merge multiple same-length scalar time-series NTLs as separate attributes in one temporal collection. Added CLI acceptance tests for merged field names/values and step-count mismatch; updated manual. Restored Python startup by converting the generated editable `.pth` project path to ASCII `\uXXXX` escapes (original backed up as `.pth.bak-utf8`); the full suite then passed, 22 tests.
- 2026-10-21: Installed PyInstaller 6.22.3 into the project virtual environment and rebuilt the Windows one-file binary. The staged executable passed `--help` and a two-field/two-step XDMF/HDF5 smoke test with exact second-field values. Replaced `dist/grape.exe` (24,176,329 bytes, SHA-256 `0FF2F8F54757D2EC294791D1DA79B372781A7034C571AF5EEF3B44DC1BAF480A`) after preserving the previous binary as `dist/grape.exe.backup-20261021-150407`.
- Archive branch/tag creation and legacy GUI deletion each require separate explicit confirmation before execution.
- No commits, pushes, or merges are authorized by this development record.

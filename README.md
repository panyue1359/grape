# Grape

Grape 是一个专用于转换 ProCAST 导出结果的无界面命令行工具。它读取由 ProCAST Viewer 导出的 `.ntl` 场文件和由 ProCAST Mesh 导出的 `.inp` 网格文件，并将网格、节点标量和三分量速度时间序列转换为 VTK、VTU 或 XDMF/HDF5。Grape 不是通用的 INP/NTL 转换工具，也不承诺兼容其他软件生成的同扩展名文件。

Grape is a headless command-line tool dedicated to converting results exported by ProCAST. It reads `.ntl` field files exported from ProCAST Viewer and `.inp` mesh files exported from ProCAST Mesh, then converts meshes, nodal scalar fields, and three-component velocity time series to VTK, VTU, or XDMF/HDF5. Grape is not a general-purpose INP/NTL converter and does not claim compatibility with files of the same extensions produced by other software.

<!-- Badge Row 1: Core Info -->
[![GitHub](https://img.shields.io/badge/GitHub-panyue1359-181717?logo=github)](https://github.com/panyue1359/grape)
[![Version](https://img.shields.io/badge/version-0.1.0-orange)](https://github.com/panyue1359/grape)

<!-- Badge Row 2: Tech Stack -->
[![Python](https://img.shields.io/badge/Python-3.11--3.13-3776AB?logo=python&logoColor=white)](https://www.python.org/)

<!-- Badge Row 3: Platforms -->
[![Windows](https://img.shields.io/badge/Windows-0078D6?logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA4OCA4OCI+PHBhdGggZmlsbD0iI2ZmZiIgZD0iTTAgMGgzOXYzOUgweiIvPjxwYXRoIGZpbGw9IiNmZmYiIGQ9Ik00OSAwaDM5djM5SDQ5eiIvPjxwYXRoIGZpbGw9IiNmZmYiIGQ9Ik0wIDQ5aDM5djM5SDB6Ii8+PHBhdGggZmlsbD0iI2ZmZiIgZD0iTTQ5IDQ5aDM5djM5SDQ5eiIvPjwvc3ZnPg==)](https://www.microsoft.com/windows/)
[![Linux](https://img.shields.io/badge/Linux-FCC624?logo=linux&logoColor=black)](https://www.linux.org/)

<!-- Badge Row 4: License -->
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

中文 | [English](#english)

## 目录

- [项目概览](#项目概览)
- [功能特性](#功能特性)
- [安装](#安装)
- [快速上手](#快速上手)
- [命令参考](#命令参考)
- [格式兼容性](#格式兼容性)
- [批处理](#批处理)
- [限制与约定](#限制与约定)
- [开发与测试](#开发与测试)
- [构建 Windows 可执行文件](#构建-windows-可执行文件)
- [贡献指南](#贡献指南)
- [致谢](#致谢)
- [许可证](#许可证)

## 项目概览

Grape 面向需要在图形界面之外检查和转换 ProCAST 导出结果的用户。其输入特指在 ProCAST Viewer 模式下导出的 `.ntl` 场文件，以及在 ProCAST Mesh 模式下导出的 `.inp` 网格文件；当前支持的语法范围有意限定为本项目已验证的 ProCAST 导出子集。推荐将发布包中的工具说明交给具有本地文件和终端访问能力的 Agent，由 Agent 理解需求、检查输入、选择输出格式、调用工具并验收结果，无需用户手动拼写命令。Grape 使用显式的源节点 ID 映射校验网格拓扑与 NTL 数据，避免把非连续或乱序 ID 错当成数组下标。

当前发行名称为 `grape-mesh-cli`，安装后的命令为 `grape`，Windows 单文件程序名为 `grape.exe`。Python 导入命名空间暂时保留为 `pinkviewer`，它属于迁移期实现细节。

发布包中的 `grape-manual.md` 是供 Agent 阅读的工具说明，包含完整操作流程、诊断方法和输入约定；仓库中的对应文件是 [Grape 操作手册](docs/grape-manual.md)。设计与验证记录见 [UDF/README.md](UDF/README.md)。

## 功能特性

- 所有检查、校验、转换和批处理能力均针对 ProCAST 导出的结果文件设计。
- 提供 `inspect`、`validate`、`convert` 和 `batch` 四个子命令。
- 解析 INP 节点与常用二维/三维单元，并校验重复 ID、未知节点引用和不支持的单元类型。
- 自动区分单步标量、标量时间序列和标题为 `VELOCITY` 的三分量速度时间序列。
- 输出传统 ASCII VTK、XML VTU，以及使用 HDF5 存储数据的 XDMF 3.0。
- 保留源节点 ID；VTK 与 XDMF/HDF5 还会保留源单元 ID。
- 拒绝覆盖既有输出文件，并以非零退出码报告可操作的错误信息。

## 安装

### 推荐：下载发布包

1. 从项目的 [Releases](https://github.com/panyue1359/grape/releases) 页面下载适用于当前平台的发布压缩包。
2. 将压缩包解压到一个独立目录，并保持 `grape.exe` 与 `grape-manual.md` 位于同一目录。
3. 向具有本地文件与终端访问能力的 Agent 提供该目录、从 ProCAST 导出的 `.inp` 网格和 `.ntl` 场文件路径，以及期望结果，然后使用下一节的提示词。

普通用户无需安装 Python，也不需要手动运行 `grape.exe`。Agent 会根据 `grape-manual.md` 确定正确命令并完成输入检查、转换和产物验收。

### 环境要求

- Python 3.11、3.12 或 3.13
- Windows 或 Linux；当前 Windows 构建和测试已经验证，Linux 支持尚未在本仓库会话中实机验证
- XDMF/HDF5 输出需要 `h5py` 和 `numpy`，它们已包含在项目依赖中

### 开发者：从源码安装

```powershell
git clone https://github.com/panyue1359/grape.git
Set-Location grape
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
grape --help
```

Linux 下将激活命令替换为：

```bash
source .venv/bin/activate
```

也可以不安装命令入口，直接从仓库运行：

```powershell
python -m pinkviewer --help
```

## 快速上手

### 从 ProCAST 获取输入文件

在使用 Grape 前，先从同一个 ProCAST 模型或算例导出结果场与网格。

**导出 NTL 结果场：**

1. 使用 Visual-Cast 打开算例的 `.vdb` 项目文件。
2. 选择 **Applications > Viewer**，切换到 Viewer 状态。
3. 在结果列表中选择要导出的场，例如 `FVOL`，并隐藏铸型（mold），以便导出目标结果。
4. 打开 **File > Export As > PATran, I-DEAS, STL, gom …**，在弹出的文件窗口中指定文件名和保存位置。
5. 在文件窗口下方的 **Options** 栏选择时间导出方式：选择 **Interval** 可按指定间隔导出时间序列结果；另外两个选项用于导出指定时间步的结果。按需求设置间隔或时间步后完成导出，生成 `.ntl` 文件。对每个需要转换的结果场分别执行此操作。

**导出 INP 网格：**

1. 选择 **Applications > Mesh**，切换到 Mesh 状态。
2. 打开 **File > Export**，在弹出的文件窗口中将导出格式保留为默认的 **ABAQUS files (*.inp)**。
3. 将文件命名为“项目名g.inp”（例如项目名为 `Casting01` 时使用 `Casting01g.inp`），选择保存位置并完成导出。
4. 将导出的 `.inp` 与一个或多个 `.ntl` 文件放在便于 Agent 访问的位置，并在任务提示中提供它们的绝对路径。

> `.inp` 网格和 `.ntl` 场文件必须来自同一个模型或算例，并保持一致的节点 ID。若网格在结果计算后发生变化，请重新导出与结果对应的网格，否则 Grape 的 `validate` 步骤可能报告节点缺失、未知节点或数量不一致。

### 推荐：让 Agent 调用 Grape

解压发布包后，将下面的提示发送给具有本地文件和终端访问能力的 Agent。请把尖括号内容替换成实际路径和目标：

```text
请使用 <Grape 发布包目录> 中的 Grape 工具处理我的网格数据。

开始前必须完整阅读同目录的 grape-manual.md，并严格按照其中的工作流调用 grape.exe。请先检查并校验输入，再根据数据类型和我的目标选择输出格式，执行转换后核对所有产物是否存在且非空；若生成 XDMF，请同时核对配套 HDF5 文件。不要覆盖已有文件。遇到输入冲突、格式不支持或信息不足时，先向我说明并询问，不要猜测。

输入网格：<mesh.inp 的绝对路径>
结果文件：<一个或多个 .ntl 的绝对路径；没有则写“无”>
期望结果：<例如“生成可在 ParaView 打开的速度时间序列”>
输出目录：<输出目录的绝对路径；可省略，使用手册约定的默认目录>

完成后请报告：实际调用的命令、节点数、单元数、单元类型、字段名、分量数、时间步数、输出文件路径、退出码，以及尚未验证的内容。
```

Agent 应按照以下闭环执行，而不是直接尝试转换：

1. 定位 `grape.exe`，阅读 `grape-manual.md`，确认输入和输出路径。
2. 运行 `inspect` 获取网格结构和 NTL 分类。
3. 运行 `validate` 检查节点映射与输入一致性。
4. 根据字段类型和兼容矩阵选择 VTK、VTU 或 XDMF/HDF5。
5. 使用未占用的输出路径运行 `convert` 或 `batch`。
6. 检查退出码、文件存在性、文件大小及必要的配套文件，并向用户汇报。

### 手动调用（高级用法）

如果需要调试或在没有 Agent 的环境中使用，建议仍按“检查 → 校验 → 转换”的顺序手动执行。

### 1. 检查网格和字段

```powershell
grape inspect mesh.inp temperature.ntl velocity.ntl
```

输出为 JSON，包含节点数、单元数、单元类型，以及每个 NTL 字段的名称、分量数和时间步数。

### 2. 校验节点映射和输入一致性

```powershell
grape validate mesh.inp temperature.ntl velocity.ntl
```

只有命令退出码为 `0` 时才应继续转换。

### 3. 转换网格或单步标量

```powershell
grape convert mesh.inp mesh.vtu --format vtu
grape convert mesh.inp temperature.vtu --format vtu --ntl temperature.ntl
```

### 4. 转换标量或速度时间序列

```powershell
grape convert mesh.inp results.xdmf --format xdmf `
  --ntl temperature_history.ntl `
  --ntl velocity.ntl
```

XDMF 转换会同时生成 `results.xdmf` 和 `results.h5`；移动或分发结果时必须保留这两个文件。

## 命令参考

| 命令 | 用途 | 基本形式 |
|---|---|---|
| `inspect` | 输出网格和 NTL 分类摘要 | `grape inspect <mesh.inp> [field.ntl ...]` |
| `validate` | 校验拓扑、节点 ID 和 NTL 覆盖关系 | `grape validate <mesh.inp> [field.ntl ...]` |
| `convert` | 转换单个网格及可选字段 | `grape convert <mesh.inp> <output> --format <vtk\|vtu\|xdmf> [--ntl field.ntl ...]` |
| `batch` | 执行 JSON 清单中的多个转换作业 | `grape batch <jobs.json>` |

查看任一子命令的完整参数：

```powershell
grape convert --help
```

## 格式兼容性

> 本节仅描述 Grape 对 ProCAST 导出文件的转换能力，不表示支持任意来源的 INP/NTL 文件。

| 数据内容 | VTK | VTU | XDMF/HDF5 |
|---|:---:|:---:|:---:|
| 仅网格 | ✓ | ✓ | ✓ |
| 一个或多个单步标量 | ✓ | ✓ | ✓ |
| 一个或多个等步数标量时间序列 | — | — | ✓ |
| 三分量 `VELOCITY`，含单步速度 | — | — | ✓ |
| 等步数标量时间序列与速度合并 | — | — | ✓ |
| 混合已知单元类型 | ✓ | ✓ | — |

支持的 INP 单元类型：

| 维度 | 单元类型 |
|---|---|
| 二维三角形 | `S3`、`CPS3`、`CPE3` |
| 二维四边形 | `S4`、`CPS4`、`CPE4` |
| 三维体单元 | `C3D4`、`C3D6`、`C3D8` |

NTL 标题规范化后精确等于 `VELOCITY`（忽略大小写）时，记录按 `vx0 vy0 vz0 vx1 vy1 vz1 ...` 解释。其他标题均按标量处理。由于 NTL 头部不提供物理时间间隔，时间坐标使用从 `0` 开始的步索引。

## 批处理

批处理清单是 JSON 数组。相对路径以清单文件所在目录为基准：

```json
[
  {
    "inp": "data/mesh.inp",
    "output": "output/mesh.vtu",
    "format": "vtu",
    "ntl": ["data/temperature.ntl"]
  },
  {
    "inp": "data/mesh.inp",
    "output": "output/history.xdmf",
    "format": "xdmf",
    "ntl": ["data/temperature_history.ntl", "data/velocity.ntl"]
  }
]
```

执行清单：

```powershell
grape batch jobs.json
```

如果任一作业失败，`batch` 返回非零退出码，并逐项输出成功或错误状态。

## 限制与约定

- 仅支持本项目已验证的 ProCAST 导出 INP/NTL 子集。来自 Abaqus、其他 CAE 软件或自行生成的同扩展名文件不在兼容性承诺范围内。
- 当前实现将完整文件读入内存，不适合内存受限环境中的超大数据集。
- INP 仅解析逗号分隔的 `*NODE` 与 `*ELEMENT, TYPE=...` 记录；集合、材料、边界条件、续行和其他单元族不在支持范围内。
- XDMF/HDF5 只支持单一拓扑类型；混合单元网格请输出为 VTK 或 VTU。
- 单步标量不能在同一次转换中与时间序列或速度合并。
- 合并多个时间序列时，它们必须具有相同的步数和相同的网格节点 ID。
- 输出文件不会被覆盖；请使用新的路径或自行处理已有文件。
- 工具只重排并转换数据，不推断单位、坐标系或物理时间。

## 开发与测试

安装开发依赖并运行测试：

```powershell
python -m pip install -e ".[test]"
python -m pytest -q
```

在包含非 ASCII 字符的 Windows 路径中，如果 Python 3.11 的可编辑安装触发 `.pth` 编码问题，可使用不创建可编辑安装的隔离命令：

```powershell
uv run --isolated --no-project --python 3.11 `
  --with pytest --with h5py --with numpy `
  python -m pytest -q
```

当前测试基线为 `29 passed, 9 subtests passed`。主要代码位于：

```text
pinkviewer/
├── cli.py       # 命令解析与作业调度
├── model.py     # INP/NTL 解析、数据模型与校验
└── writers.py   # VTK、VTU、XDMF/HDF5 输出
```

## 构建 Windows 可执行文件

```powershell
python -m pip install -e ".[build]"
pyinstaller --clean --onefile --name grape cli_entry.py
.\dist\grape.exe --help
```

仓库同时维护 `grape.spec`。构建后应至少运行帮助命令、一个小型转换烟雾测试和完整测试套件。

## 贡献指南

1. 从当前分支创建范围明确的开发分支。
2. 修改解析或输出逻辑时，为正常输入与失败路径同时添加测试。
3. 运行完整测试套件，并核对新输出不会覆盖已有文件。
4. 同步更新本 README、[操作手册](docs/grape-manual.md) 和必要的开发记录。
5. 提交 Pull Request 时说明输入方言、输出格式、验证命令和仍存在的限制。

请勿提交 `.venv/`、`build/`、`dist/`、缓存或大型生成数据。

## 致谢

本项目的转换逻辑参考了 mstifiy 使用 Python、Qt5 与 VTK 开发的三维可视化工具 PinkCAx。该工具实现了网格可视化、有限元后处理和点云处理等功能。感谢原作者公开相关实现与开发经验：

- 开发记录：[【PinkCAx】可视化工具开发记录与总结 - CSDN 博客](https://blog.csdn.net/qq_39784672/article/details/127974774?spm=1001.2014.3001.5502)
- 原项目仓库：[mstifiy/PinkViewer](https://github.com/mstifiy/PinkViewer)

Grape 的实现和交付依赖 [NumPy](https://numpy.org/)、[h5py](https://www.h5py.org/)、[pytest](https://pytest.org/)、[PyInstaller](https://pyinstaller.org/) 与 [uv](https://docs.astral.sh/uv/) 等开源工具。

## 许可证

Grape 在 MIT 许可证下发布，许可文本见 [LICENSE](LICENSE)。此许可适用于本仓库当前的 Grape 项目代码；第三方依赖及其他明确标注来源的内容仍受其各自许可证或权利声明约束。

---

<a id="english"></a>

## English

### Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Command Reference](#command-reference)
- [Format Compatibility](#format-compatibility)
- [Batch Conversion](#batch-conversion)
- [Limitations and Conventions](#limitations-and-conventions)
- [Development and Testing](#development-and-testing)
- [Building the Windows Executable](#building-the-windows-executable)
- [Contributing](#contributing)
- [Acknowledgements](#acknowledgements)
- [License](#license)

### Overview

Grape is designed for users who need to inspect and convert ProCAST-exported results without a graphical interface. Its inputs specifically consist of `.ntl` field files exported in ProCAST Viewer mode and `.inp` mesh files exported in ProCAST Mesh mode; the supported syntax is intentionally limited to the ProCAST export subset verified by this project. The recommended workflow is to give the tool instructions from the release package to an Agent with local file and terminal access. The Agent can interpret the request, inspect the inputs, choose an output format, invoke Grape, and verify the results without requiring the user to compose commands manually. Grape explicitly validates source node ID mappings between mesh topology and NTL data, so shuffled or non-contiguous IDs are never mistaken for array indices.

The distribution is named `grape-mesh-cli`, the installed command is `grape`, and the Windows single-file executable is `grape.exe`. The Python import namespace remains `pinkviewer` for now and should be treated as a migration-era implementation detail.

The `grape-manual.md` file in the release package is the Agent-facing tool instruction and contains the complete workflow, diagnostics, and input conventions. Its repository counterpart is the [Grape operation manual](docs/grape-manual.md). Design and validation records are available in [UDF/README.md](UDF/README.md).

### Features

- All inspection, validation, conversion, and batch operations are designed for result files exported by ProCAST.
- Four subcommands: `inspect`, `validate`, `convert`, and `batch`.
- INP parsing for common 2D and 3D elements, with checks for duplicate IDs, unknown node references, and unsupported element types.
- Automatic classification of single-step scalars, scalar time series, and three-component velocity time series titled `VELOCITY`.
- Legacy ASCII VTK, XML VTU, and XDMF 3.0 output backed by HDF5.
- Source node IDs are retained; VTK and XDMF/HDF5 also retain source element IDs.
- Existing outputs are never overwritten, and actionable errors use nonzero exit codes.

### Installation

#### Recommended: download a release package

1. Download the release archive for your platform from the project's [Releases](https://github.com/panyue1359/grape/releases) page.
2. Extract it into a dedicated directory and keep `grape.exe` and `grape-manual.md` together.
3. Give an Agent with local file and terminal access the release directory, the paths to the `.inp` mesh and `.ntl` field files exported from ProCAST, and the desired result, then use the prompt in the next section.

Regular users do not need to install Python or run `grape.exe` manually. The Agent uses `grape-manual.md` to determine the correct commands and performs input inspection, conversion, and artifact verification.

#### Requirements

- Python 3.11, 3.12, or 3.13
- Windows or Linux; Windows builds and tests have been verified, while Linux support has not yet been demonstrated in the current repository session
- XDMF/HDF5 output requires `h5py` and `numpy`, both declared as project dependencies

#### Developers: install from source

```powershell
git clone https://github.com/panyue1359/grape.git
Set-Location grape
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
grape --help
```

On Linux, replace the activation command with:

```bash
source .venv/bin/activate
```

You can also run the package directly from a checkout without installing the command entry point:

```powershell
python -m pinkviewer --help
```

### Quick Start

#### Export inputs from ProCAST

Before using Grape, export the result fields and mesh from the same ProCAST model or case.

**Export NTL result fields:**

1. Open the case's `.vdb` project file in Visual-Cast.
2. Select **Applications > Viewer** to switch to Viewer mode.
3. Select the result field to export, such as `FVOL`, and hide the mold so the target result is ready for export.
4. Open **File > Export As > PATran, I-DEAS, STL, gom …**. In the file dialog, choose the file name and destination.
5. In the **Options** section at the bottom of the dialog, choose the time export method. Select **Interval** to export a time series at the specified interval; the other two options export results at specified time steps. Set the interval or time steps as needed and complete the export to create an `.ntl` file. Repeat for each result field you need.

**Export the INP mesh:**

1. Select **Applications > Mesh** to switch to Mesh mode.
2. Open **File > Export**. In the file dialog, keep the default format, **ABAQUS files (*.inp)**.
3. Name the file `project-nameg.inp` (for example, use `Casting01g.inp` for a project named `Casting01`), choose a destination, and complete the export.
4. Put the exported `.inp` file and one or more `.ntl` files in a location accessible to the Agent, then provide their absolute paths in the task prompt.

> The `.inp` mesh and `.ntl` field files must come from the same model or case and use consistent node IDs. If the mesh changed after the result was computed, export the matching mesh again; otherwise, Grape's `validate` step may report missing nodes, unknown nodes, or inconsistent counts.

#### Recommended: let an Agent invoke Grape

After extracting the release package, send the following prompt to an Agent with local file and terminal access. Replace the angle-bracketed values with your real paths and objective:

```text
Use the Grape tool in <Grape release directory> to process my mesh data.

Before starting, read grape-manual.md in that directory in full and follow its workflow when invoking grape.exe. Inspect and validate the inputs first, choose an output format from the data type and my objective, then run the conversion and verify that every artifact exists and is non-empty. If XDMF is generated, verify its companion HDF5 file as well. Do not overwrite existing files. If inputs conflict, the requested format is unsupported, or information is missing, explain the issue and ask me instead of guessing.

Input mesh: <absolute path to mesh.inp>
Result files: <absolute paths to one or more .ntl files; write “none” if absent>
Desired result: <for example, “create a velocity time series that opens in ParaView”>
Output directory: <absolute output directory; omit to use the manual's default>

When finished, report the commands executed, node count, element count, element types, field names, component counts, time-step counts, output paths, exit codes, and anything that was not verified.
```

The Agent should complete the following loop instead of attempting conversion immediately:

1. Locate `grape.exe`, read `grape-manual.md`, and confirm the input and output paths.
2. Run `inspect` to obtain the mesh structure and NTL classifications.
3. Run `validate` to check node mappings and input consistency.
4. Select VTK, VTU, or XDMF/HDF5 from the field types and compatibility matrix.
5. Run `convert` or `batch` with an unused output path.
6. Check exit codes, file existence, file sizes, and required companion files, then report the results.

#### Manual invocation (advanced)

For debugging or environments without an Agent, manually follow the same “inspect → validate → convert” sequence.

#### 1. Inspect the mesh and fields

```powershell
grape inspect mesh.inp temperature.ntl velocity.ntl
```

The JSON output reports node and element counts, element types, and the name, component count, and time-step count of each NTL field.

#### 2. Validate node mappings and input consistency

```powershell
grape validate mesh.inp temperature.ntl velocity.ntl
```

Continue to conversion only when the command exits with code `0`.

#### 3. Convert a mesh or single-step scalar

```powershell
grape convert mesh.inp mesh.vtu --format vtu
grape convert mesh.inp temperature.vtu --format vtu --ntl temperature.ntl
```

#### 4. Convert scalar or velocity time series

```powershell
grape convert mesh.inp results.xdmf --format xdmf `
  --ntl temperature_history.ntl `
  --ntl velocity.ntl
```

An XDMF conversion creates both `results.xdmf` and `results.h5`. Keep the two files together when moving or distributing the result.

### Command Reference

| Command | Purpose | Basic form |
|---|---|---|
| `inspect` | Print a mesh and NTL classification summary | `grape inspect <mesh.inp> [field.ntl ...]` |
| `validate` | Validate topology, node IDs, and NTL coverage | `grape validate <mesh.inp> [field.ntl ...]` |
| `convert` | Convert one mesh with optional fields | `grape convert <mesh.inp> <output> --format <vtk\|vtu\|xdmf> [--ntl field.ntl ...]` |
| `batch` | Run conversion jobs from a JSON manifest | `grape batch <jobs.json>` |

Show the full arguments for any subcommand:

```powershell
grape convert --help
```

### Format Compatibility

> This section describes Grape's conversion capabilities for ProCAST-exported files only. It does not indicate support for INP/NTL files from arbitrary sources.

| Data content | VTK | VTU | XDMF/HDF5 |
|---|:---:|:---:|:---:|
| Mesh only | ✓ | ✓ | ✓ |
| One or more single-step scalars | ✓ | ✓ | ✓ |
| One or more equal-length scalar time series | — | — | ✓ |
| Three-component `VELOCITY`, including one step | — | — | ✓ |
| Equal-length scalar time series and velocity combined | — | — | ✓ |
| Mixed known element types | ✓ | ✓ | — |

Supported INP element types:

| Dimension | Element types |
|---|---|
| 2D triangles | `S3`, `CPS3`, `CPE3` |
| 2D quadrilaterals | `S4`, `CPS4`, `CPE4` |
| 3D solid elements | `C3D4`, `C3D6`, `C3D8` |

When the normalized NTL title is exactly `VELOCITY` (case-insensitive), records are interpreted as `vx0 vy0 vz0 vx1 vy1 vz1 ...`. Every other title is treated as scalar data. Because the NTL header does not provide a physical time interval, time coordinates use zero-based step indices.

### Batch Conversion

A batch manifest is a JSON array. Relative paths are resolved from the manifest's directory:

```json
[
  {
    "inp": "data/mesh.inp",
    "output": "output/mesh.vtu",
    "format": "vtu",
    "ntl": ["data/temperature.ntl"]
  },
  {
    "inp": "data/mesh.inp",
    "output": "output/history.xdmf",
    "format": "xdmf",
    "ntl": ["data/temperature_history.ntl", "data/velocity.ntl"]
  }
]
```

Run the manifest:

```powershell
grape batch jobs.json
```

If any job fails, `batch` returns a nonzero exit code and prints an individual success or error status for every job.

### Limitations and Conventions

- Only the ProCAST-exported INP/NTL subset verified by this project is supported. Files with the same extensions produced by Abaqus, other CAE software, or custom generators are outside the compatibility commitment.
- The current implementation reads complete files into memory and is not suited to very large datasets in memory-constrained environments.
- INP support is limited to comma-separated `*NODE` and `*ELEMENT, TYPE=...` records. Sets, materials, boundary conditions, continuation records, and other element families are outside the supported subset.
- XDMF/HDF5 requires a homogeneous topology. Use VTK or VTU for mixed-element meshes.
- Single-step scalar fields cannot be combined with time-series or velocity data in one conversion.
- Multiple time series must have the same number of steps and the same mesh node IDs.
- Output files are never overwritten; choose a new path or handle existing files yourself.
- Grape only rearranges and converts data. It does not infer units, coordinate systems, or physical time.

### Development and Testing

Install the test dependency and run the suite:

```powershell
python -m pip install -e ".[test]"
python -m pytest -q
```

If an editable install under Python 3.11 encounters a `.pth` encoding issue in a Windows path containing non-ASCII characters, use the isolated command below, which does not create an editable installation:

```powershell
uv run --isolated --no-project --python 3.11 `
  --with pytest --with h5py --with numpy `
  python -m pytest -q
```

The current baseline is `29 passed, 9 subtests passed`. The main modules are:

```text
pinkviewer/
├── cli.py       # Command parsing and job orchestration
├── model.py     # INP/NTL parsing, data models, and validation
└── writers.py   # VTK, VTU, and XDMF/HDF5 output
```

### Building the Windows Executable

```powershell
python -m pip install -e ".[build]"
pyinstaller --clean --onefile --name grape cli_entry.py
.\dist\grape.exe --help
```

The repository also maintains `grape.spec`. After building, run at least the help command, a small conversion smoke test, and the complete test suite.

### Contributing

1. Create a focused development branch from the current branch.
2. Add tests for both valid inputs and failure paths whenever parser or writer behavior changes.
3. Run the full test suite and verify that new outputs do not overwrite existing files.
4. Keep this README, the [operation manual](docs/grape-manual.md), and relevant development records synchronized.
5. In the Pull Request, describe the input dialect, output format, validation commands, and remaining limitations.

Do not commit `.venv/`, `build/`, `dist/`, caches, or large generated datasets.

### Acknowledgements

The conversion logic in this project was informed by PinkCAx, a three-dimensional visualization tool developed by mstifiy with Python, Qt5, and VTK. PinkCAx provides mesh visualization, finite-element post-processing, and point-cloud functionality. We thank the original author for sharing the implementation and development experience:

- Development article: [PinkCAx Visualization Tool: Development Record and Summary (CSDN, Chinese)](https://blog.csdn.net/qq_39784672/article/details/127974774?spm=1001.2014.3001.5502)
- Original project: [mstifiy/PinkViewer](https://github.com/mstifiy/PinkViewer)

Grape is built and delivered with open-source tools including [NumPy](https://numpy.org/), [h5py](https://www.h5py.org/), [pytest](https://pytest.org/), [PyInstaller](https://pyinstaller.org/), and [uv](https://docs.astral.sh/uv/).

### License

Grape is distributed under the MIT License; see [LICENSE](LICENSE) for the full text. This license applies to the current Grape project code in this repository. Third-party dependencies and other explicitly attributed material remain subject to their respective licenses or rights statements.

> Badge note: badges reflect the current repository metadata and verified project targets. Update them when version, platform support, or licensing changes.

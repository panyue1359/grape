# 三分量速度时间序列实现计划

**目标：** `--ntl` 自动识别规范化标题为 `VELOCITY` 的速度，输出三分量 XDMF/HDF5 时间序列，支持与同时间轴标量合并。

**依据：** `UDF/README.md`；参考工程 `inp_ntl_to_vtk.py` 的 `infer_field_layout` / `reshape_procast_values`；真实 `Benchmarkv.ntl` 的宽度 327 对应温度文件的 109 步。每节点布局为 `vx0 vy0 vz0 vx1 vy1 vz1 ...`。

**边界：** 保持 CLI 和清单结构、ID 映射、输出保护及字段命名规则。仅规范化名称等于 VELOCITY（忽略大小写）自动视作三分量，避免把速度模量误判。宽度必须能被 3 整除；宽度 3 也走一帧向量时间序列。其余文件保留原标量分类。保留零基索引时间，不猜测物理时间或单位。不提交代码，不删除现有数据。

## Todo

- [x] 解析与测试：修改 `pinkviewer/model.py`，扩展 `PointFieldTimeSeries.components` 默认 1；速度 values 为 `(steps, nodes, 3)`，标量保持 `(steps, nodes)`。复用严格节点与记录检查。支持换行、D 指数，以及速度记录中相邻科学记数值；拒绝垃圾字符、重复/未知 ID、截断及额外数据。以非对称分量与乱序节点的两步样例验证排列。
- [x] 输出与 CLI：`pinkviewer/writers.py` 验证维度，输出 `AttributeType=Vector`、`Dimensions="nodes 3"`；`pinkviewer/cli.py` 使用真实分量数与步数，保持合并和 batch 路由。测试混合标量/速度的 XML、HDF5 值、步数不匹配以及非法宽度。
- [x] 验收与交付：运行 `.venv/Scripts/python.exe -m unittest discover -s tests`。读取真实速度和网格，验证 114956 节点、109 步、3 分量，抽查原始记录与输出对应。构建独立暂存 EXE，完成真实速度转换并检查 XML/HDF5；备份原发布 EXE 后更新 `dist/grape.exe`，同步两份手册和 `UDF/README.md`。记录实际验证边界。

## 验收命令

```powershell
& .venv/Scripts/python.exe -m unittest discover -s tests
& .venv/Scripts/python.exe -m pinkviewer inspect "$ReferenceCaseDir/testFiles/Benchmarkg.inp" "$ReferenceCaseDir/testFiles/Benchmarkv.ntl"
& .venv/Scripts/python.exe -m PyInstaller --noconfirm --distpath .build-grape-velocity --workpath .build-grape-work-velocity grape.spec
```

输出到全新路径 `output/grape/Benchmark_velocity.xdmf`；配套 HDF5 每步速度形状为 `(114956, 3)`。验收检查所有时间片的向量属性和维度，并抽查首尾步的节点/分量映射，原输入和已有输出保留。

## 执行结果

- 29 项单元/CLI 测试通过；新 EXE 完成真实速度转换，另通过小型速度+温度合并转换和 inspect（3 分量、2 步）。
- `UDF/validate_velocity.py` 独立逐行读取原始速度，核对 109 帧的数组形状以及节点 1、2（首个非零节点）、114956 每帧 XYZ 值，全相等。
- `UDF/validate_velocity_paraview.py` 经 Windows pvpython 实际读取真实 XDMF：114956 节点、109 步、VELOCITY 三分量，首帧模长范围 `(0, 0.3981134)`，末帧 `(0, 0)`。未操作 GUI 或渲染图像。
- 发布 EXE 已替换并校验 SHA-256：`748EF58BF47D3C05E4CA2F69E905E777F273DE76044942E027FF23DD9D3426FF`。旧版本备份为 `dist/grape.exe.backup-velocity-20261021-201118`，发布手册与 docs 维护版内容一致。

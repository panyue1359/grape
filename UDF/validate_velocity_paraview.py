"""用离线 pvpython 验证实际 ParaView 读取器识别速度向量和时间轴。"""

import argparse
from pathlib import Path

from paraview.simple import OpenDataFile


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("xdmf", type=Path)
parser.add_argument("--steps", type=int, required=True)
parser.add_argument("--nodes", type=int, required=True)
args = parser.parse_args()

reader = OpenDataFile(str(args.xdmf.resolve()))
assert reader is not None, "ParaView 未创建读取器"
reader.UpdatePipelineInformation()
times = list(reader.TimestepValues)
assert times == list(range(args.steps)), times
for time_value in (times[0], times[-1]):
    reader.UpdatePipeline(time=time_value)
    velocity = reader.PointData["VELOCITY"]
    assert velocity.GetNumberOfComponents() == 3
    assert reader.GetDataInformation().GetNumberOfPoints() == args.nodes
    print("time=", time_value, "components=", velocity.GetNumberOfComponents(), "magnitude_range=", velocity.GetRange(-1))
print("ParaView reader validation passed:", args.nodes, "nodes,", len(times), "steps, XYZ vector")

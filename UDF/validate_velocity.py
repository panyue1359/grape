"""独立核对速度 XDMF/HDF5 的全部帧与原始 NTL 抽样值。"""

import argparse
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import h5py
import numpy as np


def validate(ntl: Path, output: Path) -> None:
    grids = ET.parse(output).findall(".//Grid[@GridType='Uniform']")
    # 独立按原始行解析样本，不调用产品的分类或记录解析函数。
    scientific = re.compile(r"[+-]?(?:\d+\.\d*|\.\d+)[EeDd][+-]\d{2}")
    samples = []
    with ntl.open(encoding="utf-8-sig") as stream:
        title = stream.readline()
        header = stream.readline().split()
        stream.readline()
        count, width = int(header[0]), int(header[4])
        assert width % 3 == 0
        steps = width // 3
        assert len(grids) == steps
        found_nonzero = False
        for record_index in range(count):
            line = next(stream)
            while not line.strip():
                line = next(stream)
            node_text, _, rest = line.strip().partition(" ")
            node_id = int(node_text)
            values = scientific.findall(rest)
            while len(values) < width:
                values.extend(scientific.findall(next(stream)))
            assert len(values) == width
            values = np.array([float(value.replace("D", "E").replace("d", "e")) for value in values]).reshape(steps, 3)
            nonzero = bool(np.any(values))
            if record_index in (0, count - 1) or (nonzero and not found_nonzero):
                samples.append((node_id, values))
            found_nonzero = found_nonzero or nonzero

    with h5py.File(output.with_suffix(".h5"), "r") as h5:
        ids = h5["/Mesh/SourceNodeIds"][:]
        assert len(ids) == count
        indices = {int(node_id): index for index, node_id in enumerate(ids)}
        for step, grid in enumerate(grids):
            assert grid.find("Time").attrib["Value"] == str(step)
            attribute = grid.find("Attribute[@Name='VELOCITY']")
            assert attribute.attrib["AttributeType"] == "Vector"
            item = attribute.find("DataItem")
            assert item.attrib["Dimensions"] == f"{count} 3"
            data = h5[item.text.split(":", 1)[1]]
            assert data.shape == (count, 3)
            for node_id, values in samples:
                np.testing.assert_array_equal(data[indices[node_id]], values[step])
    print(f"验证通过：{count} 节点，{steps} 步，3 分量；抽样节点 {[node for node, _ in samples]} 全部时间步逐分量一致。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ntl", type=Path)
    parser.add_argument("xdmf", type=Path)
    args = parser.parse_args()
    validate(args.ntl, args.xdmf)

"""Writers for the supported unstructured-grid interchange formats."""

from pathlib import Path
import xml.etree.ElementTree as ET

from .model import Dataset, PointFieldTimeSeries


VTK_CELL_TYPES = {"S3": 5, "CPS3": 5, "CPE3": 5, "S4": 9, "CPS4": 9, "CPE4": 9, "C3D4": 10, "C3D6": 13, "C3D8": 12}
VTK_CELL_NAMES = {"S3": "triangle", "CPS3": "triangle", "CPE3": "triangle", "S4": "quad", "CPS4": "quad", "CPE4": "quad", "C3D4": "tetra", "C3D6": "wedge", "C3D8": "hexahedron"}
XDMF_TOPOLOGY_NAMES = {"triangle": "Triangle", "quad": "Quadrilateral", "tetra": "Tetrahedron", "wedge": "Wedge", "hexahedron": "Hexahedron"}


def _check_cell_types(dataset: Dataset) -> None:
    for element in dataset.elements:
        if element.element_type not in VTK_CELL_TYPES:
            raise ValueError(f"element type {element.element_type} cannot be represented by the selected output format")


def write_vtk(dataset: Dataset, output: str | Path) -> None:
    _check_cell_types(dataset)
    path = Path(output)
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {path}")
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write("# vtk DataFile Version 3.0\nPinkViewer mesh\nASCII\nDATASET UNSTRUCTURED_GRID\n")
        stream.write(f"POINTS {len(dataset.nodes)} double\n")
        for node in dataset.nodes:
            stream.write("{:.17g} {:.17g} {:.17g}\n".format(*node.coordinates))
        total = sum(1 + len(cell.connectivity) for cell in dataset.elements)
        stream.write(f"CELLS {len(dataset.elements)} {total}\n")
        for cell in dataset.elements:
            stream.write(f"{len(cell.connectivity)} " + " ".join(map(str, cell.connectivity)) + "\n")
        stream.write(f"CELL_TYPES {len(dataset.elements)}\n")
        for cell in dataset.elements:
            stream.write(f"{VTK_CELL_TYPES[cell.element_type]}\n")
        stream.write(f"POINT_DATA {len(dataset.nodes)}\n")
        stream.write("SCALARS source_node_id long 1\nLOOKUP_TABLE default\n")
        stream.writelines(f"{node.source_id}\n" for node in dataset.nodes)
        for field in dataset.fields:
            stream.write(f"SCALARS {field.name.replace(' ', '_')} double 1\nLOOKUP_TABLE default\n")
            stream.writelines(f"{value:.17g}\n" for value in field.values)
        stream.write(f"CELL_DATA {len(dataset.elements)}\nSCALARS source_element_id long 1\nLOOKUP_TABLE default\n")
        stream.writelines(f"{cell.source_id}\n" for cell in dataset.elements)


def write_vtu(dataset: Dataset, output: str | Path) -> None:
    _check_cell_types(dataset)
    if Path(output).exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output}")
    root = ET.Element("VTKFile", type="UnstructuredGrid", version="0.1", byte_order="LittleEndian")
    grid = ET.SubElement(root, "UnstructuredGrid")
    piece = ET.SubElement(grid, "Piece", NumberOfPoints=str(len(dataset.nodes)), NumberOfCells=str(len(dataset.elements)))
    points = ET.SubElement(piece, "Points")
    coords = ET.SubElement(points, "DataArray", type="Float64", NumberOfComponents="3", format="ascii")
    coords.text = "\n" + "\n".join("{:.17g} {:.17g} {:.17g}".format(*n.coordinates) for n in dataset.nodes) + "\n"
    cells = ET.SubElement(piece, "Cells")
    conn = ET.SubElement(cells, "DataArray", type="Int64", Name="connectivity", format="ascii")
    conn.text = " ".join(str(i) for cell in dataset.elements for i in cell.connectivity)
    offsets = ET.SubElement(cells, "DataArray", type="Int64", Name="offsets", format="ascii")
    current = 0
    offset_values = []
    for cell in dataset.elements:
        current += len(cell.connectivity)
        offset_values.append(str(current))
    offsets.text = " ".join(offset_values)
    types = ET.SubElement(cells, "DataArray", type="UInt8", Name="types", format="ascii")
    types.text = " ".join(str(VTK_CELL_TYPES[cell.element_type]) for cell in dataset.elements)
    data = ET.SubElement(piece, "PointData")
    source_ids = ET.SubElement(data, "DataArray", type="Int64", Name="source_node_id", format="ascii")
    source_ids.text = " ".join(str(node.source_id) for node in dataset.nodes)
    for field in dataset.fields:
        array = ET.SubElement(data, "DataArray", type="Float64", Name=field.name, format="ascii")
        array.text = " ".join(f"{value:.17g}" for value in field.values)
    ET.ElementTree(root).write(output, encoding="utf-8", xml_declaration=True)


def write_xdmf(dataset: Dataset, output: str | Path) -> None:
    _check_cell_types(dataset)
    try:
        import h5py
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("XDMF/HDF5 output requires h5py and numpy") from exc
    path = Path(output)
    h5_path = path.with_suffix(".h5")
    if path.exists() or h5_path.exists():
        raise FileExistsError(f"refusing to overwrite existing XDMF/HDF5 output: {path} or {h5_path}")
    points = np.asarray([node.coordinates for node in dataset.nodes], dtype="float64")
    connectivity = np.asarray([cell.connectivity for cell in dataset.elements], dtype="int64")
    topology = VTK_CELL_NAMES[dataset.elements[0].element_type] if dataset.elements else "Polyvertex"
    if not dataset.elements:
        raise ValueError("XDMF output requires at least one element")
    if any(VTK_CELL_NAMES[cell.element_type] != topology for cell in dataset.elements):
        raise ValueError("XDMF writer currently requires a homogeneous element type")
    with h5py.File(h5_path, "w") as h5:
        h5.create_dataset("/Mesh/Points", data=points)
        h5.create_dataset("/Mesh/Connectivity", data=connectivity)
        h5.create_dataset("/Mesh/SourceNodeIds", data=np.asarray([node.source_id for node in dataset.nodes], dtype="int64"))
        h5.create_dataset("/Mesh/SourceElementIds", data=np.asarray([cell.source_id for cell in dataset.elements], dtype="int64"))
        for index, field in enumerate(dataset.fields):
            h5.create_dataset(f"/Fields/{index}", data=np.asarray(field.values, dtype="float64"))
    xdmf = ET.Element("Xdmf", Version="3.0")
    domain = ET.SubElement(xdmf, "Domain")
    uniform = ET.SubElement(ET.SubElement(domain, "Grid", Name="PinkViewer", GridType="Uniform"), "Topology", TopologyType=XDMF_TOPOLOGY_NAMES[topology], NumberOfElements=str(len(dataset.elements)))
    ET.SubElement(uniform, "DataItem", Dimensions=f"{len(dataset.elements)} {len(dataset.elements[0].connectivity) if dataset.elements else 1}", NumberType="Int", Precision="8", Format="HDF").text = f"{h5_path.name}:/Mesh/Connectivity"
    geometry = ET.SubElement(ET.SubElement(domain.find("Grid"), "Geometry", GeometryType="XYZ"), "DataItem", Dimensions=f"{len(dataset.nodes)} 3", NumberType="Float", Precision="8", Format="HDF")
    geometry.text = f"{h5_path.name}:/Mesh/Points"
    for index, field in enumerate(dataset.fields):
        attribute = ET.SubElement(domain.find("Grid"), "Attribute", Name=field.name, AttributeType="Scalar", Center="Node")
        ET.SubElement(attribute, "DataItem", Dimensions=str(len(dataset.nodes)), NumberType="Float", Precision="8", Format="HDF").text = f"{h5_path.name}:/Fields/{index}"
    source_ids = ET.SubElement(domain.find("Grid"), "Attribute", Name="source_node_id", AttributeType="Scalar", Center="Node")
    ET.SubElement(source_ids, "DataItem", Dimensions=str(len(dataset.nodes)), NumberType="Int", Precision="8", Format="HDF").text = f"{h5_path.name}:/Mesh/SourceNodeIds"
    element_ids = ET.SubElement(domain.find("Grid"), "Attribute", Name="source_element_id", AttributeType="Scalar", Center="Cell")
    ET.SubElement(element_ids, "DataItem", Dimensions=str(len(dataset.elements)), NumberType="Int", Precision="8", Format="HDF").text = f"{h5_path.name}:/Mesh/SourceElementIds"
    ET.ElementTree(xdmf).write(path, encoding="utf-8", xml_declaration=True)


def write_xdmf_timeseries(dataset: Dataset, series: PointFieldTimeSeries | tuple[PointFieldTimeSeries, ...] | list[PointFieldTimeSeries], output: str | Path) -> None:
    """Write a temporal XDMF collection with one or more per-step point fields."""
    series_list = [series] if isinstance(series, PointFieldTimeSeries) else list(series)
    if not series_list:
        raise ValueError("XDMF time-series output requires at least one field")
    reference_times = series_list[0].times
    reference_steps = len(reference_times)
    for item in series_list:
        if item.components not in (1, 3):
            raise ValueError("time-series fields must have 1 or 3 components")
        expected_shape = (len(item.times), len(dataset.nodes)) + ((3,) if item.components == 3 else ())
        if item.values.shape != expected_shape:
            raise ValueError(f"time-series field '{item.name}' dimensions do not match time steps and mesh nodes")
        if len(item.times) != reference_steps or item.times != reference_times:
            raise ValueError("all time-series NTL files must have the same number of time steps")
    if len({item.name for item in series_list}) != len(series_list):
        raise ValueError("time-series field names must be unique")

    _check_cell_types(dataset)
    try:
        import h5py
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("XDMF/HDF5 output requires h5py and numpy") from exc
    path = Path(output)
    h5_path = path.with_suffix(".h5")
    if path.exists() or h5_path.exists():
        raise FileExistsError(f"refusing to overwrite existing XDMF/HDF5 output: {path} or {h5_path}")
    if not dataset.elements:
        raise ValueError("XDMF output requires at least one element")
    topology = VTK_CELL_NAMES[dataset.elements[0].element_type]
    if any(VTK_CELL_NAMES[cell.element_type] != topology for cell in dataset.elements):
        raise ValueError("XDMF writer currently requires a homogeneous element type")
    points = np.asarray([node.coordinates for node in dataset.nodes], dtype="float64")
    connectivity = np.asarray([cell.connectivity for cell in dataset.elements], dtype="int64")
    with h5py.File(h5_path, "w") as h5:
        h5.create_dataset("/Mesh/Points", data=points)
        h5.create_dataset("/Mesh/Connectivity", data=connectivity)
        h5.create_dataset("/Mesh/SourceNodeIds", data=np.asarray([node.source_id for node in dataset.nodes], dtype="int64"))
        h5.create_dataset("/Mesh/SourceElementIds", data=np.asarray([cell.source_id for cell in dataset.elements], dtype="int64"))
        for field_index, item in enumerate(series_list):
            for index, row in enumerate(item.values):
                if len(series_list) == 1:
                    data_path = f"/TimeSeries/Step_{index:04d}"
                else:
                    data_path = f"/TimeSeries/Field_{field_index:04d}/Step_{index:04d}"
                h5.create_dataset(data_path, data=row)

    xdmf = ET.Element("Xdmf", Version="3.0")
    domain = ET.SubElement(xdmf, "Domain")
    temporal = ET.SubElement(domain, "Grid", Name="GrapeTimeSeries", GridType="Collection", CollectionType="Temporal")
    for index, time_value in enumerate(reference_times):
        grid = ET.SubElement(temporal, "Grid", Name=f"Step_{index:04d}", GridType="Uniform")
        ET.SubElement(grid, "Time", Value=f"{time_value:.17g}")
        topology_element = ET.SubElement(grid, "Topology", TopologyType=XDMF_TOPOLOGY_NAMES[topology], NumberOfElements=str(len(dataset.elements)))
        ET.SubElement(topology_element, "DataItem", Dimensions=f"{len(dataset.elements)} {len(dataset.elements[0].connectivity)}", NumberType="Int", Precision="8", Format="HDF").text = f"{h5_path.name}:/Mesh/Connectivity"
        geometry = ET.SubElement(grid, "Geometry", GeometryType="XYZ")
        ET.SubElement(geometry, "DataItem", Dimensions=f"{len(dataset.nodes)} 3", NumberType="Float", Precision="8", Format="HDF").text = f"{h5_path.name}:/Mesh/Points"
        for field_index, item in enumerate(series_list):
            attribute = ET.SubElement(grid, "Attribute", Name=item.name, AttributeType="Vector" if item.components == 3 else "Scalar", Center="Node")
            if len(series_list) == 1:
                data_path = f"/TimeSeries/Step_{index:04d}"
            else:
                data_path = f"/TimeSeries/Field_{field_index:04d}/Step_{index:04d}"
            dimensions = f"{len(dataset.nodes)} 3" if item.components == 3 else str(len(dataset.nodes))
            ET.SubElement(attribute, "DataItem", Dimensions=dimensions, NumberType="Float", Precision="8", Format="HDF").text = f"{h5_path.name}:{data_path}"
    ET.ElementTree(xdmf).write(path, encoding="utf-8", xml_declaration=True)


def write_dataset(dataset: Dataset, output: str | Path, fmt: str) -> None:
    writers = {"vtk": write_vtk, "vtu": write_vtu, "xdmf": write_xdmf}
    try:
        writer = writers[fmt.lower()]
    except KeyError as exc:
        raise ValueError(f"unsupported output format '{fmt}'") from exc
    writer(dataset, output)

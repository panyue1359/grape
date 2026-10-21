"""Small, explicit in-memory mesh model and INP/NTL readers."""

from dataclasses import dataclass
from pathlib import Path
import re

import numpy as np


SUPPORTED_ELEMENT_TYPES = {
    "S3": 3,
    "CPS3": 3,
    "CPE3": 3,
    "S4": 4,
    "CPS4": 4,
    "CPE4": 4,
    "C3D4": 4,
    "C3D6": 6,
    "C3D8": 8,
}


@dataclass(frozen=True)
class Node:
    source_id: int
    coordinates: tuple[float, float, float]


@dataclass(frozen=True)
class Element:
    source_id: int
    element_type: str
    connectivity: tuple[int, ...]


@dataclass(frozen=True)
class PointField:
    name: str
    values: tuple[float, ...]


@dataclass(frozen=True)
class Dataset:
    nodes: tuple[Node, ...]
    elements: tuple[Element, ...]
    source_id_to_index: dict[int, int]
    fields: tuple[PointField, ...] = ()


@dataclass(frozen=True)
class PointFieldTimeSeries:
    name: str
    times: tuple[float, ...]
    values: np.ndarray
    components: int = 1


@dataclass(frozen=True)
class NtlClassification:
    kind: str
    components: int
    steps: int
    node_count: int


@dataclass(frozen=True)
class LoadedNtl:
    kind: str
    field: PointField | None = None
    series: PointFieldTimeSeries | None = None


def _ntl_field_name(title: str, fallback: str) -> str:
    words = title.split()
    if words and words[0].casefold() == "procast":
        words = words[1:]
    if words and words[-1].casefold() == "results":
        words = words[:-1]
    return " ".join(words) or fallback


def _ntl_layout(title: str, width: int) -> tuple[int, int]:
    components = 3 if _ntl_field_name(title, "").casefold() == "velocity" else 1
    if width % components:
        raise ValueError("VELOCITY NTL record width must be divisible by 3")
    return components, width // components


_PACKED_SCIENTIFIC = re.compile(r"[+-]?(?:\d+\.\d*|\.\d+)[EeDd][+-]\d{2}")


def _ntl_tokens(stream, vector: bool):
    """Split packed ProCAST scientific values with two-digit exponents strictly."""
    for line_number, raw in enumerate(stream, 4):
        for token in raw.split():
            if vector and token.upper().count("E") + token.upper().count("D") > 1:
                parts = _PACKED_SCIENTIFIC.findall(token)
                if "".join(parts) == token:
                    for part in parts:
                        yield part, line_number
                    continue
            yield token, line_number


def classify_ntl(path: str | Path) -> NtlClassification:
    """Classify scalar NTL or the explicitly supported XYZ VELOCITY layout.

    Header width counts samples per node: scalars use one sample per step,
    and a normalized VELOCITY title uses three interleaved samples per step.
    """
    source = Path(path)
    with source.open(encoding="utf-8-sig") as stream:
        title = stream.readline()
        header_line = stream.readline()
        source_line = stream.readline()
    if not title or not header_line or not source_line:
        raise ValueError(f"{source}: incomplete NTL header")
    header = header_line.split()
    if len(header) < 5:
        raise ValueError(f"{source}: malformed NTL header")
    try:
        count, width = int(header[0]), int(header[4])
    except ValueError as exc:
        raise ValueError(f"{source}: invalid NTL record count or width") from exc
    if count <= 0 or width <= 0:
        raise ValueError(f"{source}: NTL record count and width must be positive")
    components, steps = _ntl_layout(title, width)
    return NtlClassification("single_step" if width == 1 and components == 1 else "time_series", components, steps, count)


def _parse_inp(path: Path) -> tuple[tuple[Node, ...], tuple[tuple[int, str, tuple[int, ...]], ...]]:
    nodes: list[Node] = []
    elements: list[tuple[int, str, tuple[int, ...]]] = []
    section: str | None = None
    element_type: str | None = None
    seen_nodes: set[int] = set()
    seen_elements: set[int] = set()

    with path.open(encoding="utf-8-sig") as stream:
        for line_number, raw_line in enumerate(stream, 1):
            line = raw_line.strip()
            if not line or line.startswith("**"):
                continue
            if line.startswith("*"):
                directive = line.split(",", 1)[0].strip().upper()
                section = directive[1:]
                element_type = None
                if section == "ELEMENT":
                    for option in line.split(",")[1:]:
                        key, sep, value = option.partition("=")
                        if sep and key.strip().upper() == "TYPE":
                            element_type = value.strip().upper()
                    if element_type not in SUPPORTED_ELEMENT_TYPES:
                        raise ValueError(f"line {line_number}: unsupported element type '{element_type or ''}'")
                continue

            columns = [value.strip() for value in line.split(",")]
            try:
                if section == "NODE":
                    if len(columns) != 4:
                        raise ValueError("node record must contain ID and three coordinates")
                    node_id = int(columns[0])
                    if node_id <= 0:
                        raise ValueError(f"invalid node ID {node_id}; IDs must be positive")
                    if node_id in seen_nodes:
                        raise ValueError(f"duplicate node ID {node_id}")
                    coordinates = tuple(float(v) for v in columns[1:])
                    nodes.append(Node(node_id, coordinates))
                    seen_nodes.add(node_id)
                elif section == "ELEMENT":
                    if element_type is None:
                        raise ValueError("element type is missing")
                    element_id = int(columns[0])
                    if element_id <= 0:
                        raise ValueError(f"invalid element ID {element_id}; IDs must be positive")
                    if element_id in seen_elements:
                        raise ValueError(f"duplicate element ID {element_id}")
                    node_ids = tuple(int(v) for v in columns[1:])
                    expected = SUPPORTED_ELEMENT_TYPES[element_type]
                    if len(node_ids) != expected:
                        raise ValueError(f"element {element_id} of type {element_type} expects {expected} nodes, got {len(node_ids)}")
                    elements.append((element_id, element_type, node_ids))
                    seen_elements.add(element_id)
            except ValueError as exc:
                raise ValueError(f"{path}:{line_number}: {exc}") from exc

    if not nodes:
        raise ValueError(f"{path}: no *NODE records found")
    return tuple(nodes), tuple(elements)


def _parse_ntl(path: Path, id_to_index: dict[int, int]) -> PointField:
    with path.open(encoding="utf-8-sig") as stream:
        title = stream.readline().strip()
        header_line = stream.readline()
        source = stream.readline()
        if not header_line or not source:
            raise ValueError(f"{path}: incomplete NTL header")
        header = header_line.split()
        if len(header) < 5:
            raise ValueError(f"{path}: malformed NTL header")
        try:
            count = int(header[0])
            width = int(header[4])
        except ValueError as exc:
            raise ValueError(f"{path}: invalid NTL record count or width") from exc
        if width != 1:
            raise ValueError(f"{path}: only scalar NTL records are currently supported, got width {width}")
        values: list[float | None] = [None] * len(id_to_index)
        seen: set[int] = set()
        for line_number, raw in enumerate(stream, 4):
            line = raw.strip()
            if not line:
                continue
            columns = line.split()
            if len(columns) != 2:
                raise ValueError(f"{path}:{line_number}: expected node ID and one scalar value")
            try:
                node_id = int(columns[0])
                value = float(columns[1].replace("D", "E").replace("d", "e"))
            except ValueError as exc:
                raise ValueError(f"{path}:{line_number}: invalid NTL record") from exc
            if node_id not in id_to_index:
                raise ValueError(f"{path}:{line_number}: unknown node ID {node_id} in NTL")
            if node_id in seen:
                raise ValueError(f"{path}:{line_number}: duplicate NTL node ID {node_id}")
            values[id_to_index[node_id]] = value
            seen.add(node_id)
        if count != len(id_to_index) or seen != set(id_to_index):
            missing = sorted(set(id_to_index) - seen)
            raise ValueError(f"{path}: NTL records do not match mesh nodes; expected {len(id_to_index)}, header {count}, missing {missing}")
        return PointField(_ntl_field_name(title, path.stem), tuple(float(value) for value in values if value is not None))


def load_ntl_timeseries(path: str | Path, id_to_index: dict[int, int]) -> PointFieldTimeSeries:
    """Read scalar samples or interleaved XYZ velocity samples per node.

    Width is steps for scalars and three times steps for VELOCITY titles.
    A node ID is followed by that many values; line wrapping is immaterial.
    Time values are represented by zero-based step indices because the NTL
    header does not declare a time interval.
    """
    source = Path(path)
    with source.open(encoding="utf-8-sig") as stream:
        title = stream.readline().strip()
        header_line = stream.readline()
        source_line = stream.readline()
        if not header_line or not source_line:
            raise ValueError(f"{source}: incomplete NTL header")
        header = header_line.split()
        if len(header) < 5:
            raise ValueError(f"{source}: malformed NTL header")
        try:
            count, width = int(header[0]), int(header[4])
        except ValueError as exc:
            raise ValueError(f"{source}: invalid NTL record count or width") from exc
        if count != len(id_to_index) or width <= 0:
            raise ValueError(f"{source}: expected {len(id_to_index)} node records and positive time-step count, got {count} records and width {width}")

        components, steps = _ntl_layout(title, width)
        shape = (steps, count, 3) if components == 3 else (steps, count)
        values = np.empty(shape, dtype="float64")
        seen: set[int] = set()
        tokens = _ntl_tokens(stream, components == 3)
        iterator = iter(tokens)
        for record_index in range(count):
            try:
                node_token, line_number = next(iterator)
            except StopIteration as exc:
                raise ValueError(f"{source}: incomplete NTL records; expected {count} nodes") from exc
            try:
                node_id = int(node_token)
            except ValueError as exc:
                raise ValueError(f"{source}:{line_number}: invalid NTL node ID '{node_token}'") from exc
            if node_id not in id_to_index:
                raise ValueError(f"{source}:{line_number}: unknown node ID {node_id} in NTL")
            if node_id in seen:
                raise ValueError(f"{source}:{line_number}: duplicate NTL node ID {node_id}")
            point_index = id_to_index[node_id]
            for step in range(width):
                try:
                    value_token, value_line = next(iterator)
                    value = float(value_token.replace("D", "E").replace("d", "e"))
                    if components == 3:
                        values[step // 3, point_index, step % 3] = value
                    else:
                        values[step, point_index] = value
                except StopIteration as exc:
                    raise ValueError(f"{source}:{line_number}: node {node_id} has fewer than {width} time values") from exc
                except ValueError as exc:
                    raise ValueError(f"{source}:{value_line}: invalid NTL value '{value_token}'") from exc
            seen.add(node_id)
        try:
            extra, extra_line = next(iterator)
        except StopIteration:
            extra = None
        if extra is not None:
            raise ValueError(f"{source}:{extra_line}: unexpected extra NTL token '{extra}'")
        if seen != set(id_to_index):
            missing = sorted(set(id_to_index) - seen)
            raise ValueError(f"{source}: NTL records do not match mesh nodes; missing {missing}")
    return PointFieldTimeSeries(_ntl_field_name(title, source.stem), tuple(float(i) for i in range(steps)), values, components)


def load_ntl_auto(path: str | Path, id_to_index: dict[int, int]) -> LoadedNtl:
    """Load scalar or XYZ velocity NTL, selecting parsing by title and width."""
    classification = classify_ntl(path)
    if classification.node_count != len(id_to_index):
        raise ValueError(
            f"{path}: NTL declares {classification.node_count} nodes but INP has {len(id_to_index)}"
        )
    if classification.kind == "single_step":
        return LoadedNtl("single_step", field=_parse_ntl(Path(path), id_to_index))
    return LoadedNtl("time_series", series=load_ntl_timeseries(path, id_to_index))


def load_dataset(inp_path: str | Path, ntl_paths: tuple[str | Path, ...] | list[str | Path] = ()) -> Dataset:
    path = Path(inp_path)
    nodes, raw_elements = _parse_inp(path)
    id_to_index = {node.source_id: index for index, node in enumerate(nodes)}
    elements: list[Element] = []
    for element_id, element_type, node_ids in raw_elements:
        for node_id in node_ids:
            if node_id not in id_to_index:
                raise ValueError(f"{path}: element {element_id} references unknown node ID {node_id}")
        elements.append(Element(element_id, element_type, tuple(id_to_index[node_id] for node_id in node_ids)))
    fields = tuple(_parse_ntl(Path(ntl), id_to_index) for ntl in ntl_paths)
    return Dataset(nodes, tuple(elements), id_to_index, fields)

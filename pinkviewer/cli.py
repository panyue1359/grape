"""Command-line interface for PinkViewer."""

import argparse
import json
from dataclasses import replace
from pathlib import Path
import sys

from .model import classify_ntl, load_dataset, load_ntl_auto
from .writers import write_dataset, write_xdmf_timeseries


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="grape", description="Inspect, validate, and convert INP/NTL meshes.")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("inspect", "validate"):
        command = commands.add_parser(name)
        command.add_argument("inp", type=Path)
        command.add_argument("ntl", nargs="*", type=Path)
    convert = commands.add_parser("convert")
    convert.add_argument("inp", type=Path)
    convert.add_argument("output", type=Path)
    convert.add_argument("--format", choices=("vtk", "vtu", "xdmf"), required=True)
    convert.add_argument("--ntl", action="append", default=[], type=Path)
    batch = commands.add_parser("batch")
    batch.add_argument("manifest", type=Path, help="JSON array of {inp, output, format, ntl?} jobs")
    return parser


def _load_ntls(inp: Path, ntl: list[Path]):
    dataset = load_dataset(inp)
    loaded = [load_ntl_auto(path, dataset.source_id_to_index) for path in ntl]
    return dataset, loaded


def _run_job(inp: Path, output: Path, fmt: str, ntl: list[Path]) -> None:
    dataset, loaded = _load_ntls(inp, ntl)
    output.parent.mkdir(parents=True, exist_ok=True)
    series = [item.series for item in loaded if item.kind == "time_series"]
    scalar = [item.field for item in loaded if item.kind == "single_step"]
    if series:
        if fmt != "xdmf":
            raise ValueError("multi-time-step or velocity NTL requires --format xdmf")
        if scalar:
            raise ValueError("single-step NTL files cannot be combined with time-series NTL files in one conversion")
        names = [item.name for item in series]
        if len(set(names)) != len(names):
            renamed = []
            for path, item in zip(ntl, loaded):
                if item.kind == "time_series":
                    renamed.append(replace(item.series, name=f"{item.series.name} ({path.stem})"))
            series = renamed
        write_xdmf_timeseries(dataset, series, output)
    else:
        write_dataset(replace(dataset, fields=tuple(scalar)), output, fmt)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command in ("inspect", "validate"):
            dataset, loaded = _load_ntls(args.inp, args.ntl)
            classifications = []
            for path, item in zip(args.ntl, loaded):
                classification = classify_ntl(path)
                classifications.append({
                    "path": str(path),
                    "kind": item.kind,
                    "components": classification.components,
                    "steps": classification.steps,
                    "name": item.field.name if item.field else item.series.name,
                })
            if args.command == "inspect":
                print(json.dumps({"nodes": len(dataset.nodes), "elements": len(dataset.elements), "fields": [field.name for field in dataset.fields], "ntl": classifications, "element_types": sorted({element.element_type for element in dataset.elements})}, indent=2))
            else:
                print(f"Valid: {len(dataset.nodes)} nodes, {len(dataset.elements)} elements, {len(classifications)} NTL files")
        elif args.command == "convert":
            _run_job(args.inp, args.output, args.format, args.ntl)
            print(f"Wrote {args.output}")
        else:
            jobs = json.loads(args.manifest.read_text(encoding="utf-8"))
            if not isinstance(jobs, list):
                raise ValueError("batch manifest must be a JSON array")
            failed = False
            for index, job in enumerate(jobs, 1):
                try:
                    base = args.manifest.parent
                    resolve = lambda value: (base / value).resolve()
                    _run_job(resolve(job["inp"]), resolve(job["output"]), job["format"], [resolve(v) for v in job.get("ntl", [])])
                    print(f"[{index}/{len(jobs)}] OK {job['output']}")
                except Exception as exc:
                    failed = True
                    print(f"[{index}/{len(jobs)}] ERROR {job.get('inp', '?')}: {exc}", file=sys.stderr)
            if failed:
                return 1
        return 0
    except (OSError, ValueError, RuntimeError, KeyError, json.JSONDecodeError) as exc:
        print(f"grape: error: {exc}", file=sys.stderr)
        return 2

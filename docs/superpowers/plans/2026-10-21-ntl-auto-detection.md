# NTL Automatic Classification and Conversion Plan

> **For agentic workers:** Execute this plan inline, task by task, with tests before implementation. Keep the Todo states below current. Do not commit, push, or merge.

**Goal:** Automatically classify supported NTL files as single-component/single-step or single-component/multi-step using their declared width, validate them against an INP mesh, and choose the corresponding output path without requiring a special time-series flag.

**Architecture:** Treat the NTL header width as the number of scalar samples per node under the product convention: width `1` means a single scalar step; width greater than `1` means one scalar component across that many time steps. Parse and validate node records against INP IDs before conversion. Ordinary `--ntl` becomes automatic; scalar NTLs remain supported by VTK/VTU/XDMF, while a multi-step NTL is written as a temporal XDMF/HDF5 collection. Multiple time-series NTL files or mixing scalar and time-series NTLs in one conversion will be rejected until explicitly modeled.

**Tech Stack:** Python 3.11–3.13, argparse, NumPy, h5py, ElementTree, pytest.

**Spec:** Product convention confirmed in the user request on 2026-10-21 and the repository instructions in `AGENTS.md`.

## Global Constraints

- Core runtime must not depend on PyQt5, PyWebView, or Tkinter.
- INP node IDs must be validated and remapped explicitly; unknown element types must fail.
- NTL values must map one-to-one to INP node IDs; duplicate, missing, unknown, or malformed records fail.
- NTL is single-component only. Header width `1` means single-step; width `N > 1` means `N` time steps.
- Do not guess physical time intervals absent from NTL metadata; XDMF time coordinates are zero-based step indices.
- XDMF/HDF5 requires homogeneous cell type and output paths must not be overwritten.
- Do not commit, push, merge, or delete user data.

---

## Files and Responsibilities

- `pinkviewer/model.py`: inspect NTL header width, parse scalar NTL or time-series NTL, return a typed classification, and validate exact node coverage.
- `pinkviewer/cli.py`: make `inspect`, `validate`, and `convert --ntl` automatically choose/report NTL kind; remove the now-unneeded `--timeseries-ntl` switch.
- `pinkviewer/writers.py`: retain scalar XDMF output and temporal XDMF/HDF5 writer.
- `tests/fixtures/shuffled_timeseries.ntl`: small width-2 fixture with deliberately shuffled node IDs.
- `tests/test_model.py`, `tests/test_cli.py`, `tests/test_writers.py`: classification, diagnostics, automatic command routing, and time-series output tests.
- `docs/grape-manual.md`, `UDF/README.md`: document convention, command examples, limits, and validation.

## Todo

- [completed] Task 1: Define and test automatic NTL classification and strict record validation.
- [completed] Task 2: Automatically route inspect/validate and convert commands based on width.
- [completed] Task 3: Verify XDMF/HDF5 temporal output, rebuild EXE, and validate real Benchmark inputs.
- [completed] Task 4: Update user/developer docs and final worktree/test review.

## Task 1 — NTL classification and parser tests

1. Add unit tests that `classify_ntl(path)` returns single-step for width 1 and time-series for width 2, including the number of steps.
2. Add tests that width-2 data maps each sample to the correct dense point index for shuffled IDs.
3. Add failure tests for node-count mismatch, missing/duplicate/unknown node IDs, invalid values, too few or extra tokens, and non-positive width.
4. Run `python -m pytest tests/test_model.py -q` and confirm new behavior fails before implementation.
5. Implement a typed classification result and one automatic loader; preserve `_parse_ntl`'s scalar validation or route it through the shared header/ID checks.
6. Run the model tests and confirm all cases pass. No 109-column data may be arbitrarily split as vector components; by convention it is 109 time samples of one scalar field.

## Task 2 — CLI automatic selection tests and routing

1. Add CLI tests proving `inspect mesh.inp values.ntl` reports kind, component count `1`, and step count; `validate` performs the same parsing and reports success.
2. Add conversion tests showing `convert --format xdmf --ntl width1.ntl` produces regular scalar XDMF and `convert --format xdmf --ntl width2.ntl` produces a temporal collection, with no special time-series option.
3. Add tests that width greater than 1 with VTK or VTU errors with a message requiring XDMF, and that mixing scalar/multi-step NTLs or passing multiple time-series files is rejected clearly.
4. Run the targeted tests and confirm they fail before CLI changes.
5. Route a single width-1 NTL through the existing dataset scalar field path. Route exactly one width-greater-than-1 NTL through `write_xdmf_timeseries`. Reject ambiguous multi-file combinations.
6. Remove `--timeseries-ntl`; keep `--ntl` as the sole NTL input option. Update batch manifest handling to apply the same automatic routing and errors.
7. Run all CLI tests and confirm they pass.

## Task 3 — Format and real-data verification

1. Assert the temporal XDMF collection has one grid per header width, times `0..N-1`, and each HDF5 step array has exactly one scalar per INP node.
2. Run the full test suite and `git diff --check`.
3. Convert `Benchmarkg.inp` plus `Benchmarkt.ntl` using only `--ntl` and `--format xdmf` to a new, non-existing output path under `output/`.
4. Verify 114,956 points, 548,500 elements, 109 steps, and step arrays at indices 0 and 108. Keep the earlier mesh-only VTU and any prior XDMF/HDF5 outputs unchanged.
5. Build `dist/grape.exe` from current sources, then run EXE `inspect`, `validate`, and time-series `convert --help`; perform a real EXE conversion to a separate new output name and inspect its XDMF/HDF5 dimensions.

## Task 4 — Documentation and handoff

1. Update the binary manual: `--ntl` automatically detects width; show width-1 scalar and width-N temporal XDMF examples; state XDMF-only restriction for multi-step output and zero-based index semantics.
2. Update `UDF/README.md` with accepted invariant, supported record layout, tests, and known ambiguity that classification follows the convention rather than intrinsic NTL metadata.
3. Record actual tests, EXE build and real data counts. Keep migration history intact.
4. Review status and diff read-only; do not commit, push, merge, or delete outputs.

## Acceptance Criteria

- `--ntl` automatically selects width-1 or width-N handling in CLI and batch.
- Inspect/validate report classification and validate all node IDs and values against the INP.
- Multi-step scalar data yields valid temporal XDMF/HDF5; each time slice has one scalar per node.
- Multi-step conversion to VTK/VTU and unsupported mixed/multiple series combinations fail clearly.
- No attempt is made to infer physical timestamps or support multicomponent NTL.
- Full tests pass; Windows EXE is rebuilt and the actual benchmark conversion is validated.

## Execution Results

- Added `classify_ntl()` and `load_ntl_auto()`; width `1` resolves to `single_step`, while width greater than `1` resolves to `time_series`, with one scalar component in both cases.
- `inspect` now reports NTL path, kind, component count, step count, and field name. `validate` validates NTL record shape and exact node-ID mapping.
- `convert --ntl` and batch jobs automatically route single-step fields to regular writers and one multi-step scalar NTL to temporal XDMF/HDF5. Multi-step data with VTK/VTU, multiple series, and scalar/series mixtures fail clearly. Removed `--timeseries-ntl`.
- TDD suite: 21 tests pass on Python 3.13.5. `git diff --check` passes.
- Rebuilt `dist/grape.exe`; its help exposes only `--ntl`. The EXE inspected and validated `Benchmarkg.inp` + `Benchmarkt.ntl`, reporting 114,956 nodes, 548,500 elements, one component, and 109 steps, then converted successfully.
- Verified EXE XDMF/HDF5 output contains 109 time grids (0–108), mesh arrays `(114956, 3)` and `(548500, 4)`, and scalar slices of length `114956` at steps 0 and 108. Output: `output/Benchmarkg_temperature_timeseries_auto_exe.xdmf` and matching `.h5`.
- Docs updated. No commit, push, merge, or deletion performed.

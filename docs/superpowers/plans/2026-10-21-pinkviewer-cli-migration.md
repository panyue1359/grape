# PinkViewer CLI Migration Plan

Date: 2026-10-21  
Repository: project root
Execution branch: `pinkviewer-cli-migration` (created after explicit user confirmation)  
Status: implementation in progress; core mapping and VTK/VTU smoke checks passed

## Confirmed product decisions

- Archive the traditional PinkViewer implementation under tag `legacy-viewer-v1` and branch `legacy-viewer`.
- Transform the active product into a headless INP/NTL command-line application. Do not maintain compatibility with old tools or commands; prioritize correctness.
- Provide `inspect`, `validate`, `convert`, and `batch` commands.
- Write VTK, VTU, and XDMF/HDF5 output.
- Support Python 3.11–3.13 and Windows/Linux; produce a Windows PyInstaller executable.
- Initial implementation may load complete datasets into memory. Streaming and performance optimization are explicitly deferred.
- Core code must not depend on PyQt5, PyWebView, or Tkinter.
- Node IDs must be explicitly validated and remapped; unsupported element types must fail clearly.
- An external local reference project was used during development; its machine-specific path is omitted. Do not copy its GUI code, `build/`, `dist/`, or large generated files.
- Do not merge or push `main` automatically.
- Product naming: the user-facing distribution is `grape-mesh-cli`, the console command is `grape`, and the Windows executable is `grape.exe`. The Python import namespace remains `pinkviewer` as an internal implementation detail for this release; this does not preserve the old GUI or CLI commands.

## Scope and acceptance criteria

Deliver an installable Python package with documented CLI behavior, parser/model/converter separation, deterministic ID mapping, useful validation diagnostics, batch processing, format writers, tests, and Windows packaging configuration. The minimum correctness proof is a small fixture with shuffled, non-contiguous node IDs: test that element connectivity maps to the correct point indices, and that missing/duplicate/invalid IDs are rejected. Unknown element types must be hard errors, not silently skipped or guessed.

The implementation should run on Python 3.11, 3.12, and 3.13 on Windows and Linux. Unit tests must not require the GUI stack. Format-specific tests should verify generated files or round-trip them where practical. Packaging configuration should produce a Windows PyInstaller EXE; an actual Windows build is required when the environment permits, otherwise document the precise blocker and command.

## Repository and source handling

- Keep active CLI source and tests in a new, clearly named package/test structure; keep `UDF/README.md` as the development record per repository workflow.
- Before removing or relocating any legacy GUI source/assets, obtain explicit confirmation using the repository's dangerous-operation warning format.
- Before creating `legacy-viewer-v1` or `legacy-viewer`, obtain explicit confirmation using that same format. The confirmed intent to archive does not waive this operation-specific gate.
- Preserve the legacy implementation in the approved archive branch/tag before any approved deletion from the CLI branch.
- Do not copy forbidden content from the sibling reference project.
- No commit, push, or merge without separate explicit confirmation.

## Architecture

1. **Package skeleton and CLI shell**: define package metadata, supported Python classifiers, console entry point, and command groups. CLI parsing and exit codes should be testable without GUI libraries.
2. **Internal model**: represent nodes, elements, element types, and optional NTL fields with explicit typed structures. Keep source IDs distinct from dense output indices.
3. **INP/NTL parsing**: parse only documented/supported syntax; report line-aware errors for malformed or unsupported constructs. Do not infer unknown element semantics.
4. **Validation and ID map**: reject duplicate or invalid node IDs, detect missing connectivity references, and create a deterministic source-ID-to-zero-based-index mapping. Preserve source IDs as metadata when output format permits.
5. **Writers**: implement VTK legacy, VTU XML, and XDMF with HDF5 data. Make cell-type mapping explicit and fail if an element cannot be represented correctly.
6. **Commands**: `inspect` summarizes inputs, `validate` checks syntax and topology, `convert` writes one requested format, and `batch` processes a manifest/input set with per-file results and predictable failure behavior.
7. **Packaging and docs**: Windows PyInstaller spec/build instructions, platform-independent package install/run instructions, examples, and limitations.

## TDD execution tasks and checkpoints

### Task 0 — Plan and development record

- Save this complete plan at `docs/superpowers/plans/2026-10-21-pinkviewer-cli-migration.md`.
- Create `UDF/README.md` with requirements, architecture, supported inputs/outputs, build/use instructions, validation plan, risks, and an execution log.
- Review the plan and repository state before implementation.
- State: completed; plan and `UDF/README.md` created and reviewed.

### Task 1 — Legacy archive checkpoint

- Prepare the legacy archive from the current committed GUI source and assets.
- Request explicit confirmation immediately before creating `legacy-viewer` and `legacy-viewer-v1`.
- Verify both references point to the preserved legacy revision.
- Only after archive verification, request a separate explicit confirmation before deleting GUI source/assets from the active CLI branch. Do not delete anything without that confirmation.
- State: completed after explicit confirmations; local archive branch/tag verified at the legacy commit, and legacy GUI modules/assets removed from the active migration branch.

### Task 2 — Package skeleton (TDD)

- Add tests first for importable package, `--help`, command names, and GUI dependency exclusion.
- Implement the smallest package metadata/entry point satisfying those tests.
- Run the targeted tests.
- State: initial package/CLI implemented; help and GUI-dependency exclusion test passes.

### Task 3 — Internal data model and ID mapping (TDD)

- Add minimal INP/NTL fixtures including out-of-order, non-contiguous node IDs and connectivity referencing those IDs.
- Write failing tests first proving dense point order and exact connectivity mapping.
- Add tests for duplicate node IDs, missing referenced IDs, invalid IDs, and unsupported element types.
- Implement explicit validation and deterministic remapping; reject unknown types.
- Run targeted tests and inspect expected arrays/connectivity by hand.
- State: completed for fixture requirements. IDs 40, 10, 90 map deterministically to 0, 1, 2; connectivity (40,10,90) maps to (0,1,2); NTL is ID-aligned. Duplicate, missing, nonpositive, and unknown types tested.

### Task 4 — Input parsing and validation (TDD)

- Add focused parser tests for supported INP/NTL constructs, malformed records, comments, and line-aware diagnostics.
- Implement only the necessary subset and document unsupported features.
- Test `inspect` and `validate` commands with valid and invalid inputs.
- State: focused Abaqus-style node/element and scalar NTL subset implemented; 11 standard-library tests pass. Reference 40 MB INP parsed as 114,956 nodes and 548,500 C3D4 elements.

### Task 5 — Single-file conversion (TDD)

- Test each writer using small fixtures before implementation.
- Implement VTK and VTU, then XDMF/HDF5 with explicit cell mappings and source-ID preservation where supported.
- Verify output existence, structure, values, and clear failures for unrepresentable cells.
- State: ASCII VTK, XML VTU, and XDMF/HDF5 writers implemented and smoke-tested. Source node/element IDs are preserved as output metadata. Existing outputs are not overwritten. XDMF requires homogeneous cells.

### Task 6 — Batch workflow (TDD)

- Test manifest/input discovery, destination naming, mixed success/failure, and exit status.
- Implement deterministic batch behavior without silently overwriting unrelated files.
- State: JSON manifest command implemented and tested for successful conversion and refusing overwrite on repeated run.

### Task 7 — Cross-version/platform and packaging

- Add CI/test configuration for Python 3.11–3.13 on Windows and Linux.
- Add PyInstaller configuration and Windows build command.
- Run available test matrix/package smoke checks; record unavailable platform/build checks explicitly.
- State: package metadata declares Python 3.11–3.13 and Windows/Linux. The 12-test suite passes on Python 3.11.7, 3.12.13, and 3.13.5. Windows PyInstaller one-file build and EXE help smoke test pass.

### Task 8 — Documentation and handoff

- Complete `UDF/README.md` with actual commands, dependencies, test/build outcomes, unsupported syntax, and risks.
- Review repository diff and ensure forbidden reference artifacts were not copied.
- Do not commit, push, or merge. Request confirmation before any separately gated operation.
- State: completed. Expanded the binary-converter manual and aligned `UDF/README.md` with Grape naming and actual supported features; no commit/push/merge performed.

## Verification strategy

- Run targeted tests after each TDD task, then the full suite.
- Verify installed CLI help and each command against small fixtures.
- Inspect generated VTK/VTU/XDMF/HDF5 artifacts and assert the exact node/cell mapping.
- Search core/package dependencies for PyQt5, PyWebView, and Tkinter imports.
- Verify supported Python versions in project metadata/CI and run what the current environment supports.
- Verify PyInstaller configuration and build the EXE on Windows when available.
- Finish with read-only `git status`, diff review, and a concise summary of any checks not executable here.

## Current execution record

- Initial read-only Git inspection: clean worktree, `main` at `5e49da11993f6ded9f9867d4a440ef9aa26f55c6`, only `main` and `origin/main`, no tags, remote `origin` configured.
- No repository or parent `AGENTS.md` file exists in the workspace; user supplied complete workflow instructions in the request.
- User explicitly approved creation of `pinkviewer-cli-migration`; branch created locally. No commit, push, merge, archive ref, or deletion has occurred.
- User subsequently explicitly approved the archive refs and legacy GUI deletion; both archive refs point at the recorded legacy commit. Legacy deletions are staged in the working tree, not committed.
- Current implementation files: `pinkviewer/`, `tests/`, `pyproject.toml`; no content was copied from the reference project.
- Verification: 12 pytest tests pass on Python 3.11.7, 3.12.13, and 3.13.5; CLI help/inspect/validate/convert/batch smoke checks pass; reference INP parsed successfully; XDMF/HDF5 exact-data checks pass; Windows PyInstaller EXE build and help smoke test pass; `git diff --check` passes. A wheel build was not required for the current delivery and was not repeated after uv installation.
- Final review: documented exact INP/NTL subset and homogeneous-only XDMF constraint, added source element IDs to VTK output, and added ignore rules for local `.venv`, PyInstaller build/dist, pytest cache, and Python bytecode. Generated EXE/build artifacts were retained locally, not deleted.
- 2026-10-21 naming update: user selected `grape`. Updated distribution metadata (`grape-mesh-cli`), console script and argparse help (`grape`), PyInstaller output name (`grape`), and the full binary converter manual. `dist/grape.exe --help` reports `usage: grape`; Windows one-file rebuild succeeded and the 12-test suite passes. Internal import package name `pinkviewer` is retained, explicitly documented as internal.

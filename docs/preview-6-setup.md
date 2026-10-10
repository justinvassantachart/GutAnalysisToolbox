# GAT Apple Silicon TEST preview 6: package notes

Release version: `2.0.1-apple-silicon.6`. Use native arm64 Fiji on macOS 14+,
with its bundled Java 21 recommended. These workers are ARM64 only; existing
Intel installations keep their legacy backend.

[Download preview 6](https://github.com/justinvassantachart/GutAnalysisToolbox/releases/tag/apple-silicon-preview-6).
An unlisted release is not published yet. This is an overlay containing the
plugin and both isolated workers, not Fiji, models or DeepImageJ engines.
No developer tools are needed to install the prebuilt package.

## What changed

The three ganglia float channels again use upstream Java V2's `1/255` scaling.
The output-selection guards remain. Native comparison matched original V2
exactly on three public samples; this is bounded behavioral parity, not
biological accuracy. See `PREVIEW_6_RELEASE_NOTES.md` for evidence and runtime
limits. Preview 5's alignment repair and prior CPU/calcium/multiplex safeguards
remain. Alignment protocol stays at version 2.

## Verify and install

1. Download `GAT-2.0.1-apple-silicon.6-macos-arm64-preview.zip`, its `.sha256`
   file and `FORK_BUILD_INFO.json` from the same release. Verify SHA-256 and ZIP
   integrity. Embedded `BUILD_INFO.json` must report version
   `2.0.1-apple-silicon.6`, `source_worktree_modified: false`,
   `alignment_protocol_version: 2` and the exact release commit
2. Extract to a new empty staging folder. Quit Fiji and back up the existing
   GAT plugin and both complete worker directories outside Fiji
3. Install only the new GAT JAR into the ImageJ data root's `plugins/`. Place
   both complete `gat-native-inference/` and `gat-native-alignment/` directories
   at the ImageJ data root alongside `plugins/`, never inside `plugins/`. Keep exactly one GAT JAR. Do not merge old/new worker libraries
   or move worker `lib/` JARs into Fiji's global `jars/` or `plugins/`
4. Keep models, engines and unrelated plugins unchanged. Use
   Plugins → GutAnalysisToolbox → GATV2. Keep working installations and images
   backed up, test a copy first, and recheck versions after Fiji updates

Current Fiji Latest uses the outer `Fiji/` data root beside `Fiji.app/`; confirm
with `IJ.getDirectory("imagej")`. Roll back by restoring the previous matched
plugin and complete worker directories. Do not use preview 2 for quantitative
multiplex exports. Installation prerequisites remain in the repository README
and [official GAT documentation](https://gut-analysis-toolbox.gitbook.io/docs/).

## Runtime and validation limits

Small ganglia inputs can still be rejected when the model's 1024-pixel tile
exceeds three times an image dimension; this normalization fix does not address
that tiling limitation.

The parity experiment substituted only two exact historical DeepImageJ/JDLL
JARs in disposable CI Fiji copies. That opt-in test mode is not an end-user
installation step, is not included in this overlay, and does not establish
compatibility with changed live-updater JARs. No model or engine upgrade is
required merely for the overlay update.

The release page records exact-source checks separately from older evidence.
Physical OpenCL/GPU, full interactive workflows and biological acceptance remain
open. Other historical inference comparisons retain their small mask/outline
differences. Legacy macros and QuPath files are preserved, not newly ported.
Earlier preview packages and reports remain unchanged historical materials.

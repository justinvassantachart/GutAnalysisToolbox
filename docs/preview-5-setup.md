# GAT Apple Silicon TEST preview 5: package notes

Release version: `2.0.1-apple-silicon.5`. Use native arm64 Fiji on macOS 14+,
with its bundled Java 21 recommended. The native workers in this download are
ARM64 only; existing Intel installations keep their legacy backend.

[Download preview 5](https://github.com/justinvassantachart/GutAnalysisToolbox/releases/tag/apple-silicon-preview-5).
An unlisted release is not published yet. This overlay contains the plugin and
both isolated workers, not a complete Fiji installation, models or engines.
Fiji/update-site/model requirements are in the repository README and
[official GAT documentation](https://gut-analysis-toolbox.gitbook.io/docs/).

## What changed

Native Template Matching now preserves adjusted display contrast and the base
LUT, matching the rendered pixels used by the original algorithm. The matching
method, reference ROI and integer shift selection are unchanged. Preview 4's
CPU/calcium safeguards and the earlier multiplex correction remain.

**The alignment protocol is version 2. Install the matching plugin and both
complete worker folders together.** Mixed-version installations fail explicitly;
a plugin-only replacement is insufficient. No new models or engine versions are
required merely for this overlay update.

## Verify and install

1. Download `GAT-2.0.1-apple-silicon.5-macos-arm64-preview.zip`, its `.sha256`
   file and `FORK_BUILD_INFO.json` from the same release. Verify the SHA-256 and
   ZIP integrity. The embedded `BUILD_INFO.json` must say version
   `2.0.1-apple-silicon.5`, `source_worktree_modified: false`,
   `alignment_protocol_version: 2` and the exact release commit
2. Extract into a new empty staging folder. Quit Fiji and preserve a backup of
   the old GAT plugin and both complete worker directories outside Fiji
3. In the ImageJ data root, install only the new GAT JAR into `plugins/` and
   place complete `gat-native-inference/` and `gat-native-alignment/` folders
   beside `plugins/`. Keep exactly one GAT plugin JAR. Do not merge old/new
   worker libraries or put their `lib/` JARs in Fiji's global classpath
4. Keep models, engines and unrelated plugins unchanged. Launch that Fiji copy
   using Plugins → GutAnalysisToolbox → GATV2. Keep working installations and
   original images backed up. Fiji updates can replace the preview plugin, so
   recheck its version and matching workers afterward

Current Fiji Latest uses the outer `Fiji/` data root beside `Fiji.app/`; confirm
with `IJ.getDirectory("imagej")` rather than assuming the inner app is the root.
To roll back, restore the previous matched plugin and complete worker folders.
Do not use preview 2 for quantitative multiplex exports.

## Evidence and limits

See `MAINTAINER_REVIEW_2026-10-06.md` and the release page for exact tested source
revisions. Compiled-class comparison verifies build consistency; it does not
prove tests ran. The current hosted OpenCL job failed; earlier runs exposed no usable device.
The exact new failure cause remains unverified until its log is inspected.
Physical GPU, full interactive workflows and biological acceptance remain open.
Historical inference comparisons retain their documented small mask/outline
differences. Legacy macros and QuPath files are preserved, not newly ported.

Earlier setup handoffs and published packages remain unchanged historical
materials. This release does not include a new computer-assistant handoff.

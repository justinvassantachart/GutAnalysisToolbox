# Same-host original/fork comparison with accepted calcium dialogs

[Actions run 37363236215, attempt 2](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37363236215/attempts/2), job 111949522086, completed on 2026-10-05. Both revisions ran on one **Apple M1 (Virtual), macOS 14.8.9, native aarch64 Temurin 21.0.12.1** host. The first attempt did not acquire a hosted runner and executed no application code.

- Original source: `1870d9e16e16fd6daeac0bd05122e851029ddedc`, clean before and after
- Fork source: `528f0b045682fa4e32465b5aaf1b61d6e834d8c3`
- Original JVM isolation checks passed: no fork inference classes or modern TensorFlow API
- **Overall job: failed.** The original StarDist command reached its TensorFlow-load error dialog and remained there until the 600-second deadline. The repaired native-call and common-control steps passed

This packet preserves the actual timeout classification. A captured native-load failure explains it; the original StarDist command did not complete a prediction or return normally.

## Actual GAT native calls and separate component controls

The native-call probes used the same optional URL-system-classloader bootstrap for both revisions. It applies the official ImageJ legacy patcher but does not modify original GAT or plugin source/classes. This is a diagnostic embedding, not the official Fiji executable.

**Original StarDist:** the actual `PluginCalls.runStarDist2DLabel` call and published StarDist/CSBDeep plugin dispatch were reached. `original-native/stardist.log:116` records that TensorFlow has no native library for `darwin/aarch64`. At the deadline, the main-thread stack is waiting in the actual GAT command (`:132–150`), while its prediction thread is blocked in `JOptionPane.showMessageDialog`, called by `TensorFlowNetwork.loadLibrary:117` (`:399–425`). This establishes an error-dialog wait after the native-load failure, rather than a bootstrap stall or slow model inference. The parent terminated the isolated process at 600.69 seconds.

**Original Template Matching:** the actual GAT call failed and left the shifted input unchanged. The captured ImageJ Exception window explicitly records `UnsatisfiedLinkError` for `jniopencv_core`/`opencv_imgproc`, through `AlignStack.alignTemplateMatching → Align_slices → cvMatch_Template → Loader`.

**Separate original-runtime controls:** direct TensorFlow 1.15 JNI initialization failed with the explicit `darwin/aarch64` message; direct OpenCV initialization failed after detecting `macosx-arm64`; direct execution of the published Template Matching plugin also failed at JNI loading. All three controls completed promptly. They are component evidence, not substitutes for the actual GAT calls above. The same old-component failures were observed in separate processes alongside the fork, which uses its isolated replacement workers for production calls.

**Fork StarDist:** the actual GAT call succeeded with 39 objects on the supplied public 175×175 Hu crop, probability 0.5, NMS 0.3, boundary exclusion 2 and four requested tiles. Its 16-bit raw label SHA-256 is `ea1767df58491cc03927e121943d955708450d091f3416b2493e1c93e51cd443`, exactly the previously preserved TF1/modern Linux four-tile reference. This remains raster evidence for a technical fixture, not biological-accuracy or strict subpixel-polygon equivalence.

**Fork Template Matching:** the actual GAT call succeeded and its aligned pixel SHA-256 exactly matches the unchanged old Linux algorithm reference: `8be9c6ad7c4c28d68b07f0b45c562deb9d29e4febf030b0ad24dcb198ea7fa9c`.

Cold subprocess wall times were 12.71 seconds for successful fork StarDist and 4.37 seconds for successful fork alignment, including setup. Failed/timed-out original runs cannot establish a speedup. No paired GPU benchmark was performed.

## Accepted-dialog calcium result resolves the earlier uncertainty

**Both original and fork pass** the bounded calcium command workflow. The controller records an accepted value of 0 (`OK_OPTION`) for each known max-projection and baseline dialog. Both execute production open/projection/normalization/ROI/measurement/export methods and recover exactly **F/F0 `[1, 1, 2]`**, with baseline frames 1–2, max-projection frames 1–3, one ROI, CSV and ROI ZIP export.

The earlier first-run cancellation/timeout observations remain unchanged in their [separate packet](../mac-first-69feedb/REPORT.md). This accepted-dialog rerun does not reproduce a projection failure in either revision. Automatic StarDist calcium ROI generation remains disabled and untested; zero-baseline behavior and manual dashboard navigation are outside this smoke test.

## SIFT: original application defects are now directly reached

Providing the real, pinned Fiji `CollectGarbage_` command removes the earlier harness interruption. The unchanged original now reaches all three assertions:

- SIFT helper output loses calibration/timing
- Single-workflow saved/reopened image has unchanged misalignment: MSE 4727.119059726331 before and after
- Two-channel batch workflow produces no expected aligned output

The fork passes all three, including zero MSE in the known-translation saved single and batch fixtures, deterministic channel-1 extraction, unchanged batch input, and preserved calibration/timing. These are application data-flow fixes; the underlying SIFT library control passes on both revisions.

## Other original workflows do work

Seven Java helper checks, both morphology/GAT bridges, the direct StackReg helper and multiplex first-choice landmark matching pass on both revisions. Both full ganglia commands execute model inference and cleanup successfully. Original/fork foreground areas are 167,430/72,236 pixels; the fork intentionally corrects the measured raw-input double scaling (original 1 instead of 255). This is an output-changing input-contract correction, not mask parity or proof of better biological accuracy.

Across the five common-control reports, the original has 15 PASS, 4 FAIL, 1 BLOCKED and 8 NOT_RUN entries; the fork has 19 PASS, 1 BLOCKED and 8 NOT_RUN. These are report entries, not counts of unique complete workflows. The same deliberate gaps remain: StackReg batch is unimplemented; full multiplex export/fallback branches, manual ganglia editing, automatic calcium segmentation and full interactive navigation are not validated here. A `PARTIAL` suite retains these gaps even when all reached assertions pass.

## Evidence integrity

`original-ci-diagnostics.zip` is the unmodified 153,013-byte GitHub artifact 11369085599, SHA-256 `a7b19dfdf4a425fef9e9e6f15463e9b91aeb6b0f0f50bdadda57ba605aa47313`. It contains 78 JSON/log/CSV files, with every member independently hashed in `original-artifact-files-sha256.json`. No research image, model or dependency binary is included. Historical runner paths remain in the immutable archive; `summary.json` uses portable path labels and retains observed results, provenance and the exact timeout cause.

Matched original/fork install artifacts were separately emitted before testing as artifact 11368870465. Their existence alone does not turn this partially scoped comparison into a release certification. Fresh official-Fiji startup, updater installation and dashboard gates are tracked by their own validation lane.

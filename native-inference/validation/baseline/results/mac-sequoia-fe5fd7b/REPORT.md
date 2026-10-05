# Independent same-host comparison on macOS Sequoia

[Actions run 37366290715](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37366290715), job 111952178284, completed on 2026-10-05. Original `1870d9e16e16fd6daeac0bd05122e851029ddedc` and fork `fe5fd7b0a5a9b6e79074ef24d79c27fd2c5c2372` ran on one **Apple M1 (Virtual), native aarch64 macOS 15.7.9 / Temurin 21.0.12.1** host. Original tracked source remained unchanged before and after.

This independently reproduces the [Sonoma paired comparison](../mac-sonoma-528f0b0/REPORT.md), using the same inputs, original production source, pinned old dependencies, optional URL-system-classloader bootstrap, component controls and assertions. It does not test another Apple Silicon chip generation.

## Observed outcomes

- **Fork StarDist and Template Matching pass.** The actual GAT call produces 39 labels with exact four-tile reference SHA-256 `ea1767df58491cc03927e121943d955708450d091f3416b2493e1c93e51cd443`. Alignment pixels exactly match the unchanged old Linux reference `8be9c6ad7c4c28d68b07f0b45c562deb9d29e4febf030b0ad24dcb198ea7fa9c`
- **Original StarDist reaches the actual GAT call and fails to load TensorFlow for `darwin/aarch64`.** Its log records that failure at line 116. The deadline thread dump records the waiting GAT caller and `TensorFlowNetwork.loadLibrary:117 → JOptionPane.showMessageDialog` at lines 411–413. It remains classified as `process_timeout` after 600.86 seconds because the error dialog prevents normal return
- **Original Template Matching fails at JNI loading.** Its actual GAT call records the ImageJ Exception window with `jniopencv_core`/`opencv_imgproc` errors and leaves the shifted input unchanged. Separate original TF1 JNI, OpenCV JNI and published-plugin controls all complete with explicit native/component failure. The fork's same old-component controls also fail in separate processes; its production calls use the replacement isolated workers
- **Original and fork calcium both pass with accepted dialogs and exact F/F0 `[1, 1, 2]`.** Baseline frames 1–2, max-projection frames 1–3, one ROI and CSV/ROI exports are checked. This repeats the resolved calcium result and does not validate automatic ROI generation or zero-baseline handling
- **Fork SIFT helper, saved single workflow and two-channel batch workflow pass.** Original helper loses calibration/timing; saved/reopened output retains misalignment MSE 4727.119059726331; original batch produces no expected aligned output. The underlying SIFT algorithm control passes on both
- **Both ganglia commands execute successfully**, with original/fork foreground area 167,430/72,236 pixels. The raw input-contract check fails only on the original (1 instead of 255). The fork intentionally changes this input scaling; equal masks or superior biological accuracy are not claimed
- Seven Java helpers, GAT morphology bridges, direct StackReg helper and first-choice multiplex landmarks pass on both. Common reports contain original 15 PASS / 4 FAIL / 1 BLOCKED / 8 NOT_RUN, and fork 19 PASS / 1 BLOCKED / 8 NOT_RUN. These are report entries, not unique complete workflows

The **overall job is failed**, solely because the original native-call step retains the error-dialog timeout. Repaired native-call and common-control steps passed. No timeout is relabeled as a completed prediction. Original source isolation, explicit unsupported StackReg batch and remaining full-GUI/multiplex/manual-review gaps are preserved.

Successful fork cold subprocess times were 12.78 seconds for StarDist and 4.92 seconds for alignment, including setup. Failed originals are not a speed comparison; no GPU multiplier or benchmark of the user's Mac follows from these observations.

## Preserved evidence

`original-ci-diagnostics.zip` is the unmodified 151,227-byte artifact 11368646756, SHA-256 `3045565bc4d1546f0f1670c9ae7d2d8fe5232d68edd07a9a40f16a729af077ea`. All 78 members are independently fingerprinted in `original-artifact-files-sha256.json`. The archive preserves original runner paths; `summary.json` uses portable path labels. No source image, model or dependency binaries are included.

Matched install artifacts are separately identified as artifact 11367939019. Fresh official-Fiji installation and dashboard checks belong to their own validation lane; this diagnostic embedding does not certify a complete interactive install.

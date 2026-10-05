# Completed paired native-Mac observations for corrected .3

[Run 37380707932, job 112001650462](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37380707932/job/112001650462) completed **SUCCESS** on Apple M1 (Virtual), native ARM64, macOS 15.7.9 (24G830), Temurin Java 21.0.12.1 aarch64. It compared unchanged original [`1870d9e16e16fd6daeac0bd05122e851029ddedc`](https://github.com/pr4deepr/GutAnalysisToolbox/commit/1870d9e16e16fd6daeac0bd05122e851029ddedc) with corrected fork [`ab046cb604dc04e75cf935b7a9f3c17b52843188`](https://github.com/justinvassantachart/GutAnalysisToolbox/commit/ab046cb604dc04e75cf935b7a9f3c17b52843188) on one host.

**Green means completed observations and passing repaired gates. It does not mean all original workflows work.** This packet preserves the tested `.3` candidate and its exact provenance; it is **not a release seal**. Its bundled guides still point to preview 2. A documentation-corrected successor must retain its own package/source identity rather than overwrite this evidence.

## Actual results

- All **3 required live passive error-dialog tests ran with zero skips**, including the visible modal positive control and negative controls. Synthetic observer tests are distinct from actual GAT calls
- Original StarDist reaches the real GAT/plugin call, then displays **“Loading TensorFlow failed”** with exact raw HTML `<html>Could not load TensorFlow.<br/>Opening the TensorFlow Library Management tool.</html>`. The newly created visible modal has `ERROR_MESSAGE` and untouched `JOptionPane.UNINITIALIZED_VALUE`. The observer saves the dialog, call stage and thread stacks, then halts only that isolated JVM with **exit 2**, after 7.26 seconds. It does not answer/dismiss the warning or enter Library Management. This is a recorded displayed failure, not a completed model prediction or a timeout
- Original Template Matching reaches the real GAT/plugin call and records an ImageJ Exception window with **missing `jniopencv_core` / `opencv_imgproc` JNI**. Deliberately shifted pixels remain unchanged; the process exits 2
- Fork StarDist succeeds with **39 objects, four requested tiles**, probability 0.5/NMS 0.3 and exact label SHA-256 **`ea1767df58491cc03927e121943d955708450d091f3416b2493e1c93e51cd443`**. Fork alignment changes the input and matches exact pixel SHA-256 **`8be9c6ad7c4c28d68b07f0b45c562deb9d29e4febf030b0ad24dcb198ea7fa9c`**
- Original SIFT helper/saved/batch checks remain FAIL; corresponding fork checks PASS. Both calcium controls PASS with F/F0 **[1, 1, 2]**. Both actual ganglia commands execute successfully, recording **167,430 original / 72,236 fork** foreground pixels. Original raw-input-contract FAIL and corrected fork PASS remain distinct; the mask change does not establish biological superiority or legacy parity
- Common workflow reports retain original **15 PASS / 4 FAIL / 1 BLOCKED / 8 NOT_RUN**, and fork **19 PASS / 1 BLOCKED / 8 NOT_RUN**. Their aggregate states remain FAIL/PARTIAL respectively. Unsupported/unrun branches are not converted into passes

Original source provenance is clean before and after execution, with no fork inference classes or modern TensorFlow in its parent JVM. `original-final-status.log` is present and empty; separate CI metadata confirms the final tracked-source cleanliness gate. The old TensorFlow/OpenCV/direct-plugin component probes fail in **both** parent JVMs, while fork actual GAT calls succeed through isolated workers. These component controls do not substitute for actual workflow evidence.

## Keep the two launcher lanes separate

This paired native-call lane explicitly uses diagnostic **`url-system` / `BaselineUrlClassLoader`** embedding. The earlier [real installed-Fiji packet](../../../../../validation/fiji-install/results/mac-mask-retention-5e2e0f4/REPORT.md), from source `5e2e0f4`, used the real official launcher and bundled Zulu JVM/AppClassLoader. There the original neuron path failed at the old `AppClassLoader` → `URLClassLoader` cast before JNI. That earlier installed-Fiji result is **not a fresh `.3` execution** and is not rewritten as this diagnostic native-load failure.

The separate [corrected full-multiplex packet](../../../multiplex-full/results/mac-ab046cb/README.md) preserves [run 37380708003 / job 112001650098](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37380708003/job/112001650098). Its evidence is not duplicated here. All six recorded production-class hashes independently match the `.3` packaged plugin.

## Matched package audit

[Matched install artifact 11372914623](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37380707932/artifacts/11372914623) is **206,659,271 bytes**, SHA-256 `57e29238e96c3713e906a33c3f003b064af3a640ceed169abf6238bf9753c227`. All 6 members and extracted bytes were verified. Large binaries are not copied into this packet.

- Fork `GAT-2.0.1-apple-silicon.3-macos-arm64-preview.zip`: **203,285,587 bytes**, SHA-256 `0be755efe7dbac48b2fa93a6e38dc04a2d4d713251a93a6b7f5ebae057ed9cf5`; 37 members
- Original `GAT-2.0.0-unchanged-1870d9e-baseline.zip`: **1,664,423 bytes**, SHA-256 `bd8b0f3ae2b9487bc9d1a92c66ddf2f300cc70944ec963754c093e07460bef09`; 4 members
- Main fork plugin SHA-256: `d92e18b467af9a1ba4ba13d0e4e82a8982b552dcdbbd434a9deec488e42ec535`; no TensorFlow, JavaCPP/Bytedeco or TemplateMatching classes in the main plugin
- All **94 bundled native Mach-O slices are ARM64**; all **14 dependency JARs** and **12 worker class byte arrays** equal the exact released native-Mac preview-2 archive, SHA-256 `9c5a542b82eb146b9c1d6c78ca20d1a0ffb8d10af7d35d6cd8ead8b927ac1f9f`. This does not equate whole worker JARs, main plugins, packages or source revisions
- All **9 packaged alignment corresponding-source files** equal their exact `ab046cb` source paths. CI build metadata records 156 packaged plugin classes matching tested classes; this packet independently repeats the six full-multiplex class comparisons, not the full 156-class build-time comparison

`package/verification.json` gives the independent byte/source results; exact supplied review JSONs, build metadata, checksums and all install/package member hashes are retained alongside it. Original and `.3` packages remain distinct from released preview 2. Packaging is not biological, physical-Mac or release acceptance.

## Preservation, verification and limits

[Report artifact 11374062110](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37380707932/artifacts/11374062110) is retained byte-for-byte as `original-ci-diagnostics.zip`: **158,524 bytes**, SHA-256 **`ef0135b2d34f73843eafc9e031bca0508f51c20408ab33a88badd74b9acc4855`**. ZIP CRC and all **79 original members** passed independent verification. The original member set was not changed.

- `original-artifact-files-sha256.json` and `ARTIFACT-MEMBERS.sha256` retain every original member's size/hash
- `summary.json` is a compact derived result; complete classpaths, dialog component trees and thread stacks remain unchanged in the ZIP
- `job-step-status.json` and `artifact-ci-status.json` are **separately sourced decoded read-only connector evidence**, not original ZIP members or raw HTTP-response bytes
- `package/` preserves small audit/provenance records and exact member manifests, without distribution JARs/ZIPs
- `SHA256SUMS` covers every packet file except itself. Run `sha256sum -c SHA256SUMS` (macOS: `shasum -a 256 -c SHA256SUMS`). Extract the original report ZIP separately, then check `ARTIFACT-MEMBERS.sha256` from that extraction root

No full interactive GUI/navigation, biological accuracy, physical-Mac Finder/Gatekeeper first-open, all-chip or GPU/OpenCL acceptance is claimed. The report ZIP does not retain ganglia TIFFs; its foreground counts are recorded runtime observations, with independently retained pixels in the separate earlier installed-Fiji packet. Fork cold-process times were 13.40 seconds for StarDist and 5.05 seconds for alignment, including setup; failed originals are not valid speed baselines. Earlier immutable packets, production code, harnesses and workflows are untouched by this packet preparation.

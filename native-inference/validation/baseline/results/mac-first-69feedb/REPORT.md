# First same-host unchanged-original comparison

[Actions run 37357196889](https://github.com/simplecoreorg-cyber/GutAnalysisToolbox/actions/runs/37357196889), job 111922492267, completed on 2026-10-05. The overall job is **failed**, because the fork's calcium control failed. The native-command steps below nevertheless completed and their evidence was preserved.

Both revisions ran sequentially on one **Apple M1 (Virtual), macOS 14.8.9, native aarch64 Temurin 21.0.12.1** host:

- Original: `1870d9e16e16fd6daeac0bd05122e851029ddedc`; tracked sources remained clean before and after
- Fork: `69feedb86f4c4fd54d6ef91f8ba497d966d5c845`
- Six isolation checks passed. Original JVMs contained no fork inference classes or modern TensorFlow API. Both used the recorded official legacy plugin environment; fork modern runtimes remained isolated child processes

## Actual native-command observations

**StarDist:** the unchanged original call failed and fell back to returning its input, which the probe rejected. The first underlying failure is `imagej-tensorflow` casting Java 21's `AppClassLoader` to `URLClassLoader`; prediction then remains null. **This run did not observe an ARM JNI-loading failure in that command path.** The test's standalone embedding and a Fiji-style URL system loader must be distinguished.

The fork's real GAT call succeeded with **39 cells** on the public 175×175 Hu crop, probability 0.5, NMS 0.3 and four requested tiles. Its raw 16-bit label SHA-256 is `ea1767df58491cc03927e121943d955708450d091f3416b2493e1c93e51cd443`. This independently matches both archived Linux TF1 and modern-worker results for `repo_DYM_22_7_Pr_Hu_crop_c1_t1_x0_y0` at the same four-tile setting. This is exact raster evidence, not only equal counts, and remains a technical fixture rather than biological-accuracy validation.

**Template Matching:** the unchanged original GAT call left the deliberately shifted input unchanged. No native exception was collected in this first report. ImageJ can put a plugin failure in a separate Exception text window, so the precise cause remains unestablished here. The fork succeeded and its aligned-pixel hash exactly matched the old Linux reference for the same seeded four-frame fixture: `8be9c6ad7c4c28d68b07f0b45c562deb9d29e4febf030b0ad24dcb198ea7fa9c`.

The supplied legacy Mac TensorFlow/OpenCV binary headers are x86-64, independently of these command outcomes. Separate direct JNI controls and improved exception collection are needed to measure the loading failure explicitly. No Rosetta was installed or used.

Cold process times, including startup and ImageJ/model setup, were original StarDist 8.06s (failed), fork StarDist 15.76s (successful), original alignment 3.10s (failed), fork alignment 5.47s (successful). These **cannot be compared as performance speedups**, and provide no CPU-versus-GPU multiplier.

## Other controls: old code did not universally fail

- Seven original and fork Java helper checks passed. Original morphology controls and the standalone SIFT fit also passed
- Original GAT SIFT helper failed calibration/timing preservation. A later original save workflow timed out in `IJ.run("Collect Garbage")`, because this embedding omitted Fiji's real `CollectGarbage_` command. Its later save/reopen and batch assertions were not reached; that timeout is not an ARM incompatibility claim
- Fork SIFT helper, single save/reopen, two-channel batch/channel-1 handling, direct StackReg helper and multiplex landmark controls passed. StackReg batch remains explicitly unimplemented; full multiplex export and fallback branches were not tested
- Original ganglia input-contract control failed: raw channel intensity was 1 rather than the expected 255 before RDF preprocessing. Fork contract control passed
- **Both original and fork full ganglia command/model/cleanup controls executed successfully.** Their foreground areas were 167,430 and 72,236 pixels. The fork intentionally corrects the reached double-scaling input contract, so this is a scientific-output change, not legacy mask parity or proof of superior biological accuracy. Manual painting/review was not tested
- Original calcium timed out. Fork calcium finished quickly but observed raw source alias (100-valued, three planes) instead of the expected 200-valued projection. The automated frame-dialog interaction may have cancelled the operation; production-versus-harness cause is unresolved. Do not describe this first result as either calcium support or a proven projection-algorithm defect

A `PARTIAL` suite contains recorded passes and explicit blocked/unrun scope. A green original-observation CI step means outcomes were collected, not that the original application passed.

## Evidence and next controls

`summary.json` retains per-check results and the important metrics with portable path labels. `original-ci-diagnostics.zip` is the **unaltered 124,400-byte GitHub artifact**, SHA-256 `83bf4c4b0caa0ed64eb8e2f2dab155a8873e7aeca1798ca4fb1369efad4988e0`; it contains 62 JSON/log/CSV files and no input images, models or dependency binaries. Original runner paths inside that byte-preserved archive are historical execution locations. `original-artifact-files-sha256.json` independently fingerprints all members.

Follow-up controls should preserve this first run, use an explicit URL-system-loader comparison and direct old JNI probes, collect ImageJ Exception text windows, provide the official VIB `CollectGarbage_` command, and correct the one-shot calcium dialog responder. Original production source must remain unchanged throughout.

# Fresh installed Fiji: engine setup passed; ganglia harness stopped before GAT

Historical [native run `37366290437`, attempt 3](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37366290437/attempts/3), [job `111973920737`](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37366290437/job/111973920737), artifact `11370048533`, on 2026-10-05. Tested fork source: `fe5fd7b0a5a9b6e79074ef24d79c27fd2c5c2372`; original: `1870d9e16e16fd6daeac0bd05122e851029ddedc`. Attempts 1 and 2 never reached application execution and are excluded.

## What passed

- **Real engine initialization and full-model execution PASS.** The dated official Fiji Latest arm64/JDK archive was downloaded, hash-verified, unpacked, updated through the supported updater and launched through its own `fiji-macos-arm64` executable. Host: Apple M1 (Virtual), native macOS **15.7.9** (24G830), Fiji-bundled **Zulu Java 21.0.7 aarch64**. Launcher and bundled Java are arm64 Mach-O binaries. This is a real installed-Fiji result, without a replacement application launcher or system classloader.
- Shipped JDLL installed **PyTorch 2.0.0 CPU**, catalog-resolved from the unchanged model declaration **2.4.1+cpu**. All seven installed engine jars plus the pinned official macOS-arm64 native CPU jar were hash-verified. A separate real Fiji process loaded the complete supplied model and ran its RDF preprocessing, tiling, inference and postprocessing before either comparison installation was copied.
- Input `[1,3,1024,1024]`; output `[1,1,1024,1024]`, axes `bcyx`; **1,048,576 finite values**, minimum **0.0**, maximum **1.0**. Measured model load/run interval: **19.067357208 seconds**; whole launcher stage: **33.37290720799996 seconds**. No scientific-reference parity claim follows from these checks.
- **Both original and fork startup and dashboards PASS** after real initialization. Both raw dashboard reports record `dashboard_visible: true` and “DeepImageJ already initialized.” The normal GAT command mapping was used; only the informational first-run notice was dismissed.
- **Fork neuron PASS:** actual GAT call, public 175×175 Hu fixture, four tiles, probability 0.5, NMS 0.3, **39 labels**, source pixels unchanged. Exact 16-bit label raster SHA-256: `ea1767df58491cc03927e121943d955708450d091f3416b2493e1c93e51cd443`.
- **Fork alignment PASS:** exact reference pixel SHA-256 `8be9c6ad7c4c28d68b07f0b45c562deb9d29e4febf030b0ad24dcb198ea7fa9c`. Shifted input SHA-256: `f5bcf95db86f3329cd2e83439aba5bd694778c63fd57e73187f358c509d21e23`.

## Original failures and ganglia qualification

**Original neuron FAIL:** `original_neuron.log:2345–2373` records the old TensorFlow path trying to cast `AppClassLoader` to `URLClassLoader` at `TensorFlowUtil.getTensorFlowJARVersion`. The resulting null/unchanged-input fallback fails the segmentation assertion. This installed-Fiji observation is distinct from timeout/native-loader findings in other validation lanes.

**Original alignment FAIL:** the raw exception names missing `jniopencv_core` and `opencv_imgproc`; the shifted input remains unchanged. These are actual GAT invocation failures.

**Both original and fork ganglia retain raw status FAIL, but are harness-setup failures before the GAT call.** Both stack traces stop at `Fresh_Ganglia_Probe.java:72`: `Field.setDouble` targets boxed `Params.gangliaProbThresh01` (`java.lang.Double`). The boxed `gangliaMinAreaUm2` setter at line 74 has the same latent defect but was not reached. Actual GAT `runDeepImageJForGanglia` invocation is later, at **line 78**, and was not reached. The raw `action` labels and aggregate `ganglia_command` note name the intended command, not a completed invocation. No ganglia mask, foreground count or end-to-end result exists for either application in this attempt. These records do **not** demonstrate application or model inference failure.

The subsequent validation-only correction `26298b73ea3fcb4c1410ad4bcd268233040c5ace` uses boxed setters and adds regression checks. It does not change production code, models, reference expectations, thresholds or engine choice. Its new native result was pending when this packet was preserved; **no corrected-run PASS is included or claimed**. The historical bounded acceptance gate remains unpassed.

## Isolation and limits

The final original inventory differs from the engine-ready inventory only in the intended original GAT plugin overlay. The final fork adds its plugin and isolated worker folders; shared runtime dependencies, every inventoried model file and all eight engine jars match exactly. Recorded main Fiji classpaths contain no isolated worker-folder entries. Raw class sources and inventories remain in the ZIP. The archive records source revisions but contains no dedicated final original-checkout git-status record; tracked-source cleanliness is not inferred from installation inventories.

OpenCL and full interactive/biological/manual-review workflows remain BLOCKED. This virtual-M1 result does not establish physical-Mac Finder/Gatekeeper behavior, other chip generations, or complete workflow support. Fiji Latest/Java 21 is the tested compatibility deviation from the upstream Stable recommendation. Live updater snapshots document the actual resolution, not a replayable updater service. Raw `ij.IJ` code-source location is unavailable and `sun.java.command` is null.

## Preserved evidence and integrity

- `gat-fresh-fiji-engines-attempt3.zip`: unchanged **1,380,119-byte** diagnostics artifact; SHA-256 `2c32f67f9d8c88cca38d75de9a44f00be30bfb9da509f2f825a7648705b5ceca`
- `original-artifact-files-sha256.json` and `ARTIFACT-MEMBERS.sha256`: sizes/hashes for all **85 members**, verified against the supplied extraction; ZIP CRC check passed
- `summary.json`: portable stage reports, exact source excerpts, engine/model hashes, class-source evidence, inventory comparisons and explicitly separate ganglia interpretation. Large classpath/menu maps are omitted only from this summary; the unchanged originals remain inside the ZIP
- `SHA256SUMS`: packet-file checksums, excluding itself. Verify from this directory with `sha256sum -c SHA256SUMS`; after extracting the ZIP to a separate directory, verify its members there using `ARTIFACT-MEMBERS.sha256`

No images, model weights, runtime dependency jars or Fiji distribution binaries are duplicated in this packet. All raw evidence is attempt 3 only; existing evidence is unchanged.

# GREEN: bounded real installed-Fiji acceptance on native Apple M1

**The required fresh-installed-Fiji acceptance gate passed.** This is a bounded result for the named stages below, not complete GAT workflow or biological acceptance. Raw original neuron/alignment failures and the two excluded BLOCKED workflow stages remain unchanged.

- [GitHub Actions run 37374804775](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37374804775), [native job 111980603286](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37374804775/job/111980603286): **SUCCESS**, 2026-10-05
- Tested fork source: [`26298b73ea3fcb4c1410ad4bcd268233040c5ace`](https://github.com/justinvassantachart/GutAnalysisToolbox/commit/26298b73ea3fcb4c1410ad4bcd268233040c5ace)
- Unchanged original source: [`1870d9e16e16fd6daeac0bd05122e851029ddedc`](https://github.com/pr4deepr/GutAnalysisToolbox/commit/1870d9e16e16fd6daeac0bd05122e851029ddedc)
- [Original diagnostics artifact 11372260331](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37374804775/artifacts/11372260331), named `gat-fresh-native-fiji-paired-evidence`; preserved locally as `gat-fresh-fiji-corrected-26298b7.zip`

## Actual runtime and installation

Host logs identify **Apple M1 (Virtual), native arm64, macOS 15.7.9 (24G830)**. Application execution used Fiji's **bundled Zulu Java 21.0.7 aarch64**, not the CI build JDK. `native-binaries.log` identifies both the Fiji launcher and bundled Java as arm64 Mach-O executables.

The harness downloaded the dated [official Fiji Latest arm64/JDK archive](https://downloads.imagej.net/fiji/archive/latest/20261004-2017/fiji-latest-macos-arm64-jdk.zip), verified **669,037,040 bytes**, SHA-256 `26af2159ca1d770de2c6b4fd99b98292891c50abdeaa00d1c66a425cd3de45b0`, validated/extracted the archive, and used the supported ImageJ updater with the documented sites. The run preserved the 11 observed site databases and installed updater database. These capture the actual live resolution; they do not provide a replayable historical updater service.

Every application stage used the distribution's own `Fiji.app/Contents/MacOS/fiji-macos-arm64` launcher with its bundled Java and a separate test home. A validation-only plugin was reached through the normal ImageJ command/macro mechanism. No replacement application launcher, manually constructed ImageJ application, synthetic GAT menu or custom system classloader was used. Real model inference completed in a separate launcher process before the engine-ready installation was copied for the two GAT revisions.

The raw reports record system, plugin and probe classloaders as `jdk.internal.loader.ClassLoaders$AppClassLoader`. Class-source locations identify each actual GAT plugin and the shared ImageJ/StarDist/TensorFlow/Template Matching/DeepImageJ jars. All recorded main Fiji classpaths were checked: **no `gat-native-inference/` or `gat-native-alignment/` worker-folder entry**. This is evidence about the recorded main application classpath, not a claim that the fork has no worker subprocesses. The raw `ij.IJ` code-source location is unavailable and `sun.java.command` is null; neither gap is hidden.

## Named stage results

| Stage | Original | Fork | Evidence |
|---|---|---|---|
| Native host, archive integrity, updater and inventory | Shared PASS | Shared PASS | `fresh-fiji-report.json`, host/updater logs |
| Pristine Fiji startup | Shared PASS | Shared PASS | `pristine_startup.json` |
| Real JDLL engine installation | Shared PASS | Shared PASS | `official_engine_install.json` |
| Full supplied model: RDF preprocessing, tiling, inference, postprocessing | Shared PASS | Shared PASS | `official_engine_inference.json` |
| Startup after GAT overlay | PASS | PASS | `original_startup.json`, `fork_startup.json` |
| Registered GAT dashboard | PASS | PASS | `original_dashboard.json`, `fork_dashboard.json` |
| Actual GAT neuron call | FAIL | PASS | `original_neuron.json/.log`, `fork_neuron.json` |
| Actual GAT Template Matching alignment | FAIL | PASS | `original_alignment.json`, `fork_alignment.json` |
| Actual GAT → registered DeepImageJ Run → model → MorphoLibJ ganglia command | PASS | PASS | `original_ganglia.json`, `fork_ganglia.json` |
| OpenCL-dependent workflows | BLOCKED | BLOCKED | No exposed device on virtual M1 |
| Complete interactive/biological/physical-Mac workflow review | BLOCKED | BLOCKED | Outside this bounded lane |

The exact tested harness's **17 required stages** were independently recomputed from its source and the raw aggregate report; all are PASS. Expected original neuron/alignment observations and excluded workflow stages are not silently converted to passes. The required-stage list is recorded in `summary.json`.

### Engine setup and full-model inference

The **shipped JDLL installer** installed PyTorch **2.0.0 CPU**, resolved by its catalog from the unchanged model declaration **2.4.1+cpu**. The seven installer-supplied jars plus the exact pinned official `pytorch-native-cpu-2.0.0-osx-aarch64.jar` were hash-verified. The native jar was supplied from its official Maven source rather than by an unpinned automatic download. No model, RDF preprocessing/postprocessing macro, runtime pin or threshold was changed to force a pass.

The subsequent real full-model run reported input `[1,3,1024,1024]`, output `[1,1,1024,1024]`, axes `bcyx`, **1,048,576 finite values**, minimum **0.0**, maximum **1.0**. Measured model load/run interval: **25.4235465 s**; entire launcher stage: **41.446832290999964 s**. This checks successful complete model execution and output sanity, not scientific-reference parity.

### Dashboards, neuron and alignment

Both dashboards record `dashboard_visible: true`, the normal `GATV2 → UI.GatPluginUI` mapping, and **“DeepImageJ already initialized.”** The harness dismissed only the informational first-run notice; GAT itself created its readiness sentinel. Registered commands include the actual `DeepImageJ_Run` and `inra.ijpb.plugins.SizeOpeningPlugin` implementations.

**Fork neuron PASS:** actual `Features.Core.PluginCalls.runStarDist2DLabel`, pinned public 175×175 Hu fixture, **4 requested tiles**, probability **0.5**, NMS **0.3**, **39 objects**, source pixels unchanged. Exact label raster SHA-256: `ea1767df58491cc03927e121943d955708450d091f3416b2493e1c93e51cd443`. Whole launcher stage: **26.166015416999926 s**. This is the established four-tile reference, not the distinct one-tile compact reference.

**Original neuron FAIL:** `original_neuron.log:2345–2373` records the old TensorFlow code attempting to cast `AppClassLoader` to `URLClassLoader` at `TensorFlowUtil.getTensorFlowJARVersion`. The later null/unchanged-input fallback fails the segmentation assertion. This exact installed-Fiji traceback is not relabeled as a TensorFlow JNI failure; separate native-loader observations belong to their own lanes.

**Fork alignment PASS:** actual `Features.Tools.AlignStack.alignTemplateMatching`, aligned pixel SHA-256 `8be9c6ad7c4c28d68b07f0b45c562deb9d29e4febf030b0ad24dcb198ea7fa9c`, matching the established reference. Shifted input SHA-256: `f5bcf95db86f3329cd2e83439aba5bd694778c63fd57e73187f358c509d21e23`. Whole launcher stage: **20.47148245799997 s**.

**Original alignment FAIL:** its exception explicitly identifies missing legacy `jniopencv_core` and `opencv_imgproc`; the shifted input remains unchanged. This is an actual GAT invocation failure.

### Both real ganglia commands now PASS

The corrected probe reached each actual seven-argument `runDeepImageJForGanglia` call. It used the full supplied test-input fixture, first two channels as Hu/ganglia, with GAT constructing **R=Hu, G=ganglia, B=Hu**. Registered DeepImageJ and MorphoLibJ commands ran inside their own fresh Fiji roots. The probe also kept an unrelated image open to reject accidental input/old-window returns.

| Recorded command metric | Original | Fork |
|---|---:|---:|
| Binary mask width × height | 1024 × 1024 | 1024 × 1024 |
| Foreground pixels | 167,430 | 72,236 |
| Command interval (seconds) | 21.104650666 | 22.696484916 |
| Source pixels unchanged | true | true |
| Pixel-width/height calibration preserved | true | true |
| Whole launcher stage (seconds) | 39.85221637500001 | 40.381272999999965 |

Both masks passed the probe's single-slice 8-bit, binary, nonempty/nonfull checks. Pixel width and height were **0.378 µm**. RDF threshold and GAT threshold were **0.6**, opening iterations **1**, minimum area **1.0 µm²**; interactive review was disabled for this bounded probe.

The foreground difference is the **already documented input-contract scaling correction**: the fork retains byte-range floats until the model's own RDF `scale_linear(1/255)` and ImageNet normalization, whereas the original divides by 255 first. It is not legacy-mask parity or evidence of biological superiority. The exact original/fork source excerpts and pre-existing documentation are preserved in `summary.json`.

**Important retention limit:** both raw reports name saved `original_ganglia-mask.tif` / `fork_ganglia-mask.tif` files and their PASS follows the probe's successful save assertion. **Neither TIFF is present in the diagnostics ZIP** because the workflow uploads JSON, logs and updater databases. This packet preserves recorded command metrics and checks; it does not provide those ganglia raster pixels for independent reconstruction, re-opening or parity analysis.

## Exact installation and isolation comparisons

`inventory-comparison.json` is the complete machine-readable comparison, with relative paths, byte counts and SHA-256 hashes. It includes every one of the **854 identical shared original/fork files**, every addition/removal/change, all **8 engine jars**, all **13 model files**, and all **32 fork-only isolated-worker files**. The four original inventories remain immutable in the ZIP.

| Comparison | Before → after entries | Byte-identical common files | Differences |
|---|---:|---:|---|
| Installed → engine-ready | 847 → 855 | 846 / 847 | 8 engine jars added; validation `Fresh_Fiji_Probe.jar` extended for ganglia checks |
| Engine-ready → original-final | 855 → 855 | 854 / 855 | Only original GAT plugin replaced |
| Engine-ready → fork-final | 855 → 887 | 854 / 854 | Update-site GAT plugin removed; fork plugin and 32 isolated-worker files added |
| Original-final → fork-final | 855 → 887 | 854 / 854 | Original GAT plugin removed; fork plugin and 32 isolated-worker files added |

The original plugin replacement is expected: the freshly built immutable original takes the place of the updater's GAT jar. Original plugin SHA-256 is `f60cc71f2990c66062a133924c6ad0c0f7c76f60dc405158265bca4f1b7ec145`; fork plugin SHA-256 is `9880583ec53479edfe20e8368b32e83c9d3d07569384162ad6b8595f65948210`. The fork archive/overlay hash in the aggregate is a different object and is retained separately.

All inventoried model files are identical across all four inventories. All 8 engine jars are identical across engine-ready/original-final/fork-final. Shared runtime dependency jars are unchanged. Isolated worker files are in `gat-native-inference/` and `gat-native-alignment/`, not injected into Fiji's `jars/` or `plugins/`. All 7 baseline pin comparisons are MATCH. These are inventory-based claims for recorded files, not claims that this packet contains the distribution binaries or measures every possible filesystem side effect.

## Source cleanliness and the earlier failed attempt

`job-step-status.json` is **separately preserved structured read-only connector evidence from the GitHub Actions jobs API**, not raw HTTP-response bytes, observed on 2026-10-05 (the recorded 21:31 UTC retrieval time is approximate). It confirms job success, harness-safeguard success, installed-Fiji stage success, and step 11 **“Confirm original source stayed unchanged” SUCCESS**. The tested workflow's final assertion is `git -C original status --porcelain --untracked-files=no`, required to be empty. Thus the checked claim is **tracked original-source cleanliness**; untracked build output is intentionally excluded.

This API observation is not an original member of the diagnostics ZIP. The ZIP records revisions in `source-and-host.log` but has **no dedicated final original-checkout git-status file**. Installation inventory equality is separate evidence and is not substituted for the source-clean CI assertion. The exact workflow source/check and API provenance are preserved separately.

The historical [attempt-3 packet](../mac-engine-setup-fe5fd7b-attempt3/REPORT.md) remains unchanged: its raw ganglia statuses are FAIL because `Field.setDouble` attempted to set boxed `Double` fields before reaching GAT. Corrected source `26298b7` changed only **seven validation/helper/test/documentation files under `validation/fiji-install/`**. It uses boxed assignments and regression checks against the actual Params class. No production source, models, thresholds, engine choice or reference expectations changed in that correction. This new run supplies the previously missing reached-command acceptance evidence; it does not retroactively alter the earlier result.

## Limits that remain

- Full interactive dashboard navigation, parameter UI, manual ROI/painting review, all workflows and representative biological acceptance are not established
- OpenCL/EDF/spatial GPU workflows remain BLOCKED without an exposed device; they require their own suitable physical-device evidence
- Virtual-M1 CI does not establish physical-Mac Finder/Gatekeeper/quarantine first-open behavior, every M1 configuration, or M2–M5/all Apple chips; no OS security setting was changed
- Fiji Latest/Java 21 is the deliberate tested compatibility deviation from upstream's Stable recommendation
- Finite model output, exact small neuron/alignment references and ganglia mask sanity do not establish broad biological accuracy, legacy ganglia-mask parity or complete scientific reference parity
- Runtime readiness here follows real updater/model/engine setup. It does not imply that merely installing the fork archive supplies every end-user prerequisite

## Preserved packet and verification

- `gat-fresh-fiji-corrected-26298b7.zip`: unchanged **1,380,683-byte** original diagnostics; SHA-256 **`86d82644e2bf03cf35b7174010e5a634b27bfe038b294fb00cdaf81a6c6763d3`**
- `original-artifact-files-sha256.json` and `ARTIFACT-MEMBERS.sha256`: exact sizes/hashes for **all 85 original ZIP members**; CRC passed and every extracted member was verified byte-for-byte
- `summary.json`: portable stage/runtime/source reports, metrics, relevant menu mappings, classpath-isolation checks, named acceptance list and explicit limits. Large classpath/menu maps are omitted only from this derived summary; the unchanged raw originals remain in the ZIP
- `inventory-comparison.json`: exact per-file comparisons described above, including the complete identical shared-file set
- `job-step-status.json`: separately sourced GitHub API job/step metadata, not added to or attributed to the original ZIP
- `SHA256SUMS`: hashes for all packet files except itself

From this directory, run `sha256sum -c SHA256SUMS` (or `shasum -a 256 -c SHA256SUMS` on macOS). Extract the ZIP into a separate directory and check its members there against `ARTIFACT-MEMBERS.sha256`. The original ZIP is preserved byte-for-byte; derived summaries are explicitly distinguished from original evidence.

No Fiji binaries, runtime dependency jars, model weights, or fixture pixels are redistributed in this diagnostics packet. Only this new evidence directory was created; prior evidence and production code are unchanged by packet preparation.

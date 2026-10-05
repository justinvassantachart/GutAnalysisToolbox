# GREEN follow-up: ganglia output masks retained and independently reopened

**The bounded installed-Fiji gate passed again, and both ganglia TIFFs are now retained with independently verified pixel/file hashes.** This separate packet closes the earlier artifact-retention gap. It does not rewrite the [26298b7 acceptance packet](../mac-accepted-26298b7/REPORT.md), whose original ZIP correctly remains an 85-member diagnostics artifact without mask TIFFs.

- [Run 37377537420](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37377537420), [job 111990534588](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37377537420/job/111990534588): **SUCCESS**, 2026-10-05
- Tested source [`5e2e0f4c42726e480213682808dfa41ea16f064f`](https://github.com/justinvassantachart/GutAnalysisToolbox/commit/5e2e0f4c42726e480213682808dfa41ea16f064f); original remains `1870d9e16e16fd6daeac0bd05122e851029ddedc`
- [Original artifact 11372264284](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37377537420/artifacts/11372264284): preserved as `gat-fresh-fiji-mask-retention-5e2e0f4.zip`, **1,393,747 bytes**, SHA-256 `5c8f7d4beb9383c412cda5fb21fbfb95cefc4bea95201f050f47344e85de6007`
- **87 original members**, ZIP CRC passed, every extracted member verified byte-for-byte; exactly two TIFF members

## Retained raster evidence

The original and fork actual GAT → registered DeepImageJ Run → model → MorphoLibJ commands both PASS. The separate `ReviewGangliaMasks.java` control reopened each retained TIFF using ImageJ 1.54p and verified **1024 × 1024, one slice, 8-bit, every pixel either 0 or 255**. Independent results match each raw report's foreground count, raw uint8 row-major raster hash and complete TIFF hash exactly.

| Check | Original | Fork |
|---|---|---|
| TIFF member | `original_ganglia-mask.tif` | `fork_ganglia-mask.tif` |
| File bytes | 1,048,801 | 1,048,801 |
| Foreground pixels | 167,430 | 72,236 |
| Raw uint8 row-major SHA-256 | `a8cb17b67de06f29bf6fa00f5ba54e9f531cc460a9355c855bb8906ffc063fa8` | `bf77cecdc827a080b7f2be7f7289fbce918fbb8e593b7c470683ccab9254788f` |
| Complete TIFF SHA-256 | `15f3c92d88890c61f06f431ee31016fe6c1793344d40f815564c29e5f5316829` | `c141a0a1e66fa9810d4c42c62834688c224929bdd3764ee6464321c87ea0682b` |
| Reopened pixel width and height | 0.3780000922320225 µm | 0.3780000922320225 µm |
| Recorded GAT command seconds | 24.084775625 | 26.747070167 |
| Runtime source pixels unchanged | true | true |
| Runtime calibration preserved | true | true |

The saved calibration is **not claimed to equal 0.378 bit-for-bit**. `ReviewTiffCalibration.java` independently creates a new 2 × 2 ImageJ TIFF with requested spacing 0.378 µm, saves it and reopens it. It produces **exactly the same 0.3780000922320225 µm** width/height as both retained masks. This demonstrates ordinary TIFF rational serialization, rather than missing/lost calibration. The small difference is explicitly preserved in `independent-mask-review.json` and `calibration-control.txt`.

These two controls were rerun for packet verification on a separate **Linux x86-64** environment, using Temurin javac 17.0.20.1 (`--release 11`), OpenJDK 21.0.12.1 runtime, and `ij-1.54p.jar` SHA-256 `2e1a09961dfb41cee66ddc821b2577a41a072566ce45a49bae69267099741e20`. Their source and outputs are derived review evidence, **not original ZIP members** and not another native-Mac application run. Both controls and outputs are retained; dependency binaries are not duplicated.

The **167,430 versus 72,236** mask difference remains the already documented input-contract correction: the fork retains byte-range float inputs until the model RDF applies `scale_linear(1/255)` and ImageNet normalization; the original divides by 255 first. Inputs are still R=Hu, G=ganglia, B=Hu. RDF/GAT thresholds remain 0.6, opening iterations 1, minimum area 1.0 µm². **No legacy-mask parity or biological superiority is claimed.** The newly retained masks permit independent examination; they do not supply biological ground truth.

## Earlier installed-Fiji results still hold

The raw aggregate contains exactly the same per-stage statuses as the prior accepted run. All **17 required stages PASS**, recomputed against the actual tested harness's required-stage list.

- Native **Apple M1 (Virtual), macOS 15.7.9 (24G830)**; real official Fiji launcher, bundled **Zulu Java 21.0.7 aarch64**, supported updater and dated archive
- Real shipped JDLL engine installation and full supplied-model execution PASS; PyTorch **2.0.0 CPU**, catalog-resolved from unchanged model declaration **2.4.1+cpu**
- Input `[1,3,1024,1024]`, output `[1,1,1024,1024]`, axes `bcyx`, **1,048,576 finite values**, range **0.0–1.0**; measured model load/run 32.217359166 s, launcher stage 50.39837995899995 s
- Original and fork startup/dashboard PASS; fork neuron PASS with **39 objects, 4 requested tiles**, probability 0.5/NMS 0.3, source unchanged, exact label hash `ea1767df58491cc03927e121943d955708450d091f3416b2493e1c93e51cd443`
- Fork alignment PASS with exact pixel hash `8be9c6ad7c4c28d68b07f0b45c562deb9d29e4febf030b0ad24dcb198ea7fa9c`
- Original neuron remains FAIL at the old TensorFlow `AppClassLoader` → `URLClassLoader` cast; original alignment remains FAIL with missing legacy OpenCV JNI. These observations are not rewritten as passes
- Both actual ganglia commands PASS with the retained outputs above
- No isolated worker-folder entries in any recorded main Fiji classpath; normal class sources/loaders remain recorded. `ij.IJ` code-source location is unavailable and `sun.java.command` is null in the raw reports

## Inventory and source comparison

`summary.json` records all cross-run changed paths with exact before/after byte counts and hashes, plus each raw inventory member's SHA-256. Full original inventories remain in the new ZIP; the earlier large derived shared-file inventory is not duplicated.

| Inventory | Entries in both runs | Identical across runs | Changed paths |
|---|---:|---:|---|
| Installed | 847 | 846 | Validation probe JAR |
| Engine-ready | 855 | 854 | Validation probe JAR |
| Original-final | 855 | 853 | Validation probe and rebuilt original GAT JAR |
| Fork-final | 887 | 883 | Validation probe, rebuilt fork GAT and two worker JARs |

No inventory paths were added or removed between runs. All **13 model files**, all **8 engine jars**, shared runtime dependency entries and other inventoried files retain their exact hashes. Within the new run, all **854 shared original/fork paths** are byte-identical; the expected fork-only plugin/isolated-worker overlay remains.

The changed GAT/worker JARs have the same recorded lengths but different file hashes. Those are **inventory observations**: the diagnostics ZIP does not contain those JARs for independent class-byte comparison. Separately, git comparison of `src`, `native-inference/src`, `native-alignment/src` and the three corresponding Maven POM files between `26298b7` and `5e2e0f4` is empty. That verifies identity of the named production-source/build-description paths; it does not establish byte-identical rebuilt artifacts.

The source follow-up adds raw-raster/TIFF checksums to the validation report and explicitly includes the two named public-fixture mask TIFFs in artifact upload. It does not include distribution binaries, models, runtime dependency jars or input fixture pixels. Source records and links are in `summary.json`.

## Scope and reproducibility

Run/job success is independently reported by the review coordinator; no CI API response is packaged in this original ZIP. It also contains no dedicated final original-checkout git-status file. Source revision records, source comparison and installation inventories are separate evidence; inventory equality is not a source-cleanliness assertion.

The native runtime's unchanged-input assertions remain recorded test results. Independent TIFF reopening verifies retained output pixels/geometry/calibration, not source pixels absent from the ZIP. These checks do not establish complete scientific-reference parity, representative biological accuracy, full interactive/manual-paint/ROI workflows, physical-Mac Finder/Gatekeeper experience, every Apple chip or OpenCL/EDF/spatial GPU support. The latter workflow stages remain BLOCKED. Fiji Latest/Java 21 remains the explicit tested deviation from upstream's Stable recommendation.

Verify this packet with `sha256sum -c SHA256SUMS` or macOS `shasum -a 256 -c SHA256SUMS`. Extract the ZIP separately and verify all 87 members there with `ARTIFACT-MEMBERS.sha256`.

To repeat the independent checks, supply ImageJ 1.54p with the hash above as `IJ_JAR`, compile both retained Java files to an external temporary directory (`javac --release 11 -cp "$IJ_JAR" -d "$CHECK_DIR" ReviewGangliaMasks.java ReviewTiffCalibration.java`), and run them headlessly. `ReviewGangliaMasks` accepts the two extracted TIFF paths; `ReviewTiffCalibration` accepts a new temporary output TIFF path. Use classpath `"$CHECK_DIR:$IJ_JAR"`. Compare the reported hashes/counts with the raw ganglia JSON reports, and calibration with `calibration-control.txt`; the controls do not embed biological or parity expectations.

The original ZIP remains unchanged. `original-artifact-files-sha256.json` / `ARTIFACT-MEMBERS.sha256` describe its 87 members; `summary.json`, the two Java controls and their review outputs are clearly separate derived evidence. `SHA256SUMS` covers every packet file except itself. Prior evidence, production code and workflows were not edited during packet preparation.

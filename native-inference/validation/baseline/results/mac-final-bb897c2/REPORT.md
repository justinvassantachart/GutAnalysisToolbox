# Retained final preview-3 build and paired native-Mac evidence

This packet preserves the final published `.3` package identities and the **already completed** [native-Mac run 37382657593 / job 112008228097](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37382657593/job/112008228097), **SUCCESS**, for source [`bb897c237732cf8569a1515eb8d7ed69feb2ab31`](https://github.com/justinvassantachart/GutAnalysisToolbox/commit/bb897c237732cf8569a1515eb8d7ed69feb2ab31). Original source remains [`1870d9e16e16fd6daeac0bd05122e851029ddedc`](https://github.com/pr4deepr/GutAnalysisToolbox/commit/1870d9e16e16fd6daeac0bd05122e851029ddedc).

**Packet preparation only read, copied and hashed existing evidence. No new application, model or test execution, CI launch, release upload, or production/handoff change occurred.** The earlier [`ab046cb` packet](../mac-ab046cb/REPORT.md) remains unchanged and provides the deeper control/launcher interpretation.

## Observed final-build results

The recorded host was **Apple M1 (Virtual), native ARM64, macOS 15.7.9 (24G830), Temurin Java 21.0.12.1 aarch64**. Green still means complete observations and passing repaired gates, not original compatibility.

- **3 live modal-observer tests passed, zero skips**. These synthetic controls are distinct from actual GAT calls
- Actual original StarDist retains the exact newly visible CSBDeep **“Loading TensorFlow failed”** native-load modal, unchanged raw HTML and untouched `JOptionPane.UNINITIALIZED_VALUE`; its isolated process halts with **exit 2** without answering the dialog. Original alignment records missing legacy OpenCV JNI and unchanged shifted pixels
- Actual fork StarDist succeeds with **39 objects, four requested tiles**, exact label SHA-256 `ea1767df58491cc03927e121943d955708450d091f3416b2493e1c93e51cd443`; fork alignment succeeds with exact pixel SHA-256 `8be9c6ad7c4c28d68b07f0b45c562deb9d29e4febf030b0ad24dcb198ea7fa9c`
- Original SIFT helper/save/batch checks FAIL; fork checks PASS. Both calcium controls PASS with **F/F0 [1, 1, 2]**. Both ganglia commands execute, recording **167,430 original / 72,236 fork** foreground pixels. The difference remains the documented input-contract correction, not legacy-mask parity or biological superiority
- Common workflow counts remain original **15 PASS / 4 FAIL / 1 BLOCKED / 8 NOT_RUN**, fork **19 PASS / 1 BLOCKED / 8 NOT_RUN**. Original source provenance is clean before/after; `original-final-status.log` is present and empty

This is the diagnostic **`url-system` / `BaselineUrlClassLoader`** lane. It is separate from the earlier [real installed-Fiji AppClassLoader evidence](../../../../../validation/fiji-install/results/mac-mask-retention-5e2e0f4/REPORT.md), where the old TensorFlow cast failed before JNI. No fresh final-`.3` installed-Fiji run is claimed. Old native component failures remain separate from the fork's successful isolated-worker calls.

## Final package and published identities

[Matched Actions artifact 11375352270](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37382657593/artifacts/11375352270): **206,660,395 bytes**, SHA-256 `ff8a14a251b8ee7e9959f3c2f4ee93efd484c192299b0f2dd3621a388010099c`. CRC and all **6 members** passed verification.

The preserved [preview-3 release API snapshot](https://github.com/justinvassantachart/GutAnalysisToolbox/releases/tag/apple-silicon-preview-3) independently records these published downloads, and their local bytes match its digests:

- [Final fork ZIP](https://github.com/justinvassantachart/GutAnalysisToolbox/releases/download/apple-silicon-preview-3/GAT-2.0.1-apple-silicon.3-macos-arm64-preview.zip): **203,286,850 bytes**, SHA-256 `5c746a31c65727779566ed9b9a1bfdd4966167504bce7ee95bd4878ed2159d03`; 37 members
- [Final unchanged-original ZIP](https://github.com/justinvassantachart/GutAnalysisToolbox/releases/download/apple-silicon-preview-3/GAT-2.0.0-unchanged-1870d9e-baseline.zip): **1,664,352 bytes**, SHA-256 `3c7f3289f714f3789b9dad47dd4f9e7032812b8886c43705a97853888d50ce86`; 4 members
- Final main plugin SHA-256: `0bb1c33b452fcd607f13291532e103199223d947eeec605a91dcac03dc047792`
- Inference **worker JAR** SHA-256: `1e24e30805e01ebb838684c913d317e3d3f09cfaa7cd66f02d8c3a6d57247b04`
- Alignment **worker JAR** SHA-256: `2ebec1639dfd3c4ed321783c03e7079bab7f36b46f0a3af8e4da9ad34924a204`

The `inference_bundle_sha256` and `alignment_bundle_sha256` in `FORK_BUILD_INFO.json` identify constituent **distribution ZIPs**, not those worker JARs. They are retained as build metadata and are not silently relabeled as JAR hashes.

Independent comparison verified **all 282 main-plugin class entries** plus **8 inference / 4 alignment worker classes** byte-for-byte against tested `ab046cb`. This includes the build metadata's **156 project classes**; the independent comparison covers all packaged `.class` entries, while the original 156-class build-time test-output comparison is retained as CI metadata. All **14 dependency JARs** are identical to the previously audited package. Final bundled guides, license and all 9 alignment corresponding-source entries match exact `bb897c2` source paths. Whole JAR/package hashes remain distinct from `ab046cb` despite class-byte continuity.

`package/published-release-identities.json` also records the exact published kit-2.1 and manual-multiplex-fixture URLs/digests. The preserved API snapshot **predates the later v5 handoff-guide upload**; it is not an exhaustive or permanently current asset inventory. Those kit/fixture identities are saved API evidence, not newly executed validation. No release asset was changed during packet preparation.

## Separate scopes and preservation

- [Full-multiplex packet](../../../multiplex-full/results/mac-ab046cb/README.md): separate complete-service cases at `ab046cb`, not newly rerun here
- [Native 40-case packet](../../../mac-corpus/results/mac-9b599df/REPORT.md): separate source-labeled official corpus; 39 unique inputs, 39/40 canonical raster/measurement matches, and explicit remaining Hu raster/subpixel differences. It does not establish complete scientific equivalence
- [Raw report artifact 11375297949](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37382657593/artifacts/11375297949) is retained unchanged as `original-ci-diagnostics.zip`: **156,912 bytes**, SHA-256 **`e45eaacb5cec7e2ec03a5c71a02dff13fcb65fb3f76c5cf20363a869cc88cdeb`**. CRC and all **79 members** passed independent verification
- `original-artifact-files-sha256.json` / `ARTIFACT-MEMBERS.sha256` preserve all original member sizes/hashes; `summary.json` is a compact derived result. Raw classpaths, dialog components and threads stay in the unchanged ZIP
- `terminal-ci-status.json` is separately sourced decoded read-only job/artifact connector evidence, **not an original ZIP member or raw HTTP bytes**. The package audit is a derived read-only review; release metadata is a separately saved API snapshot
- `package/` retains all install/package member hashes, class hashes, build metadata and small audit/identity records. The 206 MB distribution payload and its binaries are not duplicated

Verify with `sha256sum -c SHA256SUMS` (macOS: `shasum -a 256 -c SHA256SUMS`). Extract the report ZIP separately and verify `ARTIFACT-MEMBERS.sha256` from that extraction root. The original report contains recorded ganglia metrics, not retained mask TIFFs. Full GUI, physical-Mac first-open, every-chip, GPU/OpenCL, broad performance and biological acceptance remain outside this packet. Earlier evidence and core/handoff versions are unchanged.

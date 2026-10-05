# Native Apple Silicon: all 40 source-labeled official test cases

## Result

All 40 cases completed on the native ARM CPU worker and the unchanged pinned StarDist NMS. Candidate counts, object counts and winning centers matched the archived Linux TensorFlow 1.15 reference in every case. There were 4,472 detections in each engine's summed case outputs.

**39 of 40 canonical raster and measurement hashes matched.** The remaining Hu case has a measured one-pixel difference in one independently rasterized polygon and the foreground union. Its original exclusive legacy label-map differing-pixel count is unavailable. This is successful execution coverage with qualified consistency findings, not exact equivalence across all outputs or biological accuracy validation.

- 37 cases have identical raw label IDs and pixels
- Two additional cases, `neuron_test_widefield_6` and `neuron_test_widefield_3`, differ only in label IDs; their canonical raster and measurement hashes match
- All 15 subtype cases have identical canonical raster and measurement hashes, including the previous Linux `_Calb_widefield` raster outlier
- Only 8 complete polygon sets are strictly identical at the retained subpixel-coordinate level. The other 32 cases contain 162 changed polygons and 164 changed vertices across exact-center matches
- Every winning center matches; there are no unmatched centers or ray-count mismatches
- Maximum matched-vertex coordinate delta is 0.010009765625 px; maximum Euclidean vertex delta is 0.014155946303051 px. These values describe this run's exact-center matches, not a universal bound on other data
- Full probability/distance tensor numerical parity was not tested. Most full legacy arrays were not retained

No thresholds, production settings, normalization, tiling, model weights or NMS tie-breaking were adjusted to make this result pass. The run explicitly records `scientific_equivalence_established: false`.

## Exact source and run

- [Source commit 9b599df1b8c67977228bc50104f44280047c4154](https://github.com/justinvassantachart/GutAnalysisToolbox/commit/9b599df1b8c67977228bc50104f44280047c4154)
- [Native corpus workflow run 37381573321](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37381573321)
- [Coverage job 112004603172](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37381573321/job/112004603172)
- [Exact workflow source](https://github.com/justinvassantachart/GutAnalysisToolbox/blob/9b599df1b8c67977228bc50104f44280047c4154/.github/workflows/native-mac-test-corpus.yml)
- Original artifact ID 11375896651, `gat-native-mac-official40-corpus`, 6,171,926 bytes, created 2026-10-05T22:28:13Z
- Original ZIP SHA-256: `678f2f005f2975e8269cdb16d8eb853de05efc401f0d3aada8472f500808d95d`

The GitHub job and all reported steps concluded successfully. The workflow's gate checks execution coverage, not scientific equivalence. GitHub artifact metadata and the complete original artifact are preserved in `original/`; the archived copy does not depend on GitHub artifact retention.

## Dataset and independence

The [official Zenodo v4 record](https://zenodo.org/records/15314214) supplies the two archives used here. The run covers all **40 source-labeled test files**, comprising **39 unique pixel inputs**, with one input also present in the training folder. These are **not 40 independent held-out samples**.

- Hu: 25 source-labeled test images, neuron model `2D_enteric_neuron_v4_1.zip`
- Subtypes: 15 images, subtype model `2D_enteric_neuron_subtype_v4.zip`: Calbindin 3, Calretinin 2, ChAT 3, Neurofilament 2, nNOS 5
- 26,030,351 supplied pixels including the repeated test input. Entire supplied images were used, with no additional resize or crop
- `widefield.tif` and `widefield_7.tif` repeat the same test pixels
- Test `confocal_1.tif` repeats training `Mouse_confocal_28.tif`

No training images, repository supplements or temporal frames were added to this denominator. Summed detections include duplicate/related inputs and are not a count of unique independent biological cells. The wider dataset's nine subtype stains are not all represented in these test files.

Exact source-file, archive, model, input and retained-reference hashes; original dimensions; zero-origin full-image crop; tile layout; and duplicate annotations are preserved in `original/frozen-manifest.json` and the original per-case records. Pillow 11.3.0 preserved the original unsigned scalar values, including palette indices for the four palette TIFFs. Every prepared big-endian float32 GATI input matched the archived input hash before inference.

Production CSBDeep 1/99.8 percentile normalization and MirrorDouble tiling were unchanged. Requested tiles remained 4. Probability thresholds were 0.5 for Hu and 0.4 for subtypes, NMS 0.3, excluded boundary 2. StarDist source commit was `aff59dbd3cdf88dfa567d4dd562eab943bf4f99b`, with pinned ImageJ 1.54p dependencies. The modern worker and the geometry process used separate classpaths; no legacy TensorFlow execution took place on ARM.

## The Hu raster outlier

Case: `neuron_test_widefield_9`, supplied image 1100 × 882 px. Both engines retain 180 objects and 10,495 candidates. Winning center: **(606.5, 510.5)**.

For that single polygon, independently rasterized and clipped to the image:

- Legacy area: 691 pixels; native Mac area: 690 pixels
- Intersection 690, union 691, IoU **0.9985528219971056**
- Centroid shift **0.018732395302507927 px**
- Four-neighbor perimeter remains 130 px; bounding box remains x=597…618, y=487…526 inclusive
- Pixel **(617, 515)** changes from foreground to background
- Quantized vertex 7 moves from x=617.38 to x=617.37; y=515.86 is unchanged
- The full-image polygon-union foreground differs by one pixel, IoU 0.9999912471881592

A separate full-canvas ImageJ `ByteProcessor.fill(PolygonRoi)` control reproduced these values without the harness's bounding-box `Mask` implementation. Its source, output and exact legacy polygon input are preserved under `independent/`.

**These are independent polygon and foreground-union measurements.** The archived legacy polygons are sorted by center and omit their original winner paint order. The original exclusive legacy label map therefore cannot be reconstructed unambiguously for this case. Its authoritative original canonical raster and measurement hashes differ, but the original exclusive-label differing-pixel count stays null/unavailable. Do not describe the whole original label-map discrepancy as exactly one pixel.

The exact original outlier case, full geometry and all five changed matched polygons are also available as `original/outlier-case.json`, `original/outlier-actual.geometry.json` and `original/outlier-outliers.json`. Four of those five polygons have subpixel-only changes with identical independent raster masks.

## Hardware and CPU timings

The host reports **Apple M1 (Virtual)**, model `VirtualMac2,1`, macOS **15.7.9** (Darwin 24.6.0), native arm64, three reported logical and physical cores, and **7 GiB** memory. Java is Eclipse Adoptium **21.0.12.1**, aarch64. Rosetta status is 0. This is a virtual hosted M1 runner, not a direct measurement of the user's own laptop.

CPU execution used TensorFlow intra/inter-op thread settings 2/1, OMP 2, CUDA disabled and a 3 GiB Java heap cap. Cases were serial, with a new worker JVM per image and a separate geometry JVM afterward. The heap cap does not include all native allocations.

- Cold CPU worker time per image: **2.411–20.122 s**, median **5.520 s**
- Sum of 40 cold CPU worker times: **248.837 s**
- Sum of geometry subprocess times: **193.370 s**
- Geometry dependency verification/compilation setup: **3.960 s**
- Total timed validation runner: **456.501 s**

Worker timings include JVM startup, model loading, preprocessing, tiling/inference and writing GATO output. Geometry timings include NMS, rasterization, measurements and compact artifact writes. The runner total also includes metadata, integrity checks and report I/O. Initial workflow build, source/model download and input preparation occurred before the timed runner and are not represented by its total; individual durations are not recorded in this artifact.

Each case has one cold-process sample and zero warmups. This does not imply a cold disk/OS cache or a statistically stable performance estimate. No GPU comparison or GPU speed multiplier was measured. Exact per-case CPU and geometry times are in `cases.csv` and the original reports.

## Independent audit

The independent standard-library raster auditor passed seven hand-calculated encoding/measurement controls and then decoded all 40 modern raw/canonical map pairs. It independently recreated first-raster-occurrence canonical IDs and verified all 4,472 modern object measurement rows and centroids directly from pixels. All 40 measurement hashes, 404 compact-file hashes, 413 ZIP members, exact frozen metadata and source/model/input/reference pins checked successfully. Both retained original legacy composite maps were hash-verified before their exclusive-map comparisons.

Its numerical conclusions match the report above. Candidate counts were checked against pinned archived counts; absent tensor arrays prevent an independent candidate recomputation. The auditor does not reconstruct missing legacy paint order or claim tensor parity. Source, portable JSON and log are preserved in `independent/`; `RASTER_AUDIT.md` gives reproduction instructions. The separate ImageJ control verifies the one changed polygon by an independent rasterization route.

## Evidence and reproduction

- `summary.json`: portable qualified summary, exact case rows and source/run links
- `cases.csv`: one row per source-labeled case, including hashes, identity-sensitive and identity-insensitive comparisons, separate independent-mask deltas and timings. An empty original exclusive-label pixel count means unavailable, not zero
- `original/gat-native-mac-official40-corpus.zip`: byte-for-byte original artifact, all 413 files
- `original/zip-member-manifest.json`: byte length, CRC and SHA-256 for every original member; no missing, duplicate or unsafe member paths
- `original/summary.json`, `original/preparation.json`, `original/artifact-manifest.json`: unmodified readable originals
- `original/frozen-manifest.json`, `original/dependencies.json`: exact source-commit manifests, verified against recorded run hashes
- `independent/`: separately implemented outlier/raster verification and its results
- `SHA256SUMS`: checksum list for the complete published packet

Every per-case geometry, outlier, compact mask/outline and log is preserved inside the original ZIP. The CSV's `case_member`, `geometry_member` and `outlier_member` columns point to the exact ZIP members. To inspect one example without inference:

```sh
unzip -p original/gat-native-mac-official40-corpus.zip \
  target/mac-corpus-results/neuron_test_widefield_9/actual.geometry.json
```

From this directory, `sha256sum -c SHA256SUMS` (or `shasum -a 256 -c SHA256SUMS` on macOS) verifies the packet. `verify_packet.py` verifies the immutable ZIP, all member/case hashes, dataset membership and derived report/CSV claims. It does not execute a model or alter a reference.

To rerun inference, use the harness and workflow at the exact source commit linked above and the pinned public inputs. A rerun is a new observation, not a replacement of this frozen result. Nothing in this evidence packet changes production code or acceptance thresholds.

# Native Apple Silicon official-test corpus regression

Status: harness prepared and locally checked on Linux; the native Mac **40-case run has not been launched by this change**. The separate `mac-ci-job.yml.example` is owner-ready, not an active workflow. Enable it only after the currently running native multiplex validation has closed. This directory changes no production algorithms, thresholds, workflows or shared CI.

## Exact scope and scientific limits

This replays all **40 source-labeled test files** in the two official [Zenodo v4 archives](https://zenodo.org/records/15314214), comprising **39 unique pixel inputs**, with one test input also present in the training folder. They are **not 40 independent held-out samples**. The duplicate test pair is `widefield.tif` / `widefield_7.tif`; `confocal_1.tif` overlaps training `Mouse_confocal_28.tif`.

- 25 Hu cases → `2D_enteric_neuron_v4_1.zip`, probability 0.5
- 15 subtype cases → `2D_enteric_neuron_subtype_v4.zip`, probability 0.4: Calbindin 3, Calretinin 2, ChAT 3, Neurofilament 2, nNOS 5
- 26,030,351 supplied pixels in total, including the duplicated input; full images from 341×341 to 1576×1181, with smaller subtype examples starting at 400×400
- No training cases, repository supplements, temporal frames or additional models are executed
- Every case retains its source file/archive SHA-256, model SHA-256, exact GATI input SHA-256, full source dimensions, explicit zero-origin whole-image crop, exact tile plan and duplicate/overlap annotations in `frozen-manifest.json`

The record describes a broader nine-stain dataset. These 40 test files cover Hu and the five subtype stains above; do not generalize the tested stains or infer a laboratory/species for each unlabeled file. The source images were already rescaled by the dataset authors; this harness performs no additional resizing. Measurements are in pixels, without inferred physical calibration.

This is cross-platform/runtime consistency evidence, not biological accuracy against manual labels or proof of scientific equivalence. Successful CI means complete execution coverage. A complete run can report real raster, center or outline differences and still finish successfully. The report always says `scientific_equivalence_established: false`; use the separate exact-hash flags and per-cell diagnostics.

## References and immutable preprocessing

Legacy outputs were generated on Linux with TensorFlow 1.15.0 and the unchanged original preprocessing/NMS contract. Their existing portable records are `../corpus/results/core/{manifest.tsv,cases.json,provenance.json}`, with polygons in `../corpus/results/outline-payloads-001.zip`. Whole-file reference hashes are frozen here and checked before use. Nothing regenerates legacy inference on ARM, and no TF1 jars enter either the modern worker or geometry classpath.

Preparation verifies the official archive SHA-256 and exact TIFF-byte SHA-256 before decoding. Published MD5s remain recorded for source provenance. Pillow decodes the original single TIFF plane. Unsigned 16-bit values and four 8-bit palette-index images are preserved exactly as scalar pixels, matching the original NumPy conversion. Palette indices are **not converted to display RGB/luminance**. Values are written as row-major big-endian float32 GATI v1, and the complete binary must match the existing input hash. No normalization is performed during conversion.

The unchanged production worker performs CSBDeep normalization: 1st/99.8th percentile at the nearest rounded index, float32 arithmetic, lower-only clamp, no upper clamp, constant-range guard. Requested tiles remain 4. The manifest records the actual grid, 64-pixel block rounding, 64-pixel overlaps, tile input dimensions and expanded dimensions. Edge behavior is the unchanged nested MirrorDouble contract. See production `CsbdeepNormalizer.java` and `CsbdeepTiling.java`; their current source hashes and the exact worker/library hashes are recorded with each run.

NMS uses the unchanged pinned StarDist sources at commit `aff59dbd3cdf88dfa567d4dd562eab943bf4f99b`, ImageJ 1.54p and the other byte-pinned dependencies in `dependencies.json`. Probability thresholds remain 0.5/0.4; NMS 0.3; excluded boundary 2. Java validation helpers do not load TensorFlow.

### What the retained references can and cannot show

All 40 legacy polygon sets and original raw-label/canonical-raster/measurement hashes remain. Most full probability/distance tensors were removed after durable original review; only 2 test cases retain them locally. This harness performs **no numeric tensor-tolerance comparison**, including on those 2. It records fresh modern tensor hashes for provenance and never invents all 40 tensor parity.

The GATP archive orders polygons lexically by winning-center string; it does not preserve winner paint order. Therefore:

1. The actual modern exclusive label map is hashed exactly like the old comparator. Its raw ID-sensitive hash, ID-insensitive canonical raster hash and canonical per-object measurement hash are compared directly to authoritative archived legacy hashes
2. Legacy polygons are independently rasterized with pinned ImageJ. Per-polygon masks and their foreground union are geometry diagnostics, not the original overlap-resolved label map. Exact-center pairs report per-cell IoU/Dice, area, centroid, bounding box, perimeter, subpixel contour deltas and changed vertices
3. Unmatched centers remain explicit. Each reports its best-overlap counterpart, overlap multiplicity and nearest center, without forcing a one-to-one biological correspondence. Global foreground IoU never replaces these local diagnostics
4. Only the 2 cases with complete retained `legacy_object_measurements` supply original labels/paint order. Their reconstructed raw/canonical/measurement hashes must all match the archive before any original exclusive-label pixel delta is accepted
5. Without retained order, a mismatch in the authoritative raster hash has a **null/unavailable** original exclusive-label differing-pixel count. An equal canonical hash proves 0 such differing canonical pixels. Independent per-polygon/union deltas remain separately available. Canonical IDs follow first raster occurrence; differing canonical-label pixel counts are not an optimal object-matched mismatch count

Exact-center contour maxima do not bound moved-center objects. Inspect `unmatched_*_best_overlap` and `outliers.json` for those objects. All matched objects are retained, including small subpixel-only differences; there are no adjusted or fitted acceptance tolerances.

## Run on a standard native Mac runner

The owner-ready workflow uses only the standard free `macos-15` ARM runner, JDK 21 and Python 3.12; no paid/large runner label. It verifies actual `uname`, native ARM Java and Rosetta status, and records reported CPU brand/hardware model, memory, macOS, architecture and Java. A runner label alone is not evidence of an M1 chip: the report identifies the actual hardware and does not call another Apple Silicon generation M1.

From the repository root:

```sh
mvn -B -ntp -f native-inference/pom.xml clean package -Dtensorflow.platform=macosx-arm64
python3 -m pip install Pillow==11.3.0
python3 -m unittest discover -s native-inference/validation/mac-corpus -p 'test_*.py' -v
python3 native-inference/validation/mac-corpus/prepare.py \
  --archives target/mac-corpus-archives --models target/mac-corpus-models \
  --output target/mac-corpus-prepared --download
python3 native-inference/validation/mac-corpus/run.py \
  --worker native-inference/target/gat-native-inference.jar \
  --models target/mac-corpus-models --prepared target/mac-corpus-prepared \
  --output target/mac-corpus-results --expect-native-mac
```

Omit `--download` when the two pinned archives and model files are already present. Downloaded names are `neuron.zip` and `subtype.zip`; source URLs/public names are frozen in the manifest. Preparation needs Pillow; the runner/comparator otherwise need only Python's standard library and the JDK. All downloads are size-bounded and SHA-256 checked. Inputs are public, with no user/private microscopy images.

## Resource bounds and complete reporting

- Exactly one fresh modern worker process per case, followed by one fresh geometry process; never parallel model or comparator peaks
- Worker and geometry Java heaps capped at 3 GiB, TensorFlow intra/inter-op 2/1, OMP 2, CUDA disabled. This is a heap bound, not a claim that all native allocations fit inside it
- Largest input 1,861,256 pixels; largest GATO output about 722 MB. Check at least 2 GB free disk before inference. Public archives ≈113 MB, prepared inputs ≈104 MB, models ≈53 MB; dependencies and compact outputs are additional
- At most one fresh GATO is retained. After hashes, compact masks/outlines/measurements and case status are saved, it is deleted, including on failure, to prevent an unbounded anomaly queue. A failed comparator may therefore have only its log and tensor hash; rerun that exact case to investigate. Each worker has a private Java temp/output directory; parent cleanup also removes partial `.gat-result-*.tmp` files and model extraction leftovers after timeout/native abort. Partial-result hashes and status are saved before cleanup; cleanup failure stops the run
- 900-second worker and 300-second geometry timeouts; 120-minute overall CI bound. A timeout is a failure, never a match. No automatic retry hides the original failure
- `summary.json` is updated before/after every case, with all selected IDs/statuses and missing IDs. Setup failures stay blocked, runtime failures stay failed, and later cases continue where possible
- Cold worker timings include JVM startup, model loading, normalization, tiling/inference and writing the complete output. One timing sample, zero warmups. Geometry and setup times are separate; no claim of a statistically stable benchmark
- New empty output directory required for every run. No stale results or automatic resume can pass a new run. `artifact-manifest.json` hashes the per-case compact evidence; the terminal summary records that manifest's hash. Progress summaries remain incomplete until the evidence manifest is durably saved

Outputs include `summary.json`, `preparation.json`, per-case `case.json`, `actual.geometry.json`, `outliers.json`, compressed actual polygons/label maps/canonical masks and both polygon-union foreground masks, plus logs. All per-cell outliers are retained and sorted by mask IoU/centroid difference. Original legacy composite label maps are output only for the 2 verified-order cases.

## Local harness checks (not native Mac results)

Preparation was exercised against both retained official archives: all 40 new GATI files match the original hashes. Python tests cover exact scope and reference pins, architecture/classpath rejection, wrong hashes, exact-vs-ID-insensitive distinctions, null unavailable deltas, retained-order verification, and incomplete/duplicate-case coverage. Java setup runs `MacCorpusGeometryTest` with 184 checks, including random/fractional/clipped polygon-mask agreement with ImageJ, altered paint-order negative controls, moved/disjoint/empty correspondences and malformed prediction rejection.

A serial Linux development replay of the two retained modern tensors reproduces the original results: Hu `widefield_3` has identical canonical geometry despite label-ID differences; subtype `_Calb_widefield` has the same 1-pixel raster outlier and per-cell IoU 0.9993834772. A fresh cold Linux worker smoke on `neuron_test_widefield_11` also matched all original canonical raster/measurement hashes. These are harness controls, **not the pending native 40-case result**. `local-validation.json` records their hardware, timing, exact comparisons and artifact hashes.

For development only, `--case-id` selects explicit cases and `--replay-predictions /path/to/old/outputs` reads existing `<case>/modern.bin` without inference. Such subsets return nonzero and never claim all 40 completion. Replay cannot be combined with `--expect-native-mac`. `freeze_manifest.py` is an authoring utility to reproduce the manifest from the existing portable archive; normal runs never update it or the legacy references.

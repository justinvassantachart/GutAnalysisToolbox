# Native-platform diagnostic for the moved-center outlier

This fixed public fixture asks whether a platform's **unchanged production worker** reproduces the legacy Linux center, the modern Linux center, or a different result. It compares each observation against **both** fixed references. No reference, threshold, tie-break, or numeric tolerance is changed after observing the candidate.

The input is an unrescaled 760 × 1024 Hu crop at (4096, 0) from the public 4856 × 3672 tilescan. The exact source revision, URL, image/model/input hashes and crop are recorded in `fixture-manifest.json`. It uses the neuron model, tiles 4, probability 0.5, NMS 0.3 and boundary 2. Normalization remains the released worker's shared CSBDeep preprocessing.

## Why this case matters

Both archived Linux runtimes produce 148 objects, but one near-tied NMS choice changes from legacy center (396.5, 166.5) to modern (394.5, 168.5). Forty-eight foreground pixels differ. The affected cell has 441 versus 451 pixels, IoU 0.897872 and Dice 0.946188; whole-image IoU is approximately 0.9994. Thus identical counts or high global overlap can hide a meaningful local geometry difference. See the completed [corpus report](../corpus/results/REPORT.md) for the larger evidence and configuration sensitivity controls.

## Run with a built worker

Requires Python standard library and a JDK with `java` and `javac` on PATH. Use an ARM64 JDK on the native Mac. The current Apple Silicon worker requires macOS 14 or later. Models remain separate; `--models` must contain the checksum-pinned `2D_enteric_neuron_v4_1.zip` identified in the manifest.

```sh
python3 native-inference/validation/moved-center/check.py \
  --worker native-inference/target/gat-native-inference.jar \
  --models target/model-fixtures \
  --output target/moved-center-diagnostic
```

The output directory must be new. Optional `--java`, `--javac` and `--dependencies` choose the JDK and a shared pinned-NMS download cache. The helper uses the existing cross-platform dependency manifest and unchanged upstream StarDist `Candidates`/NMS plus ImageJ rasterization. The checker records its source hashes, worker hash, runtime metadata, numeric-thread environment, oneDNN environment value and timing. It explicitly selects CPU inference, as the Fiji adapter does, but leaves TensorFlow thread/kernel settings otherwise inherited; it does not enable or disable oneDNN or graph optimizations.

Use `--prediction existing.gato` instead of `--worker` / `--models` for a diagnostic of an already-produced tensor. Such reports clearly record that this checker did not execute inference; runner metadata then describes the analysis process, not the origin of that tensor.

## Interpreting the report

`report.json` contains two comparisons, against `legacy` and `modern`. Each records counts/candidates, winning centers and label order, exact and canonical masks, foreground overlap, probability errors against the fixed `atol=rtol=1e-4`, threshold crossings, per-label pixel measurements, and quantized polygons. The affected cell is matched by maximum filled-mask IoU across all candidate labels, so a moved center is not discarded as unmatched. Polygon-delta maxima apply only to identical winning centers; unmatched centers are listed explicitly.

Measurements use uncalibrated pixels: area, centroid with the ImageJ half-pixel convention, inclusive bounding box, four-neighbor perimeter, integrated input intensity and mean input intensity. The compact references contain complete probability maps and chosen polygons, but **not all 96 raw distance channels**; `distance_maps_compared` is therefore false.

A zero exit status and `diagnostic_complete: true` mean the measurements were collected successfully. They do **not** mean scientific equivalence passed. `exact_raster_reference_sides` can be `["legacy"]`, `["modern"]`, both, or neither. It reports raster/center/measurement agreement; probability errors and subpixel polygon differences remain separate. Integrity, malformed tensor, or nonfinite-value errors fail the process rather than being converted into a successful comparison. The checker never updates references.

Recommended CI artifacts are `report.json`, `actual.nms.json`, `actual.polygons.gz`, and optionally the compact actual label/probability files. Do not publish the approximately 302 MB full prediction tensor. A 3 GiB Java heap is used for inference, 2 GiB for the serial NMS subprocess; leave additional memory for native TensorFlow allocations.

## Reference integrity and reproduction

Nine compressed payloads total approximately 3.6 MB. The manifest hashes each stored file and its extracted output. GATI, maps and summaries use an outer gzip wrapper; already-gzipped polygon payloads are copied intact and then decoded by the checker. The reference generation was independently checked against the corpus's raw label, canonical mask and complete polygon maps. The reference runtime tensors remain identified by SHA-256 and are not stored in Git.

Given the original input and the two original full archived GATO tensors:

```sh
python3 native-inference/validation/moved-center/make_fixture.py \
  --input input.gati --legacy legacy.gato --modern modern.gato \
  --output reproduced-moved-center-fixtures --dependencies target/pinned-nms
```

This writes a new directory, validates the original input/tensor hashes, and verifies every generated compact payload against the fixed manifest. It cannot bless candidate predictions as reference data. Source conversion is also reproducible using `../corpus/prepare_repository.py` and the checksum-pinned source TIFF. GATI/GATO formats are documented in the worker module. Polygon payloads use big-endian GATP1: magic/version/width/height/object count, then for each object a float center X/Y, integer ray count and 96 float X/Y vertex pairs, in label order. The gzip headers are timestamp-free.

Run the negative and positive unit checks with:

```sh
python3 -m unittest discover -s native-inference/validation/moved-center -p 'test_*.py' -v
```

The Linux integration checks identify each retained side correctly, and a fresh production invocation is also tested before publication. Native Mac observations must be reported from their actual CI run; the reference packet itself is not evidence of Mac execution.

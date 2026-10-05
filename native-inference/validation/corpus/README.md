# Public-corpus legacy/runtime regression

This validation-only harness tests the complete public Hu and neuronal-subtype training/test image archives from [Zenodo v4](https://zenodo.org/records/15314214). It does not change the production worker or its binary protocol.

## Corpus and limits

Download these official files and keep the names shown:

- `2D_enteric_neuron_Hu_train_test.zip` → `archives/neuron.zip`, published MD5 `9936b4632d93ead585f77be018aa0e58`
- `2D_neuronal_subtype_train_test_data.zip` → `archives/subtype.zip`, published MD5 `2e6bfb6bc253816dedc918efd2270b1a`

The archives contain 180 raw images: 25 held-out Hu, 15 held-out subtype, 84 training Hu, and 56 training subtype. Total input is 76,504,710 pixels. The supplied filenames identify human/mouse/rat Hu, confocal/widefield acquisition, and five subtype stains (Calbindin, Calretinin, ChAT, Neurofilament, nNOS). The record describes a broader nine-stain collection; these two archive inventories do not justify claiming that all nine were tested or that the originating laboratory is known for every image.

All original archive pixels are used without resizing, histogram changes, or cropping. Model-specific normalization is the shared production CSBDeep port. Use GAT defaults: requested tiles=4, neuron probability=0.5, subtype probability=0.4, NMS=0.3, excluded boundary=2. Training images are reported separately from held-out images. Consistency between two engines is not biological accuracy against ground truth.

## Prepare and compile

`prepare_corpus.py` requires Python 3, NumPy and Pillow. It verifies archive MD5s, preserves source hashes, creates raw GATI inputs, and writes a detailed TSV manifest and inventory summary:

```sh
python3 prepare_corpus.py --archives /path/to/archives --output /path/to/corpus
```

Compile `BatchProtocol.java` and `ModernBatchMain.java` with the modern Linux worker JAR and its `lib/*` classpath. Compile `BatchProtocol.java` and `LegacyBatchMain.java` separately with `../legacy-tensorflow/target/classes` and that module's own `target/lib/*`. Keep separate class directories and runtime classpaths. Never mix TensorFlow 1.15 and 1.2 JARs or use a Mac-only runtime for Linux execution.

Example from the repository root:

```sh
javac -cp '/path/to/linux-worker/gat-native-inference.jar:/path/to/linux-worker/lib/*' \
  -d /path/to/classes-modern \
  native-inference/validation/corpus/java/org/gatanalysis/inference/{BatchProtocol,ModernBatchMain}.java
javac -cp 'native-inference/validation/legacy-tensorflow/target/classes:native-inference/validation/legacy-tensorflow/target/lib/*' \
  -d /path/to/classes-legacy \
  native-inference/validation/corpus/java/org/gatanalysis/inference/{BatchProtocol,LegacyBatchMain}.java
```

## Run and review with bounded storage

`run_corpus.py` keeps one modern and one legacy model session open per model/phase. It runs **one inference at a time**, then waits for the paired predictions to be reviewed before advancing. Java heaps are capped at 3 GiB per engine, with explicit collection between cases; TF/OMP thread environment limits are 2 intra-op/1 inter-op/2 OMP. Inputs use the original production predictor, normalizer and tiling path. Long-lived loading removes startup overhead; reference and modern models are still in separate processes.

```sh
python3 run_corpus.py --manifest /path/to/corpus/manifest.tsv --models /path/to/model-zips \
  --modern-classpath '/path/to/classes-modern:/path/to/linux-worker/gat-native-inference.jar:/path/to/linux-worker/lib/*' \
  --legacy-classpath '/path/to/classes-legacy:/path/to/legacy/target/classes:/path/to/legacy/target/lib/*'
```

A reviewer must watch `outputs/<case_id>/.ready`, compute and durably save raw-array hashes/errors, NMS/count/label and measurement comparisons using the manifest metadata, then create `outputs/<case_id>/.reviewed`. Only delete matching prediction arrays after durable metrics are saved. Preserve and investigate mismatches. The producer intentionally does not time out merely because a review is pending. A `STOP` file in the corpus directory stops the runner while waiting for review. The final `.producer-complete` marker denotes the completed requested manifest.

The raw tensors are large: the largest 1.86 MP case generates about 722 MB **per runtime**. Never queue the entire corpus's predictions or run all three Java processes at peak memory simultaneously. Java perfdata is disabled to avoid cross-process temporary-file warning interference. `.reviewed` files allow already-completed cases to be skipped on resume; an unreviewed existing output requires reconciliation before rerunning it.

The included `../nms/NmsComparison.java` is the small single-pair reference comparator. A streaming corpus reviewer may use the same unchanged upstream NMS while adding pixel-area/centroid/bounding-box/perimeter metrics; report its exact versions and comparison thresholds with results.

## Repository supplements

`prepare_repository.py` accepts a directory containing the 11 raw public TIFFs from upstream `Sample Images/2D_enteric_neuron_IF/`. It produces 49 static cases (31 neuron, 18 subtype) and a separate 142-frame calcium series. It uses explicit, documented channel mappings; ImageJ composite LUT colors corroborate the marker color suffixes. It excludes GFAP and DAPI channels. The VIP and calcium inputs are marked out-of-domain.

```sh
python3 prepare_repository.py --source /path/to/public-repo-tiffs --output /path/to/repository-corpus
```

Static channels exceeding 2.5 MP are fully covered by nonoverlapping crops no larger than 1024×1024. Smaller supported images remain intact. Pixel values are not rescaled. Crop-origin/source-size metadata is preserved. This is crop-level engine consistency evidence, not proof that the experimental worker supports the corresponding full-size wholemount; do not sum crop counts and call that a whole-image equivalence test.

The calcium set uses all 142 temporal frames as an out-of-domain numerical stress test. It does **not** test GAT's actual calcium-analysis workflow, whose baseline automatic StarDist path is disabled. Run supplements after the primary 180-image corpus with the same producer/reviewer backpressure and resource limits, in a separate output root and report section. Total planned coverage is 371 paired cases and 150,539,487 input pixels.

## Portable result export

After or during a run, export an explicit complete/partial snapshot:

```sh
python3 export_results.py --corpus /path/to/corpus --output /path/to/public-results --expected 180
# For the separate repository/calcium supplement, use --expected 191.
```

The exporter preserves data provenance/hashes and relative case paths, removes local machine paths and debug tracebacks, emits JSON and CSV case metrics, and records expected versus terminal counts. The numeric tolerance field is explicitly named for `atol=rtol=1e-4`; it is not a tolerance of 10,000. Separate positive and deliberately altered negative comparator controls are exported if present, outside the corpus denominator. Aggregate object counts simply summarize test outputs; they are not unique-cell biological counts, especially across crops or temporal frames.

### Subpixel outlines

Schema-2 reviews preserve paired compact polygon payloads separately from raster masks. Each gzip file contains big-endian GATP data: integer magic `0x47415450`, version 1, width, height, object count; then for each object float center X/Y, integer ray count, and float X/Y vertex pairs. Coordinates are global ImageJ positions, including the 0.5 offset, after StarDist's 1/100-pixel quantization. Match polygons by winner center and report unmatched centers or ray counts explicitly.

The exporter copies and hashes these payloads into a portable `outlines/` directory. It reports outline-check coverage, exact quantized-outline matches, changed vertices, and maximum coordinate/Euclidean/perimeter/area deltas separately from raster-label ID ordering and pixel geometry. Identical raster masks do not prove identical subpixel outlines. Early cases reviewed before schema 2 must be replayed before reporting complete outline coverage; replayed cases remain one case each in the denominator.

### Content duplication and independence

Hashing the exact GATI pixel inputs identifies two repeated-content pairs in the 180 archive files: test `widefield.tif` / `widefield_7.tif`, and test `confocal_1.tif` / training `Mouse_confocal_28.tif`. Thus there are 178 distinct archive pixel inputs; the 40 source-labeled test files contain 39 distinct inputs, one also present in the training folder. This benchmark compares runtimes and does not treat the folder labels as proof of independent biological validation. Both engines produced bit-identical tensor hashes on their repeated-input runs, providing an incidental repeatability check.

The repository supplement also repeats the Hu channel of the two `181107` examples, yielding 190 distinct supplement inputs. Overall planned coverage is 371 file/frame/crop cases with 368 distinct pixel inputs. Temporal frames, crops from one source, and related tissue fields are not statistically independent merely because their hashes differ. Duplicate cases remain in the manifest for full source coverage and are explicitly counted in exported summaries.

Completeness is reconciled against the manifest's exact case IDs and input hashes, not inferred from the number of result files alone. The exporter rejects duplicate/unknown IDs, mismatched model/split/hash/dimensions/tiles, inconsistent tensor dimensions, and an expected count that differs from the manifest. Partial exports remain supported and list missing case IDs explicitly. Run the exporter negative tests with `python3 -m unittest discover -s native-inference/validation/corpus -p 'test_*.py' -v` from the repository root.

Outline-delta maxima apply only to polygons whose **winning centers match exactly**. They are not a universal bound when a near-tied candidate changes which center survives NMS. The exporter therefore reports unmatched-center counts and case counts explicitly, alongside full per-object measurements for raster mismatches. For example, one repository Hu crop reverses the order of two near-equal scores, preserves the count, but changes the selected center and produces a larger local contour difference. Inspect those objects separately rather than describing every contour difference as merely 0.01 pixels.

## Outlier repeatability and sensitivity controls

`ModernSensitivityMain.java` and `LegacySensitivityMain.java` are **validation-only** executors. Compile each into its respective isolated class directory with the same modern/legacy dependencies as the batch runners. `run_sensitivity.py` accepts the manifest/case ID, model directory, two executor classpaths, comparator classpath, output directory, and optional zero-based probability-grid `--probe x,y` values.

It performs two fresh-process baseline repeats per engine, then explicit one-thread sessions, then one-thread sessions with the TensorFlow meta-optimizer/standard graph optimizations disabled and `TF_ENABLE_ONEDNN_OPTS=0`. The explicit session API sets intra/inter-op counts to one; baseline repeats request the original 2/1 environment settings. Baseline and single-thread runs explicitly request `TF_ENABLE_ONEDNN_OPTS=1` for the tested Linux configuration. oneDNN availability is platform/build-dependent; these are not Apple-hardware results.

For the moved-center Hu example, use case ID `repo_Tilescan_GAT_ms_distal_colon_MP_hu_c1_t1_x4096_y0` from the supplement manifest and probes `394,168` / `396,166`. Inputs are re-hashed before every execution. The packet records the exact source/crop metadata, input/model/tensor hashes, score margins, same-engine repeatability, and separate cross-engine/optimization comparisons. All controls keep normalization, tile count, probability threshold, NMS threshold, and tie-breaking unchanged. They are diagnostic comparisons, not a recommendation or silent modification to the released worker. Run controls serially after the main corpus queue to avoid competing memory peaks. Do not publish the large raw prediction tensors; publish the compact JSON/geometry evidence and reproduction instructions.

`run_onednn_control.py` adds a separate single-thread, oneDNN-off comparison while leaving graph optimization at its default. Run it after `run_sensitivity.py` with the same manifest/model/runtime/comparator arguments and output directory. This separates the oneDNN environment switch from the combined graph-optimization control, without changing production settings or NMS tie-breaking.

## Publication package

After both portable exports and sensitivity controls are complete, `package_results.py` reconciles the actual case records against their manifests again, verifies their summaries, and builds a compact results tree. It preserves human-readable summaries, manifests, cases, provenance and controls. Outline payloads are put into deterministic numbered ZIPs capped at 20 MiB, with per-archive and per-payload SHA-256 records and extraction instructions. The production source SHA must be passed explicitly; optional separate native-Mac smoke evidence stays distinct from the Linux corpus. Do not publish the large raw prediction tensors.

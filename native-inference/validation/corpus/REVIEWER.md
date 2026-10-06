# Independent streamed regression reviewer

`CorpusNmsComparison.java` applies unchanged StarDist ImageJ 0.3.0 NMS to paired GATO predictions. It never loads TensorFlow. Its dependencies and pinned upstream source compilation are the same as `../nms/README.md`; compile this file instead of `NmsComparison.java`. The upstream source revision is `aff59dbd3cdf88dfa567d4dd562eab943bf4f99b`; keep `Candidates`, `Utils`, `Point2D`, and `Box2D` unchanged.

## One pair

```sh
java -Xmx3g -Djava.awt.headless=true -cp "classes:$CP" CorpusNmsComparison \
  modern.bin legacy.bin 0.5 0.3 results/example
```

Arguments are modern prediction, legacy prediction, probability threshold, overlap threshold, and an optional polygon-artifact prefix. GAT defaults used in this regression are neuron probability 0.5, subtype probability 0.4, overlap 0.3, and excluded boundary 2. The boundary is fixed in the comparator. Predictions must have the same shape.

The single JSON output includes:

- Both complete prediction-file SHA-256 hashes, per-channel maximum/mean absolute errors, and count of values outside absolute/relative tolerance 0.0001. The legacy field name `outside_atol_1e4_rtol_1e4` means **1e-4**, not 10,000
- Probability-threshold flips, candidate counts, NMS winner counts and visible raster-label counts
- Original label-ID pixel differences, canonicalized object-label differences, foreground differences and IoU
- Winner-center equality; pixel-unit area, coordinate sums (exact centroids), four-neighbor pixel perimeter and bounding-box equality in canonical raster-object order
- For differing raw label rasters: up to 20 changed-pixel coordinates and complete old/new per-object measurement records keyed by winning center, including label IDs, pixel area, ImageJ pixel-center centroid, inclusive pixel-index bounding box, four-neighbor perimeter, and quantized polygon area/perimeter
- Subpixel outline comparison matched by winning center: unmatched centers, changed vertices/objects, maximum vertex-coordinate and Euclidean vertex displacement, Euclidean polygon-perimeter difference, and shoelace polygon-area difference

Canonical IDs are assigned by first raster occurrence. This distinguishes pure label numbering changes from object-mask changes. Pixel measurements describe the filled label map; they are not the same as subpixel polygon geometry, calibrated physical measurements, full GAT result tables, or biological validation. Polygon coordinates come from StarDist's 1/100-pixel quantization and ImageJ's half-pixel coordinate convention. Small float32 representation effects may make a nominal 0.01-pixel delta display as 0.01001. Polygon deltas are computed only for matched winning centers; always inspect unmatched-center counts too.

## Streamed corpus

`review_pairs.py` reads `manifest.tsv`, with `case_id` and `model` (`neuron` or `subtype`) plus provenance fields. Each producer-created case directory must contain complete `modern.bin`, `legacy.bin`, and `.ready`. The script writes durable `review/results/<case_id>.json`, compact paired polygons, then `outputs/<case_id>/.reviewed` to release a sequential producer. A temporary file, fsync, and atomic rename are used before acknowledging a case.

```sh
python3 review_pairs.py --root /path/to/corpus --classpath "classes:$CP" \
  --remove-matching-tensors
```

Raw tensors are retained by default. With the explicit removal option, they are removed only after durable metrics when label rasters, counts, winner centers and pixel measurements match, no probability-threshold flips occur, and every raw value is within atol=rtol=0.0001. Subpixel-only differences remain fully represented by paired compact polygon archives even when raw tensors are removed. Raster/count/measurement/numeric anomalies retain their raw tensors. Input images and model files are never deleted.

The reviewer pauses cleanly when `review/.stop` appears and ends when `.producer-complete` exists and every ready case has a review marker. The producer must create its completion marker only after the intended corpus is terminal. A separate manifest-versus-result count is still required; a stopped watcher alone does not prove coverage. Errors are explicitly recorded as `comparison_failed`, with tensors retained; diagnose and retry recoverable failures rather than reporting them as passes.

Each pair uses planar float arrays without duplicate interleaved arrays, and numerical metrics/hashes are computed during streaming reads. Process cases serially. Large 97-channel predictions still require substantial RAM; this script does not make arbitrary image sizes supported by the worker.

## Compact polygon format

Each `*-modern.polygons.gz` / `*-legacy.polygons.gz` decompresses to a big-endian GATP version-1 stream:

1. int magic `0x47415450`, int version 1, int width, int height, int object count
2. For each object: float32 winning-center X, float32 winning-center Y, int vertex count, then that many float32 X/Y coordinate pairs

Objects are written in lexical center-key order. Coordinates are global ImageJ coordinates, including its half-pixel offset. The payload retains complete outlines independently of large prediction tensors. No inference is performed from the polygon archives.

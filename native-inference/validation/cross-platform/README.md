# Compact cross-platform real-image regression

This CI regression runs the actual author models on a public 175 × 175 Hu image,
then compares against compact references generated with official TensorFlow Java
1.15.0 / TensorFlow 1.15.0 on Linux x86-64. The candidate is the isolated
TensorFlow Java 1.2.0 / TensorFlow 2.21.0 worker. CI runs the same test on native
macOS ARM64 and Linux x86-64; it does not substitute cross-compilation for execution.

The checked-in fixture payload is 502,088 bytes. It contains the original image's
unrescaled pixels in GATI format, two probability planes, two raw 16-bit label
rasters, and two compact NMS/measurement summaries. Full 97-channel predictions,
models, dependencies, and downloaded source are not checked in.

## Fixed test matrix and pass criteria

| Case | Model | Requested tiles | Probability | NMS / boundary | Legacy result |
| --- | --- | ---: | ---: | --- | --- |
| `neuron-hu-1` | `2D_enteric_neuron_v4_1.zip` | 1 | 0.5 | 0.3 / 2 | 500 candidates, 39 objects |
| `subtype-hu-4` | `2D_enteric_neuron_subtype_v4.zip` | 4 | 0.4 | 0.3 / 2 | 36 candidates, 3 objects |

Probability thresholds are the actual GAT defaults. **Subtype inference on this
Hu image is technical smoke only, not representative subtype performance.**

Every run requires:

- The pinned input/reference/model/dependency SHA-256 checks to pass
- Finite predictions with the exact 175 × 175 × 97 shape
- Every probability value to satisfy `abs(actual - reference) <= 1e-4 + 1e-4 * abs(reference)`
- Exactly equal raw label pixels, including label IDs and numbering
- Exactly equal NMS winner/candidate counts and ordered winner centers
- Exactly equal per-label raster area, centroid, and integrated/mean original Hu intensity

A failed comparison exits nonzero and fails CI. No tolerance fitting, reference
refresh, label renumbering, or threshold adjustment occurs in CI. Nine comparator
unit tests exercise roundoff acceptance and rejection of changed probabilities,
NaN, label-ID permutations, changed counts/intensities, truncated data, and hashes.

`comparison.json` reports both raw label hashes and canonical object-shape hashes.
Canonical IDs are assigned by first raster occurrence to diagnose otherwise
identical masks with reordered labels. **Canonical equivalence does not satisfy
the raw-label gate.** Counts, centers, and measurements are retained separately.

## Unchanged StarDist postprocessing

`dependencies.json` pins the official StarDist ImageJ commit
[`aff59dbd3cdf88dfa567d4dd562eab943bf4f99b`](https://github.com/stardist/stardist-imagej/tree/aff59dbd3cdf88dfa567d4dd562eab943bf4f99b)
and SHA-256 for `Candidates`, `Utils`, `Point2D`, `Box2D`, and Clipper 6.4.2. The
sources are downloaded and compiled without edits. ImageJ 1.54p, ImgLib2 7.1.5,
ImageJ Common 2.1.1, and SciJava Common 2.100.1 are pinned by URL and checksum too.
`FixtureNms.java` calls upstream `Candidates.nms(0.3)` with boundary exclusion 2,
then uses StarDist2DBase's reverse winner traversal, label numbering, and ImageJ
`ShortProcessor.fill` rasterization. This is validation code, not a new production
segmentation implementation. The upstream StarDist license is BSD-3-Clause;
see its [license](https://github.com/stardist/stardist-imagej/blob/aff59dbd3cdf88dfa567d4dd562eab943bf4f99b/LICENSE.txt).
Downloaded original JARs retain their embedded licenses/notices.

## Source and reference provenance

`fixture-manifest.json` records the exact public TIFF URL, SHA-256, dimensions,
conversion, model ZIP hashes, source revision, full legacy GATO hashes, fixed
parameters, and every checked-in fixture hash. Source:
[`DYM_22_7_Pr_Hu_crop.tif`](https://github.com/pr4deepr/GutAnalysisToolbox/blob/61d57c4e4bcfe82aa0369100c0a3b0739b70affa/Sample%20Images/2D_enteric_neuron_IF/DYM_22_7_Pr_Hu_crop.tif),
authored/published with the upstream GutAnalysisToolbox project. Its original
8-bit TIFF pixels were checked against every float in the GATI input; there is no
resize, extra crop, scaling, or image upload. The fixture derives only from this
public sample, never user research data. See the repository's license.

The legacy runner is the separate
[`../legacy-tensorflow`](../legacy-tensorflow/README.md) module. References were
produced on 2026-10-05. Both runtimes use the same pure-Java normalization and
tiling implementation to isolate the runtime change. This is not an independent
preprocessing equivalence test; separate worker tests cover CSBDeep compatibility.

## Run locally

After building a worker for the current platform and obtaining the checksum-pinned
models described in the CI workflow, run from the repository root with JDK 17 and
Python 3 (no Python packages required):

```sh
python3 -m unittest discover -s native-inference/validation/cross-platform -p 'test_*.py' -v
python3 native-inference/validation/cross-platform/check.py \
  --worker native-inference/target/gat-native-inference.jar \
  --models target/model-fixtures \
  --output target/cross-platform-local
```

The harness downloads only official checksum-pinned NMS source/JAR dependencies
on first use, compiles them, executes both models, and writes diagnostics under
`--output`. Subsequent runs reverify the cached bytes. The workflow separately
fetches the model ZIPs from the pinned author commit. Reports, actual probabilities,
and actual raw labels are saved as platform-specific CI artifacts, including on
comparison failure; temporary full predictions are not uploaded as artifacts.

To reproduce compact references, first generate both GATO outputs with the
legacy module, the checked-in `fixtures/hu-input.gati`, the model and tile count in
the matrix above. Then run:

```sh
python3 native-inference/validation/cross-platform/compact-reference.py \
  --legacy-neuron target/legacy-neuron-hu-1.bin \
  --legacy-subtype target/legacy-subtype-hu-4.bin \
  --output target/reproduced-compact-references \
  --dependencies target/reference-nms-dependencies
```

This requires the archived full-prediction hashes, writes a **new** directory,
and requires byte-for-byte agreement with every compact reference hash. It never
overwrites checked-in references and is never called by CI. A changed legacy
output hash needs investigation rather than automatic acceptance.

## Interpretation and limitations

Measurements here are explicitly uncalibrated raster measurements: area in
pixels, centroid using pixel centers at `(x + 0.5, y + 0.5)`, and original 8-bit Hu
intensities. They are not an end-to-end test of GAT's GUI, ROI export, physical
calibration, MorphoLibJ, subtype biology, or downstream analysis pipelines.
Exact raster/measurement equality **does not mean subpixel polygon outlines or
perimeters are exactly equal**. Tiny network differences can change individual
1/100-pixel StarDist polygon vertices without changing any raster pixel.

All 96 radial-distance channels are used by the unchanged NMS/rasterization path,
but distance arrays are not stored or compared numerically by this compact gate.
The broader corpus comparison covers those numerical and outline diagnostics.
One small image cannot establish universal scientific equivalence, performance
on representative subtype images, general robustness near decision thresholds,
or compatibility of every M1/macOS/Fiji installation.

Local Linux x86-64 validation on 2026-10-05 passed both cases: probability maximum
absolute error was 1.37090683e-6 (neuron) and 1.51991844e-6 (subtype), with zero raw
label pixel differences and all listed counts/measurements exactly equal.
Native macOS evidence must come from a successful run of this new CI step.

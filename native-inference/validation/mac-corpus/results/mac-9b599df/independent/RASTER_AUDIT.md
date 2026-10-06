# Independent native corpus raster audit

The Python standard-library-only auditor reads the exact downloaded native ZIP. It imports no repository helper and performs no TensorFlow inference, NMS, production change or legacy polygon-to-composite reconstruction.

## Reproduce

From a clone containing source commit `9b599df1b8c67977228bc50104f44280047c4154` and its unchanged legacy reference files:

```sh
python3 audit_native_corpus.py \
  --artifact /path/to/gat-mac-official40-9b599df.zip \
  --repo /path/to/GutAnalysisToolbox \
  --output independent-audit.json
```

Optional `--source-data /path/to/gat-corpus` verifies retained official archives under `archives/`, every original test TIFF inside them, every frozen GATI input under `inputs/`, and the actual overlapping training GATI bytes. Optional `--models /path/to/models` verifies both retained model archive bytes. Both options were used for the delivered report. These are checks of retained copies against exact pins; native-run raw inputs/models are not in the compact artifact.

The exact command is parameterized rather than tied to host paths. The script binds the artifact byte length/SHA-256 and source commit explicitly. JSON paths and evidence identities are portable.

## Checks and result

- Seven hand-calculated raster/encoding controls pass, including empty maps, perimeter at image borders, separated pieces, numeric label-ID renaming, and changed pixels
- All 413 artifact ZIP members pass CRC validation; all 404 compact result files pass manifest SHA-256 and exact membership checks
- Frozen manifest matches the source commit; all reference-file, helper-source, dependency-manifest, model, source-archive, source-TIFF and GATI pins are verified
- All 40 case records match every frozen metadata field; exact official-test membership, 39 unique GATI inputs, the duplicate test pair and one training overlap are checked
- Every modern raw and canonical raster is decoded. The canonical file is byte-identical to independent first-raster-occurrence relabeling
- All 4,472 modern measurement rows are checked against pixel-derived area, integer x/y sums, four-neighbor perimeter, inclusive bounding box and exact pixel centroid. All 40 measurement hashes are independently recomputed from the contract's UTF-8 integer rows
- Modern and archived legacy polygons are independently decoded to check counts, exact center sets and strict quantized vertex equality. Candidate counts are compared with pinned legacy counts but are not recomputed from unavailable tensors
- Result: 37 raw-label, 39 canonical-raster, 39 measurement, 40 center-set and 8 strict-outline case matches
- Raw-ID-only differences: neuron_test_widefield_6 and neuron_test_widefield_3
- Foreground-union maps differ only for neuron_test_widefield_9, at x=617, y=515. Its original exclusive-label differing-pixel count remains unavailable because original paint order was not retained
- For the two retained-order cases, supplied legacy maps are checked against all authoritative raw, canonical and measurement hashes before comparisons: neuron_test_widefield_3 has 942 raw-label differences and 0 canonical differences; subtype_test__Calb_widefield has 0 in both

This is a compact-output and provenance audit. It does not claim numerical tensor parity, biological accuracy or scientific equivalence. Foreground masks are decoded and compared here; separate pinned-ImageJ polygon rasterization review supplies the independent geometry check.

# Legacy versus native-worker runtime regression

## Conclusion

All 371 case/frame/crop comparisons produced the same StarDist object count: 28,958 detection instances in each runtime. The results support close technical consistency, but **do not establish identical segmentation or measurements**.

- 359/371 raw label rasters were identical.
- 362/371 masks and pixel measurements were identical after allowing label-ID permutations.
- Three cases differed only in label numbering, eight differed by one boundary pixel, and one selected a different near-tied NMS center and changed 48 foreground pixels.
- 73/371 cases had identical quantized polygon outlines. Among polygons with the same winning center, the maximum coordinate difference was 0.0100098 pixels (maximum Euclidean vertex displacement 0.0141559 pixels). This bound excludes the moved-center object described below.
- No prediction value exceeded absolute-plus-relative tolerance 1e-4 + 1e-4 × |legacy value|. The largest probability difference was 5.51343e-6; the largest distance difference was 6.86646e-5. Eight probability-threshold crossings did not change final object counts.

Production source: `366c8339e18563105ba41f82ea9d0ac6b6650077`, tag `apple-silicon-preview-1`. These corpus comparisons ran on Linux x86-64 CPU with TensorFlow Java 1.15.0 / TensorFlow 1.15.0 versus TensorFlow Java 1.2.0 / TensorFlow 2.21.0. Runtime settings, model hashes, source provenance and comparator hashes are retained with the evidence.

## Coverage and interpretation

The 180 archive files comprise 25 Hu and 15 subtype source-labeled test files, plus 84 Hu and 56 subtype training files, from [Zenodo record 15314214](https://zenodo.org/records/15314214). The five subtype stains present in those raw image files are Calbindin, Calretinin, ChAT, Neurofilament and nNOS. The QA archives were also inventoried: their TIFFs are derived predictions for the same test inputs, not additional raw images. Their SavedModel contents match the models tested here.

The repository supplement contains 49 static model/channel/crop cases and all 142 calcium frames. Oversized static inputs were covered by unrescaled, nonoverlapping crops no larger than 1024 × 1024. Crop boundaries can affect segmentation: these runs do not establish whole-image tiling support, and counts across crops must not be interpreted as a whole-image equivalence test. Calcium and VIP are out-of-domain software stress tests. The normal GAT calcium workflow does not automatically run StarDist, so this is not a validation of that workflow.

There are 368 distinct pixel inputs among 371 cases, totaling 150,539,487 input pixels. The archive's 40 source-labeled test files contain 39 distinct pixel inputs; one also appears in its training set. Exact-hash deduplication does not establish statistical independence. The 33 outline replays are excluded from the 371 denominator; both runtime tensor hashes reproduced exactly in every replay.

Every case uses the existing preprocessing and original StarDist NMS: probability 0.5 for neuron / 0.4 for subtype, NMS 0.3, boundary 2, tiles 4. We did not tune thresholds, normalization, or tie-breaking to improve agreement. Pixel areas, centroids, bounding boxes and four-neighbor perimeters are uncalibrated technical measurements. This work does not score biological accuracy against ground truth or validate the complete interactive GAT workflow.

## Moved-center counterexample

Case `repo_Tilescan_GAT_ms_distal_colon_MP_hu_c1_t1_x4096_y0` is the 760 × 1024 crop starting at (4096, 0) in the public Hu tilescan. Both runtimes return 148 objects. Two near-equal probability scores reverse order, changing one winning center from legacy (396.5, 166.5) to modern (394.5, 168.5).

The affected cell has 441 legacy versus 451 modern filled pixels, intersection 422 and union 470: **per-cell IoU 0.897872 and Dice 0.946188**. Whole-image foreground IoU is approximately 0.999400 and would conceal this local difference. Its filled area changes by 2.27%, centroid by approximately (-0.0732, +0.3895) pixels, and four-neighbor perimeter from 106 to 104 pixels. Polygon area changes from 444.2353 to 454.9502 pixels² and perimeter from 88.8961 to 88.3642 pixels. Full paired outlines, changed pixel coordinates and per-object measurements are retained.

Two fresh-process repeats per engine reproduced the original baseline tensors exactly. Explicit single-thread sessions retained the cross-engine moved-center difference. Single-thread sessions with oneDNN disabled produced equal cross-engine centers, masks and quantized polygons for this case. Disabling graph optimization as well produced the same tensor hashes as the oneDNN-only control. This isolates sensitivity to the tested Linux kernel configuration; it is not broad validation of a new configuration, and the released production settings remain unchanged.

See `controls/sensitivity.json`, `controls/moved-center-object-overlap.json`, the case record in `supplement/cases.json`, and the paired outline archive entries. Subpixel outline metrics in aggregate summaries apply only to matched centers, not this changed candidate pair.

## Native Mac evidence and remaining boundary

A separate native Mac Java 21 CI job ran both original models on the public 175 × 175 Hu fixture. Neuron at probability 0.5 / tiles 1 returned 39 objects; subtype at probability 0.4 / tiles 4 returned 3. Both matched the legacy reference labels, centers and pixel measurements exactly. Subtype-on-Hu is a technical smoke test. The exact job and source revision are recorded in `native-mac-smoke.json`.

The 371-case corpus and sensitivity controls were not run on native Mac hardware. They therefore cannot resolve whether the Mac kernel configuration reproduces the Linux moved-center counterexample. A separate compact diagnostic fixture is being prepared for that question. The Apple Silicon preview requires macOS 14 or later and remains experimental.

## Evidence integrity

The exporter reconciles every case ID, model, split, input hash, dimensions and tile count against its execution manifest, and rejects duplicates or inconsistent extras. All 371 expected cases completed without comparison errors and include subpixel outline checks. Positive and deliberately perturbed negative comparator controls are preserved. Raw outlier tensors are retained locally; the public package contains compact summaries, provenance and exact paired polygon payloads with SHA-256 manifests. Source-data/model hashes and the frozen production commit anchor reproduction.

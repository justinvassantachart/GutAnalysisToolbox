# Native backend validation, 2026-10-05

These checks establish Linux numerical compatibility on an initial sample and native macOS backend execution in CI. They are not clinical/biological validation, full GAT GUI validation, or evidence that every Apple Silicon system/model behaves identically.

## Build and pure-Java compatibility

- Standalone worker built on Linux with official TensorFlow Java 1.2.0 / TensorFlow runtime 2.21.0, Java 17 toolchain, release target Java 11
- Unit tests cover nearest-sample percentiles, low-only clipping, constant images, original-image immutability, exact tile-count/rounding behavior, central stitching and original-size fitting, GATI/GATO shape/content checks, truncated/nonfinite input, ZIP traversal/ambiguity/cleanup, and signature rejection
- All sampled tile pixels matched ImgLib2 7.1.5's actual nested MirrorDouble interval views for ordinary, odd, tiny, and multi-tile images
- `--self-test` successfully allocated a TensorFlow tensor in the isolated Linux JVM
- Apple Silicon distribution built and verified to include the three ARM64 Mach-O libraries; JNI minimum OS is 14.0, TensorFlow core minimum OS is 12.0, therefore the distribution requires macOS 14+

## Real-model legacy-runtime numerical and NMS comparison

Reference: isolated official TensorFlow Java 1.15.0 runtime. Candidate: isolated TensorFlow Java 1.2.0 / TensorFlow 2.21.0 runtime. Both used the same pure-Java preprocessing so the numerical comparison isolates the runtime change; preprocessing has independent tests above.

Input: unscaled, 8-bit public `Sample Images/2D_enteric_neuron_IF/DYM_22_7_Pr_Hu_crop.tif`, 175×175, from upstream `main`. This is a Hu-channel sample; using it with the subtype model checks software execution, not representative subtype performance.

1. `2D_enteric_neuron_v4_1.zip`, requested tiles=1
   - Output shape 175×175×97
   - Maximum probability absolute difference: 0.00000137090683
   - Maximum radial-distance absolute difference: 0.0000238418579
   - Mean absolute difference across all channels: 0.00000210322346
   - All values within atol=0.0001, rtol=0.0001
   - Probability threshold 0.5 changed sides for zero pixels
   - Unchanged Fiji StarDist NMS: 500 candidates, 39 labels in both runtimes
   - Final 16-bit label image: zero differing pixels out of 30,625
2. `2D_enteric_neuron_subtype_v4.zip`, requested tiles=4
   - Output shape 175×175×97
   - Maximum probability absolute difference: 0.00000151991844
   - Maximum radial-distance absolute difference: 0.0000267028809
   - Mean absolute difference across all channels: 0.00000236116457
   - All values within atol=0.0001, rtol=0.0001
   - Probability threshold 0.5 changed sides for zero pixels
   - Unchanged Fiji StarDist NMS: 19 candidates, 2 labels in both runtimes
   - Final 16-bit label image: zero differing pixels out of 30,625

NMS parameters: probability 0.5, overlap 0.3, excluded boundary 2. Comparison used unchanged upstream `Candidates`, `Point2D`, `Box2D`, and `Utils` at StarDist ImageJ commit `aff59dbd3cdf88dfa567d4dd562eab943bf4f99b`, Clipper 6.4.2, and ImageJ 1.54p's `ShortProcessor.fill` with StarDist's label ordering. Winner centers also matched.

## Native macOS CI execution

The [macOS job for source commit 94e039cc5b5c396bd248c04b5c5925c20f4df3a1](https://github.com/simplecoreorg-cyber/GutAnalysisToolbox/actions/runs/37338503480/job/111859285053) passed on 2026-10-05:

- macOS 14.8.9, ARM64 runner, native aarch64 Temurin Java 17.0.20.1
- All 16 worker unit tests
- TensorFlow 2.21 JNI allocation self-test
- Both actual, SHA-verified author model ZIPs on the synthetic 129×97 smoke input, each returning finite 129×97×97 predictions

This is real native macOS inference, not cross-compilation alone. The input was synthetic, so it is not cross-hardware scientific-equivalence proof. Full Fiji GUI and optional workflow testing remain separate.

## Limits and next checks

- Numerical legacy-vs-modern comparisons above ran on Linux; native macOS CI scope is listed separately
- No claim of universal bit-identical TensorFlow predictions; observed tiny numeric differences can affect threshold-edge cases on other images
- One small real image, two models, and two tiling configurations are limited coverage; representative subtype images, wholemounts, more dimensions/tilings, and saved-GAT result comparison remain necessary
- Worker tensors are limited to 268,435,456 floats. At 97 output channels this caps a single assembled tensor near 2.77 megapixels, and padded dimensions can lower the effective limit. RAM limits may be lower. Large-image streaming is not implemented
- No Metal/GPU speedup, model training, 3D inference, arbitrary multiclass exports, or full Fiji GUI end-to-end validation is claimed

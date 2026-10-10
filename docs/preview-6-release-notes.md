# Apple Silicon TEST preview 6: restore V2 ganglia behavior

Version `2.0.1-apple-silicon.6`, tag `apple-silicon-preview-6`.
Experimental native arm64 Fiji overlay for macOS 14+; bundled Java 21 recommended.
This release is prepared from `test-restore-v2-ganglia-parity`, without merging
that branch into `main`. An unlisted release is not yet published.

## Changes

- Restore all three `1.0/255.0` ganglia float-channel multiplications from
  upstream Java V2 commit `1870d9e16e16fd6daeac0bd05122e851029ddedc`
- Retain the new-output ownership, shape and stale/current-image guards
- Keep model weights, RDF preprocessing, channel mapping (`R=Hu, G=Ganglia,
  B=Hu`), thresholds, calibration, source pixels and RGB review image unchanged
- Retain preview 5's display-range/LUT Template Matching repair, alignment
  protocol 2 and earlier CPU/calcium/multiplex safeguards

Ganglia outputs change from preview 5. Preserve version/runtime provenance and
recheck analyses before combining results produced by different previews.

## Bounded native parity evidence

[Native Mac CI run 38080519366](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/38080519366)
passed on source `a676e9ae79f7309f02d19f710141b5ef72d1711e`, before the preview
version/documentation update. It compares the unchanged original V2, unchanged
preview 5 (`ab1865cc745a8cb589f8a0034968d85b99843cf2`) and restored fork in
separate, same-host installed Fiji copies.

All three public fixtures pass strict original/fork comparison:

- `model_public`: 6 ganglia
- `distal_hu_gfap`: 2 ganglia; all 83 fixed historical neuron-ROI assignments
  match, with 42 and 41 neurons assigned to the two ganglia
- `proximal_hu_chat`: 15 ganglia

Float input bytes, binary mask pixels, label pixels, counts and calibrated
areas match exactly on every fixture. Mask IoU and Dice are 1.0 with zero
changed pixels. Saved pixel hashes, unchanged source/calibration and identical
contracts/parameters are checked. Preview 5 diverges in both inputs and masks
on all three fixtures, so the comparison detects the reverted scaling change.
The source audit also verifies identical original/restored input-preparation
method bytes and unchanged scientific helpers.

[Root tests on all three platforms](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/38080663904)
passed at the same pre-release source revision. The final release page must
record the final versioned source SHA, its own CI outcomes and artifact hashes;
these earlier results are not a substitute for those checks.

## Runtime boundary and limitations

Small ganglia inputs can still be rejected when the model's 1024-pixel tile
exceeds three times an image dimension; this normalization fix does not address
that tiling limitation.

The native experiment uses an explicit test-only option to replace exactly two
official historical dependencies, JDLL `dl-modelrunner-0.6.4.jar` and
`DeepImageJ-3.2.1-SNAPSHOT.jar`, in freshly extracted disposable CI Fiji copies.
Their full hashes and the before/after inventory delta are recorded in
`historical-runtime-audit.json`; all model, RDF, macro and engine pins remain
strict and unchanged. The default official-updater validation stays strict.
No existing user installation is modified, and the release overlay contains
neither these substituted JARs nor an automatic runtime installer. This result
does not certify the currently changed live-updater runtime.

The three source images and fixed historical ROIs are not expert ground truth.
This establishes V2 behavioral parity for those samples and the tested runtime,
not biological accuracy, every image, complete interactive workflows or all
GAT functionality. Physical OpenCL/GPU, existing unimplemented modes and other
[workflow limits](apple-silicon-workflow-matrix.md) remain unchanged. Earlier
scientific reports and release assets remain immutable historical evidence.

## Package

Install the single versioned GAT JAR and both complete matching ARM64 worker
directories together. Keep worker libraries outside Fiji's global classpath.
Use `PREVIEW_6_SETUP.md`, embedded `BUILD_INFO.json`, the external identical
`FORK_BUILD_INFO.json` and SHA-256 files from the same release. Compiled-class
comparison establishes build consistency; test execution is recorded separately.

# Apple Silicon preview 7: compatibility and limits

This preview adds a separate legacy-macro Apple Silicon route. It retains the
legacy RGB preparation, DeepImageJ ganglia model, morphology, CLIJ overlap
assignment, conditional missing-neuron expansion, review and exports. It does
not replace those operations with Java V2 algorithms or retune thresholds.
The new boundary uses isolated native StarDist/Template Matching workers.

Generated scripts retain the original scientific statements except for an
explicitly audited compatibility allowlist. Original scripts remain intact.
Namespaced settings imports are quoted, and alignment callers require an
explicit success token so a failed operation cannot continue to export.
Existing Java V2 fixes and Preview 6 ganglia scaling are included separately.

## Public comparison evidence

The 30-case inference settings matrix covers the two supplied neuron/subtype
models and selected shapes, output modes, probability, overlap and tile
settings on Linux and real Apple Silicon. At candidate `ce88fad4`, both hosts
matched all label rasters, object counts and raster areas. Seven cases per host
had initial polygon-coordinate differences of at most one original StarDist
quantization step (0.01 pixel). Strict reports are retained separately from the
explicit small-difference acceptance gate. The 720-case original-NMS controls
also passed on both hosts.

- [Recorded inference run](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/38191368161)
- [Guarded alignment run:21 exact native/delegate pairs](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/38192786778)
- [Cross-platform unit run:118 tests per host](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/38192906012)
- Source-locked tests and parameter manifests: `validation/legacy-macros/`

Later complete-menu, alignment and final-package outcomes are recorded on the
release page for its exact commit. A passing component or source audit does
not mean every possible parameter combination or physical device was tested.

## Research use and known limits

This is compatibility/functional testing, not validation of biological ground
truth. Researchers must inspect outlines and review ROIs for their own staining,
specimens and scientific questions. Legacy expansion can merge neighboring
clusters, as in the original algorithm. Keep original data and working installs.

- Only the affected paths and finite settings matrix are compared. Unchanged
  spatial/EDF/calcium calculations are not advertised as newly validated.
- Physical OpenCL device behavior, macOS Finder/Gatekeeper installation clicks
  and arbitrary manual edits are not exhaustively covered by hosted tests.
- The historical Sox10-only route requires its exact historical helpers/model
  and is not established by neuron/subtype tests. No guessed model is substituted.
- Native alignment admits at most 512 MiB of raw image data and a 768 MiB
  Java-memory estimate (raw data + eight bytes per frame pixel + 64 MiB).
  The per-frame limit remains 67,108,864 pixels, with at most 10,000 frames
  and a 900-second worker timeout. This leaves headroom in the 1 GiB worker
  heap; native/OpenCV memory is additional. Unsupported inputs stop.
- Native model output still needs a Java-indexable full tensor in memory even
  with tiling. Custom models must meet the documented worker tensor contract.
- Java V2's inherited delete-all-review behavior restores fallback labels;
  its separate no-Hu original export control also has an unresolved baseline
  divergence. These diagnostic failures remain visible and do not establish
  that arbitrary Java V2 review workflows have passed.
- Ganglia model/preprocessing and OpenCL dependencies remain those of the
  original installation. Source preservation does not promise compatibility
  with future live-updater changes.

Private inputs, overlays and per-specimen findings are not distributed in
public packages, repositories or CI. Earlier preview releases remain unchanged.

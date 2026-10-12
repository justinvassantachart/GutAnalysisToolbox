# Legacy macro settings and runtime parity

This suite targets the **macros researchers used**, not the separately rewritten
Java V2 workflows. The reference is upstream commit
`f2098636d5f42f73c3e724286af0b212fe3ea5c0`, immediately before
`a5a34537f9e53a6a5da470ea454d65e6cd0110f9` deleted GAT v1. All 47 preserved
`.ijm`/`.py` files are pinned by exact Git blob, SHA-256 and byte length in
`source-manifest.json`. Existing Java V2 evidence at `1870d9e` cannot replace
these controls.

## Separate evidence scopes

1. **Source/overlay contract:** all original script bytes are unchanged; a
   generated candidate may change only the eight StarDist class targets, three
   alignment call targets, and installation/helper/menu namespace references.
   Scientific settings, RGB display stretching, float `Open`, CLIJ overlap
   assignment, missing-neuron repair and processing order are retained.
   External models and installed plugin bytes are separate runtime inputs.
2. **NMS/output contract:** actual original `StarDist2DNMS` versus the adapter on
   identical synthetic tensors. This checks output selection, label rasters and
   real ROI Manager behavior. It executes no model or whole macro.
3. **Registered macro inference boundary:** execute the exact original
   `_Analyse Neurons.ijm` `Command From Macro` line with actual ImageJ1 macro
   dispatch and discovered SciJava plugins. Candidate changes only the target
   class. This includes real model inference, label display and ROI outputs;
   it does **not** run the full neuron analysis, ganglia, review or export loop.
4. **Whole workflows:** actual original and generated macro commands, dialog
   choices, review edits and reopened scientific outputs. These remain separate
   required rows in `coverage-matrix.json`; inference-boundary passes cannot
   mark them passed.

`coverage-matrix.json` is a finite, prioritized plan, not a results file. It
contains 35 workflow/settings rows. Some rows deliberately combine a small
set of closely related choices; complete every listed choice before claiming
that row. User-selected glia models, physical OpenCL and EDF require their real
dependencies. Never replace a missing glia model with a neuron model or a CLIJ
result with a centroid approximation.

## Source/overlay audit

The independent audit does not import or trust the generator's transformation
implementation or its change manifest. It reconstructs the narrow allowed
changes from exact historical bytes, preserving all other bytes and line endings.

```sh
python3 validation/legacy-macros/audit_sources.py \
  --output target/macro-source-audit.json
python3 validation/legacy-macros/audit_sources.py \
  --overlay target/GAT-MacroFork.zip --output target/macro-overlay-audit.json
```

If an existing user settings table was explicitly supplied to the generator,
pass that same file as `--settings`. Its exact bytes, not a guessed/default
table, become the settings reference. This is source preservation, not proof
that a dialog loaded or applied those values.

## Actual original NMS and ROI Manager

```sh
python3 validation/legacy-macros/run_nms_probe.py \
  --java-home /absolute/jdk \
  --classpath-file /absolute/installed-fiji-classpath.txt \
  --production-classes target/classes --output target/nms-pair
python3 validation/legacy-macros/check_nms_report.py \
  target/nms-pair/result/report.json --output target/nms-pair/check.json
```

Run only in an existing supported AWT environment. The launcher does not create
a display connection. It compiles the actual adapter plus probe, then runs one
disposable JVM with a 256 MiB heap, one active CPU and a 240-second deadline. It
does not launch Fiji or a model. The original StarDist plugin, ImageJ and SciJava
dependencies must already be available. Original and adapter class byte hashes
and code sources are recorded. Do not put modern TensorFlow into the host JVM.

The complete 720-case grid is:

- Probability: `0, .3, .5, .8, 1`
- NMS: `0, .3, .7, 1`
- Output: `Both`, `Label Image`, `ROI Manager`
- ROI placement: `Automatic`, `Stack`, `Hyperstack`
- Odd/even rectangles: `33x29`, `32x30`
- Input axis shapes: XY; XYCT with singleton C and T

The deterministic tensor includes boundary candidates, equal scores, overlapping
objects and exact threshold values. Both variants receive identical pixels.
Checks compare label bytes, axes, type and name; ordered ROI vertices, names and
C/Z/T positions; unchanged input tensors; and optional prediction outputs.
Default-threshold controls must be nonempty. Threshold-one empty cases remain
real observations. A sentinel in the actual global ROI Manager checks the
original behavior: ROI-producing modes clear it, label-only leaves it unchanged.
An unregistered hidden ROI Manager is not accepted as the actual output target.

Local preparation reached a complete independently checked 720/720 pass on
Linux/AWT with the current candidate. That evidence is held locally; rerun this
suite against the exact committed/released code before using it as release
evidence. An earlier setup block (missing required SciJava services) and a
hidden-manager harness control were rejected rather than counted as passes.

## Actual macro-command inference

Use a real legacy ImageJ2/StarDist runtime, such as the pinned plugins and
dependency POM in `native-inference/validation/baseline/`. On hosted Linux,
provide Xvfb. On a native Mac, provide actual arm64 Java/Fiji on supported macOS.
The original TF1 reference runs on a supported Linux/Intel host, not via Rosetta.
Use the pinned `protobuf-java-3.11.4.jar` with TF1. A current Fiji containing
protobuf 4 can load the TF1 native library/model and still fail during prediction
with `NoSuchMethodError`; that is a runtime assembly failure, not inference
evidence. The runner now verifies the protobuf and four legacy plugin JAR hashes
before starting any model.
The runner reuses the baseline URL-system-loader bootstrap, applies official
ImageJ legacy initialization, and never inserts fake command menu registrations.

Prepare a classpath text file of explicit JARs/directories. For the original
control, remove every fork GAT JAR/class directory. Both variants reject modern
TensorFlow/worker classes on the host classpath. Native adds the actual compiled
adapter directory with its annotation-generated SciJava index. The worker stays
in its separate JVM and separate distribution directory.

The fixture and both models are the SHA-pinned public files in
`native-inference/validation/cross-platform/fixture-manifest.json`. The runner
refuses a different image hash, including private specimen images.

```sh
python3 validation/legacy-macros/run_inference_probe.py \
  --variant original --runtime-classpath /absolute/original-runtime-cp.txt \
  --fixture '/public/DYM_22_7_Pr_Hu_crop.tif' --model-directory /public/models \
  --preset smoke --output target/macro-original

python3 validation/legacy-macros/run_inference_probe.py \
  --variant native --runtime-classpath /absolute/original-runtime-cp.txt \
  --production-classes target/classes \
  --native-worker /absolute/gat-native-inference \
  --fixture '/public/DYM_22_7_Pr_Hu_crop.tif' --model-directory /public/models \
  --preset smoke --output target/macro-native

python3 validation/legacy-macros/compare_inference.py \
  --original target/macro-original --native target/macro-native \
  --output target/macro-inference-comparison.json
```

`--java` and `--javac` may select explicit binaries. When using a full installed
Fiji classpath, `--fiji-directory` selects its existing runtime root. The test
still uses an empty dedicated IJ1 plugins directory plus the explicit classpath
to prevent an original control from discovering a fork JAR elsewhere in Fiji.
User preferences are scoped to each disposable case.
`--cases neuron-01` is a
single integration smoke, not the complete setting-level coverage. The default
seven-case smoke spans both models, tiles `1/2/4/5/8`, 8/16/float input, odd/even
rectangles, and scales `.5/1/1.5`. `--preset matrix` runs the 30 crossed cases.
These cover levels and selected interactions, not the full Cartesian product.
Hu input through the subtype model is a technical compatibility control only.

Each original/native case runs in a fresh disposable process. The default
deadline is 600 seconds, 768 MiB parent/worker heaps, one active CPU and the
existing workflow runner's 3 GiB process-tree RSS ceiling. Run cases serially.
The native launcher sets **`gat.stardist.backend=native`**, verifies that the
actual backend selector agrees, hashes the worker files, and observes the real
`NativeInferenceMain` child. Linux automatic fallback to original StarDist is
not accepted as native evidence. `gat.inference.backend` is not the selector.

Public-image preparation is explicit: centered odd/even crops, deterministic
8/16/float representations, then the original macro's actual `Scale...` command
with `interpolation=None`. The pinned original inference call line is executed
with its original parameter names and `process=[false]`; probability, overlap
and requested tiles are passed as variables, not rounded or hard-coded inside
the adapter. A SciJava event observer reads the actual completed module outputs;
it does not substitute a model result. The probe independently checks the real
new label window, global ROI Manager, source pixels and unrelated-image sentinel.

Outputs are `summary.json`, each case's `runtime.log`, and
`evidence/{report.json,labels.f32be,invoked.ijm,imagej.log}`. A process deadline,
missing module, wrong backend, failed display or absent output is incomplete or
failed evidence. A successful launcher exit alone is insufficient.

The paired comparator checks settings and source/model/input identity; raster
IDs, areas, output metadata, ROI order/names/positions and vertices; and new
display state. It independently reopens the raw label data and recomputes counts
and areas. Exact comparisons are the default. It also reports differing pixel
counts/fractions, foreground IoU, per-label area deltas and maximum ROI vertex
difference so small numerical differences can be reviewed explicitly. An
explicit nonzero `--roi-atol` affects vertices only and is disclosed in the
report; it never weakens label, count, area, ordering or settings gates.

No full-inference result is claimed merely from compiling this harness. Whole
workflows and private specimen acceptance remain separate from this public
technical boundary test.

## Reuse and release evidence rules

- Reuse an actual inference tensor only for settings that cannot affect
  inference: probability/NMS thresholds, output selection and ROI placement.
- Never reuse it across changed model, input dtype/pixels, shape, scale or tile
  count. In those cases run both real backends again.
- Preserve requested and observed settings. Full macros choose some tile counts
  automatically based on image size; testing a direct tile parameter does not
  prove that their size-selection branches were reached.
- For complete workflows record source/overlay/model/plugin hashes, platform,
  exact menu, all script parameters and dialogs, actual backend, artifacts,
  manual edits and completion state. Compare label geometry/counts/areas, not
  only total counts or screenshots. Reopen CSV, ROI ZIP and TIFF exports.
- Keep original and candidate installations separate. Preserve negative
  controls, errors and unrun cases. Do not retune thresholds to force agreement.
- Use only public/synthetic fixtures in published CI evidence. Private inputs,
  masks, thumbnails, coordinates and other specimen derivatives stay private.

## Harness regression tests

```sh
python3 -m unittest discover -s validation/legacy-macros -p 'test_*.py' -v
```

Unit fixtures in these tests are explicitly fabricated to test evidence
rejection. They are never model or workflow results. Counterexamples include
missing/duplicate settings, fabricated full-macro claims, changed label pixels,
subpixel ROI changes, lost positions, empty positive controls, source changes
to float morphology and unauthorized settings-table replacement.

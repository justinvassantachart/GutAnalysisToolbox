# Native workflow validation

These validation-only programs run real GAT helpers and ImageJ/plugin commands
on known synthetic pixels or public model assets. They are intended to run in
separate native Linux x86-64 or macOS arm64 JVMs. They do not install into or
modify a working Fiji, change model metadata, or claim complete biological or
interactive-GUI validation.

## Run

From the repository root, with JDK 17+, Maven, Python 3 and curl:

```sh
mvn -Dgat.tests.headless=true package
mvn dependency:build-classpath -Dmdep.outputFile=target/workflow-classpath.txt
python3 -m unittest discover -s native-inference/validation/workflows -p 'test_*.py' -v
python3 native-inference/validation/workflows/run_workflows.py \
  --root-classpath target/workflow-classpath.txt \
  --output target/workflow-results
```

Use a new empty output directory each time. `--only helpers registration calcium
opencl ganglia-contract ganglia-command ganglia-djl ganglia-jdll` selects suites; omitted suites are explicitly
listed as unrun. `--java` and `--javac` select the actual native JDK. The root
plugin's already-built classes and dependency classpath are used; the runner
does not build or change production targets. Dependencies in `dependencies.json`
are downloaded only from official URLs and verified by SHA-256 before use.
A cached checksum mismatch stops that suite rather than replacing evidence.

Each suite is compiled and executed in a fresh JVM. Native load failure cannot
erase another suite's result. The runner preserves actual exit codes, continues
independent suites, and exits nonzero after unexpected failures. `BLOCKED` or
`NOT_RUN` creates a **PARTIAL** result, never a complete workflow pass. Empty,
unknown or contradictory reports fail classification; six unit tests cover
these reporting rules.

## Coverage

| Suite | Actual paths and checks | Deliberate limits |
| --- | --- | --- |
| `helpers` | Hu/marker overlap thresholds; ganglion counts, areas and minimum-count filtering; 8-bit temporal-color pixels; UTF-8 CSV merge and overwrite refusal; counts CSV; calibrated 16-bit TIFF round-trip; multiplex naming | GAT methods called directly, not entire analysis/review dashboards. No broad-schema merge or arbitrary intensity-range guarantee |
| `registration` | Real MorphoLibJ algorithms and GAT size/border command wrappers; SIFT known affine shift with pixel checks; GAT ten-frame align/save/reopen path; StackReg/TurboReg via GAT helper; GAT multiplex SIFT correspondences with ROI Manager landmark checks | AWT-dependent commands explicitly blocked without a display. StackReg batch remains unimplemented. MOPS/block fallbacks and full multiplex export are not claimed |
| `calcium` | Actual CalciumAnalysis image opening, max projection, baseline selection, F/F0, ROI naming, measurement and save/reopen outputs on a known 100→200 signal | Controls only the test process's known baseline/projection/Multi Measure dialogs. Requires AWT. No full dashboard-navigation, zero-baseline or disabled automatic StarDist claim |
| `opencl` | OS/JOCL device enumeration, actual CLIJ transfers/kernels and GAT spatial helper paths, EDF invariant as individually reported | Missing hosted-runner OpenCL access is not proof that physical Apple GPUs fail. See each check's exact scope |
| `ganglia-contract` | Actual GAT RGB construction, DeepImageJ tensor conversion, and supplied JDLL RDF normalization; before/after double-scaling control | No engine invocation; a reached numerical input-contract test |
| `ganglia-command` | Actual GAT ganglia command, public image/model, DeepImageJ/JDLL inference, unique output retrieval, MorphoLibJ cleanup, binary/calibration/source-immutability checks and saved TIFF | Requires AWT. Optional painting and dashboard navigation excluded; scientific outputs intentionally differ from the old double-scaled bug |
| `ganglia-djl` | Exact PyTorch 2.0.0 CPU / DJL 0.22.1 model load and inference with declared RDF numerical preprocessing; finite output and shape | Isolates native engine/model viability. No full JDLL tiling or DeepImageJ external macro/UI claim |
| `ganglia-jdll` | Shipped JDLL resolver, unchanged model descriptor, BioimageIoModelJava model loading, RDF preprocessing, tiling, inference and postprocessing | Excludes external DeepImageJ ImageJ macros and full GAT RGB/review/measurement path. Supplied reference parity remains explicitly unresolved |

Neuron/subtype native TensorFlow inference, raw-label and outline comparisons
are covered by the separate cross-platform/corpus harnesses. Passing these
optional-workflow probes does not replace those tests or a complete native Fiji
installation test. Old `.ijm` macros are outside the new GATV2 inference adapter.

## Ganglia provenance and interpretation

The public model's weights and NPY fixtures come from the GAT update site at
`20250501124309`. All downloads are pinned in `dependencies.json`. Model SHA-256:
`1c59382b776acc2beed84bc2309e29f474aa69ff6356ec2248a04854d4feca7b`.

The descriptor says PyTorch `2.4.1+cpu`; shipped JDLL 0.6.2-SNAPSHOT maps that to
2.0.0, using DJL 0.22.1. Native CPU binaries are pinned separately for Linux and
macOS arm64. JDLL uses its own isolated engine adapter; the supplied engine JARs
remain in a validation-only directory. No old/new TensorFlow libraries are
combined on a classpath.

The direct DJL test casts the original channel-first uint8 data to float32,
applies the RDF gain, subtracts its three channel means, and divides by channel
standard deviations plus epsilon. The JDLL test instead supplies original NPY
data to JDLL's own preprocessing, tiling and postprocessing.

Both execution paths have run successfully on Linux and native ARM macOS CI. The
direct output and JDLL assembled output are 1024×1024; the supplied reference is
768×768. A simple 64-pixel halo crop leaves 896×896. The tests do not invent a
crop or modify metadata to force agreement. This mismatch does not establish
a TorchScript-version bug. Model/test assets, external macro/RDF scaling, and
complete tiling behavior need suitable controls. The external ImageJ macro also
divides by 255 but is not invoked by these engine tests or by the pinned
DeepImageJ executeOnImagePlus command path. The reached GAT double scaling and
its targeted fix are documented below; no third scaling is inferred.

## Performance and resource bounds

The runner records actual OS/architecture/Java, native Mac chip/model/core/memory
metadata when available, source revision, root-classpath JAR hashes and a
compiled-class manifest digest. Each subprocess records cold wall time, sampled
aggregate process-tree RSS, limits, return code and log. Ganglia reports separate
engine/model setup and inference timings; JDLL's run time includes preprocessing,
tiling and postprocessing. Compilation and downloads are separate from inference.

Default process-tree RSS ceiling is 3 GiB, Java heap 768 MiB, and native numerical
threads are capped at one. Per-suite deadlines are 120–300 seconds. Exceeding a
bound fails the test with that reason; it is not interpreted as an algorithm or
architecture failure. Parent and child RSS can count shared pages more than once.
These are controlled component timings, **not a benchmark of the user's M1**.
Hosted runner results must identify virtual hardware and exposed devices.

## Reports and expected failures

`run-summary.json` combines suite status and provenance. Each suite retains its
JSON checks, compilation/execution logs and small public/synthetic outputs.
Downloaded model/engine copies are removed from the result tree after execution;
checksum-verified downloads remain in the separate cache. No private image input
or upload is part of this runner.

Native-CI results must be published separately with their exact commit and run
link. Do not relabel local Linux evidence as Mac evidence. GUI tests invoke real
commands and inspect resulting pixels/measurements; display setup failures are
reported explicitly. The saved-output SIFT regression intentionally distinguishes
an aligned image created by the plugin from the image actually returned/saved by
GAT, so a dropped-result bug cannot be hidden by plugin-only success.

## Targeted workflow corrections and their evidence

The native command runs exposed two existing result-handling bugs, plus a reached
input-scaling bug. These fixes are not claims of biological validation:

- **SIFT:** the registration plugin returned a new aligned stack while GAT saved
  the input. The baseline saved TIFF was byte-identical to the input. The corrected
  native single save/reopen control reaches zero residual MSE on the synthetic
  translations. The two-channel batch fixture compares calibration to its reopened
  input TIFF: the TIFF rational representation of `0.75` is
  `0.7500001875000468` in both files, rather than a lost calibration value.
- **Calcium:** the native command control returned the raw three-plane source as
  `maxProj` (first pixel 100), although direct ImageJ MAX over the selected planes
  returned 200. GAT now obtains the actual `ZProjector` and `ImageCalculator` return
  objects, using the same MAX/AVG and Divide/create/32-bit/stack operations. Tests
  check selected ranges, `[1, 1, 2]` F/F0, temporal metadata, source immutability,
  and unchanged ImageJ `0/0 -> NaN` behavior. Native command rerun is required.
- **Ganglia input:** `ganglia-contract` invokes the real GAT RGB preparation,
  DeepImageJ `ImageJGui.convertToInputTensors`, and the supplied RDF's JDLL
  `Processing.preprocess`. GAT used to divide its float RGB pixels by 255 before
  the RDF applied its own `scale_linear(0.00392156862)` and ImageNet mean/std.
  A white Hu pixel therefore reached the model as `-2.100770`, instead of
  `+2.248898`. GAT now preserves byte-range values for the RDF to normalize once.
  Channel order (R=Hu, G=ganglia, B=Hu), display-range conversion, weights, RDF
  normalization metadata and threshold remain unchanged. **Correcting this bug
  changes scientific outputs; legacy-mask parity is not expected.**
- **Ganglia output:** the audited DeepImageJ command publishes its output on the
  Swing event queue. GAT now drains that publication event, then requires exactly
  one newly created, full-size single-channel image carrying this invocation's
  unique title. Missing, ambiguous, wrong-shape, or non-finite results fail rather
  than using an existing/current image.

The exact command path audited is `DeepImageJ Run` -> `Runner.load(true)` ->
`executeOnImagePlus` -> `ImageJGui.convertToInputTensors` -> `Runner.run` -> JDLL
RDF processing/model execution. In the pinned DeepImageJ 3.2.0-SNAPSHOT JAR,
`executeOnImagePlus` does not call the legacy external `im_preprocessing.ijm`
listed in `config.deepimagej.prediction`. This is a **two-scaling bug**, not a
claim that an external macro applied a third scaling. The pinned JAR comes from
the [official DeepImageJ update site](https://sites.imagej.net/DeepImageJ/plugins/DeepImageJ-3.2.0-SNAPSHOT.jar-20260708144022)
and its checksum is in `dependencies.json`.

`ganglia-command` is the complementary native-AWT test. It creates an isolated
Fiji fixture directory, installs no system software or user preferences, invokes
actual `PluginCalls.runDeepImageJForGanglia` with the public test image's Hu and
ganglia channels, and runs the DeepImageJ command/model plus MorphoLibJ cleanup.
It verifies result identity, binary geometry, calibration, unchanged source and
saved TIFF. Interactive painting and biological correctness remain separate.

For the earlier public raw input, native Mac and Linux PyTorch component outputs
have maximum absolute probability difference `1.7881393e-6` and no differing
threshold-0.6 mask pixels. The actual JDLL tiled/RDF-binarized outputs differ at
one of 1,048,576 pixels. These comparisons exclude GAT's corrected RGB preparation
and do not validate the differently sized supplied 768x768 reference.

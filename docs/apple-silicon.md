# Apple Silicon experimental backend

This branch adds a **real native inference path** for the GAT v2 neuron and
neuronal-subtype workflows. It targets the common macOS arm64 architecture used
by M-series Macs. It is an experimental test build, **not a claim of validated
M1–M5 compatibility**. The hardware and scientific-validation results must be
recorded below before this becomes a supported release.

**Requirements: macOS 14 Sonoma or newer, native arm64 Fiji, Java 11+ (Fiji's
bundled Java 21 recommended).** The shipped TensorFlow JNI library's Mach-O
deployment target is macOS 14.0; an M1 running macOS 11–13 cannot use this build.

## What changes

On an Apple Silicon Mac, GAT sends one local image channel to a separate Java
process with TensorFlow Java 1.2.0. That process reads the existing GAT SavedModel
ZIP, performs network inference, and returns probability and radial-distance
arrays. Fiji then runs the **existing StarDist 2D NMS command**, including the
same probability threshold, overlap threshold and two-pixel boundary exclusion.
GAT's existing filtering, rescaling, ROI review and output workflow follows.

The worker has its own classpath, outside Fiji's `jars` and `plugins` folders.
Modern TensorFlow is never added to the Fiji classpath alongside CSBDeep's old
TensorFlow classes. A worker failure is reported as an analysis error rather
than loading the incompatible TF1 native library inside Fiji. The startup
version check no longer calls `TensorFlow.version()` in the Fiji process.

Intel and other non-Apple-Silicon installations retain the existing Fiji
StarDist/CSBDeep backend by default. The preview plugin is built for Java 11+;
the old Java-8 Fiji distribution is not the target of this preview package.

The ganglia model remains the separate **DeepImageJ/PyTorch** workflow. CLIJ2
still uses OpenCL. This change does not replace, validate or accelerate those
engines. It uses TensorFlow CPU inference, not `tensorflow-metal` or Python.

The Template Matching alignment plugin currently distributes Intel-only macOS
OpenCV. This preview blocks that option on Apple Silicon before opening or
modifying the input. You can explicitly choose the separate SIFT option if it
fits your analysis, but no algorithm is substituted automatically. See the
workflow matrix for this and other unimplemented or unverified paths.

## Try the M1 test package

1. On **macOS 14 or newer**, keep your current Fiji installation unchanged and make a separate test
   installation of **native macOS arm64 Fiji Latest**, with its bundled Java 21,
   from [Fiji's official downloads](https://imagej.net/software/fiji/downloads).
   Intel Fiji running through Rosetta is deliberately rejected for this path.
2. In that test Fiji, install GAT's usual update sites and models as described
   in the repository README: StarDist, CSBDeep, DeepImageJ, clij, clij2,
   IJPB-plugins, PTBIOP, 3D ImageJ Suite, BIG-EPFL and Gut Analysis Toolbox.
   Complete the DeepImageJ engine initialization. The native neuron worker
   does not require choosing TF1 under Edit > Options > TensorFlow.
3. Quit Fiji. From the test installation's `plugins` folder, move the existing
   `GutAnalysisToolbox_-2.0.0.jar` to a backup folder outside Fiji. Do not leave
   both plugin versions installed. Extract the preview archive into the Fiji
   root directory containing `jars`, `plugins` and `models`.
4. Confirm this layout:

   ```text
   Fiji.app/
     plugins/GutAnalysisToolbox_-2.0.1-apple-silicon.1.jar
     gat-native-inference/gat-native-inference.jar
     gat-native-inference/lib/...
     models/2D_enteric_neuron_v4_1.zip
     models/2D_enteric_neuron_subtype_v4.zip
     models/2D_Ganglia_RGB_v3.bioimage.io.model/...
   ```

   Do not move worker dependencies into Fiji's `jars` folder. The preview does
   not automatically download or install software. Normal Fiji updates can
   replace the preview plugin; check/reapply the preview after an update.
5. Start Fiji and open Plugins > GutAnalysisToolbox > GATV2. The log should say
   `StarDist backend: isolated native TensorFlow worker (experimental)`.
   Use this GATV2 entry point. Old `.ijm` macros under the legacy GAT menu are
   not patched by this preview and still call the legacy TensorFlow backend.
6. First run the neuron workflow on a small, correctly calibrated sample crop
   (up to about 1024 × 1024 pixels after GAT rescaling),
   with ganglia and spatial analysis disabled. Verify the detected outlines and
   count against a trusted Intel/legacy result. Then try subtype detection,
   followed separately by optional ganglia and spatial workflows.

Use copies of research images for initial testing. Input pixels and intermediate
files stay on the same computer and are removed after inference; no image data
is uploaded. A crash or interrupted process can leave temporary files in the
operating system's temporary directory.

## Build from source

Use JDK 17 or newer and Maven 3.9+. Build the Fiji plugin and the independent
worker separately:

```sh
mvn clean package
mvn -f native-inference/pom.xml clean package -Dtensorflow.platform=macosx-arm64
```

See `native-inference/README.md` for worker packaging and its versioned binary
protocol. For Linux validation, build the worker with
`-Dtensorflow.platform=linux-x86_64`. A Mac-classifier bundle can be assembled on
Linux, but that does not constitute running it on macOS.

The root GUI tests normally need a display. On Linux CI use `xvfb-run -a mvn
test`. The protocol/backend unit tests can be run without a display:

```sh
mvn -Dgat.tests.headless=true -Dtest=InferenceBackendTest,NativeInferenceClientTest test
```

## Configuration and diagnostics

Defaults should work with the package above. Advanced Java system properties:

| Property | Default | Purpose |
| --- | --- | --- |
| `gat.stardist.backend` | `auto` | `native` explicitly selects the worker for cross-platform validation; `legacy` is refused on Apple Silicon |
| `gat.inference.directory` | `<Fiji>/gat-native-inference` | Location of the worker JAR and its sibling `lib` folder |
| `gat.inference.timeoutSeconds` | `900` | Worker timeout, 1–86400 seconds |

Do not install pip/conda TensorFlow to repair this workflow: that is a different
runtime. The worker launches the same Java installation that runs Fiji, so a
native arm64 Java 11+ is essential on Apple Silicon.

On a failure, retain the Fiji Log/Console message and report:

- Mac chip and macOS version
- Fiji's Java version and `os.arch` (expected `aarch64` or `arm64`)
- Preview version and backend log line
- Model filename, image dimensions, pixel calibration and chosen thresholds
- Whether a small neuron-only test succeeds before ganglia/spatial options
- Worker exit code and diagnostic text, if shown

## Scientific equivalence and limits

The worker reproduces the legacy CSBDeep global 1st/99.8th-percentile
normalization, nonnegative normalized values, symmetric mirrored padding and
its 64-pixel tiling rules. It retains legacy edge behavior rather than silently
"correcting" it. Probability and distance channels are returned at input
resolution and processed with the original Fiji StarDist NMS.

Only a single 2D grayscale channel and the supported one-input/one-output
float32 NHWC SavedModel signature are accepted. Unsupported signatures/shapes,
nonfinite data, incomplete output and worker failure stop analysis. Custom
models are not presumed compatible merely because they are ZIP files.

This preview bounds each tensor to 268,435,456 float values (about 1 GiB).
Both supplied GAT models have 97 output channels, so the full prediction is
limited to roughly 2.77 million spatial pixels, **including padded dimensions**.
A conservative square limit is about 1600 × 1600 pixels after rescaling;
2048 × 2048 inputs do not fit this preview limit. Start with 1024-pixel crops
on an M1. Increasing the tile count reduces per-tile inference memory but does
not lift the full-output limit. Use calibrated crops and validate edge effects;
do not silently resize images or compare cropped counts with whole-image counts.
Available RAM may impose a lower limit because Fiji, TensorFlow and temporary
arrays also consume memory.

TensorFlow versions and CPU kernels can still produce small numerical
differences. Near a probability or overlap threshold, these can change an
individual detection. Network-array agreement and label/count agreement on
representative images must be recorded separately. No silent tolerance or
automatic threshold change is applied to make results agree.

### Validation status

- Linux x86-64/JDK 17: root plugin compiles and packages; all 30 plugin tests
  passed. All dependency-enforcer rules passed.
- Isolated worker: 16 unit tests passed, including normalization/tiling boundary
  cases and comparison of each tile pixel with ImgLib2's actual mirror views.
- Both original GAT model ZIPs load and infer using TensorFlow 2.21 through
  TensorFlow Java 1.2.0, without conversion or retraining.
- Independent TF1.15 versus TF2.21 comparison on the public 175 × 175 Hu crop:
  neuron model with one tile produced 39 labels; subtype model with four tiles
  produced 2 labels. Both final label rasters were pixel-identical (0 of 30,625
  pixels differed), using unchanged StarDist 0.3.0 NMS at probability 0.5,
  overlap 0.3 and boundary 2. Maximum raw probability differences were
  1.37e-6/1.52e-6; distance differences 2.38e-5/2.67e-5, respectively.
  The subtype model used the same Hu crop, so this is technical compatibility
  evidence, not representative validation on a subtype-stained sample.
- Real ImageJ batch-mode registration and actual subprocess timeout/noisy-output
  cleanup were independently checked. Full Fiji GUI integration was not run.
- The actual Java client launched the Linux worker with the public crop and
  received all 97 channel planes, identical to direct worker invocation. This
  tests the process boundary and protocol, separately from GUI command routing.
- The Mac package contains three ARM64 dylibs. The JNI dylib requires macOS
  14.0; the TensorFlow framework/core dylibs declare macOS 12.0. Packaging and
  inspection were performed on Linux, not a Mac.
- Native M1 execution, M2–M5 hardware, full-size images and optional
  ganglia/OpenCL/calcium/registration workflows remain unverified unless
  separately recorded in the workflow matrix or CI results.

Passing unit tests or cross-packaging arm64 libraries is not an end-to-end
M1 validation. See [the full workflow matrix](apple-silicon-workflow-matrix.md)
for the scope of the preview and remaining hardware checks.

A broader comparison across the author's public held-out data is in progress.
The initial crop results above do not yet establish consistency across donors,
labs, stains or image sizes. Check the validation results for the tested corpus
before drawing conclusions about a new dataset.

## Future upstream integration

The independent worker accepts a versioned image/model protocol and has no GAT
UI or Fiji dependencies. The Fiji adapter owns platform selection and calls
StarDist's existing NMS command. These boundaries allow a later reusable
StarDist/CSBDeep backend integration without maintaining a second segmentation
algorithm. This preview does not fork or replace StarDist itself.

## References

- [Legacy GAT v2 baseline](https://github.com/pr4deepr/GutAnalysisToolbox/tree/1870d9e16e16fd6daeac0bd05122e851029ddedc)
- [TensorFlow Java support and version matrix](https://github.com/tensorflow/java)
- [CSBDeep Fiji normalization and tiling](https://github.com/CSBDeep/CSBDeep_fiji)
- [Fiji StarDist NMS implementation](https://github.com/stardist/stardist-imagej)

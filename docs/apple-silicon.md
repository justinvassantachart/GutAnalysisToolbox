# Experimental Apple Silicon GAT v2

This fork targets **native arm64 Fiji on macOS 14 Sonoma or newer, Java 11+**
(Fiji's bundled Java 21 recommended). It is a test build. The current native
TensorFlow JNI requires macOS 14; the chip name alone is insufficient.

Use **Plugins → GutAnalysisToolbox → GATV2**. Legacy `.ijm` menus and QuPath are
separate workflows and are not redirected by this plugin.

## What has actually run

On one hosted **Apple M1 (Virtual)** runner, macOS 14.8.9 and native Java
21.0.12.1, the unchanged upstream `gat_v2` source
`1870d9e16e16fd6daeac0bd05122e851029ddedc` and fork
`69feedb86f4c4fd54d6ef91f8ba497d966d5c845` were built and exercised with the same
inputs, plugin versions and host. The actual fork StarDist call returned 39
neurons on the public 175×175 Hu image; its Template Matching call returned
exactly the expected translated pixels. The original calls failed to return
those results. [Paired run and preserved diagnostics](https://github.com/simplecoreorg-cyber/GutAnalysisToolbox/actions/runs/37357196889).

The original StarDist failure was first a Java 21 classloader cast in the old
ImageJ TensorFlow loader, **before JNI loading**. Original Template Matching
left the shifted input unchanged. The installed old native binaries were
independently identified as x86-64, but these particular command failures are
not proof that architecture was their only cause. The original source remained
unchanged and no modern TensorFlow classes entered either Fiji parent JVM.

Native Mac tests also ran the real ganglia DeepImageJ command, morphology,
SIFT single/batch saved-output checks, StackReg/TurboReg helpers and multiplex
SIFT landmarks. These are individually bounded command/component tests, not
an installation or full interactive GAT dashboard certification. **The paired
job is not an overall pass:** its calcium dialog control is being corrected
and repeated. OpenCL kernels cannot run on the hosted virtual Mac because no
OpenCL device is exposed. See the [workflow matrix](apple-silicon-workflow-matrix.md)
for every remaining limit.

## Changes and scientific implications

### Neuron and subtype inference

A separate local JVM uses **TensorFlow Java 1.2.0 / TensorFlow 2.21 CPU** with
GAT's existing SavedModel ZIPs. It preserves CSBDeep 0.6.0 normalization and
tiling, then returns probability/distance arrays to Fiji's unchanged StarDist
2D NMS. GAT's original thresholds, boundary exclusion, ROI filtering and
rescaling remain in use. There is no Python, pip, `tensorflow-metal`, or Metal
backend in this implementation.

The worker stays outside Fiji's `jars` and `plugins` classpath. Intel and other
non-Apple-Silicon installations keep their legacy StarDist path by default.
A child-process failure is reported without loading old TF1 JNI into native
Fiji. Startup preflight does not call `TensorFlow.version()`.

[All 371 paired Linux regression cases and evidence](../native-inference/validation/corpus/REGRESSION_REPORT.md)
have the same counts (28,958 detections), but masks are not universally exact:
359 raw label rasters match, three more differ only in IDs, eight differ at one
boundary pixel, and one near-tied cell changes center/outline (affected-cell
IoU 0.8979). Tiny probability changes can change NMS ordering. Subpixel outlines
also differ slightly in many otherwise identical raster cases. Thresholds and
production numerical settings were not adjusted to hide these differences.
This is runtime consistency evidence, not biological ground-truth validation.
Native Mac compact fixtures pass; the complete 371-case corpus ran on Linux.

### Template Matching

A second isolated worker ports the author's original matching code to
JavaCV/JavaCPP 1.5.12 and native OpenCV 4.11.0. It preserves method 5, the 70%
reference ROI, whole-image search, integer peak selection and ImageJ translation.
It does not substitute SIFT. Source, GPL license and build POM accompany the
worker. Keep this module outside Fiji's normal classpath.

The adapter supports 8/16-bit stacks, up to 67,108,864 total pixels and 10,000
frames, with explicit validation before modifying the source. Linux tests
include 300 output frames across synthetic references 1/2/3 and the public
142-frame calcium movie with references 1/71. The actual native Mac GAT adapter
passed the paired synthetic control; interactive single/batch review remains.

### Existing result-handling corrections

- SIFT returns a new aligned stack. GAT now saves that returned result and
  preserves timing/calibration instead of silently saving its original input
- Motion CSVs contain only verified algorithm-owned Template Matching shifts
  with real frame IDs. Unavailable SIFT transforms are not fabricated as zeros.
  A combined SIFT-plus-Template-Matching CSV describes the refinement only
- Ganglia RGB input retains byte-range float values so the shipped RDF applies
  its `1/255` normalization once. This fixes reached double normalization and
  **intentionally changes scientific outputs** compared with the old GAT path.
  The model weights, RDF, channel order and threshold are unchanged
- Ganglia output selection requires the newly produced, correctly shaped image;
  an unrelated current image is not accepted as a successful result
- Calcium projection/division consume ImageJ's returned objects directly.
  Numeric controls pass; the full native ROI/measurement dialog test remains
  pending a reliable accepted-dialog rerun, so no blanket calcium pass is claimed

## Install an experimental overlay

For a computer with no Fiji or development tools, use the separate
[M1 computer-test handoff](M1-CHATGPT-HANDOFF.md). It covers official Fiji,
update sites, models, engine initialization, paired installations and reporting.
Do not substitute preview 1 for a newer workflow-fix package: **preview 1 is
immutable and contains only the earlier neuron backend**, not these later fixes.
Use an asset only when its `BUILD_INFO.json`, source commit and checksum match
the handoff being followed.

1. Install a separate native arm64 Fiji with bundled Java on macOS 14+.
   Preserve any working installation and use copies of images
2. Install the required update sites/models from the repository README and
   finish DeepImageJ engine initialization. Record all exact versions
3. Quit Fiji. Identify its **ImageJ data root** containing `jars`, `plugins`
   and `models`. Current Fiji Latest places these in outer `Fiji/`, beside
   inner `Fiji.app/`; older bundles may put them in `Fiji.app/`. Confirm with
   `IJ.getDirectory("imagej")` rather than assuming the app is the data root
4. Move the existing GAT JAR to a backup outside Fiji. Leave only one GAT JAR.
   Extract the verified overlay into that data root:

   ```text
   <ImageJ data root>/
     plugins/GutAnalysisToolbox_-<preview-version>.jar
     gat-native-inference/gat-native-inference.jar
     gat-native-inference/lib/...
     gat-native-alignment/gat-native-alignment.jar
     gat-native-alignment/lib/...
     gat-native-alignment/source/...
     models/2D_enteric_neuron_v4_1.zip
     models/2D_enteric_neuron_subtype_v4.zip
     models/2D_Ganglia_RGB_v3.bioimage.io.model/...
   ```

5. Never move worker libraries into Fiji's `jars` or `plugins`. Nothing is
   auto-downloaded or executed at installation. Normal updater operations can
   replace the preview GAT JAR; verify versions after updates
6. Start GATV2 and first test a small, calibrated neuron crop with optional
   ganglia/spatial features off. Then test each additional workflow separately

No image upload is performed by the workers. Their local request directories
are cleaned on normal completion and handled child failure/timeout. An abrupt
parent JVM/OS crash can leave temporary files; inspect before removing them.

## Memory, performance and backend controls

Both workers use CPU. No paired GPU implementation has been benchmarked, so
there is no justified CPU-to-GPU speed multiplier. Hosted virtual-Mac cold
process timings are not predictions of physical M1 performance.

The neuron protocol caps full output at 268,435,456 floats. The supplied models
have 97 output channels, so the padded merged image must fit about 2.77 million
spatial pixels. Start with ≤1024×1024 crops; roughly 1600×1600 is a conservative
square bound after padding. A 2048×2048 result is too large. Increasing tiles
does not remove this full-output cap. Use disclosed crops/rescaling, not silent
loss of the original image area.

Optional Java properties: `gat.stardist.backend=auto|native|legacy`,
`gat.inference.directory`, `gat.inference.timeoutSeconds`,
`gat.alignment.backend=auto|native|legacy`, `gat.alignment.directory`,
`gat.alignment.timeoutSeconds`. Both children use Fiji's current Java executable. Consult the actual client
source for defaults. Native arm64 refuses forced legacy native-library paths;
Intel remains legacy by default. Do not use overrides to mix Java architectures.

## Build and package

Requires a JDK and Maven; installation of a prebuilt overlay does not.

```sh
mvn -B -ntp -Dgat.tests.headless=true clean package
mvn -B -ntp -f native-inference/pom.xml clean package
mvn -B -ntp -f native-alignment/pom.xml clean package
python3 -m unittest discover -s scripts/tests -p 'test_*.py' -v
python3 scripts/package-apple-silicon-preview.py --output ../preview-artifacts
```

Both worker POMs default to macOS arm64 packaging. Linux execution tests use
`-Dtensorflow.platform=linux-x86_64` and `-Dopencv.platform=linux-x86_64`
respectively; such bundles cannot be packaged as the Mac release. The packager
rejects mixed classifiers, incomplete corresponding source, unsafe archives and
unclean source checkouts by default. A successful build is not a runtime test.

## Long-term architecture

This GAT adapter is a focused compatibility path. A reusable inference backend
in CSBDeep/StarDist, with their normal public API and model/tiling parity tests,
would be a cleaner shared long-term solution. The isolated process boundary
could remain useful. This fork does not claim upstream acceptance, and no
upstream pull request has been submitted.

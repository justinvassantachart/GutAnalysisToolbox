# Experimental Apple Silicon GAT v2: hardening preview 4

This fork targets **native arm64 Fiji on macOS 14 Sonoma or newer, Java 11+**
(Fiji's bundled Java 21 recommended). It is a test build. The current native
TensorFlow JNI requires macOS 14; the chip name alone is insufficient.

Use **Plugins → GutAnalysisToolbox → GATV2**. Legacy `.ijm` menus and QuPath are
separate workflows and are not redirected by this plugin.

## What has actually run

This guide accompanies **2.0.1-apple-silicon.4**. Use the matching
[preview 4 release](https://github.com/justinvassantachart/GutAnalysisToolbox/releases/tag/apple-silicon-preview-4),
verify its checksum and `BUILD_INFO.json`, and follow `PREVIEW_4_SETUP.md` plus
`M1-CHATGPT-HANDOFF-v6.md`. If the release is not listed, it is not yet published.
The release adds Intel missing-OID CPU detection and calcium input/load/cancel
safeguards to the retained preview 3 multiplex repair. Calcium accepts only
single-channel grayscale stacks with one time axis (ordinary C1/Zn/T1 stacks
interpreted as time, or C1/Z1/Tn series); split channels and choose
any scientific Z preprocessing explicitly. RGB, multiple channels and combined
Z/T are rejected. Numerical projection/F/F0 remains ImageJ's operation.

[6 October hardening verification](https://github.com/justinvassantachart/GutAnalysisToolbox/blob/apple-silicon-preview-4/docs/validation/fork-hardening-2026-10-06.md)
records 97 local Java tests and fresh hosted native-Mac command/service checks.
Release-specific build/paired-run outcomes are linked on the release page.
Older scientific/fresh-Fiji reports below retain their original source and
coverage; they are not fresh full-corpus runs of preview 4.
**Preview 2 lacks the multiplex correction and must not be used for quantitative
multiplex-registration exports.** Older release bytes are preserved.

Same-host native M1 Virtual comparisons on Sonoma 14.8.9 and Sequoia 15.7.9
confirm fork StarDist and Template Matching output success, original native
failures, and fork SIFT helper/save/batch fixes. The original TF1 error dialog
records no library for `darwin/aarch64`. Early diagnostic runs timed out in
that dialog; the completed comparison below records the untouched failure
dialog and terminates only its isolated test process. The actual official-Fiji launcher separately reproduces
the earlier Java21 loader cast before JNI and explicit old OpenCV JNI errors.
These are distinct observed failure paths, not an assumption of one cause.

**Both original and fork calcium pass** accepted-dialog projection, F/F0
`[1,1,2]`, ROI measurement and CSV/ROI export controls on both OS versions.
The earlier ambiguous calcium control was resolved; no old numerical defect is
claimed. Both ganglia commands run, with intentional output changes from the
RDF input-scaling correction described below. [Qualified paired evidence](https://github.com/justinvassantachart/GutAnalysisToolbox/blob/f5b814b4a8f784246d60df88032cee037ca8fd29/native-inference/validation/baseline/results/mac-sequoia-fe5fd7b/REPORT.md).

The [complete bounded official-Fiji install](https://github.com/justinvassantachart/GutAnalysisToolbox/blob/f5b814b4a8f784246d60df88032cee037ca8fd29/validation/fiji-install/results/mac-accepted-26298b7/REPORT.md)
now passes real engine installation/model inference, both dashboards, fork
neuron/alignment and both ganglia commands. All 854 shared model/dependency/engine
paths match exactly between the two copies. The earlier missing-engine and
boxed-parameter setup failures remain preserved in their historical packets.
The later [saved ganglia-mask evidence](https://github.com/justinvassantachart/GutAnalysisToolbox/blob/f5b814b4a8f784246d60df88032cee037ca8fd29/validation/fiji-install/results/mac-mask-retention-5e2e0f4/REPORT.md)
retains both actual TIFFs and independent pixel/calibration checks. Physical
OpenCL/GPU and complete interactive workflows remain open. See the
[workflow matrix](apple-silicon-workflow-matrix.md).

The [completed same-host comparison](https://github.com/justinvassantachart/GutAnalysisToolbox/blob/f5b814b4a8f784246d60df88032cee037ca8fd29/native-inference/validation/baseline/results/mac-live-dialog-ee2907e/REPORT.md)
is green: a strictly verified observer records the unchanged original's visible,
unanswered TensorFlow error dialog and ends only that isolated process. All
three live observer controls ran without skips; no dialog is dismissed and no
installer is entered. The original still fails while fork output gates pass.

The [optional native JPEG-XR package](https://github.com/justinvassantachart/GutAnalysisToolbox/blob/f5b814b4a8f784246d60df88032cee037ca8fd29/native-inference/validation/jpeg-xr/results/mac-6996dd5/REPORT.md)
now passes its final resource-JAR decode, exact source/license checks and all 13
golden fixtures. It is a separate release asset with complete source, not part
of the core ZIP. Full Fiji importer/container/metadata testing remains required.

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

[All 371 paired Linux regression cases and evidence](https://github.com/justinvassantachart/GutAnalysisToolbox/blob/f5b814b4a8f784246d60df88032cee037ca8fd29/native-inference/validation/corpus/REGRESSION_REPORT.md)
have the same counts (28,958 detections), but masks are not universally exact:
359 raw label rasters match, three more differ only in IDs, eight differ at one
boundary pixel, and one near-tied cell changes center/outline (affected-cell
IoU 0.8979). Tiny probability changes can change NMS ordering. Subpixel outlines
also differ slightly in many otherwise identical raster cases. Thresholds and
production numerical settings were not adjusted to hide these differences.
This is runtime consistency evidence, not biological ground-truth validation.

A [native Mac replay of the selected moved-center outlier](https://github.com/justinvassantachart/GutAnalysisToolbox/blob/f5b814b4a8f784246d60df88032cee037ca8fd29/native-inference/validation/moved-center/results/mac-c6e2011/REPORT.md)
matched the legacy Linux raster/centers exactly, including the affected cell;
four other subpixel vertices still differed by about 0.01 px. This is one
deliberately selected fixture, not a native replay of the entire corpus.
The [native 300-frame Template Matching evidence](https://github.com/justinvassantachart/GutAnalysisToolbox/blob/f5b814b4a8f784246d60df88032cee037ca8fd29/native-inference/validation/template-matching/results/mac-ee2907e/REPORT.md)
also preserves exact shifts, aligned pixels and all motion CSV rows for both
the port and actual GAT adapter.
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
passed the paired synthetic control and all six/300-frame port and actual-adapter comparisons on native Mac; interactive single/batch review remains.

### Multiplex registration

The [unchanged full-service native Mac comparison](https://github.com/justinvassantachart/GutAnalysisToolbox/blob/f5b814b4a8f784246d60df88032cee037ca8fd29/native-inference/validation/multiplex-full/results/mac-ab046cb/README.md)
reproduced and corrected pre-existing landmark ownership, current-image and
saved-calibration defects. The two runs use the same 18 input files, five
harness sources and 97 runtime JAR identities. Registration parameters and
acceptance assertions were unchanged.

Both SIFT and forced-MOPS routes now pass all nine full-service checks. Saved
SIFT later-round marker interiors match their references exactly. MOPS residual
MSE is 0.180–0.360, compared with 2,751–4,313 before correction; saved landmark
errors are at most about 0.0392 px. Both aligned and QC stacks preserve the
reopened reference's physical calibration and frame interval. Independent
reopening of the actual TIFFs and ROI archives reproduces these measurements.

This is bounded synthetic native service/command acceptance. It does not prove
biological registration quality, natural SIFT-failure fallback, the unavailable
Block Matching command, computation-time cancellation or every interactive UI
mode. These Java result-handling defects also existed before the fork; they are
not evidence that ARM SIFT or MOPS numerics themselves were broken.

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
  This is result-ownership hardening: both original and fork pass the accepted
  native ROI/measurement/export control. Full GUI and edge-case testing remains

## Install an experimental overlay

For a computer with no Fiji or development tools, use the clean-Mac handoff
asset beside the matching package on the [release page](https://github.com/justinvassantachart/GutAnalysisToolbox/releases).
It covers official Fiji,
update sites, models, engine initialization, paired installations and reporting.
Do not substitute preview 1 for a newer workflow-fix package: **preview 1 is
immutable and contains only the earlier neuron backend**, not these later fixes.
Use an asset only when its `BUILD_INFO.json`, source commit and checksum match
the handoff being followed.

1. Install a separate native arm64 Fiji with bundled Java on macOS 14+.
   Preserve any working installation and use copies of images
2. Install the required update sites/models from the [repository README](https://github.com/justinvassantachart/GutAnalysisToolbox/blob/f5b814b4a8f784246d60df88032cee037ca8fd29/README.md) and
   finish DeepImageJ engine initialization. Record all exact versions
3. Quit Fiji. Identify its **ImageJ data root** containing `jars`, `plugins`
   and `models`. Current Fiji Latest places these in outer `Fiji/`, beside
   inner `Fiji.app/`; older bundles may put them in `Fiji.app/`. Confirm with
   `IJ.getDirectory("imagej")` rather than assuming the app is the data root
4. Quit Fiji and move existing GAT JARs and BOTH old worker directories to a
   dated backup outside Fiji. Install both complete new worker directories; do
   not merge their `lib` contents with an older version. Leave only one GAT JAR.
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

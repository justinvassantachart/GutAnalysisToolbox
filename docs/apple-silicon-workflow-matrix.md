# Apple Silicon workflow audit

Audit date: **2026-10-05**. Scope: the Java **GATV2** plugin based on upstream
`gat_v2` commit `1870d9e16e16fd6daeac0bd05122e851029ddedc`, plus this branch's
experimental inference adapter. This is a coverage report, not a supported
M1–M5 release certification. **No workflow has yet been run on a physical Mac
in this audit.** Linux tests and the existence of arm64 libraries do not prove
macOS execution or scientific equivalence.

Follow the [installation and validation guide](apple-silicon.md) for the exact
supported preview configuration, model/input limits, and diagnostic reporting.
The neuron worker does not change DeepImageJ, OpenCL, registration, or data
analysis algorithms. It provides no Metal acceleration.

## Reading the status

- **Component tested (Linux):** the named code actually ran on Linux x86-64;
  this is narrower than a complete Fiji workflow or native Mac test
- **Audited; Mac untested:** source/dependency paths were inspected, but the
  native Mac workflow has not run
- **Unsupported as supplied:** a concrete missing implementation or incompatible
  distributed native dependency was identified; this is not merely an absent test

## Workflow inventory

| GATV2 workflow or option | Execution path | Evidence and current Apple Silicon status |
| --- | --- | --- |
| Hu neuron detection, MIP, no optional ganglia/spatial analysis | Isolated TensorFlow CPU worker → existing StarDist NMS → Java/ImageJ ROI processing | **Component tested (Linux)** with the real supplied neuron model, including legacy-vs-worker array and NMS comparisons. Native Mac execution and complete review/export workflow remain untested |
| Neuron subtypes, with Hu gating | Same worker for each subtype; `LabelOps.neuronsPositiveByOverlap` does pixel-based gating in Java | **Component tested (Linux)** for the real subtype model and synthetic overlap gating. Full multichannel, combinations, ROI review, and output run on a Mac remain untested |
| Neuron subtypes without Hu | Same worker, separate per-marker masks/combinations | Shared inference path inspected; **audited; Mac untested** end to end. Hu-gating tests do not prove the no-Hu combination workflow |
| Custom/imported ROIs, manual editing, border/size filters, label conversion | ImageJ ROI Manager, MorphoLibJ, PTBIOP | **Audited; Mac untested**. These operations have no GAT-specific native inference requirement, but still need their Fiji commands and UI |
| Ganglia from Hu expansion, imported ROIs, or manual drawing | ImageJ morphology and label/ROI helpers; no PyTorch for these modes | **Component tested (Linux)** for calibrated counts/areas using real small label images. Existing unit tests mock several plugin calls. Complete segmentation/review workflow remains Mac untested |
| Ganglia from the RGB deep-learning model | DeepImageJ → JDLL → TorchScript/PyTorch; model declared as `2.4.1+cpu` | **Audited; Mac untested**, with an important engine-version risk: shipped JDLL maps this to PyTorch 2.0.0. A native arm64 CPU engine is listed, but model loading, operators, preprocessing, tiling, and output parity are not proven |
| Neurons per ganglion, areas, minimum-count filtering | GAT Java loops on label maps, calibrated ImageJ pixels | **Component tested (Linux)** for counts and areas; full Mac workflow untested. Correct segmentation remains a prerequisite |
| Image import (Bio-Formats) | Distributed Bio-Formats 8.5.0; actual reader/codec depends on format | **Audited; Mac untested** for representative microscopy inputs. JPEG-XR-compressed files have a confirmed incompatible supplied native decoder; ordinary TIFF/LIF do not automatically take that path. HDF5 arm64 native code is present |
| Maximum-intensity projection (MIP) | ImageJ CPU projection | **Audited; Mac untested** in a complete GAT run. Select this instead of EDF for the initial neuron-only preview test |
| Extended depth of focus (EDF) | CLIJ2 variance fusion, OpenCL native binding/device | **Audited; Mac untested**. Requires actual OpenCL kernel and transfer tests; a detected GPU name is insufficient. No CPU fallback is implemented |
| Single-cell-type spatial analysis | CLIJ2 label dilation and touching-neighbor map | **Audited; Mac untested**. Requires OpenCL and numerical reference checks. No CPU fallback is implemented |
| Two-cell-type spatial analysis / overlap maps | CLIJ2 dilation, optional ganglia-mask multiplication, overlap counts, intensity replacement | **Audited; Mac untested**. This is distinct from the Java-only Hu/subtype overlap gate above |
| Probability, rescaling, ganglia-expansion tuning tools | Reuse neuron/subtype segmentation and ImageJ morphology; optional EDF | Inference routing inspected; **audited; Mac untested** as tuning/UI workflows. EDF carries its separate OpenCL requirement |
| Calcium alignment with SIFT | Fiji's “Linear Stack Alignment with SIFT”, mpicbg Java algorithms | **Audited; Mac untested**. SIFT can be explicitly selected with Template Matching disabled; it is a different registration method, not an equivalent silent replacement |
| Calcium alignment with Template Matching | “Align slices in stack...” → JavaCV/OpenCV native libraries | **Unsupported with the audited update-site distribution on native arm64**: its macOS OpenCV native JAR is x86-64 only. The preview now rejects this option before opening/modifying inputs in single/batch alignment, and guards direct calls |
| StackReg/TurboReg | Java registration plugins from BIG-EPFL | Plugin/platform route inspected; **Mac untested**. A single-image helper exists, but the current single-run method does not call it. **Batch StackReg is explicitly unimplemented** and throws on every platform |
| Calcium F/F0, ROI intensity measurement, trace and ROI export | ImageJ projections, divide, ROI Manager Multi Measure, file output | **Audited; Mac untested** end to end. Existing calcium tests cover file-open behavior, not the trace calculation. Use imported or manually drawn ROIs |
| Calcium automatic StarDist ROI generation | `CalciumAnalysis.runStarDist` | **Unsupported in the audited baseline on every platform**: the method is a disabled stub. A checked UI option is not evidence that ROIs were generated |
| Temporal color coding | Java/ImageJ pixels, LUT, optional projection/scale | **Component tested (Linux)** for a two-frame 8-bit input and scale creation. Native Mac UI, frame-range variations, projection, and scientific output review remain untested |
| Multiplex registration across rounds | SIFT → MOPS → block-matching correspondences; landmark transformation | **Audited; Mac untested**. Does not use the OpenCV Template Matching alignment plugin. Requires a full landmark/channel-order/transformation/output check |
| CSV merging | Java NIO/UTF-8, experiment-label strategy | **Component tested (Linux)** for two small input files and overwrite refusal. Mac UI, larger trees, mixed headers, quoted values, and repeated operations remain untested |
| Counts/summary CSV, TIFF labels, flattened overlays, ROI ZIP export | Java/ImageJ file output | **Component tested (Linux)** for basic counts CSV and lossless 16-bit label TIFF round-trip. ROI ZIP, overlays, all multichannel summaries, and Mac path behavior remain untested |
| Legacy update-site `.ijm` workflows and QuPath | Separate scripts/application | **Outside this preview's coverage.** The GATV2 Java adapter does not intercept arbitrary direct StarDist calls in older scripts or change QuPath |

Local entrypoints: [pipelines](../src/main/java/Features/AnalyseWorkflows/),
[plugin wrappers](../src/main/java/Features/Core/PluginCalls.java),
[analysis](../src/main/java/Analysis/),
[alignment](../src/main/java/Features/Tools/AlignStack.java),
[batch alignment](../src/main/java/Features/Tools/AlignStackBatch.java),
[multiplex](../src/main/java/services/multiplex/),
[merge](../src/main/java/services/merge/), and
[export](../src/main/java/Features/Tools/OutputIO.java).

## Native dependency findings

### Ganglia: arm64 engine exists, exact model runtime does not

The [distributed model descriptor](https://sites.imagej.net/GutAnalysisToolbox/models/2D_Ganglia_RGB_v3.bioimage.io.model/rdf.yaml-20250501124309)
identifies TorchScript weights created with PyTorch `2.4.1+cpu`, a three-channel
1024-pixel input, preprocessing, output halo, and binarization. These settings
must be preserved during validation.

The [DeepImageJ update-site manifest](https://sites.imagej.net/DeepImageJ/db.xml.gz)
currently supplies `dl-modelrunner-0.6.2-SNAPSHOT.jar`, timestamp
`20251011144925`. Its embedded engine catalog and the audited
[current JDLL catalog](https://github.com/bioimage-io/JDLL/blob/main/src/main/resources/availableDLVersions.json)
list native `macosx-arm64` CPU PyTorch 2.0.0 using DJL 0.22.1; neither lists an
exact PyTorch 2.4.1 engine. Running the shipped JDLL version resolver on Linux
confirmed `2.4.1+cpu` → `2.0.0`. The resolver's
[major-version fallback](https://github.com/bioimage-io/JDLL/blob/main/src/main/java/io/bioimage/modelrunner/versionmanagement/SupportedVersions.java)
is engine selection, not proof that a newer TorchScript model loads in an older
runtime or produces equivalent masks. Keep this workflow experimental until
its supplied test input/output and a representative image pass with the actual
selected engine on arm64.

An `engines` directory or installed menu command alone does not prove model
compatibility. Record the engine directory/version actually selected by
DeepImageJ. Do not edit the model's declared version merely to suppress an
error, and do not mix replacement native JARs into Fiji ad hoc.

### OpenCL: check execution, not only installation

The [CLIJ update-site manifest](https://sites.imagej.net/clij/db.xml.gz) supplies
JOCL 2.0.5. The inspected official Maven JAR contains
`libJOCL_2_0_5-apple-arm64.dylib`; therefore the binding is not intrinsically
Intel-only. GAT still calls [CLIJ2 OpenCL operations](https://clij.github.io/clij2-docs/api_intro),
and this cloud audit had no OpenCL device to validate them.

The dependency chain also includes BridJ 0.7.0, whose inspected macOS native
library is x86-64. Standard 8/16/32-bit ImagePlus transfer code uses NIO buffers,
but legacy/off-heap interop paths can reference BridJ. This does not establish
that every GAT CLIJ call fails; it does mean the complete dependency chain must
be exercised, including push/pull and kernels. Preserve exact JAR versions in
Mac test reports. No GPU speed or M-series-wide support claim follows from
finding the arm64 JOCL binary.

### Template Matching: an actual native architecture mismatch

The [author's plugin documentation](https://sites.google.com/site/qingzongtseng/template-matching-ij-plugin)
identifies JavaCV/OpenCV as the implementation. The audited
[Template_Matching update-site manifest](https://sites.imagej.net/Template_Matching/db.xml.gz)
provides `jars/macosx/opencv-macosx-x86_64.jar`, timestamp `20190625083034`, and
no macOS arm64 OpenCV artifact. The distributed plugin alone therefore cannot
supply the native library for an arm64 JVM.

Both single and batch alignment reach `AlignStack.alignTemplateMatching`.
This preview now rejects Template Matching on Apple Silicon before opening or
changing an image; the shared direct-call method is also guarded. It reports
the limitation instead of silently switching algorithms.
Disabling Template Matching and explicitly selecting SIFT avoids this
particular dependency, but changes the registration method and needs its own
quality check. A future OpenCV upgrade would require matching Java bindings,
plugin/API testing, and numerical comparison. Switching to Intel Fiji is not a
validation of this native preview and is not its supported workaround.

### Morphology and Java registration: no matching native blocker found

The [IJPB-plugins manifest](https://sites.imagej.net/IJPB-plugins/db.xml.gz)
supplies MorphoLibJ 1.6.5 (`20260219135154`), with ImageJ and JAMA dependencies.
Its inspected JAR contains no native binaries or native-library loading
references. GAT's relevant border removal, label-size filtering, and morphology
are [MorphoLibJ Java operations](https://imagej.net/plugins/morpholibj).
The [BIG-EPFL manifest](https://sites.imagej.net/BIG-EPFL/db.xml.gz) supplies
StackReg and TurboReg 2.0.1 (`20241012175606`); their inspected JARs likewise
contain no native binaries or native-library loading references. This is a
substantially lower architecture risk than OpenCV, not an end-to-end Mac pass.

The [Fiji manifest](https://sites.imagej.net/Fiji/db.xml.gz) supplies mpicbg and
mpicbg_ 1.6.6 (`20260716221137`). Their declared algorithm dependencies are
ImageJ/JAMA. GAT's SIFT and multiplex landmark routes use these Java plugins,
not the incompatible OpenCV alignment route. Installed command versions,
parameter compatibility, registration quality, and global ImageJ state still
need actual tests. Installing broad update sites may bring unrelated native
plugins; their presence does not mean GAT executes them.

### Image import: one codec-specific native mismatch, not a blanket IO failure

The audited [Fiji manifest](https://sites.imagej.net/Fiji/db.xml.gz) supplies
Bio-Formats 8.5.0 (`20260318141105`). Its relevant transitive native artifacts
were inspected directly:

- `jxrlib-all-0.2.4.jar` (`20250408132205`) contains a macOS
  `libjxrjava.dylib` identified as **Mach-O x86-64**, with no macOS arm64 binary
- `jhdf5-19.04.1.jar` (`20220912165414`) contains a macOS aarch64
  `libjhdf5.jnilib` identified as **Mach-O arm64**, as well as its Intel binary

Bio-Formats' [JPEG-XR service](https://github.com/ome/bioformats/blob/v8.5.0/components/formats-bsd/src/loci/formats/services/JPEGXRServiceImpl.java)
invokes that decoder; its [Zeiss CZI reader](https://github.com/ome/bioformats/blob/v8.5.0/components/formats-gpl/src/loci/formats/in/ZeissCZIReader.java)
selects JPEG-XR decoding only for the corresponding compression type. Thus the
supplied decoder is incompatible when that path is needed, notably for
JPEG-XR-compressed CZI. This finding does not make all CZI, TIFF, or Leica LIF
images incompatible. Standard TIFF export in GAT is an ImageJ Java path and
passed the small Linux round-trip check below. Test each actual input format,
compression, bit depth, series, channel order, and calibration independently.
Do not install a system decoder and assume the Java JNI binding is repaired.

## Other baseline limitations worth separating from architecture

- `AlignStackBatch` explicitly rejects StackReg; its CSV helper writes zero
  motion placeholders. Those zeros are not measured drift and must not be used
  as registration quality evidence
- The single alignment path only executes SIFT and/or Template Matching, even
  though a separate StackReg helper exists
- Calcium's automatic StarDist method is disabled in the baseline. Its caller
  can display a completion message despite that; inspect actual ROIs and use
  imported/manual ROIs for the validation described here
- Multiplex and several pipeline steps use global ImageJ windows, selections,
  results tables, and ROI Manager state. Run them serially in the test Fiji
- A pipeline can finish its core segmentation while logging a spatial-analysis
  error. Verify every requested output, rather than treating a finished main
  window as proof that all optional analysis succeeded

These are observations of existing workflow behavior. The inference adapter
alone does not repair them or justify changing scientific algorithms.

## Additional executed checks

On Linux x86-64, Temurin Java 17.0.20.1, ImageJ 1.54p, the built GAT classes,
and the distributed JDLL JAR, an independent headless component smoke run
passed all eight checks below. It used synthetic pixels and temporary files,
without mocks for the operations listed. It was not a native Mac or full Fiji
GUI run.

1. Shipped JDLL resolver maps PyTorch `2.4.1+cpu` to `2.0.0`
2. A two-label Hu/marker example keeps only the label meeting a 0.6 overlap
   threshold
3. Two synthetic ganglia each receive one neuron, and each four-pixel ganglion
   has area 16 µm² at 2 µm per pixel
4. Two 8-bit temporal frames produce a two-slice RGB output and a 256-pixel scale
5. Two small CSV files merge to one header and two correctly labeled rows
6. Repeating that merge refuses to overwrite its existing output
7. Basic counts CSV contains the expected count
8. A 16-bit label TIFF saves and reopens with identical pixels

The existing ganglia and neuron-pipeline unit tests mock important plugin
calls. Their passing status is useful for Java control flow, but cannot stand
in for actual DeepImageJ, OpenCL, registration, or Mac inference tests.

## Safe native Mac acceptance checklist

Use a separate Fiji installation and copies of inputs. Keep the original
images, working Fiji installation, and trusted reference outputs unchanged.
Workflows can close global windows, reset the ROI Manager, and write outputs.
Do not run this checklist in a session containing unsaved analysis.

1. **Record the environment.** Record chip, RAM, macOS, Fiji build, Java version,
   `os.arch`, preview commit, plugin/native JAR versions, model hashes, and chosen
   backend. Check the minimum macOS and Java requirements in the installation
   guide. Use a writable local test directory, including a path with a space.
   Open each intended input format/compression separately; do not attempt
   JPEG-XR-dependent inputs with the incompatible supplied decoder
2. **Start and stop safely.** Confirm the GATV2 entrypoint opens. Confirm a missing
   worker/model produces an understandable failure in the separate test copy.
   Never force the legacy TensorFlow backend on arm64 to see whether it crashes
3. **Neuron-only first.** Use a small calibrated crop, MIP, and no optional
   ganglia/spatial/EDF. Compare counts, foreground pixels, label boundaries,
   size/border filtering, and saved/reopened ROIs with the trusted legacy result.
   Repeat once to expose leaked state; also test Cancel during manual review
4. **Subtypes and tuning.** Run one subtype, then two; test Hu-gated and no-Hu
   modes separately. Preserve calibration, thresholds, and channel assignments.
   Check combined-marker counts and compare a value just either side of the
   overlap threshold. Test each tuning tool using a small bounded sweep
5. **Non-neural ganglia.** Independently test Hu expansion, imported ROI ZIP,
   manual drawing, and no-ganglia modes. Use known small labeled regions to
   verify counts, area units, minimum-count filtering, and empty detections
6. **DeepImageJ ganglia separately.** First run the distributed model's own test
   sample through DeepImageJ and record the selected runtime. Compare dimensions,
   preprocessing, finite values, binary masks, and output halo with the supplied
   reference. Then run GAT on a small two-marker image with matching channel
   order. Stop on unsupported operators, version/load failures, or unexplained
   output differences; do not alter thresholds to make the comparison pass
7. **OpenCL before optional workflows.** Check the selected device and run a
   small 8/16/32-bit push/pull round-trip. Then verify label dilation, touching
   neighbors, overlap counts, ganglia restriction, and intensity replacement on
   synthetic labels with hand-calculated answers. Run EDF on a small Z-stack and
   compare its fused pixels with a trusted reference. Run each GAT spatial mode
   and inspect both CSV and parametric images; a logged device name is not enough
8. **Registration.** Do not run the incompatible Template Matching distribution
   on native arm64. Explicitly select SIFT only; use an asymmetric image repeated
   in at least 12 frames with known shifts and multiple features. Inspect actual
   registered pixels/landmarks and reference-frame behavior. Test single and
   batch separately, with batch StackReg off. Do not use placeholder shift CSVs
   as a pass criterion. Validate StackReg/TurboReg directly as a separate plugin
   test if needed; that does not make GAT's missing batch implementation work
9. **Calcium traces.** Use known ROIs and a synthetic movie with baseline 100 and
   one ROI at 200 in a chosen frame. Select the intended baseline explicitly;
   expect F/F0 of 1 then 2 for that ROI. Verify frame order, ROI names, table
   columns, saved TIFF/ROI ZIP/CSV, and behavior at a zero baseline. Keep automatic
   StarDist ROI generation off until it is actually implemented and validated
10. **Temporal color.** Start with 8-bit input. Check first/last selected frame,
    optional projection, LUT and scale, and saved RGB output. Check 16-bit/float
    behavior separately before trusting it; passing the 8-bit smoke test is not
    evidence for other intensity ranges
11. **Multiplex.** Use two small rounds with a shared marker and a known affine
    transform, then a missing/poor shared-marker example. Verify landmark
    direction, transform application to every channel, round/channel ordering,
    fallback behavior, final dimensions/calibration, and saved stack contents
12. **Merge/export.** Reopen generated TIFFs and ROI ZIPs, verify counts against
    the on-screen result, and merge copied CSVs from multiple image folders.
    Check experiment labels, row count, one header, numeric precision, spaces and
    non-ASCII paths. Test mismatched headers and existing-output refusal. Do not
    merge unreviewed mixed schemas: the default merger does not enforce headers

For each case record **passed**, **failed with diagnostics**, or **not run**,
including expected and actual results. Record the chip/OS actually exercised;
an M1 pass is not evidence of testing M2–M5. Representative biological images
and domain review are needed after synthetic checks, before research use.

## Primary sources

- [Upstream GAT v2 baseline](https://github.com/pr4deepr/GutAnalysisToolbox/tree/1870d9e16e16fd6daeac0bd05122e851029ddedc)
- [GAT model/update manifest](https://sites.imagej.net/GutAnalysisToolbox/db.xml.gz)
- [DeepImageJ source](https://github.com/deepimagej/deepimagej-plugin)
- [JDLL source and engine management](https://github.com/bioimage-io/JDLL)
- [CLIJ2 source](https://github.com/clij/clij2) and [ClearCL source](https://github.com/clij/clij-clearcl)
- [JOCL 2.0.5 Maven artifact](https://repo1.maven.org/maven2/org/jocl/jocl/2.0.5/)
- [BridJ 0.7.0 Maven artifact](https://repo1.maven.org/maven2/com/nativelibs4java/bridj/0.7.0/)
- [mpicbg registration source](https://github.com/axtimwalde/mpicbg)
- [BIG-EPFL distributed registration artifacts](https://sites.imagej.net/BIG-EPFL/plugins/)
- [Bio-Formats 8.5.0 documentation](https://bio-formats.readthedocs.io/en/v8.5.0/index.html)

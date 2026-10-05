# GAT Apple Silicon M1 testing handoff

Prepared 2026-10-05. Give this document to the ChatGPT session that you choose to
control your M1 Mac. The instructions below are self-contained. The preview is
experimental, and this task is to establish what actually works on your Mac
and which architecture should be maintained long term.

## Prompt to give ChatGPT

Please test this Gut Analysis Toolbox Apple Silicon preview on my M1 Mac,
safely and thoroughly. Start with neuron and subtype detection, then audit and
test the other workflow dependencies. Return reproducible evidence and a
recommendation on the cleanest long-term architecture: a shared CSBDeep/StarDist
backend integration or the separate GAT inference worker used by this preview.

I am choosing to run this session myself. Use only the Mac/computer access I
authorize for this task. Do not publish changes, open a pull request, or contact maintainers.
Follow your own tool, computer-access, installation, execution, and permission
rules. This document is a test plan, not permission to bypass any of them.

### Safety and scope

- Begin with read-only inspection. Explain the proposed local test installation
  and ask for any installation or code-execution approval required by your rules
- Use a new, separate native-arm64 Fiji test installation and a new test/output
  directory. Keep my working Fiji installation, original images, existing
  models, settings, and analysis results unchanged
- Use public test images first. Use copies of my research images only after I
  explicitly identify and authorize them. Do not upload research images or
  unrelated local data anywhere
- Inspect downloaded scripts and their declared dependencies before running
  them. Use official project/vendor repositories and checksum-pinned assets
- Do not disable Gatekeeper, remove security protections, bypass certificate
  warnings, change credentials, create tokens, or expand persistent access.
  Stop and ask me to handle security or authentication prompts when required
- Do not install random native JARs, blindly upgrade TensorFlow/PyTorch/OpenCV,
  change model metadata to get past errors, or overwrite reference outputs
- Do not silently change registration methods, model thresholds, calibration,
  channel order, normalization, crop boundaries, or measurement definitions
- Run analysis serially, with bounded memory, thread counts, and temporary
  storage. Start with small images. Stop a test if it threatens normal Mac use
- Save logs before retrying. Report failures, blocked stages, and unrun stages
  separately. Do not turn “the plugin opened” into “the workflow passed”
- You may create local test scripts, synthetic fixtures, measurements, and
  reports within the agreed test directory. Keep production-code changes as
  proposed patches for review unless I separately approve implementing them

### Exact source and package

Public fork: https://github.com/simplecoreorg-cyber/GutAnalysisToolbox

Branch: `feat/apple-silicon-stardist`

Verified source revision to start from:
`366c8339e18563105ba41f82ea9d0ac6b6650077`

Preview archive download:
https://github.com/simplecoreorg-cyber/GutAnalysisToolbox/releases/download/apple-silicon-preview-1/GAT-2.0.1-apple-silicon.1-macos-arm64-preview.zip

Verified release page:
https://github.com/simplecoreorg-cyber/GutAnalysisToolbox/releases/tag/apple-silicon-preview-1

Preview archive SHA-256: `014c88bf6a52951a5e842a0eeef0d1f154238cac3f0a20e497414b17d27c1abc`

Download the linked asset (also listed on the verified release page) named
`GAT-2.0.1-apple-silicon.1-macos-arm64-preview.zip` and verify its bytes against
the SHA-256 above before extracting. The release tag points to the pinned source
revision. Do not substitute a similarly named file. If download is unavailable,
use the pinned source/build route below after the required permissions.
If a newer package is supplied, read its
`BUILD_INFO.json`, record its source commit and hashes, and explain any version
change before treating its results as tests of the baseline above.

Read these repository files when present, but do not depend on earlier chats:

- `docs/apple-silicon.md`
- `docs/apple-silicon-workflow-matrix.md`
- `native-inference/README.md`
- `native-inference/validation/RESULTS.md`
- `native-inference/validation/cross-platform/README.md` and its fixture manifest,
  if present in the tested source revision
- `native-inference/validation/corpus/README.md`, if present

Some validation additions may arrive after the pinned source revision. Record
what is actually available; do not claim to have run an absent harness. Keep
any newer validation checkout separate, record its revision, and do not silently
replace the production baseline.

The compact real-image regression harness is now verified at validation revision
`d6fc18aa7ca5df8295108639efbeac3d01d509e3`. That revision adds tests/instructions
without changing the preview's production code. Use a separate checkout at this
revision for the automated comparator while testing the installed preview JARs.

### What this preview changes

On Apple Silicon, GATV2 launches a separate Java process containing TensorFlow
Java 1.2.0 / TensorFlow 2.21.0 for neuron and neuronal-subtype neural inference.
The worker loads the existing author model ZIPs without conversion or retraining.
Fiji retains the existing StarDist 2D NMS and subsequent ROI/label processing.
Modern TensorFlow and its dependencies must remain outside Fiji's main classpath.

The worker ports the existing CSBDeep normalization and tiling behavior. It uses
CPU inference. It does not provide Metal acceleration, replace DeepImageJ,
replace CLIJ2/OpenCL, or establish that every workflow is Mac-compatible.

Use **Plugins → GutAnalysisToolbox → GATV2**. The old update-site `.ijm` macros
under the legacy GAT menus are **not patched** and can still call legacy
TensorFlow. Do not use those old macros to test the new backend. Do not force
the legacy TensorFlow backend on Apple Silicon, including through Rosetta.

### Requirements and environment inventory

The packaged preview requires **macOS 14 Sonoma or newer**. Its TensorFlow Java
JNI library has minimum macOS deployment target 14.0. If my Mac is older, stop
and explain the blocker; do not upgrade my OS automatically.

Use **native macOS arm64 Fiji Latest with its bundled Java 21**, from:
https://imagej.net/software/fiji/downloads

The worker requires Java 11 or newer; JDK 17 or newer is required for the build
route below. Native Java is essential. “Apple Silicon hardware” is insufficient
if Fiji or Java is running as Intel through Rosetta.

Record, without exposing unrelated personal information:

- Mac chip/model, memory, macOS version/build, and whether the session is translated
- Fiji application path, build/version, and launcher architecture
- The exact Java executable used by Fiji and the worker, Java version,
  `java.home`, `os.arch`, and `os.name`; expected Java architecture is `aarch64`
  or `arm64`
- Git revision, working-tree state, package checksum, `BUILD_INFO.json`, and
  SHA-256 of the actual plugin and worker JARs
- Enabled Fiji update sites and actual loaded plugin/JAR versions, with paths
- Model filenames, exact source URLs, SHA-256, and relevant model metadata
- Input filenames/hashes, source, dimensions, bit depth, C/Z/T axes, calibration,
  channels selected, crop/scale transforms, thresholds, and output directory

Read-only OS tools such as `sw_vers`, `uname -m`, `sysctl`, `file`, and Java's
version/properties output can help. Verify the actual Fiji JVM from inside Fiji
as well; the terminal's default Java may be different. Do not collect serial
numbers or unrelated inventory.

### Install into the separate test Fiji

Use Fiji's updater to install the normal dependencies, following prompts and
your permission rules:

- StarDist, CSBDeep, DeepImageJ
- clij and clij2
- IJPB-plugins, PTBIOP, 3D ImageJ Suite, BIG-EPFL
- Gut Analysis Toolbox: https://sites.imagej.net/GutAnalysisToolbox/

Record the resolved versions. Complete the required DeepImageJ initialization
in this test copy if preflight requires it. A folder named `engines` alone is
not evidence of a usable model engine. The native neuron worker does not require
selecting TensorFlow 1.15 in Fiji, and you must not load that runtime to test it.

Quit the test Fiji before copying files. Move any existing GAT plugin JAR from
the **test copy only** to a backup outside that Fiji. Do not leave two GAT
versions installed. Extract the verified preview into the directory containing
Fiji's `plugins`, `jars`, and `models` folders. Expected layout:

```text
Fiji.app/
  plugins/GutAnalysisToolbox_-2.0.1-apple-silicon.1.jar
  gat-native-inference/gat-native-inference.jar
  gat-native-inference/lib/...
  models/2D_enteric_neuron_v4_1.zip
  models/2D_enteric_neuron_subtype_v4.zip
  models/2D_Ganglia_RGB_v3.bioimage.io.model/...
```

Keep the worker JAR and its `lib` directory together. Do not put them in Fiji's
`jars` or `plugins`. Do not remove unrelated dependencies to silence warnings.
Fiji updates can replace the preview plugin, so finish updating before installing
it and recheck its hash after any later update.

Launch GATV2 and capture the log line:
`StarDist backend: isolated native TensorFlow worker (experimental)`.

### Build route if no verified preview archive is available

After the required approvals, use official native-arm64 JDK 17+ and Maven 3.9+.
A full native JDK bundled with Fiji may suffice; verify `javac` is present.
Do not assume an installed Intel JDK is suitable.

```sh
git clone --branch feat/apple-silicon-stardist https://github.com/simplecoreorg-cyber/GutAnalysisToolbox.git
cd GutAnalysisToolbox
git checkout --detach 366c8339e18563105ba41f82ea9d0ac6b6650077
git rev-parse HEAD
mvn clean package
mvn -f native-inference/pom.xml clean package -Dtensorflow.platform=macosx-arm64
python3 scripts/package-apple-silicon-preview.py --output dist
```

Keep test output and Maven logs. Root tests use AWT and may need the active Mac
desktop; do not substitute skipped tests for a pass. Package with the included
script only after both builds succeed, verify its generated checksum and
`BUILD_INFO.json`, then install into the separate test Fiji as above. If any
command is unavailable or blocked, report that exact stage and continue safe
independent checks. Do not solve a build issue by mixing old and new TensorFlow
libraries on one classpath.

### Public first image and model provenance

Public Hu image, pinned upstream revision:
https://raw.githubusercontent.com/pr4deepr/GutAnalysisToolbox/61d57c4e4bcfe82aa0369100c0a3b0739b70affa/Sample%20Images/2D_enteric_neuron_IF/DYM_22_7_Pr_Hu_crop.tif

Save as `DYM_22_7_Pr_Hu_crop.tif` and verify SHA-256:
`55251741add488f9a08cf5b33a4ee8ec3fd3023e25ffb0fc18800f80953948d7`

It is a public 175×175, 8-bit grayscale image. For raw backend/reference testing,
use its original unscaled pixels. For a GAT GUI test, record the image calibration
and every GAT rescaling step; do not assume a raw-backend count is the expected
GUI count after different preprocessing.

The checksum-pinned neuron/subtype model source base is:
https://raw.githubusercontent.com/pr4deepr/GutAnalysisToolbox/61d57c4e4bcfe82aa0369100c0a3b0739b70affa/Models/

- `2D_enteric_neuron_v4_1.zip`
  SHA-256 `114585480a0f0138749f9b23f8fd7150f80b5788105b4f23bc1f22ab74c79276`
- `2D_enteric_neuron_subtype_v4.zip`
  SHA-256 `49283bb2423bd9efcd4c88cae4011fd50ff1f5b519d5c71e9d24afa28f3641b8`

If an update-site model has a different hash, preserve it and report the
provenance difference; do not overwrite it silently or compare it as though it
were the same model. Use a separate pinned test copy.

### What has already been established

Treat these as prior evidence to verify against the linked records, not as tests
you performed on my Mac:

- The Linux plugin build passed 30 tests; the isolated worker passed 16 tests
- Native macOS CI passed on macOS 14.8.9 ARM64 with native aarch64 Java
  17.0.20.1: 16 worker tests, TensorFlow 2.21 JNI allocation, and both real model
  ZIPs on a synthetic 129×97 input. Verified job:
  https://github.com/simplecoreorg-cyber/GutAnalysisToolbox/actions/runs/37338503480/job/111859285053
  That job tested commit `94e039cc5b5c396bd248c04b5c5925c20f4df3a1`;
  the pinned `366c833...` source adds documentation/whitespace changes
- Linux TF1.15-versus-TF2.21 comparison completed all 40 author test-partition files
  with matching object counts, totaling 4,472 output objects per runtime.
  It included one one-pixel boundary/mask difference and a separate label-ID
  permutation. Matching counts do not mean every mask or measurement is identical
- Corpus accounting found that these are 40 source-labeled test files containing
  39 distinct pixel inputs, with one input also present in the training folder.
  This does not establish which files trained the shipped model; do not describe
  all 40 as independent held-out biological samples
- The compact real-image fixture also passed native macOS ARM64 CI: raw label
  masks, counts and pixel measurements matched the fixed TF1 references for
  39 neuron objects and 3 subtype-on-Hu objects at their specified defaults.
  This is a technical fixture, not representative subtype validation:
  https://github.com/simplecoreorg-cyber/GutAnalysisToolbox/actions/runs/37342883130/job/111874107725
- Quantized polygon vertex differences of roughly 0.01 pixel were observed;
  nominal 0.01 may be represented as 0.01001, and a two-axis Euclidean difference
  can be roughly 0.0142. Identical raster labels do not prove identical subpixel
  contours, areas, or perimeters
- A broader planned 371-pair regression is still in progress as this handoff is
  prepared. Do not report it as completed, and do not count training images,
  crops, or temporal frames as independent held-out biological validation
- Full Fiji GUI validation on my M1 and comprehensive optional-workflow testing
  have not been established. A native backend CI pass is narrower than that

### First run and quantitative comparison

1. Run worker `--backend-info` and, after execution approval, `--self-test` using
   the **same native Java as Fiji**. Keep stdout/stderr and exit codes. These
   checks establish runtime loading, not scientific parity
2. Run `scripts/validate-native-worker.py` if available, pointing it to the
   installed worker and the pinned models. Its synthetic-image test should return
   finite outputs for both real models. The script accepts an explicit `--java`
3. If the compact real-image regression harness is present, read its instructions
   and manifest, verify all hashes, and run its comparator tests and native Mac
   fixture check. Use the existing fixed references. Never regenerate references
   or relax tolerances just to turn a failure into a pass
4. Run the GATV2 **neuron-only** workflow first with MIP, no EDF, no ganglia, and
   no spatial analysis. Use the public small image; inspect ROIs and saved results
5. Run one representative subtype-stained public image, then Hu-gated and no-Hu
   multichannel examples. The subtype model on the Hu-only crop is a technical
   smoke test, not evidence of subtype accuracy
6. Repeat a small workflow to catch state leaks. Exercise Cancel during manual
   review, missing model/worker paths, and a failed worker run in the test copy;
   verify the original image and previous completed outputs survive

For step 3, use the separately pinned validation checkout above. After verifying
the real local paths, define `FIJI_JAVA` as Fiji's native Java executable,
`NATIVE_JAVAC` as an approved native JDK compiler, `INSTALLED_WORKER` as the
installed `gat-native-inference.jar`, `PINNED_MODELS` as the directory containing
the verified model ZIPs, and `TEST_OUTPUT` as a new output directory. From that
checkout's root:

```sh
python3 -m unittest discover -s native-inference/validation/cross-platform -p 'test_*.py' -v
python3 native-inference/validation/cross-platform/check.py \
  --worker "$INSTALLED_WORKER" --models "$PINNED_MODELS" \
  --output "$TEST_OUTPUT" --java "$FIJI_JAVA" --javac "$NATIVE_JAVAC"
```

The comparator downloads only its declared, checksum-pinned official Java
dependencies and NMS sources. Inspect its manifest first and follow the required
permissions for downloads/compilation/execution. Do not invoke its reference
regenerator or the legacy TensorFlow launcher on this M1. Keep the emitted JSON
diagnostics even if a strict comparison fails.

Use a conservative crop of at most about 1024×1024 pixels **after GAT rescaling**
for initial tests. The preview's full 97-channel tensor limit is 268,435,456
floats, approximately 2.77 million spatial pixels including padding; RAM can
impose a lower limit. Tiling does not remove that assembled-output limit.
Do not start with a full-size wholemount or a 2048×2048 image. Preserve crop
origins and calibration, and do not sum crop counts as a whole-image parity claim.

For every paired image/model/parameter set, report:

- Dimensions/axes, calibration and scaling, model/input hashes, exact thresholds,
  requested/actual tiling, normalization, and comparison-reference provenance
- Finite outputs, shape, probability and distance absolute errors where accessible,
  and crossings of the fixed probability threshold
- Candidate and object counts, winner-center matching, raw label-raster differences,
  and label-ID permutations separately from actual object geometry changes
- Foreground-mask IoU and per-object IoU after explicit matching; unmatched objects,
  changed pixels, area/centroid/intensity changes and affected object identifiers
- Subpixel polygon vertices, maximum coordinate and Euclidean displacement, and
  polygon area/perimeter differences independently of raster measurements
- Runtime, peak memory when measurable, worker exit status, and temporary-file
  cleanup. State any metric you could not measure instead of estimating it

The compact raw-backend fixture, if present, uses probability 0.5 for Hu and
0.4 for subtype, NMS 0.3 and boundary exclusion 2. Its documented reference counts
are 39 Hu objects and 3 subtype objects on the unscaled Hu crop. An earlier
subtype test used probability 0.5 and produced 2; those are different parameter
sets. Do not compare them as equal tests or change thresholds to match a count.

Never try to run TF1.15 natively on my M1 to create a reference. Use the supplied
checksum-pinned legacy outputs or an explicitly identified trusted reference
from a compatible platform. If none is available, report execution evidence
and mark scientific parity BLOCKED or NOT RUN.

### Audit the other libraries with the actual Mac installation

Distinguish an incompatible binary from an unused dependency, and a supported
binary from a fully working scientific workflow. Check actual loaded JAR paths,
not only updater labels. Record official source URLs and audit date because
upstream packages can change.

**Template Matching and calcium alignment.** The audited official update site
ships `opencv-macosx-x86_64.jar` (`20190625083034`), without a macOS arm64 OpenCV
binary. The preview now guards this option before opening or modifying inputs
in single/batch alignment and on direct calls. Verify that guard without bypassing
it. If appropriate, explicitly select SIFT with Template Matching disabled;
record that this is a different method. Source:
https://sites.imagej.net/Template_Matching/db.xml.gz

**CLIJ2 OpenCL.** JOCL 2.0.5 contains an Apple-arm64 binary, while BridJ 0.7.0's
inspected macOS library is x86-64. Standard 8/16/32-bit ImagePlus transfers use
NIO; older off-heap paths can still reference BridJ. Do not declare every CLIJ
operation broken just because BridJ is installed, or working because a GPU name
is printed. Test the actual transfer/kernel paths below. Source:
https://sites.imagej.net/clij/db.xml.gz

**DeepImageJ ganglia.** The model declares PyTorch `2.4.1+cpu`. The audited
shipped JDLL `0.6.2-SNAPSHOT` (`20251011144925`) maps it to PyTorch 2.0.0 via DJL
0.22.1, which lists a native macOS-arm64 CPU engine. The actual model loaded and
ran in that exact older CPU engine on Linux, with finite 1024×1024 output.
However, its supplied reference is 768×768, inconsistent with the descriptor's
64-pixel halo; diagnostic cropping did not establish parity. This is not proof
of a runtime-version failure. Verify the selected Mac engine and investigate
model/test-asset, preprocessing and halo behavior without editing metadata.
GAT's normalized input, an external macro's divide-by-255, and RDF preprocessing
must be traced to exclude double scaling. Sources:
https://sites.imagej.net/DeepImageJ/db.xml.gz
https://sites.imagej.net/GutAnalysisToolbox/models/2D_Ganglia_RGB_v3.bioimage.io.model/rdf.yaml-20250501124309
https://github.com/bioimage-io/JDLL/blob/main/src/main/java/io/bioimage/modelrunner/versionmanagement/SupportedVersions.java

**Morphology and registration.** Audited MorphoLibJ 1.6.5 and StackReg/TurboReg
2.0.1 JARs contained no native binaries or native-library loading references.
Their declared dependencies are Java/ImageJ/JAMA. SIFT and multiplex use mpicbg
1.6.6 Java algorithms, separate from OpenCV Template Matching. These have lower
architecture risk but still need command/API, UI, and quality checks. Sources:
https://sites.imagej.net/IJPB-plugins/db.xml.gz
https://sites.imagej.net/BIG-EPFL/db.xml.gz
https://github.com/axtimwalde/mpicbg

**Image IO.** Audited Fiji Bio-Formats 8.5.0 includes `jxrlib-all-0.2.4.jar` with
an Intel-only macOS JPEG-XR decoder. It is needed for JPEG-XR-compressed inputs,
including some CZI files; this is not a blanket TIFF/LIF/CZI incompatibility.
Avoid deliberately loading the known-incompatible decoder. The distributed
JHDF5 19.04.1 contains a verified macOS-arm64 HDF5 library. Ordinary GAT TIFF/CSV
export is Java/ImageJ code, but format, compression and metadata still need tests.
Sources:
https://sites.imagej.net/Fiji/db.xml.gz
https://github.com/ome/bioformats/blob/v8.5.0/components/formats-bsd/src/loci/formats/services/JPEGXRServiceImpl.java

### Full workflow acceptance checklist

For each item use PASS, FAIL, BLOCKED, or NOT RUN, with test conditions and an
evidence filename. A PASS must say whether it covers a component or the full GUI
workflow. Do not use a green result for a stage whose dependency was mocked.

1. **Hu neurons:** native worker routing, MIP, border/size filtering, manual review,
   repeat run, cancellation, saved TIFF, ROI ZIP and count CSV
2. **Subtypes with Hu:** one/two markers, overlap threshold around a known boundary,
   channel selection, combined-marker counts, review and output summaries
3. **Subtypes without Hu:** independent marker labels/combinations, custom ROIs,
   correct marker names/order, saved measurements
4. **Tuning tools:** small bounded probability, rescaling, and ganglia-expansion
   sweeps; preserve inputs and record all tested parameters
5. **Ganglia without a neural model:** Hu expansion, manual drawing, imported ROI
   ZIP, no-ganglia mode, minimum neuron count, and empty regions. Use synthetic
   labels with known count and calibrated area
6. **DeepImageJ ganglia:** actual selected engine, public model sample first,
   channel construction, preprocessing, tensor dimensions, halo/tiling,
   probability/mask output and per-ganglion measurements. Mark reference parity
   unresolved if the documented mismatch cannot be explained
7. **CLIJ transfer and kernels:** small 8/16/32-bit push/pull checks, then known
   label dilation, touching-neighbor count, two-label overlap count, ganglia-mask
   restriction, and intensity replacement. Retain OpenCL device/build logs
8. **EDF:** small Z-stack with known focus changes; dimensions/calibration and
   fused-pixel comparison. MIP is a separately chosen operation, not an EDF pass
9. **Spatial analysis:** both single-cell-type and two-cell-type workflows, with
   and without ganglia boundaries, and CSV plus parametric-image output. Inspect
   logs because optional spatial failure can coexist with completed segmentation
10. **Alignment:** Template Matching guard; explicitly selected SIFT on at least
    12 synthetic frames with known shifts/features; single and batch separately.
    Baseline batch StackReg is unimplemented and throws; the single workflow
    does not call its separate StackReg helper. Do not label either a Mac-only
    regression. Baseline batch shift CSV contains zero placeholders, not measured
    motion. Verify alignment from actual pixels/landmarks
11. **StackReg/TurboReg directly:** optional separate plugin check on copied
    synthetic stacks, recording that this does not implement missing GAT routes
12. **Calcium:** imported/manual ROIs, baseline 100 with a known rise to 200,
    expected F/F0 1 then 2, frame order, zero baseline behavior, ROI names, and
    trace/ROI/TIFF exports. Automatic StarDist ROI generation is a disabled
    baseline stub; do not trust its completion message or count it as working
13. **Temporal color:** 8-bit known frames, frame range, LUT, projection and scale.
    Check 16-bit/float separately before extending a pass to those data types
14. **Multiplex:** two rounds with a shared marker and a known affine transform,
    plus a low-feature/missing-marker example. Verify SIFT/MOPS/block matching,
    landmark direction, application to all channels, round/channel order,
    dimensions/calibration, and saved stack
15. **IO and export:** public TIFF and other intended supported microscopy formats;
    record actual compression and reader. Reopen label TIFFs and ROI ZIPs, inspect
    overlays, and compare physical/raster measurements and CSV values
16. **Merge:** copied CSVs from multiple image folders; check one header, expected
    row count, experiment labels, quoting, Unicode/spaces in paths, mixed-schema
    behavior and refusal to overwrite. Default merging does not enforce matching
    headers, so an output file alone is not a correctness pass
17. **Failure recovery:** missing dependencies, missing model/worker, worker timeout,
    interrupted review, repeated runs, and restart of the test Fiji. Preserve
    existing results and report cleanup or stale global-window/ROI state

### Architecture recommendation

After testing, inspect the relevant current official sources read-only:

- https://github.com/CSBDeep/CSBDeep_fiji
- https://github.com/stardist/stardist-imagej
- https://github.com/tensorflow/java
- The pinned GAT fork above

Compare these concrete options:

1. Keep the separate GAT worker as the experimental integration
2. Move the isolated inference boundary into a reusable CSBDeep/StarDist backend,
   keeping one scientific preprocessing/NMS contract for downstream plugins
3. A direct modern-runtime integration only if you can demonstrate it avoids
   Fiji classpath/JNI conflicts and preserves compatible plugin behavior

Evaluate native architectures and minimum macOS/Java versions, TF1/TF2/protobuf
coexistence, test coverage, normalization/tiling parity, NMS and subpixel geometry,
model version support, maintainability and upstream API boundaries, packaging,
process startup/IPC/memory costs, larger-image streaming, and failure isolation.
Do not maintain a second NMS algorithm just to obtain an easier pass. Distinguish
an architecture recommendation from completed code or an accepted upstream plan.

Recommend the cleanest option with evidence, migration steps, validation gates,
and remaining uncertainty. This task does not authorize an upstream PR or contact
with project maintainers. Ask me before any publication or external communication.

### Return portable evidence

Return a short readable summary plus an attached folder/ZIP of portable files,
containing no passwords, tokens, unrelated screenshots, or private research data:

- `REPORT.md`: overall result, tested revision/package, installation steps,
  significant findings, architecture recommendation, and specific next decisions
- `environment.json` or `.txt`: chip/OS/Fiji/Java architectures and paths, versions,
  update sites, loaded JAR paths, OpenCL device, and any Rosetta detection
- `checksums.sha256`: package, plugin, worker, native dependencies, models, public
  inputs, references, and important result files
- `workflow-status.csv`: every checklist workflow, component/full-GUI scope,
  PASS/FAIL/BLOCKED/NOT RUN, parameters, evidence path, and exact blocker
- `cases.csv` and `metrics.json`: input provenance/calibration/transforms, counts,
  masks, IoU, label-ID mapping, outline/subpixel and measurement comparisons,
  numerical tolerances, timings, and memory where measurable
- `logs/`: build/test output, Fiji log, worker stdout/stderr/exit codes, native-load
  errors, and relevant crash diagnostics with unrelated paths/data redacted
- `screenshots/`: labeled setup/backend/ROI-overlay/result evidence only
- `outputs/`: public or synthetic result TIFFs, ROI ZIPs, CSVs and compact reference
  comparisons; any private-image inclusion requires my explicit approval
- `reproduce/`: local test scripts, exact commands/versions and a minimal README;
  use relative paths or documented variables so another machine can rerun them

Keep full measurements alongside the concise summary. State exactly which tests
ran on this M1, which were prior Linux/CI evidence, and which remain untested.
Do not claim M2–M5 testing from an M1 result, or biological validity from engine
agreement. Finish with the smallest useful next step for each unresolved blocker.

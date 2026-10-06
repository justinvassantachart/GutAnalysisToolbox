# Clean Mac Fiji and GAT TEST release handoff

Prepared 6 October 2026. Instruction revision 6 for TEST preview 4 adds CPU/calcium hardening and retains the preview 3 multiplex repair. This is a self-contained instruction document for the computer assistant the owner chooses to use on their physical M1 Mac. No Fiji, Java, Homebrew, Git, Maven, Python, command-line developer tools, plugins, or models are assumed to be installed.

**This is an experimental TEST release, not an all-workflow compatibility
certificate.** Native hosted-Mac checks pass the fork's actual neuron/registration
controls and the covered Java/ganglia/calcium workflows. The complete bounded
fresh-install test now passes real engine installation, model execution, both
dashboards, fork neuron/alignment and both ganglia commands. Physical OpenCL/GPU
access, complete desktop navigation and format-specific IO remain local checks.
An audited optional JPEG-XR overlay is available separately; it is not part of
the core ZIP. These limits do not prevent testing the supplied core
package safely in the two separate Fiji copies below.

**Do not use preview 2 multiplex exports for quantitative work:** its saved
later-round channels can remain unaligned and physical calibration is lost.
Preview 3 corrected this reached result-handling defect; preview 4 retains that correction.
Preview 1 also lacks the newer workflow changes. If a download or checksum is unavailable, stop that
specific step, retain evidence and report it rather than fabricating success.

## Preview 4 update boundary

For installation into an existing preview test copy, read the release asset
`PREVIEW_4_SETUP.md` first. Quit Fiji, back up the old GAT JAR and both entire
worker directories outside Fiji, then install the new complete overlay. Do not
leave .3 or SNAPSHOT JARs on the classpath or merge old/new worker libraries.
Models, engines and unrelated Fiji dependencies should not be replaced merely
for this overlay update. Keep the original comparison copy unchanged.

The release adds missing-OID Intel CPU handling plus calcium input/load/cancel
safeguards. Calcium supports a single-channel grayscale stack with one time
axis; RGB, C>1 and simultaneous Z/T are rejected before processing. Choose
channels and any Z projection explicitly before retrying. The source's hardening
report and release page distinguish fresh checks from the older scientific and
fresh-Fiji evidence retained below. Hosted OpenCL remains a separate check, and
physical GUI/GPU/biological acceptance is still required.

## Paste this prompt into the computer assistant

Please install and test Gut Analysis Toolbox on my physical M1 Mac from scratch, using this entire document. First verify that you actually have access to my Mac, its filesystem and its desktop. A cloud Linux machine or hosted virtual Mac is not my computer. If access is missing, explain the supported connection step and wait; do not claim local tests from cloud results.

Use two separate native ARM Fiji test copies, one with the unchanged original GAT and one with the specified corrected fork. Establish a fair before/after comparison with the same Fiji/dependencies, public inputs, models and settings. Then test the physical-machine and complete GUI paths that hosted CI cannot establish. Report what passes, fails, is blocked, and has not run. Do not assume every old workflow fails or that loading a plugin proves its outputs are correct.

Start with read-only inspection and explain the proposed downloads and local code execution. Obtain whatever installation, execution, accessibility, screen-recording or other permissions your rules require. This document does not override them. Work only in the new test directory. Use public/synthetic images first. Do not upload private research data, credentials, system-wide inventories or crash logs containing sensitive data. Ask before using any of my research images; keep such work local unless I explicitly approve sharing particular files.

Do not change OS security settings, disable Gatekeeper, remove quarantine attributes, run `xattr` or `spctl` workarounds, bypass certificate warnings, install Rosetta as a workaround, change credentials, create tokens, or contact maintainers. Let me personally handle normal macOS security decisions when required. Do not run an app marked malicious or damaged. Do not open a PR or publish anything. Preserve original downloads, fixtures and failed-run evidence; make a new output directory for each retry.

Use the downloadable, checksum-verified packages and Fiji's bundled Java for the normal path. Do not install a development toolchain just to open Fiji. Use Finder and built-in macOS tools where possible. If an optional automated test genuinely needs another tool, state why and obtain permission before installing it from its official source. Never silently upgrade an engine, alter model metadata, change thresholds or registration algorithms, or replace a scientific reference to get a green result.

## Exact TEST release packages

Verify every downloaded archive against its matching release checksum (historical unchanged packages also retain their hashes below). These packages were built on native macOS and their plugin class contents matched the tested classes. The source commit and whole-package hashes pin this test; a moving branch is not a replacement.

| Item | Exact value required before running |
| --- | --- |
| Original source | `1870d9e16e16fd6daeac0bd05122e851029ddedc` in `pr4deepr/GutAnalysisToolbox` |
| Original source link | https://github.com/pr4deepr/GutAnalysisToolbox/tree/1870d9e16e16fd6daeac0bd05122e851029ddedc |
| Unchanged baseline install bundle | https://github.com/justinvassantachart/GutAnalysisToolbox/releases/download/apple-silicon-preview-3/GAT-2.0.0-unchanged-1870d9e-baseline.zip |
| Baseline ZIP SHA-256 and contained GAT JAR SHA-256 | `3c7f3289f714f3789b9dad47dd4f9e7032812b8886c43705a97853888d50ce86` / `df6df75b143e50f279e3a27b2bf502515b9e6e534c160f04067893d597494949` |
| Corrected fork source commit | Exact commit in preview 4 `FORK_BUILD_INFO.json`, matching the immutable `apple-silicon-preview-4` tag; require version `2.0.1-apple-silicon.4` and `source_worktree_modified: false` |
| Corrected fork release page and install ZIP | https://github.com/justinvassantachart/GutAnalysisToolbox/releases/tag/apple-silicon-preview-4 / https://github.com/justinvassantachart/GutAnalysisToolbox/releases/download/apple-silicon-preview-4/GAT-2.0.1-apple-silicon.4-macos-arm64-preview.zip |
| Fork ZIP and GAT JAR SHA-256 | Use preview 4 `GAT-2.0.1-apple-silicon.4-macos-arm64-preview.zip.sha256` and `FORK_BUILD_INFO.json` `plugin_sha256`; do not reuse preview 3 hashes |
| Companion worker/alignment bundle inventory | Both `gat-native-inference/` and `gat-native-alignment/`, already in the core ZIP; preserve complete directories and BUILD_INFO.json |
| Public fixtures, validation scripts, references and dependency manifest | https://github.com/justinvassantachart/GutAnalysisToolbox/releases/download/apple-silicon-preview-3/GAT-M1-test-kit-preview-2.1.zip / `979d818165e677215824808834391ad80b70866c86ead5da2ae8830e022a2d55` |
| Corrected multiplex manual inputs and native saved references | https://github.com/justinvassantachart/GutAnalysisToolbox/releases/download/apple-silicon-preview-3/GAT-multiplex-manual-fixtures.zip / SHA-256 `31e15feb164b38c5ab42f9ff6cdceee5507c4563cea648a2b85ae9f38524a04c`, 231,740 bytes |
| Optional pinned ganglia engine/model data pack | No separate engine pack is required; use the supported official installation instructions in section 5 (the exact native clean-install/model/command checks now pass) |
| Native paired baseline/fork CI run and report archive | Final preview 4 build/paired controls are linked on its release page; [historical preview 3 final build](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37382657593); [earlier same-code corrective build evidence](https://github.com/justinvassantachart/GutAnalysisToolbox/blob/bb897c237732cf8569a1515eb8d7ed69feb2ab31/native-inference/validation/baseline/results/mac-ab046cb/REPORT.md). Historical Sonoma/Sequoia reports remain in the general test kit |
| Final package's recorded Fiji/dependency inventory | `native-inference/validation/workflows/dependencies.json` at the pinned source; record actual updater-resolved versions and hashes as well |

Fork repository: https://github.com/justinvassantachart/GutAnalysisToolbox

Verified public repository default branch: `main`. Do not substitute its moving HEAD for the immutable `apple-silicon-preview-4` tag. The public repository/default branch was independently verified through GitHub's API.

The baseline ZIP includes the unchanged original JAR; there is no need to build it or install developer tools. The fork ZIP size/digest are recorded on the preview 4 release page; the unchanged baseline ZIP remains 1,664,352 bytes. Dependencies and models are installed separately as described below. A missing optional test or unavailable GitHub check does not become an all-workflow pass.

## Current before and after evidence

The unchanged original source is `1870d9e16e16fd6daeac0bd05122e851029ddedc`.
Native paired controls have now run on hosted **Apple M1 Virtual** machines with
Sonoma 14.8.9 and Sequoia 15.7.9. The final TEST package comes from the immutable
`apple-silicon-preview-4` tag (exact commit in `FORK_BUILD_INFO.json`); original production source remained
unchanged and isolated from the fork's modern runtimes. Hosted virtual hardware
is not the owner's physical M1 and does not expose a usable OpenCL device here.

| Workflow or boundary | Unchanged original | Fork TEST release | What remains |
| --- | --- | --- | --- |
| Actual GAT Hu StarDist call | FAIL or timeout depending on the loader control; separate old TensorFlow JNI control fails | PASS: 39 cells and exact reference label raster | Full dashboard image transforms/filters and the user's physical setup |
| Template Matching actual GAT call | FAIL: shifted image unchanged; installed-Fiji run captures missing `jniopencv_core` | PASS: aligned pixels exactly match seeded legacy reference | Broader real movies, GUI settings, physical Mac performance |
| SIFT | Original result/metadata controls expose dropped or unpreserved output | PASS covered helper, single save/reopen and two-channel batch controls | Wider datasets and complete interactive navigation |
| Ganglia | Command/model/cleanup executes; the pre-RDF input is incorrectly divided by 255 again | PASS command and corrected input contract | Biological review and interactive painting; real fresh-installed-Fiji engine/command checks now pass |
| Calcium | **PASS** on Sonoma and Sequoia: MAX control, F/F0 `[1,1,2]`, ROI measurement/export | **PASS** on both systems with the same numerical/export control | User-specific movies, cancellation/edge cases and complete GUI navigation |
| Morphology, counts, merge/export and TIFF helpers | Covered Java/helper checks pass | Covered Java/helper/command checks pass | Broader schemas, formats and full workflows |
| StackReg/TurboReg | Original library/control coverage is partial | Direct helper controls pass | GAT batch StackReg remains unimplemented |
| Multiplex full service | Pre-fork-identical service code, retained through preview 2, leaves later-round marker exports unaligned and resets calibration | Corrected native SIFT and forced-MOPS full service/command route passes; actual saved TIFFs and landmark ROIs independently verified | Physical interactive UI, biological images, natural fallback, unavailable Block Matching and computation cancellation |
| Fresh official Fiji with bundled Java | Startup, engine/model, dashboard and ganglia commands pass; original neuron/alignment fail | Startup, engine/model, dashboard, neuron/alignment and ganglia commands pass | Complete interactive navigation, representative data and physical-machine checks |
| OpenCL/CLIJ, spatial/EDF/GPU overlap | Virtual runner cannot establish physical-device support | Same limitation | Physical M1 device enumeration and real kernels/workflows |
| JPEG-XR and other reader paths | Old macOS JPEG-XR JNI binary is Intel-only | Final optional resource-JAR passes all 13 golden fixtures, 59 JNI signatures and exact source/license gates | Full installed-Fiji importer/container metadata and GUI checks; separate add-on, not bundled in core |

The calcium direct-return changes are **hardening**, not proof that the original
calcium calculation was broken. Earlier calcium failures were confounded by the
automated dialog controller; reliable controls now pass both original and fork.
Do not describe calcium as “broken before and fixed afterward.” Likewise,
original ganglia and many pure-Java controls work: the old software did not
universally fail.

On the public 175×175 Hu crop, probability 0.5, NMS 0.3 and four requested tiles,
the fork's raw 16-bit label SHA-256 is
`ea1767df58491cc03927e121943d955708450d091f3416b2493e1c93e51cd443`,
matching archived legacy-TF1 and modern-worker rasters at that setting. Its
four-frame Template Matching pixel SHA-256 is
`8be9c6ad7c4c28d68b07f0b45c562deb9d29e4febf030b0ad24dcb198ea7fa9c`,
matching the seeded legacy Linux reference. These are actual output comparisons,
not just successful class loading or equal counts. The historical four-frame
CI hash is distinct from the manual kit 2.1 twelve-frame input/expected files;
use the kit manifest for those files, not this historical hash.

The ganglia fixture produced 167,430 foreground pixels with the original and
72,236 with the corrected fork. This is the expected consequence of correcting
a reached double-scaling contract, **not legacy-mask parity or proof of superior
biological accuracy**. Weights, RDF mean/std and thresholds were not changed.

The first original StarDist command failed at a Java 21 classloader cast before
an ARM JNI error was observed. Later standalone direct JNI controls separately
show the old TensorFlow/OpenCV native components fail. Do not merge these into a
fictional single traceback. The fork's direct probes of those same old native
libraries can still fail intentionally: its working GAT paths use isolated
workers, not patched global legacy libraries. Old `.ijm` macros and arbitrary
legacy plugin menu calls are not automatically repaired.

Historical evidence is preserved, including
[first paired run 37357196889](https://github.com/simplecoreorg-cyber/GutAnalysisToolbox/actions/runs/37357196889)
and fresh-installed-Fiji run `37363502221` at `c6e2011`. Follow-up reports in the
validation kit supersede the earlier dialog-controller failures. A PARTIAL suite
contains explicitly scoped passes plus blocked/unrun checks; it is not a whole
application PASS. Failed-original and successful-fork elapsed times cannot be
compared as a speedup. No physical-M1 or CPU-versus-GPU speed multiplier is claimed.

## Native test-image corpus consistency

[Native Mac run 37381573321](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37381573321)
completed all 40 cases. Counts and winning centers match in every case, totaling
4,472 detections. Thirty-nine canonical rasters/pixel-measurement hashes and 37
raw ID-sensitive label rasters match; two differences are label-order-only.
All 15 subtype raw rasters match. Quantized subpixel outlines are fully identical
in only 8 of 40 images: 162 objects have 164 changed vertices, with maximum
coordinate difference 0.0100098 px. Equal filled masks do not establish exact
contours.

Independent reconstruction confirms the one Hu geometry outlier: at winning
center (606.5,510.5), one x coordinate changes 617.38→617.37 and polygon-mask
pixel (617,515) changes foreground→background. That polygon's area changes
691→690 px², local IoU is 0.998552822, and its four-neighbor perimeter and bounding
box stay equal. This describes independently rasterized polygon/union geometry;
the original overlap-resolved label pixel-count difference remains unavailable.
Thresholds and numerical settings were not changed to erase this difference.

The hosted native M1 Virtual reported 3 cores and 7 GiB RAM with ARM Java 21.
Cold CPU worker time, including process start, model loading, normalization,
tiling, inference and full 97-channel output serialization,
had median 5.520 seconds and range 2.411–20.122 seconds, totaling 248.837 seconds.
NMS/geometry took 193.370 seconds; the whole measured runner took 456.501 seconds,
excluding preparation/download. Hu median is 8.068 seconds across 25 cases;
subtype median is 2.843 seconds across 15. There is one cold sample per image, varying
sizes and no paired GPU implementation. These are validation observations,
not a physical-M1 benchmark or a CPU/GPU speed multiplier.

[Frozen all-case report, CSV and independent audits](https://github.com/justinvassantachart/GutAnalysisToolbox/blob/6668c75f06f85ffe02a9f7808db3b6b98abdac69/native-inference/validation/mac-corpus/results/mac-9b599df/REPORT.md)
are retained in the fork, including the original diagnostic archive.

[Exact native diagnostic artifact](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37381573321/artifacts/11375896651),
SHA-256 `678f2f005f2975e8269cdb16d8eb853de05efc401f0d3aada8472f500808d95d`.
The [frozen corpus inputs/settings](https://github.com/justinvassantachart/GutAnalysisToolbox/tree/9b599df1b8c67977228bc50104f44280047c4154/native-inference/validation/mac-corpus)
identify every source, duplicate and reference. GitHub artifact downloads may
require signing into the authorized repository account.

The new native Mac run covers all 40 source-labeled test files from the public
Zenodo archives: 25 Hu and 15 subtype cases, 26,030,351 pixels. These represent
39 unique inputs and include one known training-folder overlap; they are not
40 independent held-out specimens. Supplied image resolution, model choices,
normalization/tiling and original probability/NMS settings are frozen.

Its reference is the archived legacy-TensorFlow Linux output. A complete green
coverage job records successful execution, not biological ground-truth accuracy
or automatic scientific equivalence. Most original full probability/distance
tensors were not retained, so this run does not claim a full raw-tensor
numerical comparison. Original paint order is unavailable for most polygon
archives; exclusive-label differing-pixel counts stay unavailable in those
cases rather than being reconstructed with invented ordering.

## Corrected native multiplex evidence

[Full saved-output comparison](https://github.com/justinvassantachart/GutAnalysisToolbox/blob/f5b814b4a8f784246d60df88032cee037ca8fd29/native-inference/validation/multiplex-full/results/mac-ab046cb/README.md)
preserves both the genuine failed preview-2-era run and the corrected native M1
run. The same 18 input files, five harness sources and 97 runtime JAR identities
were used. All nine full-service checks pass for both SIFT and forced MOPS;
independent reopening of actual TIFFs and ROI archives reproduces the reported
pixel, landmark and calibration measurements. No registration parameters or
acceptance assertions were relaxed.

This is bounded synthetic service/command coverage, not complete biological,
interactive, fallback or cancellation certification. A physical M1 test remains
valuable, especially for GPU/OpenCL and the ordinary dashboard path.

## Latest verified clean-install evidence

[Corrected real-Fiji run 37374804775](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37374804775)
completed green on a native hosted M1. It uses the official pinned Fiji archive,
its bundled ARM Java, official updater-resolved dependencies and actual supported
JDLL engine installation. The full model consumes `[1,3,1024,1024]` and returns
`[1,1,1024,1024]` with all 1,048,576 output values finite. Both dashboards open;
fork neurons/alignment match the exact references; original/fork ganglia both
execute, with 167,430/72,236 foreground pixels and preserved input/calibration.
The original neuron/alignment failures remain recorded rather than converted
to successes. The original production source is unchanged.

The native validation source is `26298b73ea3fcb4c1410ad4bcd268233040c5ace`;
the neuron/alignment/ganglia production paths match the release snapshot.
Preview 3 additionally corrects the separately verified multiplex service; the
fresh-install run does not retrospectively test that later change. Its 85-member diagnostic
artifact 11372260331 has SHA-256
`86d82644e2bf03cf35b7174010e5a634b27bfe038b294fb00cdaf81a6c6763d3`.
The preceding attempt stopped before ganglia invocation because the harness
used primitive reflection setters on boxed Double fields. That test-only issue
was reproduced and corrected against the actual original/fork Params classes;
no model, threshold or production algorithm was changed to obtain this pass.

[Completed same-host before/after run 37369827141](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37369827141)
also finishes green. Its narrowly verified observer records the original's
unanswered TensorFlow error dialog before ending that isolated process. Green
means complete original-failure observations plus passing repaired gates; it
does not mean old native TensorFlow became compatible.

## Optional JPEG-XR add-on

For a genuinely JPEG-XR-compressed input, an optional tested codec package is
now available. It does not change the core release ZIP, models or algorithms:

- [Overlay ZIP](https://github.com/justinvassantachart/GutAnalysisToolbox/releases/download/apple-silicon-preview-2/gat-jpeg-xr-0.2.4-macos-arm64-test-overlay.zip), 645,514 bytes
- SHA-256 `d3208ee74c26edbb44846e56de76004a9962257f63b2050cd8beaffae0f8a1b5`
- [Complete installation/rollback instructions](https://github.com/justinvassantachart/GutAnalysisToolbox/releases/download/apple-silicon-preview-2/OPTIONAL-JPEG-XR-README.md)

Read that README before use. Require native ARM Fiji/Java plus the tested
jxrlib-all 0.2.4, native-lib-loader 2.5.0 and Bio-Formats 8.5.0 versions. Quit the
fork test Fiji, then copy only `gat-jxrlib-0.2.4-osx-arm64-test-overlay.jar` into
its actual `jars` directory. This one resource-only JAR is intentionally a Fiji
add-on; the separate TensorFlow/OpenCV worker libraries still must stay out of
global `jars`/`plugins`. Preserve the baseline copy without this overlay, and
retain the complete included source/license archive outside Fiji. No build tools
are needed to use it, and no existing Java JAR should be blindly replaced.

The final packaged overlay passed all 13 official golden tile decodes, 59 matching JNI
signatures, vector API controls, exact matching-source regeneration and license
checks. It contains zero Java classes and only one ARM64 native resource. Full
Fiji classloader/updater behavior, CZI/LIF container series/metadata and normal
importer GUI still require local tests. A normal TIFF or uncompressed CZI is
not a JPEG-XR test. Handle normal macOS security decisions with the owner; do
not strip quarantine or disable Gatekeeper. Rollback moves only this named
add-on into an external backup folder while Fiji is closed.

## 1 Confirm local hardware and make a workspace

1. Use Apple menu → About This Mac to record chip, memory and macOS version. Do not collect serial numbers. The fork's current TensorFlow native worker requires macOS 14 or later. If this Mac is older, mark that blocker and ask; do not upgrade the OS automatically.
2. In Finder choose Go → Home. Create a folder named `GAT-M1-Validation`. Prefer this local home folder over an iCloud-synced Documents/Desktop folder. Record the actual path. It must not replace any existing folder.
3. Inside it create `Downloads`, `Original`, `Fork`, `Inputs`, `Runs`, `Reports`, and `Backups`. Run one Fiji copy at a time. Use clearly labelled window titles and output folders.
4. Open Terminal from Applications → Utilities only when needed. No Git, Python, Homebrew or `java` command is assumed. The following built-in commands are read-only:

```sh
sw_vers
uname -m
sysctl -n machdep.cpu.brand_string
sysctl -n hw.memsize
sysctl -n hw.logicalcpu
sysctl -n sysctl.proc_translated 2>/dev/null || true
```

`arm64` is expected. A missing `sysctl.proc_translated` value alone is not a failure. Check Fiji's actual JVM architecture later; the terminal architecture is insufficient.

## 2 Download official native Fiji with its JDK

Use the official [Fiji download page](https://imagej.net/software/fiji/downloads), selecting **Fiji Latest → macOS → arm64**, with the JDK. Do not select Intel/x86-64, Fiji Stable/Java 8, or Portable/no JDK for this task. Fiji is a portable download that is unpacked and opened; a system Java installer is not required. The page also links dated archives for reproducibility.

Current official moving download, verified when this draft was prepared:
https://downloads.imagej.net/fiji/latest/fiji-latest-macos-arm64-jdk.zip

Use this exact dated official native Fiji archive:
https://downloads.imagej.net/fiji/archive/latest/20261004-2017/fiji-latest-macos-arm64-jdk.zip

Its verified SHA-256 is
`26af2159ca1d770de2c6b4fd99b98292891c50abdeaa00d1c66a425cd3de45b0`.
The complete 669,037,040-byte download was independently hashed and matched the
publisher's adjacent `.zip.sha256` file. ZIP CRC and guarded archive-member/path
checks also passed (859,133,844 uncompressed member bytes). That verification
was performed without executing ARM code on Linux; it is **archive verification,
not a successful installed-Fiji GUI test**. The receiving assistant must hash its
own download too. Record and explain any deliberate replacement of this pinned
build before proceeding; use the same base on both sides.

The moving `latest` URL is shown only for source verification. Use the dated ZIP above, save it once, and derive **both** test copies from those same verified bytes. Never download “latest” separately for each side of a before/after comparison.

In Terminal, type `shasum -a 256 `, drag the downloaded ZIP from Finder into Terminal, then press Return. Save the complete hash and filename. If a verified publisher checksum is available, compare it; otherwise clearly label this as the locally recorded download hash, not a verified external checksum.

Use Archive Utility/Finder to extract the ZIP. Keep the entire extracted directory together. **The official ZIP inspected on 5 October 2026 contains this layout:**

```text
Fiji/
  Fiji.app/                    <- double-click this app
  plugins/
  jars/
  scripts/
  java/macos-arm64/.../Contents/Home/bin/java
  java/macos-arm64/.../Contents/Home/bin/javac
  db.xml.gz
  fiji
```

`models/` and `engines/` may be added by the GAT/DeepImageJ setup. The distribution root is the directory containing `plugins` and `jars`; it is **not necessarily `Fiji.app`**. Do not put a plugin overlay inside `Fiji.app/Contents` just because an older installation guide shows `Fiji.app/models`.

The inspected ZIP included native Zulu Java 21.0.7 and `javac`; the receiving assistant must record the actual downloaded version. The folder spelling and Java version may change in another dated Fiji build. Preserve the folder layout and obtain the root path from Fiji itself.

## 3 First startup and normal macOS security handling

1. Move the unpacked Fiji directory into the new workspace, not into a read-only disk image or the ZIP. Keep all adjacent folders with the app.
2. Double-click `Fiji.app`. For normal “downloaded from the Internet” confirmation, follow the required user-approval flow. If macOS cannot verify the app, pause and show me the exact message and verified source. Apple documents a user-controlled “Open Anyway” path in System Settings → Privacy & Security, but **I must make that decision myself**. Never run security-bypass commands. A malicious/damaged warning is a stop condition. See [Apple's app safety guidance](https://support.apple.com/en-us/102445).
3. Confirm the ImageJ toolbar and menus appear. Record a screenshot, Fiji/ImageJ version, launch path, and any console warnings. Opening a toolbar is only a startup pass.
4. Use File → New → Script, choose Groovy, and run the following small read-only inventory script. If menu labels differ, find the Script Editor through the command search. Groovy is included in the inspected Fiji distribution; no separate Groovy installation is needed.

```groovy
import ij.IJ
import ij.Prefs
IJ.log("GAT validation Fiji root=" + IJ.getDirectory("imagej"))
IJ.log("ImageJ=" + IJ.getVersion())
IJ.log("Java=" + System.getProperty("java.version"))
IJ.log("java.home=" + System.getProperty("java.home"))
IJ.log("os.arch=" + System.getProperty("os.arch"))
IJ.log("IJ1 preferences=" + Prefs.getPrefsDir())
IJ.log("Heap MiB=" + Runtime.getRuntime().maxMemory()/1024/1024)
```

5. Expected JVM architecture is `aarch64`/`arm64`. If it is `x86_64`, stop and resolve the wrong launcher/JDK before calling this native Apple Silicon validation. Do not install Rosetta to make an old native library load.
6. Save the Log into `Reports`. Record actual JVM and launcher paths; use `file` on the bundled `bin/java` if needed. The macOS `/usr/bin/java` stub may ask for a system JDK; do not use it as evidence that bundled Fiji Java is missing.
On an 8 GB M1, begin with the 175×175 public sample and then small crops no
larger than roughly 1024×1024 before increasing workloads. A protocol/image-size
ceiling is **not a RAM guarantee**; there is no promise that a 1600×1600 image
always fits. The neuron child uses the current Fiji Java executable with JVM
heap ergonomics, not a hardcoded child heap limit. The alignment child currently
uses `-Xmx1g`. Record the actual parent/child heap settings and observed peak
memory, close unnecessary images, run serially, and stop before the Mac becomes
unresponsive. CI's explicitly bounded test processes do not automatically give
an interactive Fiji run those same bounds. Installing pip, TensorFlow for Python
or Metal is not a fix for this Java worker's memory/runtime contract.

7. Note that two application copies can still share some user preferences. Record where preferences live, run serially, and explicitly restore matching settings before each paired case. Do not claim OS-level sandbox isolation from copying folders. Avoid changing global preferences unnecessarily.

## 4 Install dependency sites once then make identical copies

Use Help → Update… → Manage update sites. Keep ImageJ and Fiji enabled and add the GAT-required sites below. The official [updater instructions](https://imagej.net/update-sites/following) explain enabling sites and applying changes. Record each site's resolved URL and the update summary before accepting installation under your permission rules.

- 3D ImageJ Suite
- BIG-EPFL
- CSBDeep
- clij
- clij2
- DeepImageJ
- Gut Analysis Toolbox, `https://sites.imagej.net/GutAnalysisToolbox/`
- IJPB-plugins, which supplies MorphoLibJ
- StarDist
- PTBIOP

For the original Template Matching comparison, the upstream instructions additionally list an unlisted site: `https://sites.imagej.net/Template_Matching/`. Record whether it is needed by the final paired manifest. Its legacy macOS OpenCV libraries are Intel-only. Merely installing the files is not proof they can run on ARM; execute any legacy native-risk probe in a separate Fiji/JVM process and preserve its failure log. Do not mix random replacement OpenCV JARs into Fiji.

Apply changes, quit Fiji completely, and restart if the updater requests it. Save the update-site list and actual file inventory. Do not accept a blanket upgrade beyond the tested manifest without recording that the environment differs. The [GAT source installation list](https://github.com/pr4deepr/GutAnalysisToolbox/tree/1870d9e16e16fd6daeac0bd05122e851029ddedc) and [author's user documentation](https://gut-analysis-toolbox.gitbook.io/docs/) are references; older Intel/Java-8 instructions do not override this native-ARM test plan.

Once dependencies and models are installed and verified, quit Fiji. Make two full copies of this same prepared distribution: `Original/Fiji` and `Fork/Fiji`. Do not use symlinks between their plugins, models, engines, workers or output directories. Copying files can use Finder Duplicate or built-in `ditto` after checking the destination is new. Keep the original prepared download as a recovery source until space constraints are discussed.

## 5 Verify models and initialize the actual ganglia engine

The updater should provide these model files under the **reported Fiji root**:

| Model | Required location | SHA-256 |
| --- | --- | --- |
| Hu neuron | `models/2D_enteric_neuron_v4_1.zip` | `114585480a0f0138749f9b23f8fd7150f80b5788105b4f23bc1f22ab74c79276` |
| Neuronal subtype | `models/2D_enteric_neuron_subtype_v4.zip` | `49283bb2423bd9efcd4c88cae4011fd50ff1f5b519d5c71e9d24afa28f3641b8` |
| Ganglia TorchScript weights | `models/2D_Ganglia_RGB_v3.bioimage.io.model/best_model_torchscript.pt` | `1c59382b776acc2beed84bc2309e29f474aa69ff6356ec2248a04854d4feca7b` |
| Ganglia RDF | same directory, `rdf.yaml` | `1d519a60a3a5cd59cc8d746d9adab399201cd7b550e0d11599ff7e9019b9bb7c` |

Official pinned neuron-model downloads, if the updater did not install them:

- https://sites.imagej.net/GutAnalysisToolbox/models/2D_enteric_neuron_v4_1.zip-20250724102211
- https://sites.imagej.net/GutAnalysisToolbox/models/2D_enteric_neuron_subtype_v4.zip-20250724102211

Download as the plain filenames shown in the table; retain the original StarDist ZIPs zipped. Use `shasum -a 256` to verify. If a model differs, keep it separate and ask before substituting it.

For ganglia, install the **complete official model directory**, including its descriptor, weights and supplied assets, through the updater or the final pinned model pack. Do not download only the `.pt` file and assume the rest. Public official directory:
https://sites.imagej.net/GutAnalysisToolbox/models/2D_Ganglia_RGB_v3.bioimage.io.model/

Use the supported setup instructions below and save the selected engine,
installed JAR versions/paths and initialization log. No separate prebuilt engine
pack is required. Do not create an empty `engines` directory merely to pass GAT's
startup check. The supported API installer, full model run and resulting
installed-Fiji GAT ganglia command have now passed native Mac validation. The
menu-driven setup flow and every security/interaction prompt still need to be
observed on this physical Mac.

### Supported initialization when the fresh GAT dashboard asks for engines

The observed preflight message is **GAT – DeepImageJ not initialized**, directing
you to **Plugins → DeepImageJ → DeepImageJ Run**. That is a setup blocker, not
proof that the neuron worker failed. Open that actual plugin, select the installed
`2D_Ganglia_RGB_v3.bioimage.io.model`, and follow its model/CPU-engine setup flow.
Keep its logs and approve downloads according to your rules. Do not choose a
TensorFlow engine for this TorchScript model.

If the GUI does not offer a clear install action, the installed JDLL exposes the
following supported installer used by the prepared clean-Fiji validation lane.
After approval for these official dependency downloads, run this in Fiji's
Groovy Script Editor. It uses the real installed classes and this Fiji's own
root, without Python, Maven, a fake sentinel or an empty-directory workaround:

```groovy
import ij.IJ

def loader = IJ.getClassLoader()
def versions = Class.forName("io.bioimage.modelrunner.versionmanagement.SupportedVersions", true, loader)
def resolved = versions.getMethod("getJavaVersionForPythonVersion", String.class, String.class)
                       .invoke(null, "pytorch", "2.4.1+cpu")
if (resolved != "2.0.0") throw new IllegalStateException("Unexpected JDLL catalog result: " + resolved)
def root = new File(IJ.getDirectory("imagej"), "engines")
def installer = Class.forName("io.bioimage.modelrunner.engine.installation.EngineInstall", true, loader)
installer.getMethod("installEngineWithArgsInDir", String.class, String.class,
                    Boolean.TYPE, Boolean.TYPE, String.class)
         .invoke(null, "pytorch", "2.0.0", true, false, root.getAbsolutePath())
IJ.log("Engine installer returned. Verify all hashes and run the full model before marking initialization PASS.")
```

Expected engine directory under the reported Fiji root:
`engines/pytorch-2.0.0-2.0.0-macosx-arm64-cpu/`.
Verify these pinned files. Download the last native CPU JAR from its official
Maven URL if the installer did not provide it; save/copy it into this engine
directory, **not Fiji's global jars/plugins**. Do not replace a mismatched file
without recording the discrepancy and asking whether to use the pinned setup.

| Filename | SHA-256 |
| --- | --- |
| `api-0.22.1.jar` | `1aa9e0719fa134e5690796c705c35a01641f12925c22725756c7eb7f35cb84eb` |
| `pytorch-engine-0.22.1.jar` | `ffd646505386188ac085ef07ab24cd24da817fd760ed306b885a9dbce515e627` |
| `pytorch-jni-2.0.0-0.22.1.jar` | `ccebb78ddeedb9a4b136164caf8bac2d61d0875f40708114b15c0457b1aa57c6` |
| `dl-modelrunner-pytorch-0.4.4.jar` | `004633ad168ae3438b2e53a0834c29ca8c2637d4c63c55ad6550b9e068c17933` |
| `jna-5.13.0.jar` | `66d4f819a062a51a1d5627bffc23fac55d1677f0e0a1feba144aabdd670a64bb` |
| `commons-compress-1.22.jar` | `53d04a0efc7223baecaa303bd5d298eb0600e6b82b4076f9cecd558b97ba760b` |
| `slf4j-api-2.0.6.jar` | `2f2a92d410b268139d7d63b75ed25e21995cfe4100c19bf23577cfdbc8077bda` |
| `pytorch-native-cpu-2.0.0-osx-aarch64.jar` | `5d986c6872872b798838e477569d063519c58210563187a76974bbe8deae6995` |

Official native CPU JAR:
https://repo1.maven.org/maven2/ai/djl/pytorch/pytorch-native-cpu/2.0.0/pytorch-native-cpu-2.0.0-osx-aarch64.jar

Restart Fiji after dependency setup. Run the supplied public ganglia model input
through DeepImageJ and then the GAT ganglia path, and save the output/log before
claiming readiness. If any required JAR, model, class or native load fails,
report that exact error. Merely seeing an engines folder or an installer return
is insufficient. The bounded clean-install/native test of this exact pinned
setup now passes, including the actual GAT ganglia command on original and fork.
That evidence does not replace checking this physical Mac or certify every
interactive option, format or biological measurement.

The audited JDLL 0.6.2-SNAPSHOT resolves the model's declared `PyTorch 2.4.1+cpu` to its available `PyTorch 2.0.0` CPU engine using DJL 0.22.1. Real native ARM model tests have run through that engine; do not “repair” the descriptor to say 2.0 or upgrade it blindly. The native worker for neuron/subtype inference is separate and does not require loading legacy TensorFlow 1.15 in Fiji. Keep the copied model and engine files identical across original and fork for a fair comparison.

## 6 Install the baseline and fork overlays

Quit both Fiji copies before changing their files. Inspect both downloaded archives and their manifests before extraction. Verify ZIP hashes, source commits, actual filenames and all declared companion modules. Reject absolute paths, parent-directory traversal or unexpected executable installation locations.

In each **test copy only**, move any updater-installed GAT plugin JAR to the workspace's corresponding `Backups` folder outside Fiji, then install exactly the intended baseline or fork JAR. Do not leave two GAT versions on one classpath. Never remove unrelated Fiji dependencies to suppress an error. Merge overlay contents into the actual Fiji root; do not replace the entire `plugins` or `jars` folder.

The fork's neuron module requires this arrangement:

```text
Fork/Fiji/
  Fiji.app/
  plugins/GutAnalysisToolbox_-2.0.1-apple-silicon.4.jar
  gat-native-inference/gat-native-inference.jar
  gat-native-inference/lib/<complete pinned worker dependencies>
  models/<verified model files>
  engines/<verified DeepImageJ engine>
  gat-native-alignment/gat-native-alignment.jar
  gat-native-alignment/lib/<complete pinned alignment dependencies>
```

Keep worker JAR and `lib` together. Never place worker TensorFlow dependencies in Fiji's `jars` or `plugins`. This release includes `gat-native-alignment/`: keep its worker JAR, full `lib` directory, GPL-3.0 license and original source/notices together, outside Fiji's global classpath. The matching archive BUILD_INFO records `inference_bundle_sha256` and `alignment_bundle_sha256` for preview 4. Those identify the constituent build archives, not a hash of an extracted directory.

The unchanged original copy must not contain the fork's adapter/plugin or silently gain its worker as a substitute. A failure in the original is valid evidence when the dependency/input environment is otherwise matched. Preserve logs before closing a failed baseline process.

After overlay installation, do not run the updater again during paired tests. It may replace the selected GAT JAR or change dependencies. If updating becomes necessary, preserve the old inventory, obtain any needed permission, rehash files and start a newly labelled comparison.

## 7 Full installed Fiji and GAT startup check

For each copy, independently:

1. Launch the copy's own `Fiji.app` and save architecture/version/root information from inside that JVM.
2. Open the GATV2 entry. The inspected plugin configuration registers **Plugins → GutAnalysisToolbox → GATV2**. If the final installation exposes `GATV2 → Start GAT`, record the actual menu and loaded JAR rather than launching an old `.ijm` macro by accident.
3. Screenshot every first-run/preflight message. Verify models, DeepImageJ engine, required plugin commands and dashboard controls. Do not dismiss an error by manufacturing a sentinel file.
4. For the fork, verify the Log identifies the isolated native TensorFlow worker when neuron/subtype inference actually runs. Record the worker's real Java executable and architecture, not merely its folder's presence.
5. Open a public image, inspect channel names and C/Z/T dimensions, change nothing, close without saving. Confirm menus, dialogs and normal exit work.
6. Repeat startup once after quitting. Record repeated launch, stale-worker/window behavior and whether settings persist as expected.

Old GAT `.ijm` macros are separate legacy entry points and are not automatically patched by GATV2. Record their status separately. Do not use a legacy macro to judge whether the fork's new worker is reached. Only the approved, isolated original-baseline probe should deliberately attempt known incompatible legacy native runtimes; a crash must not take the fork test session or unsaved work with it.

## 8 Public inputs and reproducible synthetic controls

Use **test kit preview 2.1**, not the superseded four-frame preview-2 kit.
The corrected ZIP is 4,726,604 bytes, with the SHA-256 in the package table.
It extracts to `GAT-M1-test-kit/`. Read its README, `manifest.json`,
`SHA256SUMS` and `fixtures/image-inventory.tsv` before running anything. Its
fixtures open directly in Fiji; the optional `developer-validation/` sources are
not prerequisites for the manual tests. The kit retains its historical preview-2
title and evidence. Its input/reference bytes also serve these unchanged core
controls in preview 4. Follow **this v6 handoff** for current installation/status,
not the kit's older first-install status; use the pinned preview-4 repository
source for new developer builds. The separate multiplex add-on supplies the
newly corrected workflow's exact native inputs and references.

| Test | Files under `GAT-M1-test-kit/fixtures/` | Settings and expected result |
| --- | --- | --- |
| Hu technical fixture | `Hu_crop.tif` | 175×175 uint8, C1/Z1/T1; raw 39-cell reference only with matched inference/NMS configuration, not arbitrary GUI rescaling/filters |
| Calcium | `calcium-fixture.tif`, `calcium-roi.zip` | 8×8 float32, C1/Z3/T1; choose planes 1–3 as frames, baseline 1–2, top-left 2×2 ROI named SyntheticCell_1; MAX=200 and F/F0 `[1,1,2]`; verify actual three-row export |
| SIFT single | `sift-workflow-input.tif`, `sift-workflow-expected.tif` | 256×256 uint8, C1/Z1/T10, reference frame 1; saved/reopened pixels should match the expected aligned stack |
| SIFT batch | `sift-batch-input.tif`, `sift-batch-expected.tif` | 256×256 uint8, input C2/Z1/T12, output C1/Z1/T12; intended channel 1, reference frame 1; compare saved pixels and calibration with reopened files |
| Template Matching 8-bit | `template-8bit-input.tif`, `template-8bit-expected.tif` | 128×96, C1/Z1/T12; **reference frame 2**; integer method 5, subpixel off; exact expected stack comparison |
| Template Matching 16-bit | `template-16bit-input.tif`, `template-16bit-expected.tif` | Same geometry/reference as above, preserving 16-bit pixels and metadata |

The Template Matching cases have **12 frames**, because the full GAT alignment
workflow rejects fewer than 10. Their expected shifts are `(3,-2), (0,0), (7,-7),
(3,-2)` repeated for three four-frame cycles, with reference frame 2. The exact
12-frame 8/16-bit client→worker controls were checked on Linux; the recorded
native-Mac paired alignment reference uses a different seeded fixture. Do not
claim this exact kit's 12-frame pixels were already tested on the physical M1.
Do not use the obsolete four-frame kit for the GAT dashboard.

The kit's historical calcium TIFF uses **C1/Z3/T1, pixel sizes 1×1 and frame
interval 0**. Appendix A creates an alternative temporal fixture with C1/Z1/T3,
pixel sizes 0.5×0.75 and interval 1.25. They share the `[1,1,2]` numerical control,
but their dimensions/calibration are intentionally different; do not compare
metadata as if they were the same file. The kit's Hu TIFF also carries its own
non-unit calibration (about 1.51445 in X/Y); read the actual unit and calibration
in Fiji. Full GAT rescaling can therefore differ from the raw-worker fixture.

Use the validation bundle's manifest for provenance and hashes. Each fixture must have a source, SHA-256, dimensions, data type, channels, Z/T ordering, calibration and purpose recorded before testing. Keep original fixtures read-only by convention and make per-run copies. Never overwrite reference masks.

First public Hu sample:
https://raw.githubusercontent.com/pr4deepr/GutAnalysisToolbox/61d57c4e4bcfe82aa0369100c0a3b0739b70affa/Sample%20Images/2D_enteric_neuron_IF/DYM_22_7_Pr_Hu_crop.tif

Save as `DYM_22_7_Pr_Hu_crop.tif`. SHA-256:
`55251741add488f9a08cf5b33a4ee8ec3fd3023e25ffb0fc18800f80953948d7`

It is a 175×175 uint8 image. The supplied compact raw-worker/NMS fixtures use neuron probability 0.5, subtype probability 0.4, NMS 0.3 and boundary exclusion 2. Their historical raw counts are 39 neurons and 3 subtype detections. **Those are raw technical-fixture counts, not an unconditional full-GAT dashboard result.** Full GAT can rescale, change calibration and apply size/border/overlap filters. Match every stage before comparing counts. Subtype inference on this Hu image is an execution control, not a biological subtype accuracy test.

Ganglia public test arrays from the same official model directory:

- `test-input.npy-20250501124309`, SHA-256 `986cfd751c0e2cfd3367cfc39b5583c10e55da2f1a7772d73845c6395eefd681`
- `test-output.npy-20250501124309`, SHA-256 `c6ca99486a9cdb6c6a8f273e17e5e35ccb8a19832fb5097625f4951c44cb72c9`

The input is uint8 `[1,3,1024,1024]` in Fortran storage order. The supplied reference is `[1,1,768,768]`, while the reached engines produce 1024×1024. Do not invent a crop or relax a tolerance to force parity. A 64-pixel halo crop alone yields 896×896. Use the final command fixture and published native outputs for reproducible execution checks; label the original reference mismatch unresolved unless a validated complete transformation is supplied.

The shipped validation sources provide exact synthetic patterns, known shifts, label maps and calcium movies. They can be inspected without developer tools. For an alternative calcium GUI control without any downloads beyond Fiji, use Appendix A. It has different C/Z/T and calibration from the historical kit TIFF, as documented above.

## 9 Workflow acceptance checklist

Run the original and fork on identical fresh fixture copies and separately named output directories. Save exact GUI options, logs and output hashes for each. Do not mark an entire row PASS if only a helper or library-load subcheck ran.

### Neurons and subtypes

- Run the pinned raw worker/NMS fixture if its ready-to-run validation package is supplied; verify probabilities, finite values, raw label numbering, canonical masks, counts, centers, areas and original-image intensity measurements against the published references.
- Run the public Hu image through the full GATV2 neuron workflow, recording input calibration, rescaling, model, normalization percentiles, requested tiles, thresholds, minimum size and border settings. Save the actual segmentation, ROI ZIP, counts/measurement CSV and overlay; reopen all of them.
- Repeat on a representative public subtype image from the final fixture manifest with Hu and subtype channels explicitly identified. Check cell overlap and count denominators. Never call Hu-only subtype smoke biological validation.
- Test image dimensions not divisible by tiling requirements, one tile and multiple tiles, all-zero and constant images, and repeat-run consistency. Preserve boundary differences rather than tuning them away.
- Compare label IDs separately from object shapes. Report mask IoU, differing pixels, one-to-one matched objects, area/centroid/intensity differences, and subpixel polygon-vertex distances. Equal counts alone do not establish parity.

### Ganglia

- Verify the exact GAT → DeepImageJ conversion → RDF preprocessing contract before inference. Corrected GAT retains byte-range R=Hu/G=ganglia/B=Hu pixels; the RDF applies 1/255 and ImageNet normalization once. The contract fixture's white Hu pixel reaches the model near +2.248898; the old double-scaled path reached about −2.100770.
- Run the actual GAT ganglia workflow, not only DJL/JDLL. Check the output belongs to that invocation despite an unrelated pre-existing image window. Save the returned binary mask, overlay, size-filtered labels, counts per ganglion and area measurements. Reopen outputs and check source pixels are unchanged.
- Keep supplied weights, metadata and thresholds unchanged. Correcting double scaling can change scientific masks: report this as a bug correction, not legacy-output parity.
- Test optional manual painting separately: add/remove a clearly marked synthetic region, finish review, verify precisely that edit survives filtering/export. Ask me to make biological decisions.
- Engine-only cross-platform context: the public raw direct-PyTorch outputs previously differed by at most 1.78814e-6 and had equal threshold-0.6 masks; JDLL's tiled binary outputs differed by one pixel out of 1,048,576. These observations do not certify the full corrected GAT pipeline or solve the differently sized supplied reference.

### Registration and saved results

- SIFT single: use the exact known-shift fixture; confirm returned image and saved/reopened TIFF are aligned. Inspect residual pixel error, not just the separate window the SIFT plugin creates. Verify calibration, frame interval, reference frame and unchanged original.
- SIFT batch: use the two-channel, 12-frame fixture with channel 2 initially selected. Verify intended channel 1 output, C1/Z1/T12, correct reference pixels and unchanged input file. Compare output calibration with the **reopened input TIFF**; TIFF rational storage may encode 0.75 as 0.7500001875000468.
- Template Matching: run the pinned algorithm and settings through actual single and batch GAT paths. If the final fork includes the native adapter, confirm its process/JAR architecture and returned shifts. Do not silently fall back to SIFT. Inspect logs and saved results; a protective guard is BLOCKED, not an alignment pass.
- StackReg/TurboReg: verify the supported GAT helper on a known rigid shift, then separately check any requested batch path. The original code's explicitly unimplemented batch path must not be described as working because the plugin itself passes.
- Repeat with non-square pixels, two channels, nonzero reference frame, user cancellation and invalid/missing plugin result. Failed alignment must not overwrite input or publish stale output. If motion CSV fields are placeholder zeros, report that defect even when the image aligns.

### Calcium end to end

- Use the 8×8, three-frame movie with values 100/100/200 in a 2×2 ROI. Select MAX frames 1–3: that ROI must be 200 in a new one-plane projection, while source frame 1 remains 100.
- Select baseline frames 1–2. F/F0 in that ROI must be `[1, 1, 2]`. This is F/F0, not ΔF/F0. Verify non-ROI control pixels remain 1.
- Create/import the 2×2 ROI, give it a known name, measure all frames, save CSV, normalized TIFF and ROI ZIP, then reopen. Check three numeric measurement rows, ROI position/name, dimensions, frame timing and calibration.
- Test selected subranges, cancelled dialogs, baseline zero and nonfinite values separately. The current division path preserves ImageJ's 0/0→NaN semantics; do not silently replace NaN with zero. Flag whether downstream export handles it intelligibly.
- Automatic calcium StarDist has been a disabled stub in the original code. Only mark it working if the final tested source actually implements it and returned ROIs are verified. A “segmentation completed” message alone is insufficient.

### Multiplex

Use the separate checksum-verified **GAT-multiplex-manual-fixtures** add-on listed
in the package table. Read its README first. It supplies the exact synthetic
native-test input images, saved references and ROI/measurement evidence; no
build tools are needed to open the TIFFs in Fiji. Keep inputs and references in
separate folders, and make a new output folder per original/fork run.

- Put all nine `Layer1_`, `Layer2_` and `Layer3_` TIFFs together in one **flat input folder**, not layer subfolders. Select common marker `Hu`, three rounds and layer prefix `Layer`, following the kit's exact GUI instructions. Record actual settings/dialogs.
- Compare all seven output channels and their labels/order, C/Z/T, unchanged source images, and both saved/reopened aligned and common-marker QC stacks. Compare calibration with the **reopened input TIFF**, including non-square pixels, unit and frame interval.
- The corrected native SIFT fixture gives pixel-exact later-round marker interiors. Forced-MOPS service controls give residual MSE 0.180–0.360, versus 2,751–4,313 before the fix, and landmark errors at most about 0.0392 px. Inspect the kit's exact per-channel references and paired ROI coordinates, not just a visual overlay or global correlation.
- The ordinary GUI does not expose the harness's forced-MOPS setting. `Finetune_parameters` is stored but unused by the inspected service. Do not claim a normal GUI SIFT run exercised MOPS or natural fallback; that boundary needs the documented optional developer harness or a genuine captured fallback.
- Test no usable landmarks, missing markers/rounds and mismatched dimensions as explicit errors/cancellations without stale output. Computation-time cancellation and the unavailable Block Matching command remain separately unverified.
- The confirmed saved-output defect existed in the unchanged pre-fork Java service and in preview 2. It is a result/ROI ownership correction, not proof that ARM SIFT/MOPS numerical libraries were incompatible.

### Physical OpenCL and CLIJ workflows

- Record actual OpenCL platform/device name, CPU/GPU type, driver/version and device selected by CLIJ2. An Apple GPU name in a system report does not prove CLIJ access.
- Run 8-, 16- and 32-bit ImagePlus push → simple known kernel → pull controls and compare every pixel with a CPU/ImageJ reference. JOCL can load while device enumeration or kernels fail.
- Run actual GAT spatial analysis on the known label layout; compare neighbor counts/distances and exported CSV against the CPU expectation. Test at/just outside the distance boundary.
- Run the full ROI/label overlap route, with known disjoint, partial and complete overlaps. Distinguish the actual ROI Manager command chain from a private helper-only control.
- Test EDF on identical slices (known invariant) and a public/synthetic stack with different planes in focus; verify the chosen algorithm and any CPU comparison. Do not call an unrelated projection “EDF.”
- The hosted virtual M1 previously returned OpenCL device-query error −30, although native OS/JOCL libraries loaded. The physical M1 is needed to settle real device/kernel availability. Treat no device as a concrete environment blocker and retain the error; do not claim GPU success from an engine DLL load.
- Avoid unnecessary BridJ/off-heap paths. The audited JOCL includes arm64, while a shipped legacy BridJ macOS binary is x86-64. Test the actual reached path rather than declaring all CLIJ broken or all compatible.

### Morphology, counts, formats, merge and export

- MorphoLibJ: known-size labels, threshold boundary inclusion, border-label removal, connectivity and preserved calibration. Java-only code is still subject to workflow/result-handling bugs.
- Counts/areas: known label IDs and pixel counts, zero objects, ganglion minimum-count filtering and calibrated area. Use unequal pixel widths/heights to reveal incorrect area conversion; report rather than hiding a pre-existing calculation bug.
- Image IO: 8/16/32-bit TIFF, RGB, C/Z/T hyperstack, calibration and frame interval save/reopen. For CZI/LIF/other formats, use a public vendor/Bio-Formats sample with exact compression/series metadata and record selected series/channels.
- JPEG-XR: use a genuinely JPEG-XR-compressed public microscopy sample or a validated codec fixture. The shipped old macOS decoder was Intel-only; a plain TIFF or non-JPEG-XR CZI does not exercise it. Use the optional overlay above only after verifying its dependencies and hash, then test that precise path and sample separately.
- HDF5 and other native formats: only claim support after a real public sample decode/write control. The presence of an arm64 library alone is insufficient.
- Merge/export: two known CSVs with distinct row IDs, headers, units, Unicode/spaces in names, missing/empty inputs, and a deliberately existing destination. Check row counts/content and explicit overwrite behavior; never test by deleting a real result.
- Reopen all saved ROI ZIPs, masks, overlays and CSVs. Check titles, column definitions, identifiers, units, output paths and whether the original images remain unchanged.

## 10 Optional automated checks without assuming a developer toolchain

Prefer a final validation pack that runs with Fiji's bundled native Java and includes its checksum-pinned dependencies. Inspect its scripts first, obtain required execution approval, and invoke the exact documented command from that pack. Record which production JAR it loads: accidentally testing source `target/classes` while using a different installed JAR is not installed-Fiji validation.

The repository's current developer workflow runners use Python 3 and compiled Java classes; Python is not guaranteed on a clean Mac. If no ready-to-run pack exists, either complete the GUI checks first or request permission for this optional developer route:

1. Use the Fiji-bundled `java` and `javac` by full verified path. If a full JDK is genuinely unavailable, obtain a native ARM JDK from [Eclipse Adoptium](https://adoptium.net/) after approval.
2. Download the **pinned commit source ZIP** through GitHub in the browser. Git is optional; do not trigger installation of Apple's command-line developer tools just by typing `git`.
3. If builds are needed, install the official Maven binary distribution from [Apache Maven](https://maven.apache.org/download.cgi) in this workspace; verify its published checksums/signature. Use its `bin/mvn` by full path. Do not assume Homebrew.
4. If a supplied Python runner is needed, use the official macOS installer from [python.org](https://www.python.org/downloads/macos/) after explaining that it installs another runtime and obtaining approval. No Python packages should be added unless the exact runner declares them. Prefer built-in-only runners over installing NumPy just to inspect a log.
5. Build the original and fork in separate source directories at the pinned commits. Save all build/test output, Java/Maven versions and produced JAR hashes. Follow that revision's module instructions, including any final native-alignment module; do not copy an outdated build command from preview 1.
6. Run fixture comparisons and workflow harnesses separately from normal interactive Fiji sessions. Use bounded processes and original scripts' failure handling. Capture model-load/cold-start time separately from inference-only time. A timeout remains a failure/blocker until diagnosed.

Do not begin a local source modification to “make the test pass” without separately asking me. A proposed patch and reproducible failing fixture are useful results.

## 11 Report and return evidence

Create `Reports/summary.md` plus a machine-readable `results.csv` or JSON. Each check needs:

- Workflow and exact boundary: library load, helper, actual GAT command, full GUI, or saved/exported result
- Original and fork status: PASS, FAIL, BLOCKED or NOT_RUN, with exact reason
- Source commit, package/JAR/model/input hashes and all relevant loaded plugin versions/paths
- Hardware, macOS, native/translated state, actual Fiji and worker Java version/architecture/path, heap/thread settings and OpenCL device
- Input source, dimensions/type, axes, calibration, channel selections, transforms/crops, model and settings
- Expected numerical/image outcome and actual outcome, including label/count/area/centroid/intensity/IoU and subpixel differences where applicable
- Cold launch/model-load time, inference/processing time and observed memory, labelled with this Mac's hardware and run conditions
- Logs, errors, screenshots and output paths; keep failures before retries and distinguish cancelled tests

Suggested report layout:

```text
Reports/
  summary.md
  results.csv
  inventory/
  original/<case-id>/
  fork/<case-id>/
  comparisons/
  screenshots/
  checksums.txt
```

Keep public/synthetic images and resulting small outputs in the report. Exclude downloaded engine JARs, model weights and full Fiji copies from the report ZIP; include their hashes and provenance instead. Exclude usernames where unnecessary, credentials, serial numbers, private research images and unrelated logs. Review screenshots for private information before packaging. In Finder, Compress the Reports folder, or use built-in `ditto -c -k --keepParent` on this report directory. Verify the ZIP opens. Share it only back to me through this session after any required approval; do not upload it to GitHub or a third-party issue tracker.

Finish with a short recommendation: which workflows I can safely try with the stated limitations, which remain blocked, and the next smallest useful test. Discuss the long-term backend choice using evidence: a shared CSBDeep/StarDist backend versus the isolated GAT worker, including output semantics, dependencies, native packaging, reproducibility, maintenance and rollback. Do not choose solely from speed on one tiny image. Do not call M1 success proof of M2–M5 support without corresponding evidence.

## Appendix A Minimal calcium fixture using only Fiji

This is an optional alternative, not a regeneration of the kit’s historical TIFF: it uses C1/Z1/T3, 0.5×0.75 pixels and 1.25-second timing instead of C1/Z3/T1, unit pixel sizes and unspecified timing. In the verified test Fiji, open File → New → Script, choose Groovy, paste this code, and run it. The only write is a TIFF you select in the save dialog. Save into the new `Inputs` folder. No external packages, network or Python are used.

```groovy
import ij.ImagePlus
import ij.ImageStack
import ij.process.FloatProcessor
import ij.io.SaveDialog
import ij.io.FileSaver
import java.util.Arrays

def stack = new ImageStack(8, 8)
for (int frame = 0; frame < 3; frame++) {
    float[] pixels = new float[64]
    Arrays.fill(pixels, 100f)
    if (frame == 2)
        for (int y = 0; y < 2; y++)
            for (int x = 0; x < 2; x++) pixels[y * 8 + x] = 200f
    stack.addSlice(new FloatProcessor(8, 8, pixels))
}
def image = new ImagePlus("calcium-public-synthetic", stack)
image.setDimensions(1, 1, 3)
image.setOpenAsHyperStack(true)
image.getCalibration().pixelWidth = 0.5
image.getCalibration().pixelHeight = 0.75
image.getCalibration().frameInterval = 1.25
image.getCalibration().setUnit("um")
def save = new SaveDialog("Save synthetic calcium fixture", "calcium-fixture", ".tif")
if (save.getFileName() != null) {
    if (!new FileSaver(image).saveAsTiffStack(save.getDirectory() + save.getFileName()))
        throw new IOException("TIFF save failed")
    image.show()
}
```

Record its SHA-256 after saving. Select the top-left 2×2 ROI at x=0,y=0 for the `[1,1,2]` calcium control. TIFF byte hashes can vary with metadata/version even when pixels are identical, so compare reopened dimensions, calibration and pixel values as well as recording the file hash.

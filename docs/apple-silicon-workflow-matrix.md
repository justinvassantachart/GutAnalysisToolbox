# Apple Silicon workflow coverage

**Updated 2026-10-06. Scope: Java GATV2 in this fork.** Native evidence comes
from hosted Apple M1 (Virtual), macOS 14.8.9 and 15.7.9, arm64 Java 17/21. It is not a
physical-M1 installation, GPU or complete interactive dashboard certification.
This matrix accompanies hardening **2.0.1-apple-silicon.4**. Use the matching
ZIP and clean-Mac handoff asset from the [release index](https://github.com/justinvassantachart/GutAnalysisToolbox/releases).
Verify the version/source/checksum before installing; an unlisted preview is
not yet published. Preview 2 does not contain the multiplex correction.

The [6 October hardening report](https://github.com/justinvassantachart/GutAnalysisToolbox/blob/apple-silicon-preview-4/docs/validation/fork-hardening-2026-10-06.md)
distinguishes current CPU/calcium regression and command checks from historical
scientific evidence. Preview 4 retains the multiplex repair and rejects
ambiguous calcium input (RGB, C>1 or combined Z/T) before analysis. Final
release-build checks are recorded on the release page. Historical sources below
are deliberately retained, not relabelled as a fresh full-corpus run.

## Evidence keys

- **Native command/component pass:** the stated code and output actually ran;
  untested surrounding UI, modes and scientific assumptions remain separate
- **Blocked:** the environment or missing implementation prevented execution
- **Pending:** a test/control must still complete reliably
- **Intentional output change:** correctness repair; old-mask equality is not
  its acceptance criterion

Primary evidence:

- [Corrected native full-service multiplex exports](https://github.com/justinvassantachart/GutAnalysisToolbox/blob/f5b814b4a8f784246d60df88032cee037ca8fd29/native-inference/validation/multiplex-full/results/mac-ab046cb/README.md): unchanged synthetic inputs/assertions, independently reopened aligned/QC TIFFs and landmark ROI archives
- [Actual retained ganglia-mask TIFFs](https://github.com/justinvassantachart/GutAnalysisToolbox/blob/f5b814b4a8f784246d60df88032cee037ca8fd29/validation/fiji-install/results/mac-mask-retention-5e2e0f4/REPORT.md): exact binary masks, raw/file hashes and calibrated reopen controls

- [Complete bounded official-Fiji install](https://github.com/justinvassantachart/GutAnalysisToolbox/blob/f5b814b4a8f784246d60df88032cee037ca8fd29/validation/fiji-install/results/mac-accepted-26298b7/REPORT.md): real updater/engine/model, both dashboards and ganglia, fork neuron/alignment; shared 854-file inventory identical

- [Completed same-host evidence job](https://github.com/justinvassantachart/GutAnalysisToolbox/blob/f5b814b4a8f784246d60df88032cee037ca8fd29/native-inference/validation/baseline/results/mac-live-dialog-ee2907e/REPORT.md), original failures and repaired passes, with all live controls
- [Final optional JPEG-XR package audit](https://github.com/justinvassantachart/GutAnalysisToolbox/blob/f5b814b4a8f784246d60df88032cee037ca8fd29/native-inference/validation/jpeg-xr/results/mac-6996dd5/REPORT.md), golden tile/ABI/source gates passed; full importer still open

- [Qualified Sonoma/Sequoia paired results](https://github.com/justinvassantachart/GutAnalysisToolbox/blob/f5b814b4a8f784246d60df88032cee037ca8fd29/native-inference/validation/baseline/results/mac-sequoia-fe5fd7b/REPORT.md), original `1870d9e`, fork `fe5fd7b`

- [Same-host unchanged original versus fork](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37357196889), original `1870d9e`, fork `69feedb`
- [Native workflow commands after ganglia/SIFT changes](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37354405010), fork `000464e`
- [Native real-image TensorFlow fixture on Java 17 and 21](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37344903137)
- [Native JPEG-XR and initial Template Matching comparisons](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37351640627)
- [371-pair Linux inference/NMS consistency report](https://github.com/justinvassantachart/GutAnalysisToolbox/blob/f5b814b4a8f784246d60df88032cee037ca8fd29/native-inference/validation/corpus/REGRESSION_REPORT.md), including the local outline counterexample

## Workflow inventory

| Workflow / option | Current evidence | Remaining acceptance checks |
| --- | --- | --- |
| Hu neuron detection using MIP | Actual GAT StarDist call on native Mac returns 39 labels; native compact fixture exactly matches legacy labels, centers and pixel measurements | Complete dashboard, ROI review, calibrated exports and representative user images |
| Subtype inference | Native real SavedModel fixture passes; Linux corpus includes Calbindin, Calretinin, ChAT, NFM and nNOS | Native multi-marker runs with and without Hu gating, all combinations and review/export; Hu-only subtype fixture is technical smoke |
| Hu/subtype label overlap and ganglia counts/areas | Java helper controls pass on native Mac and Linux | Complete multichannel workflow and biological validation |
| Imported/manual ROIs and morphology | Actual native border/size-filter/label command controls pass | Interactive edits, cancel/repeat behavior, ROI ownership and full export round trip |
| Ganglia, deep-learning RGB model | Actual native GAT → DeepImageJ → JDLL → PyTorch command passes, source unchanged, binary output geometry/calibration and saved TIFF checked | Interactive painting; official supplied reference has unresolved 768² versus 1024² shape mismatch; no biological accuracy claim |
| Ganglia input normalization | Real reached RDF contract fails in original and passes in fork | **Intentional output change:** old GAT double-normalizes; preserve fixed raw-range RGB input and model metadata |
| Ganglia expansion/import/manual modes | Native Java helpers/morphology tested | Full UI mode combinations and calibrated parameter review |
| MIP | Direct operation and accepted-dialog GAT calcium max projection pass on both original/fork and both native OS versions | More ranges, cancelled selections and full dashboard behavior |
| EDF | **Blocked on hosted Mac:** system OpenCL and JOCL load, but no usable OpenCL device | Physical-M1 push/pull and variance-fusion kernels plus paired numerical reference |
| Single-type spatial analysis | **Blocked by missing hosted OpenCL device** | Physical-M1 label dilation, touching neighbors, CSV and parametric-image correctness |
| Two-type spatial analysis | **Blocked by missing hosted OpenCL device** | Physical-M1 overlap counts, optional ganglia restriction and output checks; this is not the Java Hu-gating operation |
| Probability/rescaling/expansion tuning tools | Shared inference/morphology components tested | Each interactive tuning tool, selected image ownership and EDF option |
| SIFT calcium alignment, single | Native actual GAT save/reopen control passes with residual MSE 0 | UI selections, richer/non-translation inputs and scientific registration quality |
| SIFT calcium alignment, batch | Native two-channel/12-frame save/reopen control passes with MSE 0 and calibration/timing preserved | Larger batches, file naming, cancellation and non-first reference cases |
| Template Matching alignment | Native Mac and Linux port/actual GAT adapter match 300 frame outputs, references 1/2/3 and public movie 1/71; exact shifts and aligned-pixel hashes | Full native single/batch GUI and larger movies; 8/16-bit and bounded stack sizes only |
| Motion CSV | Unit tests and native six-CSV/300-row checks verify algorithm-owned Template Matching shifts and true frame IDs; fabricated zero/stale-table export removed | Full downstream CSV consumer integration. SIFT transforms are unavailable; combined CSV is template refinement only |
| StackReg/TurboReg | Native direct helper controls pass | **GAT batch StackReg remains unimplemented on every platform.** A plugin helper pass does not implement that option |
| Calcium F/F0, ROI intensity, CSV/ROI ZIP | Accepted-dialog original and fork controls both PASS on Sonoma and Sequoia, F/F0 `[1,1,2]`, ROI/CSV round trip | Full GUI, zero-baseline/nonfinite cases and representative biological movies |
| Calcium automatic StarDist ROI generation | **Disabled stub in original and fork** | Requires a separately specified implementation/validation; use imported or manual ROIs |
| Temporal color coding | Native small 8-bit helper test passes | Selected frame range, projection, scale, 16-bit/float behavior and complete GUI/save flow |
| Multiplex registration | Corrected native full service and real command route pass: SIFT later-marker interiors exact; forced-MOPS MSE 0.180–0.360; seven-channel order, distinct exported landmarks, aligned/QC calibration, source preservation, final dialogs and input/error cases verified from saved files | Biological samples, natural SIFT failure→MOPS fallback, unavailable Block Matching command, computation-time cancellation and complete interactive modes. Preview 2 retains the confirmed unaligned-export/calibration defects |
| CSV merging | Native helper checks for small files and overwrite refusal pass | Quoted/mixed schemas, non-ASCII paths, larger trees and UI. Default merger does not enforce identical headers |
| Summary CSV / label TIFF export | Native basic counts and lossless label round-trip helpers pass; SIFT/ganglia saved outputs checked | Every workflow's overlays, ROI ZIPs, multichannel summaries and calibration |
| Ordinary TIFF and microscopy IO | TIFF controls pass; actual readers depend on format/compression | Representative LIF/CZI/HDF5/user formats and metadata; a filename extension does not identify its codec |
| JPEG-XR codec | Rebuilt native arm64 JNI passes 13 official golden fixtures, 59 JNI signatures and vector API checks through Bio-Formats 8.5.0 service/codec | Final packaged resource-JAR/source/license gates passed; optional release add-on available. Full installed-Fiji loader/updater and JPEG-XR CZI reader sample still needed |
| Legacy `.ijm` macros / QuPath | Outside the GATV2 adapter | Test separately; do not infer arbitrary direct StarDist calls were repaired |

## Before/after interpretation

The first same-host run preserves both source revisions and plugin provenance.
Original StarDist's first failure is a Java 21 loader class cast before JNI;
its fallback returns the original 8-bit input, which the test correctly rejects.
The fork returns a new 16-bit 39-object label image. Original Template Matching
leaves the synthetic shifts unchanged; the fork matches the known translated
pixels exactly. Original ganglia command execution **passes**, although its
input-contract test shows double normalization. Unaffected original helper
passes are retained. Not every old workflow is expected to fail.

The first paired job's calcium automation did not reliably accept its dialog.
That ambiguity is now resolved: corrected accepted-dialog controls pass on BOTH
original and fork on Sonoma and Sequoia. Early URL-loader diagnostic jobs remain recorded as failed because the old
TF native-load modal timed out. The later completed same-host evidence job
records that exact unanswered error dialog and ends only the isolated original
process; its repaired output gates and all three live observer controls pass.
The historical reports retain their original timeout classifications.
Do not call calcium an established old numerical or architecture defect.

## Native dependency status

- **TensorFlow Java:** old TF1.15 supplies Intel macOS JNI only. The fork uses a
  separate TF Java1.2.0/TF2.21 arm64 process. Python TensorFlow/Metal installation
  cannot repair Fiji's Java classpath
- **Template Matching:** the distributed old OpenCV is Intel-only. The isolated
  port uses OpenCV4.11.0/JavaCPP1.5.12, with complete original/modified source and
  GPL notices supplied beside the worker
- **DeepImageJ/JDLL:** shipped engine resolution selects PyTorch2.0.0 CPU with
  DJL0.22.1 for the model declared2.4.1+cpu. Actual native loading/inference and
  tiled RDF processing pass. Version fallback is not proof of reference parity
- **OpenCL:** JOCL2.0.5 contains arm64 native code and loads. The system framework
  reports Apple OpenCL1.2, but all device queries on the hosted VM return -30.
  That is an environment blocker, not evidence that physical M1 OpenCL fails.
  BridJ0.7.0's macOS binary is Intel-only; standard tested transfers still need
  actual device execution, including any off-heap route
- **MorphoLibJ1.6.5, StackReg/TurboReg2.0.1, mpicbg1.6.6:** relevant algorithms are
  Java; named native command tests pass. This reduces architecture risk without
  certifying every interactive workflow
- **JPEG-XR:** upstream jxrlib-all0.2.4 lacks arm64. The unchanged codec can be
  source-built; native-lib-loader2.5.0 recognizes `META-INF/lib/osx_arm64`.
  Wrapper headers are GPL-2.0-or-later despite a BSD POM; preserve both sets of
  notices/corresponding source and do not describe the wrapper as BSD-only

The [historical initial dependency audit](https://github.com/justinvassantachart/GutAnalysisToolbox/blob/f5b814b4a8f784246d60df88032cee037ca8fd29/docs/apple-silicon-dependency-audit.md)
retains official update-site/source links and artifact findings. Its earlier
untested statuses are superseded by this matrix. Exact pinned dependencies and
checksums are in [the workflow harness](https://github.com/justinvassantachart/GutAnalysisToolbox/blob/f5b814b4a8f784246d60df88032cee037ca8fd29/native-inference/validation/workflows/).

## Remaining physical-Mac acceptance

Use the clean-install handoff with isolated original/fork Fiji copies. Record
native Java/chip/OS, ImageJ data root, all updater JARs/models/engines, known
input names/hashes, actual outputs, UI screenshots, logs, and pass/fail/blocked
per row. GPU identification alone is insufficient: exercise transfers and
kernels. Review cell masks and per-object geometry, not counts alone. Keep
private research images local; report public/synthetic fixtures first.

No full M1–M5 certification, physical-GPU benchmark or maintainer acceptance is
claimed. The test suite and documented blockers are intended to make the next
physical-M1 checks reproducible and honest.

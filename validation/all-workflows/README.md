# All-workflow acceptance additions

`NoHuImportedRoiProbe.java` is a bounded, real-production **imported-ROI** workflow
probe. It uses no mocks, inference replacement, model execution or production
source changes. At preparation time it is new validation code, not passed
evidence. Run original V2 `1870d9e` and the exact fork revision in separate
disposable processes with the same ImageJ/MorphoLibJ dependencies.

## Runtime and invocation

- AWT is required: hosted macOS arm64, or public Ubuntu with Xvfb. OpenCL is not
  required for this probe. The current no-X11 cloud process cannot execute it.
- Real ImageJ commands `Connected Components Labeling` and `Label Map to ROIs`
  must be registered from the installed MorphoLibJ 1.6.5 plugin. The probe never
  inserts command registrations. Their actual class mappings are recorded.
- Use the real pinned subtype model ZIP. The pipeline insists the file exists
  even with all markers imported. Its hash is recorded, but it is never loaded
  for inference in these cases. Do not substitute a fake model.
- Compile against one production variant's classes, ImageJ and that variant's
  regular classpath. Run against that same variant. Never put original and fork
  production classes on one classpath.
- External per-process limit: 300 seconds, 768 MiB heap, one active CPU, 3 GiB
  process-tree RSS, serial cases. Use the existing workflow runner's `execute`
  limiter or the fresh-Fiji launcher's existing process guard. A deadline is
  incomplete evidence, not successful cancellation.

The standalone main accepts exactly three positional arguments:

```
java [normal installed ImageJ runtime options] NoHuImportedRoiProbe \
  /absolute/new-empty-evidence-directory \
  /absolute/2D_enteric_neuron_subtype_v4.zip \
  unchanged
```

It initializes `ImageJ(NO_SHOW)` only if no ImageJ application already exists.
An ordinary `ij.jar` classpath without installed plugin discovery will report
`BLOCKED_SETUP`; this is not evidence of a pipeline failure.

For the actual Fiji launcher, package the compiled class as a validation-only
plugin in the disposable installation and invoke through the regular ImageJ
macro route:

```
run("No-Hu Imported ROI Probe", "/absolute/evidence\n/absolute/model.zip\nunchanged");
```

The plugin JAR's `plugins.config` entry is:

```
Plugins>GAT Validation, "No-Hu Imported ROI Probe", NoHuImportedRoiProbe
```

Both entry points terminate the process: run this probe **only in a dedicated,
disposable validation Fiji process**, never a user's running installation.
They exit 0 for the passed scope, 1 for reached failure, or 2 for setup block or
fatal harness error. Always read `report.json` rather than treating a launcher
exit code as a workflow pass.

## Cases and evidence

Run every case in a fresh process and new empty output directory:

1. `unchanged`: import two A and two B rectangles; accept each review unchanged.
   Expected counts A=2, B=2, A+B=1. Exact intersection is a 6×12 rectangle.
2. `delete-one`: in A's real review, delete the first (overlapping) ROI and retain
   the second through the actual ROI Manager. Expected A=1, B=2, A+B=0. This
   checks that manual edits reach counts, combinations and exports.
3. `delete-all`: delete all A ROIs in A's real review. Correct expected output is
   A=0, B=2, A+B=0 and absent empty ROI archives. Original V2's shared
   `ReviewUI` fallback restores labels while leaving ROI Manager empty, so this
   is a strict bug-reproduction case expected to fail until repaired. Do not
   weaken its expectations or label it native-backend divergence.

The controller only accepts exact `Review: A (review)` and `Review: B (review)`
dialogs in the expected order, after checking the seeded ROI geometry. It
clicks the real OK button. It then clicks End on the exact `Workflow finished`
dialog only if it names this probe's output directory. Every unrelated dialog
is left untouched. It does not open the user's file manager.

`report.json` is atomically checkpointed before production invocation and while
checking outputs. It records the actual production code source, command
registrations, input/model hashes, case, dialogs, phase and per-check outcomes.
Saved ROI ZIPs are decoded independently with `RoiDecoder`, and exact per-object
foreground geometry is verified as well as union pixels/counts. MAX/overlays
are reopened independently; MAX C/Z/T, pixels and calibration, RGB overlay
dimensions/type/calibration, source image/input-file/ROI immutability and an
unrelated image window are checked. Overlay hashes are retained as evidence,
not used as cross-OS font-rendering equivalence assertions.

Only generated 64×48 synthetic images and ROI ZIPs enter the output directory.
Upload this scoped evidence directory, never a whole runtime/cache/workspace.
`PASS_IMPORTED_ROI_SCOPE` means precisely the selected imported-ROI case.

## Deliberate exclusions and next exact routes

- No automatic subtype inference, EDF, spatial analysis, ganglia or full settings
  dashboard navigation is exercised. All markers have real imported ROI ZIPs;
  Z=1 keeps projection choice out of this minimal scope.
- There is no computation-time cancel contract in `ProgressUI`, and
  `ReviewUI.reviewAndRebuildLabels` does not inspect a WaitForUserDialog escape
  or cancel state. Do not simulate killing the process and call it successful
  application cancellation. A separate window-close/escape observation should
  report what the unchanged source actually does before specifying a repair.
- `NeuronsMultiPipeline.run` unconditionally invokes `NeuronsHuPipeline.run`,
  and that always calls real StarDist for Hu. Imported subtype ROIs do not make
  Hu-gated runs inference-free. Exercise that exact route on public Ubuntu
  Xvfb with original TF1/actual URL system-loader runtime and fork's isolated
  worker; retain the distinct native-Mac backend corpus evidence.
- Hu+marker dialogs are `Neuron ROIs review`, then `Review: A (Hu-gated)` and
  `Review: B (Hu-gated)`, then `Workflow finished`. Its A+B masks are captured
  before manual marker review in unchanged V2. A deletion counterexample is a
  separate high-priority shared-behavior test.
- Next no-Hu case: real `IMPORT_ROI` ganglia with two known labeled regions,
  followed by reopened per-ganglion CSV checks. Shared `OutputIO` mixes
  one-based arrays with zero-based CSV iteration, so total-row correctness must
  not stand in for per-ganglion correctness.

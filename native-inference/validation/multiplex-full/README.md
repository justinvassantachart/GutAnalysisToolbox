# Full multiplex service acceptance

This validation-only directory invokes the existing
`services.multiplex.core.MultiplexRegistrationService.run()` in isolated JVMs.
It does not replace feature extraction, landmark warping, the production service,
or its dialogs with mock implementations. No production code or shared workflow
is modified by this harness.

## Current evidence

`results/linux-6996dd5-checkpointed/summary.json` records a Linux x86-64 compile and control
run against revision `6996dd50f5ea06ac1f5ecb38c245139cb1508292` production classes:

- Harness compilation: PASS
- Python reporting/provenance tests: PASS (13 tests)
- Nine calibrated deterministic TIFF fixture save/reopen controls: PASS
- Alignment-comparator positive/negative controls: PASS (reject unchanged input,
  inverse-direction warp, and common-marker pixels copied into an independent channel)
- Actual `MultiplexRegistrationService.run()` existing-Results overwrite guard:
  PASS; sentinel data preserved, no added files, previous batch mode restored
- Exact success-prompt matcher positive and five adversarial controls: PASS
- Actual AWT display/ImageJ preflight: BLOCKED_SETUP (no working display)
- Complete SIFT and MOPS service, saved/reopened aligned output, negative-input
  and missing-round cases: NOT EXECUTED because the display preflight was blocked

This is **not a Mac result or a successful complete-workflow result**. The saved
summary's `full_service_acceptance_passed` is false. Local checks do not establish
transform correctness, output calibration retention, ROI export, or final-dialog
behavior in the full service. The existing source constructs new stacks without
an explicit calibration copy; this is a concern to measure, not a claimed reached
saved-output defect. No production correction has been made.

## Portable evidence copies

Published Linux logs and JSON reports use `<CLOUD_WORKSPACE>`, `<RUNNER_HOME>`
and `<RUNNER_USER>` in place of cloud-local workspace/home prefixes and the
runner account name. `results/publication-redactions.json` documents each changed
file with its original and published SHA-256. Untouched originals are retained
separately outside this repository's publication scope. Numerical outcomes,
source/class/dependency/input hashes, runtime versions and architecture are
unchanged; these placeholder paths are provenance labels, not runnable paths.

## Run on a native Mac

Use a JDK 17+ (21 in the example), Python 3, Maven and curl. A working macOS
WindowServer/AWT session is required. The test opens only its own synthetic
images in an isolated process; do not run inside a session containing unsaved
research images. Each case has a fresh JVM and a new output directory.

From the repository root:

```sh
mvn -B -ntp -DskipTests package dependency:build-classpath \
  -Dmdep.outputFile=target/multiplex-classpath.txt
python3 -m unittest discover -s native-inference/validation/multiplex-full -p 'test_*.py' -v
python3 native-inference/validation/multiplex-full/run.py \
  --root-classpath target/multiplex-classpath.txt \
  --expect-native-mac --output target/multiplex-full-mac
```

`--expect-native-mac` verifies both the Darwin/arm64 host and the JVM's
`os.arch`. It cannot turn Linux execution or an x86 JVM into Mac evidence.
`mac-ci-job.yml.example` is an owner-ready, separate workflow recipe; it is
not installed or enabled by this directory. The actual runner's chip/model,
OS, JDK, commit, dirty worktree, class hashes, dependencies and GitHub run URL
are recorded. Hosted Mac success must never be relabeled as a physical M1 test.
If `macos-15` does not provide arm64/AWT, the gate correctly blocks.

`--only controls` runs the reached headless controls without claiming full
service coverage. `--only full-sift` narrows to the normal SIFT path;
`--only full-mops` exercises the explicit MOPS boundary configuration. Omitted
cases are recorded. `--java`, `--javac`, `--cache` and `--timeout` are configurable.
Use a fresh `--output` directory on every run; existing evidence is never replaced.

## Exact fixture and expected existing output contract

The common-marker pattern and its translation helper are copied unchanged from
`../workflows/RegistrationMorphologySmoke.java`. A unit test compares those method
bodies. `provenance.json` pins the source hash and complete fixture recipe.

- 256×256, 8-bit, three rounds
- Per round: common `Hu`, independent `MarkerA`, independent `MarkerB`
- Round shifts in x/y: `(0,0)`, `(7,-5)`, `(-6,8)`
- Independent marker geometry/intensities use separate deterministic seeds for
  every marker and round; their pixels are never copied from Hu
- Pixel width 0.5 µm, height 0.75 µm, depth 2.0 µm, interval 1.25 s
- All input TIFFs are reopened before calibration comparison so TIFF rational
  rounding (notably 0.75) is not misdiagnosed as metadata loss
- `Aligned_Stack.tif` is expected to have seven channels, one z-plane and one
  time point: reference Hu, then MarkerA/MarkerB from each round
- The existing service deliberately excludes later-round Hu from the final
  aligned composite; `hu_stack.tif` retains all three Hu inputs unwarped for QC

The test checks each final channel's exact filename label and independently
expected pixels. Round-1 pixels must be unchanged over the entire image. Each
later-round marker must reduce interior MSE by at least 85% versus its own
unaligned source, using the same 24-pixel border exclusion as the earlier SIFT
smoke test. The opposite signs in rounds 2/3 expose reused-pair and direction
errors. This is a synthetic registration contract, not biological validation or
a tolerance for arbitrary images.

Every output is read from disk. Tests check final hyperstack dimensions, both
outputs' calibration, all original TIFF hashes, every common-QC plane, and the
saved ZIP's exact four ROI names. ROIs are decoded from ZIP bytes independently
of live ROI Manager state; point types, counts, pair identity and mean known
translation error under 1 pixel must agree. A command listener only observes and
returns each unchanged command, recording two or more SIFT extractions (normal
path), or exactly two MOPS extractions (fallback path), and four affine warps.

## Dependencies and MOPS/block scope

`dependencies.json` repeats the exact SHA-256 pins already used by the workflow
suite: mpicbg/mpicbg_ 1.6.6 and JAMA 1.0.3. Downloads use the existing checksum
verified fetch helper and official URLs. These pinned plugin jars precede
transitive Maven jars; current built GAT production classes precede all jars.
The runner records all source/class/JAR hashes and rejects classpaths containing
old production-class directories. Build the current source before invoking it.

The only plugin mappings installed in the isolated ImageJ command table are
verified against the pinned jar's actual `plugins.config`:

- Extract SIFT Correspondences → SIFT_ExtractPointRoi
- Extract MOPS Correspondences → MOPS_ExtractPointRoi
- Landmark Correspondences → Transform_Roi

MOPS is reached using the existing configuration builder with
`stepsPerScaleOctave=31`: the unchanged helper's SIFT loop runs only at values
≤30, so this route reaches actual MOPS without faking a failed SIFT plugin.
This tests the boundary/fallback route and full subsequent export, **not a
naturally occurring SIFT failure**. The plugin receives the real existing GAT
arguments; no parameter rewriting makes the case pass.

The pinned command manifest contains no `Extract Block Matching Correspondences`.
This harness neither invents a command class nor substitutes the mpicbg library
API. That fallback remains explicitly NOT_RUN. Its absence from this pinned
manifest is not proof that all external Fiji installations lack the command.

## Dialogs, cancellation and failure output handling

Only the two known, test-owned final success dialogs are controlled:

1. After all three expected export files exist, verify the exact upstream HTML
   results-folder message inside a single JOptionPane, with INFORMATION_MESSAGE
   and OK_CANCEL_OPTION, then click that pane’s actual **Cancel** button in
   `Open results?`. Check the
   actual JOptionPane value and confirm all three files remain byte-identical
2. Verify the `Multiplex Registration` MessageDialog class and its exact
   `Done. / Saved to:` text, then click its actual **OK** button

Headless matcher controls accept the exact message and reject a prefix, a
similar-but-wrong path, ERROR_MESSAGE, YES_NO_OPTION and a second competing pane.
These controls do not create or click a real dialog. Each actual action and value is logged. The AWT label has no getter, so the harness reads
its pinned ImageJ `MultiLineLabel.lines` field without modifying it to verify
that exact message. No unrelated prompt, ImageJ error, or plugin dialog is
silently suppressed or accepted. An unrecognized dialog is logged and left
alone. Native UI timing and final batch-flag restoration are themselves checked.

There is **no computation cancellation API** in the existing service/pane.
Cancelling the final result-opening prompt is not cancelling registration. The
harness explicitly does not claim interrupted-work cleanup or UI Cancel coverage.
It does not invent a thread-interruption contract or call `System.exit` mid-export
and mislabel that as application cancellation.

Additional real-service cases cover:

- Existing Results: reject overwrite, preserve sentinel, restore batch mode
- No TIFFs / no common marker: expected exception, empty Results left behind,
  no final exports, batch mode restored
- Missing round-3 common marker with later independent images present: expected
  missing-ROI-pair exception, original files unchanged, no Aligned_Stack or ZIP;
  an intermediate common-marker QC file may remain

An empty Results directory after a failure blocks retry under the existing
service contract; this behavior is recorded, not silently cleaned up by tests.

## Reporting and exit codes

The runner uses the existing isolated-process wall-time/RSS limiter (768 MiB
Java heap, one active CPU, 3 GiB sampled process-tree ceiling). Deadlines measure
bounded test execution, not M1 performance.

- Exit 0: every requested scope passed
- Exit 1: reached assertion/process/report/harness-compile failure
- Exit 2: setup block or incomplete/inconclusive execution

`PASS_REQUESTED_SCOPES` is deliberately narrower than “all workflows pass.”
The separate `full_service_acceptance_passed` requires full SIFT and MOPS and all
three GUI-dependent negative cases to pass. It never includes unsupported
computation cancellation or block matching; these remain explicit NOT_RUN checks
and top-level coverage limits. Missing, duplicate or unknown checks cannot
produce a complete report. The headless control's explicit NOT_RUN full-workflow
row cannot satisfy full-service acceptance.

A setup timeout is BLOCKED_SETUP; an unhandled dialog is BLOCKED_INTERACTION;
a deadline/RSS stop during computation is INCONCLUSIVE_RESOURCE_LIMIT. None is
called a registration algorithm defect. Every independent check immediately checkpoints its result to disk. A reached
assertion failure remains a failure even if a later file read, GUI wait or process
stage times out. Preserve the logs and phase
marker before diagnosing a native failure or proposing a production change.

# Actual legacy macro alignment boundary

This is a separate, fail-closed test of the original macro's registered Template
Matching command and MacroFork's static compatibility call. It is **not** the
whole calcium, batch, SIFT or save/export workflow.

## What runs

`run_alignment_probe.py` copies the actual pinned alignment line from
`Calcium imaging/_Align_stack.ijm`. Both occurrences must still be identical.
The native and legacy-delegate variants use the production macro bridge with
the same explicit `GAT_ALIGNMENT_OK` guard as the generated macros. Every other
return token exits the macro before downstream processing.
The probe runs that line through `IJ.runMacro`, in real AWT, with the original
macro's exact template-size/origin expressions. Reference 3 is the actual macro
setting; references 1 and 4 are explicitly labeled boundary-extension controls.

`alignment-cases.json` contains six positive cases: 8/16-bit images and first,
middle and last reference slices in a four-plane stack. Reference-3 inputs are
127×95; the others are 128×96. Non-default display ranges and anisotropic spatial
calibration are deliberate. A seventh case uses an unsupported 32-bit stack.
The original plugin's `setup()` supports only 8/16-bit stacks, so that case must
be rejected, with an actual diagnostic, no worker, no Results window and no
mutation. A negative control is never counted as a successful float alignment. A marker
after the actual call records whether the macro continues after rejection; that
behavior must also match. The guarded native `call()` boundary must show the
real modal Macro exit dialog with the exact expected type-error diagnostic and
no unrelated errors. Its actual OK action is acknowledged only for that exact
message. The original interpreter's real modal Macro Error is
observed and only its matching supported-type error is acknowledged with its
actual OK action. Unexpected dialogs are not dismissed. A continuation mismatch fails the paired report even when
all six supported inputs match exactly.

The comparator independently reconstructs the seeded Java random input and the
expected integer translations. Required evidence includes raw input/output
pixels, exact motion values and traversal order, visible Results, CSV roundtrip,
ROI, selected slice, display range, calibration, slice labels and an untouched
unrelated image. A real separate worker must be observed for every supported
native case. Original cases must invoke the real registered plugin and cannot
see fork classes. The separately labeled Linux `legacy-delegate` control forces
the production bridge's non-Apple branch, invokes that same real plugin, and
must preserve its six supported outputs and unsupported-input abort. It never
starts a worker. There is no numeric tolerance or fallback success path.

## Dependency preparation

Use an explicit ImageJ runtime dependency classpath, ideally the existing pinned
`native-inference/validation/baseline/dependencies-pom.xml` with
`-Dbaseline.opencv.platform=linux-x86_64`. The helper also supports an existing
Fiji classpath without changing that installation. It excludes and records old
or modern JavaCV/JavaCPP/OpenCV/OpenBLAS artifacts and OpenCV bridge JARs, then
adds the five exact dependencies in `alignment-artifacts.json`:

- The official ImageJ update-site `Template_Matching.jar` from 2020-05-15
- Maven Central JavaCV and JavaCPP 1.4.4
- Maven Central OpenCV 4.0.1-1.4.4 and its Linux x86_64 native JAR

SHA-256 and lengths are mandatory. The Maven files were also checked against
the registry's published SHA-1 when the pins were established. Fork or worker
classes inside the original parent classpath are rejected, even if renamed.
Preparation downloads bytes only; it does not execute or install Java software.

```sh
python3 validation/legacy-macros/alignment_runtime.py \
  --dependencies-classpath /path/to/explicit-classpath.txt \
  --cache target/alignment-dependencies --output target/alignment-runtime
```

The original JNI reference runs on Linux x86_64. The native adapter can run on
the platform of its separate, verified worker. Old JNI dependencies in its
parent classpath are deliberately not executed.

## Execution

Coordinate any shared GUI/JVM capacity first. On a supported desktop, run the
commands directly. On hosted Linux, wrap each runner invocation in `xvfb-run -a`.
No display server is started by these scripts. `--compile-only` prepares the
bounded 256 MiB / one-CPU compile without launching AWT. It records
`COMPILED_NOT_RUN`, which the comparator rejects as runtime evidence.

```sh
python3 validation/legacy-macros/run_alignment_probe.py \
  --variant original \
  --runtime-classpath target/alignment-runtime/runtime-classpath.txt \
  --output target/alignment-original
python3 validation/legacy-macros/run_alignment_probe.py \
  --variant native \
  --runtime-classpath target/alignment-runtime/runtime-classpath.txt \
  --production-classes target/classes \
  --native-worker /path/to/gat-native-alignment \
  --output target/alignment-native
python3 validation/legacy-macros/compare_alignment.py \
  --original target/alignment-original --native target/alignment-native \
  --output target/alignment-comparison.json
```

The additional Linux-only delegation control uses the same runtime and classes:

```sh
python3 validation/legacy-macros/run_alignment_probe.py \
  --variant legacy-delegate --production-classes target/classes \
  --runtime-classpath target/alignment-runtime/runtime-classpath.txt \
  --output target/alignment-legacy-delegate
python3 validation/legacy-macros/compare_alignment.py \
  --original target/alignment-original --native target/alignment-legacy-delegate \
  --native-variant legacy-delegate --output target/alignment-delegate-comparison.json
```

For a full Fiji dependency set, `--fiji-directory /path/to/Fiji` provides its
runtime root, while an empty, disposable `plugins.dir` prevents implicit plugin
loads. `--java` and `--javac` select Java 21. Every run uses a new output directory
and disposable home/preferences. The parent JVM heap is 256 MiB; the unchanged
production worker specifies a 1 GiB maximum heap. Both have one active processor
and one OpenMP/BLAS thread. The entire process tree is capped at 1 GiB observed
RSS and 180 seconds; worker timeout is 60 seconds. These are test bounds, not
measurements of the user's Mac.

```sh
python3 -m unittest discover -s validation/legacy-macros -p 'test_alignment.py' -v
```

The unit tests deliberately fabricate evidence to test rejection of incomplete,
wrong-setting, wrong-runtime, wrong-pixel, missing-worker and metadata-drift
reports. Their synthetic reports are never scientific/runtime pass evidence.

## Hosted execution

`.github/workflows/legacy-macro-alignment.yml` runs the same seven-case schedule
on standard GitHub-hosted runners. The original OpenCV 4.0.1 JNI reference runs
on Ubuntu x86_64. Native candidates on Ubuntu and macOS 15 arm64 download only
that same workflow run's reference evidence and apply the strict comparator.
The Linux candidate also runs all seven legacy-delegation controls and compares
them with the same-run original. The real CPU/JDK architecture is recorded and
checked. No private image or
model input is accepted by this workflow.

Raw evidence, process logs, dependency hashes and comparison failures are kept
as artifacts even when a control fails. In particular, a native call that
continues after an error when the original aborts is a failing result, not a
permitted exception. The lane has no tolerance or automatic mismatch approval.

## Size-limit follow-up

The inherited production alignment protocol currently rejects more than
67,108,864 total pixels, even for 8-bit data. For example, a 512×512×257 movie
contains 67,371,008 pixels and crosses that limit. The original plugin's source
does not impose that specific limit. No parity claim for that movie follows
from the small boundary test above. Testing the original on that bounded
counterexample is a separate queued experiment; neither the cap nor production
adapters have been changed here.

A possible future remedy needs an independently verified, streamed per-frame
worker design. Simply removing the cap would not address the current whole-
stack allocations and would weaken memory safeguards. No such remedy is
implemented or claimed by this harness.

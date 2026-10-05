# Actual unchanged GAT native-path probes

`run_native.py` calls the real public methods in the selected GAT checkout:

- `PluginCalls.runStarDist2DLabel`: original public 175 × 175 Hu TIFF and neuron
  model, probability 0.5 / NMS 0.3. Original GAT chooses four requested tiles.
- `AlignStack.alignTemplateMatching`: the same seeded 128 × 96, four-frame 8-bit
  fixture used in the old/new alignment regression, with known nonzero shifts.

These are actual ImageJ command/plugin calls. `Command From Macro`, StarDist,
CSBDeep, ImageJ TensorFlow, and Template Matching are original published plugins.
No fake command registrations or substituted inference implementations are used.
The original production checkout must remain at commit
`1870d9e16e16fd6daeac0bd05122e851029ddedc`, with unchanged tracked files and no fork
inference classes. The common baseline validator checks this before and after.

## Explicit original plugin environment

The GAT POM supplies its ImageJ/CLIJ/UI foundation but does not bundle StarDist or
TensorFlow. This harness therefore assembles and records the plugin environment:

- Original published StarDist 0.3.0, CSBDeep 0.6.0, imagej-tensorflow 1.1.6,
  Clipper 6.4.2, and Template_Matching JARs, pinned by timestamp URL and SHA-256
  in `plugin-artifacts.json`
- Official TensorFlow Java/runtime 1.15.0 Maven artifacts, including explicit
  `libtensorflow` and `libtensorflow_jni` 1.15.0 overrides; otherwise the SciJava
  BOM can silently substitute 1.12.0 for those transitive dependencies
- Original JavaCV/JavaCPP 1.4.4 and OpenCV 4.0.1-1.4.4; macOS receives the original
  `macosx-x86_64` native artifact, not an ARM64 replacement
- The original GAT POM's SciJava 45.1.0 ImageJ foundation, with pinned real
  ImageJ legacy/SciJava UI dependencies in `dependencies-pom.xml`

TensorFlow 1.15 is not selected merely to match an earlier scientific reference.
The unchanged `UI/Preflight.java` requires version prefix `1.15` and instructs
users to select **TensorFlow 1.15.0 CPU**. The official
[CSBDeep update-site database](https://sites.imagej.net/CSBDeep/db.xml.gz) also
publishes the TensorFlow 1.15.0 runtime plus the CSBDeep/ImageJ-TensorFlow versions
above. `dependency-environment.json` preserves the relevant database records and
its retrieved checksum. Runtime reports record the exact dependency file hashes,
class code sources, and Mach-O CPU headers from the native JARs.

The live TensorFlow update site also has other versions. This test represents
GAT's explicitly required 1.15 CPU environment, not every possible conflicting
update-site installation. Original GAT source is never rewritten to select it.

## Actual ImageJ bootstrap on Java 17

The probe uses the official ImageJ legacy bytecode patcher exactly as a standalone
ImageJ2 embedding requires. The JVM receives:

```text
--add-opens=java.base/java.lang=ALL-UNNAMED
-javaagent:<resolved ij1-patcher-2.0.0.jar>=init
```

This is test-environment initialization, not a GAT or algorithm patch. It prevents
ImageJ1 classes from loading before the real ImageJ2 legacy bridge can initialize.
The probe constructs the real ImageJ context and verifies both the SciJava
commands and the ImageJ1 `Command From Macro` menu registration before invocation.
Template Matching's menu entry points directly to the published
`TemplateMatching.Align_slices` plugin class.

GUI-capable execution is necessary for the original `IJ.run` integration. On a
headless Linux host, both probes report `unavailable`, leave
`actual_gat_method_invoked` false, and produce incomplete evidence/nonzero runner
status. This is not an observation of native incompatibility. Native macOS ARM64
CI is the authoritative comparison requested here.

## Run original baseline

After compiling the unchanged original checkout and writing its Maven dependency
classpath file, run:

```sh
python3 native-inference/validation/baseline/run_native.py \
  --project-root /path/to/unchanged-checkout \
  --root-classpath /path/to/unchanged-classpath.txt \
  --cache /path/to/shared-pinned-downloads \
  --output /path/to/new-baseline-diagnostics
```

`--output` must be new or empty. `--timeout` must be positive. Each probe runs in
its own JVM with the common process-group deadline/RSS limiter, which terminates
child workers too. The shared cache holds model/plugin downloads, keeping them
outside uploaded diagnostics. TIFF and model hashes come from the existing
cross-platform fixture manifest.

For the paired fork, use the same script, fixtures, and original plugin JARs with
`--allow-fork`, the fork's root classes/classpath, and its isolated worker paths:

```sh
python3 native-inference/validation/baseline/run_native.py \
  --project-root /path/to/fork \
  --root-classpath /path/to/fork-classpath.txt \
  --cache /path/to/shared-pinned-downloads \
  --output /path/to/new-fork-diagnostics \
  --allow-fork \
  --inference-directory /path/to/fork/native-inference/target \
  --alignment-directory /path/to/fork/native-alignment/target
```

Only the fork JVM receives the native-backend selector and worker-directory
properties. Neither original JVM receives fork classes, modern TensorFlow, or
native-worker JARs. In the fork, modern runtimes remain isolated child processes.

## Results and failure semantics

The probe captures uncaught/ImageJ/SciJava exceptions, actual returned image
properties, raw labels/counts, input/model hashes, and aligned-pixel hashes.
Returning the original input through old GAT's StarDist fallback is explicitly
rejected. Alignment must change the deliberately shifted input and match the
original Linux fixture's exact aligned-pixel hash.

Reports are checkpointed before entering the actual GAT method and on captured
exceptions, so a later modal dialog/native abort can retain useful evidence.
Process timeouts/resource stops remain separately labeled and do not become
ordinary incompatibility claims.

`native-summary.json` includes `evidence_complete`:

- Original success stays success; original `workflow_failure` after the real
  method was invoked is recorded evidence, not an expected-failure assertion
- Setup failures, unavailable GUI, absent reports, or process deadlines produce
  incomplete evidence and a nonzero runner status
- The paired fork additionally requires both probes to succeed

Local preparation verified the actual command registrations and TensorFlow
service in a real headless ImageJ context, both probe compilation, original
source/classpath isolation, and unavailable-GUI reporting. It does not claim
that the original native calls ran on this headless host.

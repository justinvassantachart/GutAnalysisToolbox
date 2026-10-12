# Real top-menu workflow gate

This gate runs the installed **original macro body** or its independently
byte-audited MacroFork counterpart from the actual discovered ImageJ menu. It
is separate from the 720-case NMS grid and 30-case inference-command matrix.
Those narrower tests cannot satisfy this gate.

## Current scope

`impact-matrix.json` classifies all47 macros against the exact original blobs:
eight StarDist boundaries, three alignment boundaries and namespace/settings
routing. It is generated independently from the overlay with
`build_impact_matrix.py`. Unchanged EDF, spatial, calcium tracing and CSV
computations are not new standalone test projects.

`topmenu-cases.json` is the finite prioritized schedule, not a results file.
The implemented initial scenarios are single-neuron Hu analysis with ganglia,
spatial analysis, fine tuning and contribution disabled, followed by unchanged,
delete-first or add-one review. The pinned public 175×175 Hu fixture is saved
with `.568 × .568 microns` calibration in a fresh per-case input directory.
Pixels are unchanged. The normal dashboard is filled, not suppressed with
macro options. The real global ROI Manager is edited only at the unchanged
source's review prompt. The original source's completion is an `exit()` with
`Neuron analysis complete`; all other aborts remain failures or incomplete
workflows, never translated into successful output.

The controller only handles exact source-known dialogs. Unknown dialogs are
recorded and left untouched; after ten seconds the bounded attempt fails.
No mask replacement, save shortcut, command registration stub, review bypass,
script rewriting or synthetic results are used. `IJ.doCommand` dispatches the
real registered menu after the launcher macro has returned.

## Isolated setup

`prepare_topmenu.py prepare` takes an existing supported Fiji distribution
with original TF1/protobuf3.11.4, the independently checked overlay, the candidate
plugin JAR and native worker directory. It creates separate original/native
installations under a **new** output root. It refuses an existing destination.
Only approved runtime directories are copied. Fork/probe JARs are excluded
from the original control by names and actual JAR members.

Immutable JAR/JDK/native-library files may be hardlinked. Every script, model,
config and other potentially mutable file is copied. Per-case HOME,
preferences, temporary files and OpenCL/model caches are isolated. Every
hardlinked source/destination and installed script hash is recorded and checked
before and after execution. The first-run GAT marker is created by the actual
original macro, not pre-seeded by the test.

```sh
python3 validation/legacy-macros/prepare_topmenu.py prepare \
  --runtime /absolute/proven/Fiji \
  --output target/topmenu-unchanged \
  --overlay target/GAT-MacroFork-overlay.zip \
  --candidate target/GAT-MacroFork.jar \
  --native-worker /absolute/gat-native-inference \
  --scenario unchanged
```

Compile `LegacyMacroTopMenuProbe.java` and the existing validation-only
`native-inference/validation/baseline/BaselineUrlClassLoader.java` using an
explicit original runtime classpath, with
`javac -J-Xmx256m -J-XX:ActiveProcessorCount=1 -proc:none`.
Package only its compiled classes and this `plugins.config` entry into
`LegacyMacroTopMenuProbe.jar`, then copy that validation-only JAR into each
new installation's `Fiji/plugins` directory:

```text
Plugins>Validation, "Legacy Macro Top Menu Probe", LegacyMacroTopMenuProbe
```

Package only `BaselineUrlClassLoader.class` into
`LegacyValidationUrlLoader.jar`, then copy that JAR into each isolated
installation's `Fiji/jars` directory. The launcher explicitly selects this
proven URL system loader, required by the original TF1 plugin on Java21.
Fiji's URL application/context loader alone is not assumed sufficient.
Record both source and compiled class/JAR hashes.

## Execution and comparison

Run only in the supported desktop/GUI environment after the shared resource
scheduler grants the slot. For local cloud execution inherit the supported
Terminal display. Do not inject a display address or start a transport bridge.
The existing supported OpenCL/POCL environment must already be configured,
because the unchanged legacy startup checks CLIJ2 even with ganglia disabled.

```sh
python3 validation/legacy-macros/run_topmenu.py \
  --installation target/topmenu-unchanged --variant original
# Diagnose the original attempt before launching native.
python3 validation/legacy-macros/run_topmenu.py \
  --installation target/topmenu-unchanged --variant native
python3 validation/legacy-macros/compare_topmenu.py \
  --installation target/topmenu-unchanged --output target/topmenu-paired.json
```

The launcher uses a 768 MiB/one-CPU host JVM and the same inherited bound for
the real native child, a 3 GiB aggregate RSS ceiling, and a 600-second deadline.
Native must explicitly select `gat.stardist.backend=native` and record the
actual worker process. Original must not see fork classes or worker classes.

Each side records the actual menu mapping, unchanged source SHA, target class,
actual inference parameter values, observed dialogs and actions, before/after
ROI geometry, worker provenance, runtime log and bounded launcher result.
The probe reopens both ROI archives, label/MAX TIFFs, preview JPEG and cell
count CSV. The comparator ties saved bytes back to those reopened records and
checks review effects, CSV counts, pixels/calibration, ROI order/names/positions
and geometry. Log contents and ZIP container metadata are retained, but are
not mistaken for scientific output equality.

The default is exact. `--roi-atol` is an explicit, recorded alternative for ROI
vertex coordinates only; it cannot relax labels, counts, names, order, positions,
parameters or measurements. Preserve the strict result first.

`test_topmenu.py` tests the verifier and setup guardrails. These unit tests are
not runtime workflow evidence. Only a successful actual paired report can
mark the corresponding workflow scenario executed.

## Namespace and abort-path controls

`LegacyMacroOptionProbe.java` uses pinned IJ1 `Macro.getValue` and the actual
`Results... ` command. It expects the original unquoted settings path to open,
the renamed unquoted path to truncate at its first space and fail, and an outer
bracket-quoted path to preserve nested `[MacroFork]` brackets and reopen the
settings. This no-model AWT control captures its intentional negative error;
it is not a whole-workflow result. Use a fresh output directory whose ancestors
do not contain spaces so the original-path positive control remains meaningful.

The r3 overlay quotes all seven settings option sites and guards all three
alignment calls with an explicit success token. Every other source byte must
match the independently reconstructed allowlist. A passing registration audit
alone cannot detect either command-argument parsing or error-continuation bugs.

When only candidate setup changed, `compare_topmenu.py --original-installation`
can reuse a separately recorded successful original control. Both installation
roots are written to the comparison report and validated independently. Failed
candidate attempts and all earlier reports remain separate; no report is copied
or rewritten to imply a fresh original execution.

## Finite affected entry points

After the unchanged Hu gate succeeds, run the same real-menu probe with
`--scenario delete-one` and `--scenario add-one`. The global ROI Manager must
show the actual edit before the original source resumes; exported CSV counts,
ROI ZIPs and label rasters must match that edit.

`prepare_marker_topmenu.py --family hu-one-marker` and `--family no-hu-one-marker`
prepare two distinguishable public channels (unchanged Hu pixels and a
three-pixel horizontal translation with zero fill). These are technical channel
routing fixtures, not biological marker accuracy evidence. Compile/package
`LegacyMacroMarkerMenuProbe` separately, install its validation JAR and the
same URL loader in both clones, then use `run_topmenu.py` and
`compare_marker_topmenu.py`. The Hu path must execute Hu then subtype models,
use both genuine reviews, and reopen its exports. The no-Hu path must accept
its exact original advanced defaults and execute only the subtype model.

`prepare_batch_topmenu.py` keeps the entire original/generated batch example
and changes exactly eight input-data assignments: public file path, channel,
ganglia toggle/channel/unused ROI path, fine-tuning toggle, probability0.3 and
NMS0.7. It preserves the literal `run(command,args)` dispatch, argument assembly
and analysis body. `LegacyMacroBatchMenuProbe` appends only an after-call
completion marker. Batch must retain the original absence of manual review and
unmodified ROI archives; it must print completion and save the final ROI ZIP,
CSV, label/MAX TIFFs and preview. `compare_batch_topmenu.py` independently
reconstructs those data-only edits, verifies actual renamed dispatch, actual
nondefault model parameters and reopened outputs.

Both extended probes are validation-only JARs with separately recorded source,
class and JAR hashes. Always diagnose an original run before launching its
native sibling. Compilation, source preparation, and unit verifier tests do not
count as an executed workflow. A runtime failure stays separate from a later
retry. Namespace-only helper routes are additionally audited against all47
exact script blobs; none are claimed to have executed solely because Fiji
registered their menus.

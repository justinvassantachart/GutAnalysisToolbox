# Fresh native Fiji installation lane

Status: the initial lane ran natively on macOS 14.8.9 / Apple M1 Virtual with
Fiji's bundled Zulu Java 21.0.7 in GitHub Actions run `37363502221`,
source `c6e2011`. Fresh archive/updater/startup and fork neuron/alignment passed;
original neuron/alignment failed. Both dashboards were genuinely blocked by
missing DeepImageJ engines. The engine-initialization extension described below
is prepared for a new native rerun; it is not yet a passed result.

The active workflow is `.github/workflows/native-mac-fresh-fiji.yml`; the
example is retained as a reference. The next run uses the standard macOS15
arm64 M1 label because GitHub reported macOS14 runner-acquisition capacity
failures. The recorded Sonoma results are preserved, the actual new OS/hardware
must be reported, and no paid/larger runner is selected. The engine extension
itself is validation-only and does not change production GAT algorithms.

This lane complements the existing standalone GAT API tests. It does not claim
full workflow support, physical-Mac validation, or a zero-prerequisite user
handoff has passed. GitHub's build runner supplies Python, Maven and build Java;
**Fiji execution uses only the JDK inside its freshly downloaded distribution**.
The end-user GUI installation instructions remain separate.

## What is new here

1. Check native macOS arm64, available disk space and host identity
2. Download the dated official Fiji Latest arm64/JDK ZIP into a new runner-temp
   directory, verify exact publisher SHA-256/length, validate every ZIP member
   and internal symlink, then unpack using macOS `ditto`
3. Execute the distribution's actual `fiji-macos-arm64` launcher, selecting its
   bundled Zulu JDK explicitly. Do not invoke a custom Java main, manually
   initialize ImageJ, install a replacement classloader, or inject command menus
4. Invoke the supported ImageJ updater CLI to activate the exact documented GAT
   sites, apply updates and retain update databases, resolved versions and hashes
5. Use the shipped JDLL supported installer to install the catalog-selected
   PyTorch 2.0.0 CPU engine. Verify its seven jars against existing validation
   hashes, add the exact pinned official native macOS ARM CPU jar, then load and
   execute the whole supplied model through JDLL inside installed Fiji. The real
   model, descriptor, preprocessing/postprocessing macros and JDLL/DeepImageJ
   jars must match their pins; conflicts fail without changing those files
6. Copy that one engine-ready installation into two independent trees on one runner.
   Install the original immutable GAT plugin in one, and the exact clean fork
   preview in the other. Only identified GAT plugin jars are displaced; worker
   libraries stay in their isolated folders, never Fiji's `jars`/`plugins`
7. In each tree, use a small validation-only plugin, reached through a regular
   ImageJ macro/command, to record real runtime/menu/class-source information,
   invoke the registered `GATV2` entry point, and observe the actual preflight
8. Separately execute the real GAT neuron call on the pinned public 175×175 Hu
   TIFF and Template Matching call on the established deterministic shifted
   stack. Check output against the existing exact raster references. Also invoke
   the actual GAT ganglia command using the whole public two-channel fixture,
   registered DeepImageJ command, real model and MorphoLibJ cleanup. The neuron
   reference is corpus case `repo_DYM_22_7_Pr_Hu_crop_c1_t1_x0_y0`, tiles 4,
   probability 0.5/NMS 0.3, matching the actual GAT API; the separate one-tile
   compact reference is not used

The plugin is added as `Fresh_Fiji_Probe.jar`; its source is in this directory.
It runs inside the normal installed Fiji classloader. Its only startup-dialog
automation dismisses GAT's informational first-run notice. Any other modal dialog
is recorded as **BLOCKED** and left unaccepted until the isolated process exits.
No sentinel or fake engine directory is created by the harness. JDLL itself
installs the real engine; full model loading/inference must pass before either
matched copy is created. Installer success or folder existence alone cannot
pass the initialization stage.

## Important expected blockers and limits

- Upstream's [GAT setup guide](https://gut-analysis-toolbox.gitbook.io/docs/home#installation-and-configuration)
  recommends Fiji **Stable**. This lane deliberately tests native arm64 Fiji
  **Latest**, with Java 21. That is a compatibility deviation needing direct
  evidence, not an equivalent supported setup
- The first run proved the missing-engine blocker. The extension uses
  `EngineInstall.installEngineWithArgsInDir("pytorch", "2.0.0", true, false, dir)`
  from the actual installed JDLL, then verifies all downloaded bytes. Its native
  library is supplied from the pinned official CPU jar before inference, avoiding
  an unpinned automatic DJL native download
- The unchanged model declares PyTorch `2.4.1+cpu`; shipped JDLL maps this to
  `2.0.0`. The extension asserts that exact catalog result. It is the already
  native-tested engine combination, not a claim of version/scientific parity
- OpenCL/EDF/spatial workflows, exhaustive dashboard navigation, manual
  ROI/painting review, and an all-workflow claim remain **BLOCKED**
- The current virtual M1 runner has no exposed OpenCL devices. A physical M1 must
  supply that separate evidence. CI cannot validate a Finder download's
  Gatekeeper/quarantine experience; no OS security setting is changed
- The official archive is immutable/pinned, but update sites are live. Each run
  stores resolved inventories and database snapshots. They document the actual
  resolution; they do not turn it into a reproducible historical updater server
- Expected versions/hashes from existing baseline/fixture manifests are compared
  to updater output. Differences are retained in `pin-comparison.json`, never
  repaired by swapping runtime jars or downgrading dependencies. A changed neuron
  model blocks the exact-reference neuron test
- The old and fork GAT inputs share byte-identical freshly resolved dependencies.
  Errors in the original are recorded, not assumed. Before/after claims require
  reading both stage results and the class-source/error evidence

## Running the proposed lane

The review-only YAML builds both revisions, packages the fork, runs local harness
safety tests, then runs:

```sh
python3 validation/fiji-install/run_fresh_fiji.py \
  --original-jar /absolute/path/GutAnalysisToolbox_-2.0.0.jar \
  --fork-archive /absolute/path/GAT-2.0.1-apple-silicon.2-macos-arm64-preview.zip \
  --original-commit 1870d9e16e16fd6daeac0bd05122e851029ddedc \
  --fork-commit FULL_40_CHARACTER_FORK_COMMIT \
  --output /absolute/path/new-evidence-directory
```

The harness never accepts an existing Fiji path. It allocates a new isolated
runner-temp directory, a private test home and new per-variant installations.
Allow at least 12 GiB free; all installations remain for diagnosis until the
runner is discarded. It does not use cached installed plugins/models/engines.
The source build toolchain is not represented as an end-user prerequisite.

The acceptance gate requires fresh download/updater/runtime setup plus fork
startup, dashboard, neuron, alignment and ganglia-command passes, plus successful
real engine initialization/full-model inference. A blocked fork dashboard is
**not a green installation result**. Original neuron/alignment failures are
baseline observations. The separate all-workflow exclusions never disappear.
Exit codes: 0 = this bounded acceptance gate passed; 2 = a required stage failed;
3 = a required stage is blocked (including running on a non-Mac host).

## Evidence

- `fresh-fiji-report.json`: explicit PASS / FAIL / BLOCKED stages and command logs
- `installed-inventory.json`, `engine-ready-inventory.json`, `*-final-inventory.json`: installed file hashes,
  including models and worker libraries
- `pin-comparison.json`: exact prior validation pin matches/conflicts
- `updater-databases/`: observed official update databases and installed database
- `pristine_startup.json`, `original_*.json`, `fork_*.json`: actual runtime,
  command menu, class source, exception window, preflight dialog, and result evidence
- `official_engine_install.json`, `official_engine_inference.json`: supported
  installer and full-model execution proof, before copying either GAT revision
- `original_ganglia.json`, `fork_ganglia.json`: actual installed-Fiji GAT ganglia
  command results. Mask TIFFs are retained locally; JSON reports record metrics

Do not upload the whole temp directory or distribution as a test artifact.
The proposed YAML preserves diagnostics only.

## Source verification

- [ImageJ command-line documentation](https://imagej.net/learn/command-line)
- [ImageJ updater CLI source](https://github.com/imagej/imagej-updater/blob/master/src/main/java/net/imagej/updater/CommandLine.java):
  `edit-update-site` creates/activates a site; `update` resolves and installs it
- [Official update-site catalog](https://github.com/imagej/list-of-update-sites/blob/master/sites.yml):
  ten listed GAT sites; Template Matching is added from the GAT documentation
- Launcher options and default main were inspected directly in
  `Fiji/config/jaunch/fiji.toml` and `jvm.toml` inside the pinned distribution

Full-byte archive verification and local-only test results are recorded in
`PREPARATION_RESULTS.json`. Those are not native Mac results.

## Reached clean-install follow-up

Native attempt 3 of run 37366290437 installed the actual PyTorch engine, ran the
full 1024×1024 model, opened both GAT dashboards, and passed fork neuron/alignment.
Both ganglia probes then stopped before invoking GAT because the harness used
primitive reflection setters on two boxed Double parameters. This is a test
setup defect, not evidence that either ganglia implementation failed.

The corrected probe uses Fresh_Ganglia_Params for the two boxed assignments.
A regression compiles the repository's actual Params.java, demonstrates both
old setters fail, and checks all four configured values. The same check passes
against unchanged 1870d9e Params. Production code, models, thresholds and engine
selection are unchanged. The corrected installed-Fiji ganglia gate subsequently
passed in [run 37374804775](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37374804775)
at 26298b7; see the accepted result packet. Historical artifacts retain their
original failure status.

## Public mask retention

The accepted 26298b7 run recorded successful saves and command metrics but did
not retain its ganglia TIFFs in the diagnostic archive. That historical gap is
not relabelled as raster evidence. Subsequent runs record both the raw row-major
uint8 pixel SHA-256 and the TIFF-file SHA-256, and upload only the two specifically
named public-fixture mask TIFFs. They do not upload a full Fiji install, model
weights, arbitrary user images or native caches. The raw-pixel convention has
a known-byte regression test.

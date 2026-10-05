# Fresh native Fiji installation lane (review-only)

Status: prepared 2026-10-05; **not yet executed on macOS**. The proposed workflow
is deliberately stored as `native-mac-fresh-fiji.yml.example`, outside active
workflows. No publication or existing workflow was changed. An owner can review
and later copy it to `.github/workflows/native-mac-fresh-fiji.yml`.

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
5. Copy that one resolved installation into two independent trees on one runner.
   Install the original immutable GAT plugin in one, and the exact clean fork
   preview in the other. Only identified GAT plugin jars are displaced; worker
   libraries stay in their isolated folders, never Fiji's `jars`/`plugins`
6. In each tree, use a small validation-only plugin, reached through a regular
   ImageJ macro/command, to record real runtime/menu/class-source information,
   invoke the registered `GATV2` entry point, and observe the actual preflight
7. Separately execute the real GAT neuron call on the pinned public 175×175 Hu
   TIFF and Template Matching call on the established deterministic shifted
   stack. Check output against the existing exact raster references

The plugin is added as `Fresh_Fiji_Probe.jar`; its source is in this directory.
It runs inside the normal installed Fiji classloader. Its only startup-dialog
automation dismisses GAT's informational first-run notice. Any other modal dialog
is recorded as **BLOCKED** and left unaccepted until the isolated process exits.
No sentinel or fake engine directory is created by the harness.

## Important expected blockers and limits

- Upstream's [GAT setup guide](https://gut-analysis-toolbox.gitbook.io/docs/home#installation-and-configuration)
  recommends Fiji **Stable**. This lane deliberately tests native arm64 Fiji
  **Latest**, with Java 21. That is a compatibility deviation needing direct
  evidence, not an equivalent supported setup
- A fresh installation may have no DeepImageJ engines. GAT's real preflight can
  therefore block the dashboard even if neuron/alignment probes pass. The first
  lane records that blocker; a later explicit real engine-installation stage can
  use the documented GUI or the already-hashed actual JDLL engine artifacts
- No engine installer, ganglia command, OpenCL/EDF/spatial workflow, exhaustive
  dashboard navigation, manual ROI/painting review, or all-workflow claim is
  included. Those stages remain **BLOCKED** in the report
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
startup, dashboard, neuron and alignment passes. A blocked fork dashboard is
**not a green installation result**. Original neuron/alignment failures are
baseline observations. The separate all-workflow exclusions never disappear.
Exit codes: 0 = this bounded acceptance gate passed; 2 = a required stage failed;
3 = a required stage is blocked (including running on a non-Mac host).

## Evidence

- `fresh-fiji-report.json`: explicit PASS / FAIL / BLOCKED stages and command logs
- `installed-inventory.json`, `*-final-inventory.json`: installed file hashes,
  including models and worker libraries
- `pin-comparison.json`: exact prior validation pin matches/conflicts
- `updater-databases/`: observed official update databases and installed database
- `pristine_startup.json`, `original_*.json`, `fork_*.json`: actual runtime,
  command menu, class source, exception window, preflight dialog, and result evidence

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

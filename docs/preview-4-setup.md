# GAT Apple Silicon TEST preview 4: setup and upgrade

Experimental native arm64 Fiji overlay for macOS 14+, Java 11+ (bundled Java 21
recommended). This release is `2.0.1-apple-silicon.4`, not a SNAPSHOT. It contains
the preview 3 multiplex repair plus Intel CPU-probe and calcium input/load/cancel
hardening. Its native worker binaries are ARM64 only. Existing Intel GAT keeps
its legacy backend; do not install this ARM worker bundle on Intel.

## Download and verify

Use the [preview 4 release](https://github.com/justinvassantachart/GutAnalysisToolbox/releases/tag/apple-silicon-preview-4).
Download the core ZIP, its `.sha256` file and `FORK_BUILD_INFO.json` together.
Keep `M1-CHATGPT-HANDOFF-v6.md` for full clean-Mac/Fiji/model/engine instructions.
The release page records the exact source commit, native build/test run and
archive size. Do not substitute any earlier core ZIP or a development SNAPSHOT.

In Terminal, change to the directory containing the downloaded files, then run:

```sh
shasum -a 256 -c GAT-2.0.1-apple-silicon.4-macos-arm64-preview.zip.sha256
unzip -t GAT-2.0.1-apple-silicon.4-macos-arm64-preview.zip
unzip -p GAT-2.0.1-apple-silicon.4-macos-arm64-preview.zip BUILD_INFO.json
```

Require checksum `OK`, no ZIP errors, version `2.0.1-apple-silicon.4`,
`source_worktree_modified: false`, `target: macos-arm64`, and a source commit
matching the release tag and adjacent build info. These commands verify bytes;
they do not run Fiji or establish scientific correctness.

Extract into a NEW staging folder using Finder, or from that download directory:

```sh
mkdir GAT-preview-4-staging
unzip -q GAT-2.0.1-apple-silicon.4-macos-arm64-preview.zip -d GAT-preview-4-staging
shasum -a 256 GAT-preview-4-staging/plugins/GutAnalysisToolbox_-2.0.1-apple-silicon.4.jar
```

The JAR digest must equal `plugin_sha256` in BUILD_INFO. Keep both worker JARs,
all `lib/` dependencies and all source/license/notices together. If staging
already exists, choose a new empty folder; never merge an older extraction.

## Install or upgrade a separate test Fiji

1. Use native arm64 Fiji on macOS 14+ with bundled Java. For a new installation,
   finish the v6 handoff's update-site, model and DeepImageJ engine setup first.
   No Git, Maven, Homebrew or Python is needed for a prebuilt overlay
2. Quit Fiji completely. Find the ImageJ data root using
   `IJ.getDirectory("imagej")` in Fiji before quitting. It contains `plugins`
   and `jars`. Current Fiji Latest uses outer `Fiji/`, beside `Fiji.app/`
3. Make a dated backup OUTSIDE Fiji. Move all old GAT plugin JARs there, including
   preview 3 or `.4-SNAPSHOT`. Also move the ENTIRE old `gat-native-inference`
   and `gat-native-alignment` folders there. Keep backups and old downloads
4. Copy only the new GAT JAR from staging `plugins/` into Fiji `plugins/`.
   Copy both complete worker folders into the data root. Do not replace Fiji's
   whole `plugins` folder, merge old/new worker libraries, or put worker `lib/`
   JARs in Fiji's global `jars`/`plugins`. Keep models, engines and unrelated
   dependencies unchanged unless the full handoff identifies a separate need
5. Check there is exactly one GAT plugin JAR and that its filename/digest match
   preview 4. Both complete workers must be siblings of `plugins`, not inside it
6. Launch that Fiji copy. Use Plugins → GutAnalysisToolbox → GATV2. Confirm the
   actual JVM is arm64/aarch64, then test a small public neuron crop and the
   supplied single-channel calcium fixture. Save logs and actual output files
7. Keep the original comparison Fiji copy unchanged. The updater can replace
   the preview JAR; after any update, repeat version/hash/worker checks before
   using results. Never bypass macOS security warnings to make a test pass

To roll back, quit Fiji, move the new JAR and both new worker directories to a
separate backup, then restore the previous matched JAR and complete worker
folders. Do not mix releases. Avoid preview 2 for quantitative multiplex work.

## Checks and limits

The release page and `FORK_HARDENING_2026-10-06.md` state exact tested revisions
and outcomes. Root regression suites and native hosted-Mac paired calls are
bounded technical checks. Historical fresh-Fiji and scientific corpus results
retain their dates and scope. Hosted OpenCL may expose no usable device;
physical GPU, full interactive workflows and biological acceptance remain open.

Calcium accepts single-channel grayscale stacks with one time axis: ordinary
C1/Zn/T1 stacks interpreted as time, or C1/Z1/Tn series. The supplied historical
calcium fixture is C1/Z3/T1; do not project away its time planes. RGB,
multiple channels and combined Z/T are rejected. Select channels/Z treatment
explicitly before analysis; no scientific preprocessing is chosen silently.
F/F0 retains ImageJ behavior including zero-baseline NaN/infinity. Automatic
calcium StarDist ROI generation and GAT batch StackReg remain unimplemented.

The unchanged baseline and manual fixtures remain available with pinned hashes
in the v6 handoff. Optional JPEG-XR is a separate prior-release add-on with its
own source/license/checksums and importer limitations; it is not inside this
core ZIP. No upstream PR has been opened.

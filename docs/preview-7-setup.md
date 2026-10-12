# GAT Apple Silicon preview 7: start here

Version `2.0.1-apple-silicon.7`. This is a native-Apple-Silicon compatibility
preview for the **legacy GAT macros**, alongside the existing GATV2 plugin.
Use native arm64 Fiji on macOS 14+ with its bundled Java (Java 21 recommended).
The supplied workers are ARM64 only. No developer tools are needed.

## Which workflow to use

Researchers continuing an existing macro analysis should use the new
**GAT MacroFork** menu and commands ending in **[MacroFork]**. The original
GAT macro menus remain available. GATV2 is a separate Java workflow with
different legacy ganglia behavior; selecting GATV2 does not reproduce the
macro pipeline.

## Install the matching package

1. Download the preview-7 ZIP and its SHA-256 file from the same release.
   Verify the checksum. `BUILD_INFO.json` inside the ZIP must name version
   `2.0.1-apple-silicon.7`, the release commit and
   `source_worktree_modified: false`. An unlisted release is not yet published.
2. Quit Fiji. Back up the existing GAT plugin, both worker directories and
   saved settings outside Fiji. Keep the previous working installation.
3. Extract the package to a temporary folder. Copy its single plugin JAR into
   the Fiji data root's `plugins/` folder, replacing the older GAT JAR. Keep
   exactly one GAT plugin JAR. Copy the complete `gat-native-inference/` and
   `gat-native-alignment/` directories into the data root, alongside
   `plugins/`, never into `plugins/` or `jars/`. Do not mix worker versions.
4. Copy the package's `scripts/GAT MacroFork/` directory into the data root's
   `scripts/`. Preserve the existing `scripts/GAT/` directory. Current Fiji
   Latest uses the outer `Fiji/` data root beside `Fiji.app/`; confirm the
   location with ImageJ's `IJ.getDirectory("imagej")` if uncertain.
5. Keep the original GAT model files, DeepImageJ engines and required plugins
   installed. The package is an overlay, not a complete Fiji/model installer.
   Dependencies include StarDist/CSBDeep, DeepImageJ, CLIJ/CLIJ2, PTBIOP and
   other prerequisites in the original GAT installation guide.

## Preserve your researchers' settings

The distributed MacroFork settings file contains repository defaults.
Before running an existing project, back up both settings files and copy
`scripts/GAT/Tools/commands/gat_settings.ijm` unchanged to
`scripts/GAT MacroFork/Tools/commands/gat_settings [MacroFork].ijm`.
Keep the exact filename and extension. Do not reformat the contents.
This preserves that settings table; dialog choices must still be checked.
Use the same image, channels, scale, model, probability and overlap choices.

Restart Fiji and select the matching **GAT MacroFork** command. Test a copy of
an image with a new output folder first. Keep original and fork comparisons
in different output folders because the original export naming is preserved.
Inspect the review ROIs before accepting results, as with the original macros.

## Memory and failure messages

Native inference runs in a separate Java worker as well as Fiji. Large images
can require multiple GiB of memory; a 1 GiB worker limit is insufficient for
some ordinary whole-field analyses. Use one analysis at a time, close other
large images/apps, and allow enough RAM for both processes. Tiling does not
remove the full output-tensor memory requirement. Do not change rescaling or
thresholds merely to hide a resource failure.

If a worker reports out-of-memory or inference failure, stop and retain its
error details. A following “No cells detected” dialog does not establish a
biologically empty image after failed inference. See the release notes for
remaining input and workflow limits.

## Rollback

Quit Fiji and restore the previous matched plugin and complete worker
folders from your backup. Remove only the new MacroFork directory if desired;
the original macro directory/settings were not modified by this overlay.
Recheck the plugin/worker versions after Fiji updates.

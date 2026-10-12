# GAT MacroFork native-Mac compatibility candidate

MacroFork is a separate **legacy macro** route. It does not call the GATV2
Java workflow. The original macros remain untouched. This candidate is not a
validated release until the runtime/settings matrix has passed.

## Architecture boundary

The generator keeps source bytes, line endings and processing order except for
an audited allowlist of command targets, installation paths and unique menu
names. It routes eight original StarDist calls to
`Features.Macros.LegacyMacroStarDist`, and three original Template Matching calls
to `Features.Macros.LegacyTemplateMatching.run`. Every replacement is recorded
with original and generated SHA-256 hashes in `MACROFORK_BUILD_INFO.json`.

The StarDist adapter accepts the existing script parameter map unchanged. It
uses the original requested tiles, model, probability, overlap, boundary and
output mode. `Both` still populates ROI Manager; the single-neuron macro depends
on that count. Thresholds are not rounded again. The original StarDist 0.3.0 NMS
command owns polygon selection, ROI construction and labels. `Automatic` ROI
placement uses the original dimension/RGB decision. Declared module outputs are
returned for ImageJ's normal display; no current-window fallback is used.
Probability/distance tensors keep the original uncalibrated axis metadata and
names from `StarDist2D.splitPrediction`; calibration is not silently added at
this boundary. Singleton TIME axes remain present because the original command
exports ROI frame 1 even for a one-frame time axis. Existing prediction planes
are wrapped without an additional full-volume copy.

Only inference uses the same isolated native worker as GATV2. Its supported
SavedModel contract still applies. The macros always request normalized input
with percentiles 1.0/99.8 and no CSBDeep progress dialog; unsupported changes to
those internal fixed options stop explicitly. The public macro settings for
rescale, probabilities, overlap, channels and custom models are retained. No
custom model is retrained, converted, replaced or downloaded.

Template Matching preserves the macros' method 5, 70% template, floor(size/6)
origin, full-image search, integer shifts and explicit reference slice 3. It
retains the selected reference/template rectangle, original Results headers and
before-reference descending/after-reference ascending row order. Unsupported
native worker options fail instead of being silently replaced.

The original RGB display-range preparation, DeepImageJ command, float-image
`Open` behavior, CLIJ overlap assignment, missing-neuron expansion, review,
measurement, export and settings code stay in the generated macros. DeepImageJ
is not replaced by the Java V2 ganglia implementation.

## Build and installation route

1. Build a GAT plugin containing the two new adapter classes and its generated
   SciJava plugin index. Keep both native workers outside `plugins/` and `jars/`
   as in the matching Apple Silicon package. Use native arm64 Fiji, its bundled
   JDK, and the same GAT dependency/model installations as the original macros.
2. Generate the separate script overlay, preserving existing settings when
   researchers already have an installation:

   ```sh
   python3 legacy-macros/build_overlay.py --output target/GAT-MacroFork-candidate.zip \
     --settings '/existing/Fiji/scripts/GAT/Tools/commands/gat_settings.ijm'
   ```

   Omit `--settings` only to use the repository's original default settings.
   This script only creates a ZIP; it does not install, overwrite or publish.
3. Extract the overlay into the Fiji data root (the folder containing `scripts`,
   `plugins`, `jars`, and `models`) alongside the original `scripts/GAT` folder.
   Restart Fiji. The separate `GAT MacroFork` menu uses unique `[MacroFork]`
   command names. The copied batch example calls its corresponding MacroFork
   command. Original command names and original script files remain unchanged.
4. Run the same workflow with the same image, saved settings, choices and model
   files. Output folders are still chosen by the original scripts: use separate
   output folders for original-versus-fork comparisons to avoid overwrite.

### Keep your existing research settings (no development tools needed)

Before first use or an upgrade, quit Fiji and open its data folder in Finder
(the folder containing `scripts`, `plugins`, `jars`, and `models`).

1. In `scripts/GAT/Tools/commands`, find `gat_settings.ijm`. Make a backup copy
   outside the Fiji folder. Keep the original in place.
2. If you already used MacroFork, back up its existing
   `scripts/GAT MacroFork/Tools/commands/gat_settings [MacroFork].ijm` outside
   Fiji as well before replacing any MacroFork package files.
3. Copy the original `gat_settings.ijm` into
   `scripts/GAT MacroFork/Tools/commands` and name that copy exactly
   `gat_settings [MacroFork].ijm`. Replace the package's default file there only
   after making the backups above. Keep the `.ijm` extension; do not open,
   reformat or edit its contents.
4. Reopen Fiji. For a comparison, choose the same image, channels, rescaling,
   ganglia method and other dialog choices in the original and MacroFork menus.
   Use separate results folders.

This copies the settings file unchanged. It does not transfer every dialog's
last-used values automatically. A distributed package contains repository
defaults until you supply your own file. We have tested byte-exact migration
using synthetic custom settings, but cannot verify your researchers' saved
values without their actual settings file. The optional `--settings` generator
argument above provides the same byte-preserving copy for automated packaging.

The script overlay alone is insufficient: it requires the plugin with the new
adapters and the matching native workers. This candidate currently has no
installer that automatically merges an existing Fiji or replaces its plugin.

## Evidence and limits

Run source contract tests with:

```sh
python3 -m unittest discover -s legacy-macros/tests -v
```

See the source repository's `validation/legacy-macros/` directory for the finite coverage contract. Source
allowlist checks and synthetic unit tests cannot establish full workflow parity.
Public-model and actual menu/UI checks must name their exact platform, commit,
model hashes, tested parameter combinations, output comparisons and any skipped
stages. Private microscopy inputs and all derived images stay outside public
artifacts and public CI.

The baseline is the preserved legacy script blobs in this repository, not Java
V2's `1870d9e` commit (which does not contain the legacy macros). Existing macro
bugs remain visible unless separately corrected and documented.

### Historical Sox10 route

The preserved `_Analyse Glia (Sox10 only).ijm` script still refers to
`GAT/Other/commands` and the original TensorFlow-era ganglia model. The exact
historical dependencies were recovered rather than substituted:

- Commit `e639a037341fd415534e1bb4da49a83085370bd2` (12 September 2021) renamed
  `Other` to `Tools`. Its parent contains the original
  `Other/commands/Ganglia_prediction_post_processing.ijm`, SHA-256
  `c3de8bb3148b9c17188b0292e6fa528e2a797476305a94253d46a9d733970261`.
  It selects prediction channel 1 and thresholds at 0.8 before making a mask.
- Commit `86ef468e7c72ed0eb4deaeda4eddf83b50adc641` contains
  `Models/2D_enteric_ganglia.bioimage.io.model_v1.zip`, 39,642,942 bytes,
  SHA-256 `9074c69f0198ae594988fa6ce87b86302cd2544633e9c825627f4741f765ff49`.
  Its descriptor name is `2D_enteric_ganglia`, with TensorFlow input
  `[1,768,768,3]` and the matching `per_sample_scale_range.ijm` preprocessing.
  The nested SavedModel archive's actual SHA-256 matches its descriptor:
  `25260bd717bbb290df375219c39c8724ceae420937db2b284dd819f66ff3b3a2`.
- Later history changes the postprocessor's 8-bit handling (`8739fa5`) and then
  embeds postprocessing in a newer model (`6888d99`, 16 February 2022).

These artifacts establish historical availability, not native execution or
which combination the researchers installed. The exact installed DeepImageJ
version, macro helpers and model still need matching before this route can be
validated. Its old three-channel TensorFlow model cannot be substituted with
the single-channel StarDist worker or the newer RGB v3 ganglia model. No
historical model was executed during this source lookup. Do not infer Sox10
validation from the supported neuron/ganglia candidate tests.

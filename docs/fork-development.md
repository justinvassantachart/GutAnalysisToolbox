# Developing the GAT v2 fork

The preview 6 release version is `2.0.1-apple-silicon.6`.
Published preview tags and release assets are immutable;
new source changes do not update an installed preview. This work concerns Java
GAT v2, not the original `.ijm` menus or QuPath workflows.

## Smallest useful checks

Use a complete JDK 17 or newer and Maven 3.9. SciJava dependencies require
`https://maven.scijava.org/content/groups/public`; they are not all available
from Maven Central.

```sh
python3 -m unittest discover -s scripts/tests -p 'test_*.py' -v
mvn -B -ntp -Dgat.tests.headless=true test
mvn -B -ntp -DskipTests package
```

Root tests exercise production helpers and adapter protocols without loading
legacy TensorFlow. CI runs them on Linux, hosted Intel macOS, and native ARM
macOS. It explicitly checks the real host's CPU detection; unit fixtures also
cover the Intel missing-sysctl-key response, Rosetta and failed probes. These
checks do not substitute for a physical Mac's OpenCL or interactive Fiji tests.
The suite runs on relevant pushes, `main`/`gat_v2` pull requests and manual dispatch;
configuring the trigger does not create a pull request.

The isolated workers have their own builds:

```sh
mvn -B -ntp -f native-inference/pom.xml clean package -Dtensorflow.platform=linux-x86_64
mvn -B -ntp -f native-alignment/pom.xml clean package -Dopencv.platform=linux-x86_64
```

Use `macosx-arm64` for each platform property when building ARM bundles. Run native-runtime validation
on the corresponding architecture. Existing corpus, fresh-Fiji, alignment,
multiplex and same-host baseline workflows remain the deeper, qualified gates;
retain their diagnostics and distinguish skipped, failed and passed steps.

## Supported input boundaries

- Ganglia input preparation follows upstream Java GAT v2 commit
  `1870d9e16e16fd6daeac0bd05122e851029ddedc`: reset each selected channel's
  display range, convert to 8-bit, then multiply each float channel by
  `1.0/255.0`. DeepImageJ receives a `[0,1]` float hyperstack with
  `R=Hu, G=Ganglia, B=Hu`; the RGB review image remains byte-valued.
  Keep the supplied model preprocessing unchanged. The model RDF's own
  scaling is not a reason to remove the upstream input scaling when testing
  V2 behavioral parity. `GangliaInputContractTest` covers all 256 byte values,
  16-bit and float conversion, channel mapping, unchanged source pixels and
  overlays, calibration, and retained output-selection safeguards. Input
  preparation tests alone do not establish end-to-end model or mask parity;
  use the same-host original/fork ganglia validation for those results
- Native StarDist accepts one 2D grayscale plane and full-resolution,
  single-channel SavedModels with probability plus radial-distance outputs.
  The validated models are GAT's existing neuron and subtype ZIPs; arbitrary
  custom models are not automatically compatible
- The worker/protocol cap is 268,435,456 float values per image/tensor. The
  supplied 97-output-channel models have a theoretical full-output ceiling of
  2,767,375 pixels before block padding. A 2048 × 2048 result exceeds it.
  Extra tiles reduce individual inference work, but do not remove the merged
  full-output allocation. Several arrays, TensorFlow and Fiji coexist; actual
  available memory may impose a smaller limit. Crop large inputs and validate
  representative workloads rather than treating this cap as a RAM guarantee
- Calcium analysis supports a single-channel grayscale stack whose one stack
  axis represents time: an ordinary ImageJ stack or C=1, Z=1 time series.
  RGB, multiple channels and simultaneous Z/T stacks are rejected before
  projection or F/F0 normalization. Separate channels and choose an explicit
  Z-plane/projection in Fiji first; GAT does not silently choose that scientific
  preprocessing for the user. Supported projection/division still use ImageJ's
  algorithms, including its zero-baseline NaN/infinity behavior

## Installation and update boundary

`mvn package` builds the plugin JAR only. The `app` and `install-to-fiji`
profiles do not install or update native workers. An ARM test installation
needs the matching complete preview overlay, including both worker directories,
model files and required Fiji dependencies; keep worker `lib/` directories out
of `Fiji/jars` and `Fiji/plugins`.

Use `scripts/package-apple-silicon-preview.py` and its matching build evidence
for a new test bundle. Its compiled-class comparison establishes build consistency,
not test execution; review the separate test results for the packaged revision.
Do not replace files inside a published release, mix
worker versions casually, or describe a plugin-only update as a complete native
installation. The Fiji updater may replace the preview plugin. Reapply only a
verified matching overlay and rerun its installation checks after an update.
Automated upstream distribution/update ownership is still unresolved; this is
an experimental separate-download fork.

Historical outputs and evidence stay in place. See
[the preview guide](apple-silicon.md) and
[the workflow matrix](apple-silicon-workflow-matrix.md) for dated results and
remaining physical/biological validation limits.

Current hardening evidence: [6 October 2026 verification](validation/fork-hardening-2026-10-06.md).

Independent cleanup review: [6 October 2026 findings and verification](validation/maintainer-review-2026-10-06.md).

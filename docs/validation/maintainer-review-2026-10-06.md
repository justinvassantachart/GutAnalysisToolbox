# Independent maintainer-readiness review — 6 October 2026

Review baseline: `cf758ad3bcb8304d96a3cba5f96b3d8b0923e314` (preview 4).
The published preview 4 tag, assets and historical validation packets are unchanged.
This review concerns Java GAT v2 and its isolated workers. It does not port the
legacy ImageJ macros or QuPath scripts, or claim biological acceptance.

## Findings and disposition

- **Alignment display mapping: fixed.** The original Template Matching code
  matches rendered 8-bit pixels. The process adapter preserved the base LUT but
  discarded the display range, which could change the selected shift. A seeded
  64 × 64 control with display range 100–120 changed from the direct algorithm's
  `(10, -7)` to `(-2, -1)` after the old protocol round trip. Protocol version 2
  carries the base palette and display range. The worker restores both and
  rejects inconsistent per-plane metadata that ordinary ImageStack cannot
  preserve. Old plugin/worker protocol versions fail explicitly. Install the
  plugin and matching alignment worker together
- **Main-branch CI: fixed.** Existing native workflow push filters now include
  `main`; existing pull-request filters include `main` and `gat_v2`. Path filters,
  historical-result exclusions and explicit failure reporting remain unchanged.
  No pull request was opened
- **Packaging evidence wording: fixed.** Newly generated metadata says
  `plugin_classes_match_compiled_classes`. Byte comparison establishes build
  consistency, not test execution. Separate test results must be reviewed.
  Historical metadata is preserved as originally published
- **Documentation freshness: fixed.** README source instructions no longer
  depend on main remaining unchanged. The initial multiplex correction's test
  status is labeled historical and links to the subsequent native paired run
- **Main-only assets: integration gate.** Main has 101 paths absent from the
  Java-v2 branch, including original models, sample data, macros, QuPath scripts
  and citation information. The final merge must preserve their exact original
  blob IDs and modes and both branch histories. Their presence does not expand
  the native preview's supported workflow scope

Independent architecture review approved the scoped CI/provenance changes and
requested no broad runtime refactor. Runtime review independently reproduced
the alignment defect and verified all 30 seeded direct-versus-roundtrip cases
match after the correction. The scientific matching method, reference ROI,
search, integer peak selection and image translation are unchanged.

## Local verification

Linux x86-64, complete Temurin JDK 21, Maven 3.9.11, cached pinned dependencies:

- Root plugin: 78 tests passed, zero failures/errors/skips; full package built
- Native alignment: 12 tests passed, zero failures/errors/skips; clean Linux
  worker package built. Four cases execute real native OpenCV and compare exact
  rendered pixels and shifts for adjusted grayscale, inverted and colored 8-bit
  LUTs, and a 16-bit control
- Native inference: 16 tests passed, zero failures/errors/skips; inference source
  and numerical settings are unchanged
- Packaged process boundary: the actual production client launched the newly
  packaged worker JAR; all four display/LUT controls matched direct algorithm
  shifts, including the original `(10, -7)` regression case
- Packaging: seven Python tests passed
- Baseline harness: six Python tests reported, including two explicit virtual-GUI
  skips; this is not a native-Fiji execution result
- `git diff --check` passed

Local test JVM heap and thread limits and Mockito's startup agent accommodate
the constrained container. They are not production runtime defaults.

## Remaining verification boundaries

These local results do not establish native-Mac execution, physical OpenCL,
complete interactive workflows or biological equivalence. Hosted checks for the
new revision must be assessed separately before release. The prior
[hardening report](fork-hardening-2026-10-06.md) and
[workflow matrix](../apple-silicon-workflow-matrix.md) retain their original,
qualified results; a hosted Mac with no OpenCL device is not a passing GPU test.

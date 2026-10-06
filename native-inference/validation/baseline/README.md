# Unchanged pre-fork GAT on native Apple Silicon

This is a **baseline experiment**, not a modified old release. The production
checkout must be the exact upstream `gat_v2` commit
`1870d9e16e16fd6daeac0bd05122e851029ddedc`, in a separate directory from the fork.
Its tracked files are checked for changes before and after execution. Build
outputs are generated from those sources. No fork `Features.Inference` classes,
modern TensorFlow API, native worker, Rosetta, or replacement alignment backend
is on the original application's classpath.

The same validation Java sources, synthetic/public fixtures and pinned plugin
dependencies used for the fork are compiled against the original classes.
The wrapper imports the common workflow runner and changes only its production
project root. It does not edit the common runner or baseline sources. Original
SIFT single/batch save-and-reopen, calcium controls, ganglia input-contract,
helpers and command results retain their actual PASS/FAIL/BLOCKED/NOT_RUN states.
Unrelated helpers are allowed to pass; this experiment never asserts that every
old workflow must fail. Standalone PyTorch engine checks are GAT-independent and
are labeled accordingly if selected.

Every native-risk suite runs in a separate JVM with a deadline and memory bound.
A timeout or setup problem is recorded as such, not inferred to be an Apple
Silicon incompatibility. A successful CI evidence job means observations were
saved, **not** that the old program passed. Consult `run-summary.json` and each
per-check report. Missing observations and source/classpath contamination fail
the evidence job.

## Build without changing the original POM

The original POM omits an explicit SciJava repository. The external
`scijava-settings.xml` supplies that repository only. This is documented build
environment configuration, not a source patch. The original Java release level
and dependency versions remain unchanged. Use the same native Java 21/macOS 14
runner as the fork workflow, and preserve `uname -m`/JVM architecture evidence.

Check out the fork and original revision as sibling directories, for example
`$GITHUB_WORKSPACE/fork` and `$GITHUB_WORKSPACE/original`, so baseline isolation
checks cannot accidentally accept the fork's target directory.

```sh
mvn -B -ntp -s fork/native-inference/validation/baseline/scijava-settings.xml \
  -f original/pom.xml -DskipTests -Dlicense.skipAddLicense=true -Dlicense.skip=true \
  clean compile dependency:build-classpath \
  -Dmdep.outputFile="$PWD/original-classpath.txt"
python3 fork/native-inference/validation/baseline/run_workflows.py \
  --project-root original --root-classpath original-classpath.txt \
  --output baseline-results/workflows --cache baseline-dependencies \
  --only helpers registration calcium ganglia-contract ganglia-command
```

No source checkout, download, or plugin installation happens automatically in
the wrapper. The shared runner fetches only its hash-pinned official validation
dependencies. Do not upload source data or entire caches as CI diagnostics.

## Local control

The unchanged source compiled successfully on Linux Java 17 with only the
external SciJava repository profile. This is a build/control result, not the
requested native Mac result. Baseline Mac evidence must be linked to its exact
CI job and source revision before drawing a platform conclusion.

Run isolation tests with:

```sh
python3 -m unittest discover -s native-inference/validation/baseline -p 'test_*.py' -v
```

## Same-host Mac job

`mac-ci-job.yml.example` checks out both revisions as siblings and executes the
same controls sequentially on one native Mac/JVM installation. Original workflow
failures are preserved as observations; repaired-control failures still fail
their CI step. Every later evidence step and final upload runs even after a
failure. The same recipe is provided in the separate
`.github/workflows/unchanged-baseline.yml`; it does not modify the general
workflow-validation job. Native probe implementation and exact dependency provenance
are supplied by `BaselineNativeProbe.java` and `run_native.py`.

## Preserved native Mac observations

- [First paired run](results/mac-first-69feedb/REPORT.md): original command failures,
  classloader qualification and unresolved calcium dialog interaction
- [Sonoma accepted-dialog rerun](results/mac-sonoma-528f0b0/REPORT.md): original and
  fork calcium pass; original SIFT data-flow failures are reached; repaired native
  APIs pass; original TensorFlow native-load error and modal timeout are explicit
- [Sequoia independent comparison](results/mac-sequoia-fe5fd7b/REPORT.md): same
  substantive before/after outcomes on macOS 15.7.9, with separate immutable evidence

Both later runs keep their failed overall CI status from the original native
error-dialog timeout. Original unaffected helpers and ganglia command passes
are preserved, as are unsupported/unrun branches. They do not establish complete
GUI coverage or support across all Apple Silicon chip generations.

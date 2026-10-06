# GAT v2 fork hardening — 6 October 2026

Source baseline: `287c27e5bd12b874044f271f13d7a241991ac9ca`.
Development version: `2.0.1-apple-silicon.4-SNAPSHOT`.
Published preview 3 and all historical evidence remain unchanged.

## Corrections

1. CPU selection accepts Intel macOS's exact missing `hw.optional.arm64` OID
   diagnostic (exit 1), as well as numeric zero. Native ARM and Rosetta retain
   their native-worker route. Unknown/malformed/error outcomes still fail
   closed before loading legacy TensorFlow. The bounded probe uses a fixed
   locale and rejects extra output
2. Calcium analysis rejects multichannel, RGB and simultaneous Z/T input before
   prompts or numerical processing. Ordinary one-channel stacks and C=1/Z=1
   time series retain ImageJ projection and F/F0 behavior. Failed loads clear
   stale state; the dashboard reports errors and does not add an old result tab
   after cancellation
3. Root CI covers Linux, hosted Intel macOS and native ARM macOS, checks the
   actual host detector, and runs for relevant pushes, `gat_v2` pull requests
   and manual dispatch. Whole-suite retries were removed so a failed assertion
   cannot be hidden by a later retry. No pull request was opened

## Local verification

All runs below used a Linux x86-64 cloud environment, Maven 3.9.11, and a
checksum-verified complete Temurin JDK 21.0.12.1. These are not physical-Mac
results.

- Root Maven: **76 tests, zero failures, errors or skips** across 16 test classes
- Native inference: **16 tests passed** and the Linux worker ZIP built
- Native alignment: **5 tests passed** and the Linux worker ZIP built
- Across the three Maven modules: **97 tests, zero failures, errors or skips**.
  Worker unit suites cover protocol, normalization and signature contracts; they
  are not evidence of a fresh native-Mac or biological corpus run
- Fresh Linux TensorFlow 2.21 JNI/model smoke: both checksum-pinned GAT models
  passed using the unchanged validation script and four tiles. Each returned
  finite 129 × 97 × 97 predictions; neuron probability range 0–0.853756 and
  subtype range 0–0.754191. This is execution/protocol validation, not scientific
  equivalence or Fiji/Mac validation
- Full root package and runtime-classpath generation: passed; the shaded plugin
  includes its UI dependencies and excludes ImageJ classes
- Focused calcium checks: 17 passed, including real ImageJ 1.54p projection and
  division, unsupported TIFF loading, error propagation and cancellation
- Focused backend checks: 11 passed, including Intel missing-OID, Rosetta,
  malformed/failed probes, and the actual Linux host. The two focused counts
  are subsets of the root suite, not additional independent corpus samples
- Ten portable Python validation/package suites: all successful; their output
  reports 156 tests with three skip entries (one native-dialog setup class
  requiring extra probe dependencies and two virtual-GUI tests)
- Independent diff review and `git diff --check`: passed

Root verification command (with local Maven/proxy settings outside the repo):

```sh
mvn -B -ntp package dependency:build-classpath \
  -Dmdep.outputFile=target/workflow-classpath.txt \
  -Dgat.tests.headless=true -Dgat.test.expectedAppleSilicon=false
```

This constrained container needed bounded JVM heaps and Mockito's standard
startup Java agent. An initial unbounded Maven process was killed before test
results; the first bounded run reached 76 tests but 18 mock-based tests could
not self-attach. With the startup agent, all 76 passed. No tests were excluded
and no production code was changed to suppress those environment failures.

The first real-model smoke loaded TensorFlow and the neuron model but was killed
before predictions completed. A bounded retry passed both models with 96 MB
Java heap/direct-memory caps, one active processor, one thread per native
runtime and `MALLOC_ARENA_MAX=2`. Model weights, tiling, oneDNN and production
numerical settings were unchanged. These test-environment limits are not new
production defaults.

## Hosted CI after publication

The following runs target the exact production/test commit
`cad2da658141cd281c6717408eb6f1a2ae6b0efd`. Any later change that only updates this
report is evidence maintenance, not a new tested production revision.

- [Root platform matrix](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37506388212):
  Linux and hosted native ARM Mac were verified successful. The last verified
  Intel Mac snapshot was still running at 17:49:58 UTC; its final result and raw
  sysctl diagnostics were not verified when this report was written. Do not
  infer that Intel passed or failed; the linked run is the authoritative record
- [Native multiplex](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37506388233):
  completed successfully
- [Native workflow checks](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37506388283):
  workflow/engine, Template Matching and JPEG-XR jobs completed successfully.
  The separate OpenCL job failed: the virtual Mac exposed no devices and
  `clGetDeviceIDs` returned `-30`. This gate is left visibly failed; it is not a
  passing GPU check or proof of a defect on a physical Mac
- [Same-host unchanged Java-v2 baseline comparison](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37506388426):
  completed successfully. This compares upstream Java GAT v2 with the fork;
  it does not validate the legacy `.ijm` workflows

The downloaded calcium report confirms the production open/projection/F/F0/
ROI/measurement/save path on hosted Apple M1 (Virtual), macOS 15.7.9, Java 21.
The controlled baseline and projection dialogs produced measured F/F0
`[1, 1, 2]`, one ROI and saved CSV/ROI outputs. It is a bounded command test,
not dashboard navigation or a manual physical-Mac trial. The broader report
remains explicitly partial: unsupported, blocked and unrun checks retain
those labels rather than becoming a blanket full-workflow pass.

## Remaining gates

Rosetta outcomes above are simulated probe regressions, not a physical
translated-JVM test. The separate local Linux GUI attempt was blocked before
Java started by unavailable display sockets; the hosted Mac calcium command
result above is the fresh, bounded numerical check that subsequently ran.
Physical OpenCL/GPU, complete interactive workflows and biological acceptance
remain open. Earlier native/paired scientific evidence retains its original
scope and qualifications; it is not a fresh full corpus run of this revision.

# Actual original/native alignment capacity regression

This source-only harness compares the actual original and native alignment
routes on a deterministic synthetic movie. It is separate from the basic
seven-case alignment lane. Actual hosted artifacts record execution outcomes;
no private images or historical local result receipt are included here.

## Question

Can the actual pinned original Template Matching command align a
512×512×257 8-bit stack (67,371,008 total pixels), just above MacroFork's former
67,108,864-total-pixel safety cap? A successful run would demonstrate one real capacity
difference. Failure under this experiment's resource ceiling is inconclusive;
it does not establish an original maximum size.

## Bounds and evidence

- One 256 MiB / one-CPU ImageJ parent. The native route uses the separate
  unchanged 1 GiB-heap worker and a 120-second test-only worker timeout. Each
  entire process tree is capped at 1 GiB observed RSS and 180 seconds, with one
  OpenMP/BLAS thread. Original runs on Linux; native runs on Linux and arm64 Mac.
- The same official pinned Template Matching/OpenCV parent runtime and actual
  original macro call/options as the basic alignment probe. No fork/worker is
  visible to the original parent.
- Four cyclic known integer shifts of a fixed Java-Random seed8291 image,
  reference slice3, 257 planes. Original bytes are about64.25MiB. Hashing and
  the independent translation checks operate one byte plane at a time; the
  probe does not construct a whole-stack float duplicate.
- Real command dispatch, completed macro continuation, unchanged expected
  display/calibration/ROI/slice labels, all67,371,008 aligned pixel values,
 256 motion rows in the original traversal order, visible Results, and an
  actual CSV roundtrip are required.
- The Python launcher independently reconstructs exact input/output hashes and
  checks the invocation, original plugin hash and all CSV values. Native reports
  additionally require forced native dispatch, the exact production class and
  an observed separate worker. Reports never claim full calcium-workflow parity.
- Original image bytes are synthetic and are generated only inside the test.
  Retain JSON, invoked macro, runtime log and CSV; no private inputs are accepted.

## Explicit execution, after capacity coordination

Prepare the isolated classpath with `alignment_runtime.py` as documented in
`alignment-README.md`. The dedicated alignment workflow runs both original and native capacity controls.
On a supported Linux desktop use the command below. On hosted Linux, prefix it
with `xvfb-run -a`; the launcher never starts a display server.

```sh
python3 validation/legacy-macros/run_alignment_capacity.py \
  --runtime-classpath target/alignment-runtime/runtime-classpath.txt \
  --output target/alignment-capacity-original
```

`--compile-only` compiles without any AWT execution and records
`COMPILED_NOT_RUN`. Every attempt requires a fresh output directory. Timeout,
process-tree ceiling, compilation failure and any incomplete/mismatched
observations remain failure/inconclusive evidence. Do not loosen bounds merely
to obtain a pass.

```sh
python3 -m unittest discover -s validation/legacy-macros \
  -p test_alignment_capacity.py -v
```

These tests exercise the evidence gate with explicitly fabricated reports;
they are not model, JNI or macro runtime evidence. Any streaming or per-frame
production redesign requires review of actual results first.

## Native comparison and memory admission

Use `--variant native --production-classes target/classes --native-worker
native-alignment/target` with a fresh output directory for the native control.
`compare_alignment_capacity.py --original ORIGINAL_DIRECTORY --native
NATIVE_DIRECTORY --output REPORT_JSON` requires exact synthetic pixels, motion
rows/CSV, source versions and explicit measured RSS within the common bounds.
The report includes the actual 67,371,008 raw pixel bytes on each host.

Production admission now requires both raw bytes≤512 MiB and raw bytes plus
8×plane pixels plus64 MiB≤768 MiB. The 8-byte/pixel term reserves transient
managed plane storage; a further256 MiB remains outside the estimate under the
worker's 1 GiB heap. Native OpenCV allocations are not included, so this is not
an all-memory guarantee. Fiji serializes to disk without a full byte payload
copy; after the worker exits it builds a translated copy of the source stack.
No matching algorithm, protocol or image processing operation is changed.

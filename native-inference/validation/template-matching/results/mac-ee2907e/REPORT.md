# Native Mac Template Matching: port and actual adapter

[Run 37369827047, job 111963931249](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37369827047/job/111963931249) passed on native macOS ARM64 / Temurin 21.0.12.1, source `ee2907e371b12b1951a507141f797afedb460aef`. The comparison uses unchanged original-author Linux references from JavaCV 1.4.4 / OpenCV 4.0.1 and the API-only OpenCV 4.11 port. No matching algorithm or threshold was changed for the native build.

## Exact outcomes

Both the original-algorithm API-port harness and the actual GAT `alignTemplateMatching → isolated worker → translated image` path match **all six fixed cases and 300 frame outputs** exactly in integer shifts and aligned-pixel hashes:

- 8-bit and 16-bit four-frame synthetic fixtures with reference 1
- 8-bit reference 3 and 16-bit reference 2 synthetic fixtures
- All 142 public calcium frames with reference 1, then the same frames with reference 71

These are **300 outputs per execution path**, not 600 independent images. The public source has 142 distinct frames reused for two references. This tests alignment software, not automatic calcium segmentation or biological accuracy.

Independent review compared each case's width, height, bit depth, frame count, every shift pair and full aligned-pixel SHA-256 against the pinned legacy reference (SHA-256 `fa5cbcb330667911af446d7e85f84d8bae1eeffed6fea25282946e2612a978fa`). All fields matched. It separately parsed all **six motion CSVs / 300 rows**, checking algorithm, reference index, sequential slice IDs and numeric Dx/Dy against the actual adapter's shifts. Metadata and input-preservation assertions ran inside the adapter harness. A successful helper/process test is not a complete dashboard/navigation test.

This packet fixes an evidence-retention gap in an earlier job: the port output is now outside Maven's cleaned `target/` directory. Both port and adapter reports are retained. The earlier missing artifact did not establish a failed algorithm test; it lacked the requested saved evidence.

## Preserved evidence

`original-ci-diagnostics.zip` is the unmodified 6,807-byte GitHub artifact 11370540242, SHA-256 `37eff7ef0c97df86cee2f5d3caeedd76e2cd36f5fc3462f6c0119cd1b7c29639`. It contains the two independent result sets, adapter log and six CSVs. Every member is fingerprinted in `original-artifact-files-sha256.json`; `summary.json` preserves the reports and independently checked outcomes. The public image SHA-256 is `3ff6e4eb82a1ee4cd128c079a97c7d99be2be51168cbe4c9a0fe6e77e13f91af`.

The full API-port process took 8.13 seconds including setup; actual adapter per-case measurements are retained. These are single hosted-runner timings, not a controlled hardware benchmark or CPU/GPU speed comparison. No general physical-Mac, arbitrary bit-depth or every-GAT-workflow claim follows from these bounded fixtures.

Run `python3 independent_check.py` from this directory (or invoke its full path) to repeat the read-only artifact/reference/CSV checks. It needs only Python’s standard library and extracts no files.

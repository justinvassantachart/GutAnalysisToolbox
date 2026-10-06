# Completed same-host baseline with passive error-dialog evidence

[Run 37369827141, job 111963926821](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37369827141/job/111963926821) completed successfully on **native M1 (Virtual), macOS 15.7.9, aarch64 Temurin 21.0.12.1**. Original `1870d9e16e16fd6daeac0bd05122e851029ddedc` and fork `ee2907e371b12b1951a507141f797afedb460aef` ran on the same host. Original source remained clean and isolated from fork inference classes/modern TensorFlow.

**Green CI means the observations are complete and the repaired gates pass. It does not mean the original application passed.** The actual before/after results reproduce the [prior Sequoia comparison](../mac-sequoia-fe5fd7b/REPORT.md), with the former error-dialog timeout replaced by a narrowly observed failure:

- Original StarDist reaches the real GAT/plugin call and displays the exact CSBDeep TensorFlow native-load error. The observer records its raw HTML/title, ERROR_MESSAGE type, newly created visible modal window, untouched option state (`UNINITIALIZED_VALUE`), call stage and thread stacks. It atomically saves `workflow_failure` and halts only that isolated JVM, exit 2, after 6.28 seconds. It does not dismiss/answer the warning, enter Library Management or wait for the 600-second deadline. The native-load warning and separate TF1 JNI control identify missing `darwin/aarch64` support
- Original Template Matching reaches the real GAT/plugin call and records the OpenCV JNI loading error; deliberately shifted pixels remain unchanged
- Repaired StarDist returns 39 objects and exact four-tile reference raster hash `ea1767df58491cc03927e121943d955708450d091f3416b2493e1c93e51cd443`. Repaired alignment returns exact reference pixel hash `8be9c6ad7c4c28d68b07f0b45c562deb9d29e4febf030b0ad24dcb198ea7fa9c`
- Original and repaired accepted-dialog calcium controls both pass; both full ganglia commands also execute successfully. Original SIFT helper/save/batch and ganglia raw-input-contract failures remain failures, while repaired checks pass
- Common-control reports retain original 15 PASS / 4 FAIL / 1 BLOCKED / 8 NOT_RUN and fork 19 PASS / 1 BLOCKED / 8 NOT_RUN. Explicit unsupported/unrun branches remain outside acceptance

The dedicated **live Mac observer step ran all three tests, with zero skips**. These include a real visible modal control and near-match/pre-call/preexisting/nonmodal negative controls. Synthetic observer tests do not masquerade as real GAT results; actual original/fork calls are separate observations. The earlier immutable packets retain their genuine timeout status. Original command termination here is an observation of its displayed failure, not a completed successful or failed model prediction.

The native-call probes use the explicitly recorded diagnostic URL-system-loader embedding. The separate official-Fiji launcher/setup validation is not replaced by this run. It does not establish complete GUI coverage, biological accuracy, every Apple Silicon generation or GPU performance. Successful repaired cold process times, including setup, were 12.87 seconds for StarDist and 4.75 seconds for alignment; failed originals are not a valid speed comparison.

## Immutable evidence

`original-ci-diagnostics.zip` is the unmodified 158,216-byte GitHub artifact 11370716947, SHA-256 `467cb389b0ddfbd1e450af0295d3830cc4457195c3f3d2e74effbe23f871425b`. All 79 members are independently hashed in `original-artifact-files-sha256.json`. The archive includes `live-dialog-controls.log`, actual-call snapshots, explicit component failures and final clean-source status. `summary.json` retains portable copies of the observations, including full dialog/thread evidence; raw archive paths and contents are unchanged.

# Frozen native multiplex failure evidence: 5a00f6d

**Native full-service acceptance failed.** This packet preserves the failure, not a
correction or a claim that multiplex registration is ready for release. Future
fixes and reruns belong in a separate evidence directory; do not rewrite this one.

## Recorded native run

- Commit: `5a00f6d6a414f5bd59e0b5dc461eb469afda907c`
- [Run 37375259755](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37375259755)
- [Job 111995832061](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37375259755/job/111995832061)
- [Artifact 11372532765](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37375259755/artifacts/11372532765)
- GitHub job: completed, `failure`. Artifact-preservation step: `success`
- Suite: `FAIL`; `full_service_acceptance_passed=false`
- Host: macOS 15.7.9, Darwin arm64, `Apple M1 (Virtual)`, `VirtualMac2,1`
- JVM: Eclipse Adoptium / Temurin 21.0.12.1, native `aarch64`
- Source tree recorded clean; source, class, dependency and harness hashes are
  retained in `summary.json` and in the untouched original archive

This is the recorded hosted virtual Mac, not the user's physical M1. The fixture
is deterministic synthetic 256×256, 8-bit TIFF data: three rounds, three markers
per round, with known round translations `(0,0)`, `(7,-5)` and `(-6,8)`. No private
research images were used. No biological or platform-universal claim follows.

## Reached checks

`controls`, `display-probe`, `no-files`, `missing-marker` and `missing-round` all
passed their recorded scopes. `full-sift` and `full-mops` both finished at phase
`complete`, each with six PASS, three FAIL and two NOT_RUN checks.

The actual SIFT-path service returned in 2.271115792 s (cold process 3.194886833 s).
The actual MOPS-path service returned in 9.708668042 s (cold process 10.6900385 s).
These are observed synthetic-run timings, not a performance benchmark.

Both full-service cases passed:

1. Actual service return
2. Saved/reopened dimensions, all seven channels and exact filename labels
3. All three common-marker QC planes retained unwarped
4. All nine original input TIFF hashes preserved
5. Observed real plugin route: two SIFT or two MOPS extractions, then four
   `Landmark Correspondences` warps
6. The narrowly scoped final open-results **Cancel** and verified Done dialog
   (`[  OK  ]` button), with saved bytes unchanged and batch mode restored

Both full-service cases failed these three actual assertions:

1. `every_round_and_channel_transform`: the first later-round marker examined,
   `Layer2_MarkerA.tif`, had unchanged MSE, 3030.62287352071 before and after
2. `saved_calibration`: reopened aligned output had unit pixels and zero frame
   interval instead of the reopened input's calibrated values
3. `landmark_zip_roundtrip`: pair 1 had wrong direction/order, with mean known-
   translation error approximately 8.602325267 px

The native transform assertion stops within that check at the first failing
channel; it does not itself supply measurements for the remaining channels.
The independent saved-output inspection below checks all seven. Likewise, the
native ROI assertion stops at pair 1; the independent audit inspects both pairs.
The calibration check logs both outputs before the first assertion fails.

Computation cancellation and block-matching fallback are explicitly NOT_RUN.
Final-dialog Cancel is not computation cancellation. MOPS was deliberately reached
at the allowed `stepsPerScaleOctave=31` boundary, not through a naturally occurring
SIFT failure. The pinned plugin manifest lacks the block-matching command; this
says nothing about every external Fiji installation. A service return and final
Done dialog do not establish transform correctness.

## Direct saved-output evidence, independent of the harness

`independent/ReviewMultiplexOutput.java` reopens the archive's TIFFs and decodes
its ROI ZIPs with the exact recorded ImageJ 1.54p JAR. Its rerun log is byte-identical
to the original independent review log. For each of SIFT and MOPS:

- All seven aligned output channel byte arrays equal their corresponding
  **unwarped source** arrays, including all four later-round marker channels
- Dimensions are `[256, 256, 7, 1, 1]`
- Reference/target coordinates within each exported ROI pair are identical:
  SIFT pair counts 62 and 80; MOPS pair counts 1040 and 1483
- Both pairs have mean dx=0, mean dy=0 and maximum paired displacement=0

`independent/ReviewSavedCalibration.java` separately reopens all relevant TIFFs:

| Saved TIFF | Pixel width | Pixel height | Pixel depth | Frame interval | Unit |
| --- | ---: | ---: | ---: | ---: | --- |
| Input `Layer1_Hu.tif` | 0.5 | 0.7500001875000468 | 1.0 | 1.25 | µm |
| `Aligned_Stack.tif` | 1.0 | 1.0 | 1.0 | 0.0 | pixel |
| `hu_stack.tif` | 1.0 | 1.0 | 1.0 | 0.0 | pixel |

These values hold in both cases. The input is reopened from disk, so ordinary
TIFF rational rounding of 0.75 is already accounted for. The nominal fixture
pixel depth is not substituted for the saved input's actual depth of 1.0.

These independent audits ran on Linux x86-64 / Temurin 17.0.20.1, headless, with
no registration or model inference. They establish facts about the saved Mac
bytes; they are not another native workflow run. Their process exits, runtime,
JAR hash and logs are recorded in `independent/provenance.json`. Audit exit 0
means inspection/reproduction completed, not that the production workflow passed.

## Source causal diagnosis, separated from measured outputs

Historical source snapshots are copied from the tested commit and their SHA-256
values match the native summary. They are evidence copies, not production edits.

- `IJUtils.java:70–74` selects via
  `WindowManager.setCurrentWindow(imp.getWindow())`. The isolated
  `ReviewMultiplexBatchSelection` control shows that, in batch mode, both windows
  are null; the helper leaves `review_target` current when asked for `review_ref`.
  `IJ.selectWindow` selects `review_ref` in the same control. This is a reproduced
  helper-level failure with a positive selection control
- `FeatureMatching.java:139–149` depends on that helper around `rm.addRoi` and
  `rm.select`. Restoring the reference ROI onto the still-current target could
  overwrite the target's live selection before it is stored. This is a source-
  based causal explanation consistent with identical exported pairs, not a
  native trace proving every intermediate mutation
- `MultiplexRegistrationService.java:279–282` restores each ROI before selecting
  its intended image, another current-image ordering concern
- New QC and final stacks are constructed at service lines 169–170 and 219–220
  without an explicit calibration copy, consistent with measured metadata loss

The saved-output defects stand independently of those diagnoses. No production
fix or corrected native run is implemented or validated by this packet.

## Earlier cancelled run remains inconclusive

[Run 37374110712](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37374110712),
[job 111978206214](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37374110712/job/111978206214),
used commit `3ef9d824d34e9800b961725a87c1236f829c0c9c`. The coordinator reports
operational cancellation after the declared 40-minute observation bound.
Separately saved connector metadata records terminal `cancelled`, no artifacts,
and a post-terminal log lookup returning HTTP 404 `BlobNotFound` at
2026-10-05T21:57:25.0102979Z. The service step remained marked in-progress in that
terminal response; no actual service assertion or output was recovered.

That run is **inconclusive**, with no product-defect attribution. The later padded
Done-button matcher correction must not be presented as proof of what caused the
entire earlier stall. `separate-run-metadata/` contains decoded read-only connector
results, not raw HTTP bytes or members of the original native artifact ZIP.

## Preservation and verification

- `original/gat-multiplex-native-5a00f6d.zip` is the untouched 394,926-byte artifact
- SHA-256: `5fb5df261efbb1666b1427c53b62fc7fc4b8e534456273a3c0109e8ad3a63985`
- `original/artifact-manifest.json` records the size and SHA-256 of all 77 members
- All input TIFFs, saved output TIFFs and ROI ZIPs remain inside that original ZIP;
  they are not redundantly expanded in this compact packet
- Summary, reports, commands, fixture manifests, phase markers and logs have
  readable portable copies at the same relative paths. Only documented runner
  path/user substitutions differ. `portable-copy-manifest.json` maps every copy
  to its original size/hash and portable size/hash
- `SHA256SUMS` covers every packet file except itself. A separately frozen staging
  manifest outside the repository covers every relative path, SHA-256 and size,
  including `SHA256SUMS`

Run the read-only verifier from any directory:

```sh
python3 /path/to/mac-5a00f6d/verify_packet.py
```

The verifier checks packet membership/hashes, the original ZIP and every member,
the exact portable transformations, source hashes, separately sourced terminal
metadata and the recorded failure status. It performs no network request or write.

To rerun only the independent inspections, use JDK 17+ and the already available
ImageJ 1.54p JAR with SHA-256
`2e1a09961dfb41cee66ddc821b2577a41a072566ce45a49bae69267099741e20`.
Work outside this frozen packet:

```sh
cd /path/to/mac-5a00f6d
python3 verify_packet.py
export IJ_JAR=/absolute/path/to/ij-1.54p.jar
WORK=$(mktemp -d)
mkdir "$WORK/classes"
unzip -q original/gat-multiplex-native-5a00f6d.zip -d "$WORK/artifact"
javac -encoding UTF-8 -cp "$IJ_JAR" -d "$WORK/classes" \
  independent/ReviewMultiplexOutput.java \
  independent/ReviewSavedCalibration.java \
  independent/ReviewMultiplexBatchSelection.java \
  independent/source-snapshot/services/multiplex/util/IJUtils.java
java -Djava.awt.headless=true -cp "$WORK/classes:$IJ_JAR" ReviewMultiplexOutput \
  "$WORK/artifact/full-sift" "$WORK/artifact/full-mops"
java -Djava.awt.headless=true -cp "$WORK/classes:$IJ_JAR" ReviewSavedCalibration \
  "$WORK/artifact/full-sift" "$WORK/artifact/full-mops"
java -Djava.awt.headless=true -cp "$WORK/classes:$IJ_JAR" ReviewMultiplexBatchSelection
```

The batch control deliberately compiles the historical helper and expects its
selection failure; compiling a later fixed working-tree helper would change the
question being tested. These inspections never modify the native outputs.

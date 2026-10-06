# Frozen corrected native multiplex evidence: ab046cb

**All requested native scopes passed, including full-service acceptance.** This
packet preserves the corrected run and its comparison with the adjacent frozen
failure packet. It does not replace or modify that earlier evidence.

## Exact identities

| | Failed source | Corrected source |
| --- | --- | --- |
| Commit | `5a00f6d6a414f5bd59e0b5dc461eb469afda907c` | `ab046cb604dc04e75cf935b7a9f3c17b52843188` |
| Run | [37375259755](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37375259755) | [37380708003](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37380708003) |
| Job | [111995832061](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37375259755/job/111995832061) | [112001650098](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37380708003/job/112001650098) |
| Artifact | [11372532765](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37375259755/artifacts/11372532765) | [11373712129](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37380708003/artifacts/11373712129) |
| Suite | `FAIL` | `PASS_REQUESTED_SCOPES` |
| Full-service acceptance | false | true |

Corrected GitHub job conclusion: `success`. Its source POM identifies core candidate
`2.0.1-apple-silicon.3`. This is the corrected source candidate, not a retrospective
validation of the earlier preview-2 build. Release-package identity and distribution
are separate checks; this packet contains test evidence rather than an installable
release. It neither modifies nor replaces existing preview-2 release bytes.

Both runs record a clean source tree, macOS 15.7.9 / Darwin arm64, an
`Apple M1 (Virtual)` / `VirtualMac2,1` hosted runner, and native Eclipse Adoptium
Temurin 21.0.12.1 (`aarch64`). These are recorded runner identities, not the user's
physical M1 or proof that the runs used the same individual VM.

## What changed, and what did not

`comparison/paired-comparison.json` records direct byte/hash checks:

- All 18 retained full-route input TIFFs are byte-identical across runs: nine
  inputs each for SIFT and MOPS
- All five recorded harness sources have identical hashes, also checked against
  their exact Git blobs in both revisions. The full probe, runner, dependency
  manifest, fixture provenance and reporting tests are unchanged
- All 97 runtime JAR filename/SHA-256 pairs, the three pinned registration
  dependencies and the official command manifest audit are identical
- Only three of the five recorded multiplex production source files changed
- The prior 56-file failure packet still matches its original frozen manifest

Therefore the new pass is not achieved by changing assertions, thresholds, input
TIFFs, expected fixture generation, plugin dependencies or the tested configuration.
This is a paired correction result, not an experiment isolating each individual
code change. Exact old/new source hashes and a focused production diff are retained.

The production correction does four related things:

1. Selects batch images through ImageJ's image-aware selection API
2. Snapshots independent reference/target landmark ROIs before ROI Manager
   operations, then restores cloned pairs directly to their intended images
3. Selects the newly created, validated transformed image instead of silently
   accepting an unchanged input or stale current image
4. Copies reference calibration into both output stacks

Historical corrected source snapshots match the native run's hashes. Three new
regression-test source identities are recorded, but this packet's independent
review does not itself execute the Maven test suite. The unchanged native report
wording "unchanged production classes" means the harness invoked the built classes
without replacing them; it does not mean production was unchanged between commits.

## Corrected native results

`controls`, `display-probe`, `full-sift`, `full-mops`, `no-files`, `missing-marker`
and `missing-round` all passed. Every case reached phase `complete`, exit 0.
Each full-service route has **nine PASS and two NOT_RUN** checks.

Both routes pass actual service return, exact saved dimensions and seven filename
labels, every round/channel transform, saved calibration, common-marker QC,
landmark ZIP round-trip, source preservation, real plugin commands, and the narrow
final-dialog behavior. SIFT records two real SIFT extractions; the MOPS boundary
route records two real MOPS extractions; both execute four affine landmark warps.

The three failures in the old run are now passes:

- Four later-round marker channels receive their intended transformations
- Both aligned and common-QC TIFFs retain reopened input calibration and interval
- Both exported ROI pairs retain the correct known displacement and ordering

The actual SIFT service returned in 2.702532417 s (cold process 3.919284417 s).
The MOPS service returned in 13.262009292 s (cold process 14.448761166 s).
These are observed synthetic-run timings, not a performance benchmark.

## Independent read-only inspection of saved outputs

`ReviewCorrectedMultiplex.java` independently reopens the saved native outputs.
It does not call the service, register images again, or reuse the harness pattern
generator. For each interior output pixel, it derives the expected value from the
retained shifted source TIFF at `(x+dx, y+dy)`, using known synthetic shifts and the
same declared 24-pixel border exclusion. Round-1 and QC comparisons use full planes.
The audit log was independently rerun and reproduced byte-for-byte.

All eight later-channel before/after MSE pairs and all four ROI displacement errors
match the native reports exactly:

| Later marker | Before MSE | SIFT after MSE | MOPS after MSE |
| --- | ---: | ---: | ---: |
| Layer2_MarkerA | 3030.62287352071 | 0 | 0.1910364275147929 |
| Layer2_MarkerB | 2751.3859791050295 | 0 | 0.17954881656804733 |
| Layer3_MarkerA | 4031.473372781065 | 0 | 0.324426775147929 |
| Layer3_MarkerB | 4313.435465976331 | 0 | 0.35972170857988167 |

SIFT's four later-channel interiors are exact. MOPS reduces their MSE by
99.99166–99.99370%, exceeding the unchanged 85% requirement. All three round-1
output planes and all three common-QC planes retain exact original pixel arrays.

| Route/pair | Points | Expected dx,dy | Mean displacement error (px) |
| --- | ---: | --- | ---: |
| SIFT / 1 | 62 | 7, -5 | 0.0000005229826896421371 |
| SIFT / 2 | 80 | -6, 8 | 0.00000019073486328125 |
| MOPS / 1 | 1040 | 7, -5 | 0.03373452549289706 |
| MOPS / 2 | 1483 | -6, 8 | 0.0392154692758565 |

Both saved TIFFs in both routes exactly retain the reopened source's pixel width
0.5 µm, pixel height 0.7500001875000468 µm, pixel depth 1.0 and frame interval
1.25 s. The comparison uses the saved input's actual values, including TIFF
rational rounding. `ReviewSavedCalibration.java` prints each field independently.

An isolated `ReviewCorrectedBatchSelection` control uses two windowless 8×8 images
in batch mode and the corrected historical `IJUtils` source. The helper now selects
`review_ref` while `review_target` was current. The prior packet's equivalent old
helper reproduction left `review_target` current.

These additional inspections ran on Linux x86-64, headless Temurin 17.0.20.1, using
the exact native run's ImageJ 1.54p JAR. They inspect native Mac output bytes and a
small helper behavior; they are not another native full-service or model run.
Process exits, dependency identity and exact metric comparisons are in
`independent/provenance.json`.

## Scope limits retained

This is deterministic synthetic, 256×256, 8-bit, three-round/three-marker service
coverage. The aligned output contract is seven channels: reference Hu plus six
independent markers; later Hu planes remain unwarped in the three-plane QC stack.
It is not biological accuracy validation, complete GAT GUI-pane validation,
performance evidence for a physical M1, or a platform-universal guarantee.

MOPS is reached at the allowed `stepsPerScaleOctave=31` boundary, not through a
naturally occurring SIFT failure. Block Matching is absent from the pinned command
manifest and remains NOT_RUN. Computation cancellation also remains NOT_RUN.
Only the exact final open-results Cancel and verified padded Done/OK dialog are
exercised, with output hashes and batch-state restoration checked. Cancelling that
final prompt is not cancelling computation. The earlier cancelled run remains
inconclusive as documented in the unchanged failure packet.

## Preservation and verification

The original ZIP is retained byte-for-byte at
`original/gat-multiplex-native-ab046cb.zip`: **398,562 bytes**, SHA-256
`fac1354084a4e06ff86359c92dfb23ec4979e70b28806905d3b03947b0da441c`.
`original/artifact-manifest.json` records every one of its 77 member sizes/hashes.
TIFFs and ROI ZIPs remain compactly preserved inside it.

Thirty-four readable text copies retain all measurements and claims, with only
explicit runner-path/user substitutions. `portable-copy-manifest.json` maps their
original and portable hashes. `separate-run-metadata/terminal-ci-status.json` and
`separate-run-metadata/artifact-ci-status.json` contain separately obtained decoded
connector results, including GitHub's matching artifact digest, not raw HTTP bytes or an
original artifact member. No content is inserted into the original ZIP.

`SHA256SUMS` covers all packet files except itself. A separately frozen staging
manifest outside the repository covers every relative path, size and SHA-256,
including that checksum file. Future reruns belong in another directory.

Run the read-only verifier from any directory. Keep the adjacent `mac-5a00f6d`
packet present so it can also verify the paired original artifacts:

```sh
python3 /path/to/mac-ab046cb/verify_packet.py
```

To repeat only these independent inspections, use JDK 17+ and ImageJ 1.54p with
SHA-256 `2e1a09961dfb41cee66ddc821b2577a41a072566ce45a49bae69267099741e20`.
All temporary extraction and compiled classes stay outside this frozen packet:

```sh
cd /path/to/mac-ab046cb
python3 verify_packet.py
export IJ_JAR=/absolute/path/to/ij-1.54p.jar
WORK=$(mktemp -d)
mkdir "$WORK/classes"
unzip -q original/gat-multiplex-native-ab046cb.zip -d "$WORK/artifact"
javac -encoding UTF-8 -cp "$IJ_JAR" -d "$WORK/classes" \
  independent/ReviewCorrectedMultiplex.java \
  independent/ReviewSavedCalibration.java \
  independent/ReviewCorrectedBatchSelection.java \
  independent/source-snapshot/services/multiplex/util/IJUtils.java
java -Djava.awt.headless=true -cp "$WORK/classes:$IJ_JAR" ReviewCorrectedMultiplex \
  "$WORK/artifact/full-sift" "$WORK/artifact/full-mops"
java -Djava.awt.headless=true -cp "$WORK/classes:$IJ_JAR" ReviewSavedCalibration \
  "$WORK/artifact/full-sift" "$WORK/artifact/full-mops"
java -Djava.awt.headless=true -cp "$WORK/classes:$IJ_JAR" ReviewCorrectedBatchSelection
```

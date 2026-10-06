# Native Mac observation of the fixed moved-center outlier

[Run 37363502181, job 111943305508](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37363502181/job/111943305508) executed the fixed public Hu tile on an **Apple M1 (Virtual), macOS 14.8.9, native aarch64 Temurin 21.0.12.1** host. CI source was `c6e2011a9bc930c6b87e9cc7bfddd8af5bc292e4`. The raw report's `production_source_commit` field names the fixture's earlier baseline `366c833`; it is not the CI checkout. The production worker Java sources are unchanged between those revisions; the actual worker JAR hash and all checker source hashes are retained.

## Result: Mac raster matches the legacy Linux reference in this case

The 760×1024 tile `repo_Tilescan_GAT_ms_distal_colon_MP_hu_c1_t1_x4096_y0` produces **148 objects and 4,851 candidates**. At probability 0.5, NMS 0.3 and boundary exclusion 2, Mac labels, label IDs, winning centers and pixel measurements exactly match the fixed TF1.15 Linux reference. An independent ImageJ polygon re-rasterization reproduced the complete reference label image, SHA-256 `2ec2a85e86db52535c0f87c2213f4c89e3adc03de23d798e9d1d62245f735837`.

The affected object 104 stays at center **(396.5,166.5)** with area **441 pixels**, IoU/Dice **1.0** against legacy. Against the fixed modern Linux result, it differs at **48 pixels**: Linux-modern center (394.5,168.5), area 451, intersection 422, union 470, IoU **0.8978723404**, Dice **0.9461883408**. Equal total counts therefore do not establish equivalent geometry. Mac scores retain legacy ordering: 0.6602807641 at the old center versus 0.6602801085 at the alternative center.

Probability maximum absolute errors are **2.74181366×10⁻⁶** versus legacy and **2.98023224×10⁻⁶** versus modern Linux, with zero threshold flips and zero values outside the fixed `atol=rtol=1e-4` gate. Full distance maps were not retained or compared by this compact diagnostic.

**Strict subpixel outlines are not identical even where the raster is exact.** Four vertices on labels 113, 123, 125 and 136 differ from legacy by up to **0.010009765625 pixels**. Maximum matched-center polygon area/perimeter differences are 0.01115236 px² / 0.003344919 px. The affected object 104's polygon itself exactly matches legacy: area 444.2352749 px² and perimeter 88.8961417 px. `independent-review.json` records each changed vertex. The matched-center coordinate bound must not be applied to the unmatched/moved center when comparing against modern Linux.

Successful diagnostic completion is **not a scientific-equivalence pass**. This is one deliberately selected outlier, not all 371 corpus cases on Mac, not biological validation and not proof for every Apple Silicon generation. The single cold worker process took 7.13 seconds including startup/model loading; no GPU comparison was performed.

## Immutable evidence and independent check

`original-ci-diagnostics.zip` is the original 111,912-byte artifact 11367950413, SHA-256 `7ac6de4193b06a17250ec87beefb2c153ab5ca47df7a895ebb757d999b584cb8`. Its three members and this packet have separate hash inventories. `summary.json` removes repeated full object summaries but preserves both comparisons, score probes, runtime and provenance. Raw evidence is unchanged.

`PolygonRasterReview.java` independently reads the retained GATP polygons and fills them with the same pinned ImageJ 1.54p rasterizer, without calling the diagnostic checker. To reproduce after extracting the artifact, compile it against the ImageJ JAR identified in `../../../cross-platform/dependencies.json`, then run:

```sh
javac -cp /path/to/ij-1.54p.jar PolygonRasterReview.java
java -Djava.awt.headless=true -cp .:/path/to/ij-1.54p.jar \
  PolygonRasterReview actual.polygons.gz reconstructed-labels.u16be
```

The reported raster hash must equal the value above and the decompressed fixed reference `../../fixtures/legacy.labels.u16be.gz`. This verifies retained polygon-to-label consistency; it cannot reconstruct or prove equality of discarded raw distance channels.

# GAT runtime regression evidence

Production source commit: `366c8339e18563105ba41f82ea9d0ac6b6650077`.

Core: 180 archive files / 178 distinct inputs. Supplement: 49 static cases plus 142 calcium frames / 190 distinct inputs. Overall: 371 cases / 368 distinct pixel inputs. Refer to each summary for exact results and limitations. Counts refer to StarDist NMS, not the complete GAT workflow or unique biological cells.

The core and supplement directories contain human-readable case JSON/CSV, reconciled manifests, summaries and provenance. The controls directory contains repeatability and configuration sensitivity evidence. Large raw prediction tensors and source images are deliberately excluded.

## Outline payloads

All paired gzip polygon payloads are stored in deterministic numbered ZIP archives, each below 25 MiB. Extract every `outline-payloads-*.zip` into this results directory; this creates `core/outlines/`, `supplement/outlines/` and `controls/outlines/`. `outline-sha256.json` records each archive and each extracted payload's SHA-256 and size. The gzip payload is the documented big-endian GATP version-1 format.

Geometry delta maxima cover only matched winning centers. Consult unmatched-center counts and the complete per-object measurements for NMS candidate changes. Global IoU can hide a larger local change in one cell. These cross-runtime corpus tests ran on Linux CPU. If present, `native-mac-smoke.json` records separate, narrower native-Mac CI evidence and its exact job link; it does not establish broad Mac corpus parity.

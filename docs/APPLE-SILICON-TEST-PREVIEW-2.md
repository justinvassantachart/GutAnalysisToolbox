# Apple Silicon test preview 2

Experimental test release for native Apple Silicon Macs running **macOS 14 or later**. Use a separate Fiji installation. This is a tested snapshot, not a claim that every GAT workflow is validated.

## Downloads

[Verified prerelease and all assets](https://github.com/justinvassantachart/GutAnalysisToolbox/releases/tag/apple-silicon-preview-2).

- `GAT-2.0.1-apple-silicon.2-macos-arm64-preview.zip`: fork plugin and isolated ARM64 inference/alignment workers
- `GAT-2.0.0-unchanged-1870d9e-baseline.zip`: unchanged original plugin for a separate comparison installation
- Matching `.sha256` files and `FORK_BUILD_INFO.json` / `ORIGINAL_BUILD_INFO.json`
- `M1-CHATGPT-HANDOFF.md`: complete zero-prerequisite clean-Mac instructions (added with this release)
- `GAT-M1-test-kit-preview-2.1.zip`: corrected manual fixtures, references, manifests and paired Mac evidence. **Use kit 2.1; the earlier kit 2 has four-frame Template Matching helper fixtures that the dashboard rejects because it requires at least ten frames.** The corrected twelve-frame kit has been checked through the real worker

Follow the complete instructions before installing; the core ZIPs do not include Fiji, its update sites, models or DeepImageJ engines.

The two installation packages were built together on an **Apple M1 (Virtual), native macOS 15.7.9 / Java 21** runner. Fork source: `fe5fd7b0a5a9b6e79074ef24d79c27fd2c5c2372`; unchanged original source: `1870d9e16e16fd6daeac0bd05122e851029ddedc`.

## What was actually verified
- Same-host original/fork comparisons on macOS Sonoma and Sequoia: fork Neuron Analyse/StarDist and Template Matching pass; original calls fail. The original TensorFlow ARM library is unavailable and its optional diagnostic path waits in a native-load error dialog. Original Template Matching reports missing legacy OpenCV JNI
- Fork four-tile public Hu crop: exactly 39 labels and the same label pixels as both Linux references
- Fork SIFT helper, saved single-stack and two-channel batch checks pass; original GAT loses metadata or saves the wrong result
- **Original and fork calcium both pass** accepted-dialog F/F0 `[1,1,2]` and ROI/CSV export controls
- Both ganglia commands run. The fork deliberately removes a second normalization step to obey the model RDF. That changes output masks; biological accuracy and equivalence to old masks are not claimed
- 371 paired Linux neural-runtime cases preserve all object counts, but some boundaries and one cell's selected center differ. Detailed numerical and outline evidence is in the repository

## Remaining tests and limitations
- A real official-Fiji clean-install run already passes fork neuron/alignment and reproduces original failures, but both dashboards stop until DeepImageJ engines are initialized. The extended automatic engine-initialization/dashboard test is still pending; GitHub reported a hosted-runner assignment incident during this validation
- Physical-M1 OpenCL/GPU, full interactive workflows and representative biological acceptance remain to be tested. The virtual runner exposes no usable OpenCL device
- Automatic calcium ROI segmentation and batch StackReg were incomplete upstream and are not supplied by this release
- Optional JPEG-XR native repair is now available as the separate `gat-jpeg-xr-0.2.4-macos-arm64-test-overlay.zip`, with complete matching source and `OPTIONAL-JPEG-XR-README.md`. Its final native packaged-JAR decode passed 13 golden fixtures and 59 JNI signatures. Full Fiji importer, microscopy-container metadata and GUI checks remain pending; it is not bundled into the core ZIP
- CPU inference only. No GPU speedup claim. Start with small images; tiling does not remove the full prediction-memory limit
- Modern TensorFlow and OpenCV stay in child processes outside Fiji's plugin classpath. Do not copy worker library JARs into Fiji `jars` or `plugins`

The original packaging comparison retains its red overall result from the unchanged original TensorFlow error-dialog timeout. A [later same-host comparison completed green](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37369827141): it passively recorded that exact unanswered failure dialog and ended only the isolated original process. All repaired gates passed. Green means complete before/after observations, not original compatibility.

## Evidence
- [Saved qualified paired report](https://github.com/justinvassantachart/GutAnalysisToolbox/blob/ee2907e371b12b1951a507141f797afedb460aef/native-inference/validation/baseline/results/mac-sequoia-fe5fd7b/REPORT.md)
- [Sequoia paired original/fork run](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37366290715)
- [Sonoma paired original/fork run](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37363236215/attempts/2)
- [Real installed-Fiji comparison](https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37363502221)
- [371-case regression report](https://github.com/justinvassantachart/GutAnalysisToolbox/blob/fe5fd7b0a5a9b6e79074ef24d79c27fd2c5c2372/native-inference/validation/corpus/REGRESSION_REPORT.md)

Fork ZIP SHA-256: `9c5a542b82eb146b9c1d6c78ca20d1a0ffb8d10af7d35d6cd8ead8b927ac1f9f`

Original ZIP SHA-256: `d2224b968368abd5a198f190db51022d8fa41cd72d6cfb7c845a224f94420ad8`

The earlier preview-1 tag and files retain their original provenance. No upstream pull request has been opened.

Optional JPEG-XR ZIP SHA-256: `d3208ee74c26edbb44846e56de76004a9962257f63b2050cd8beaffae0f8a1b5` (645,514 bytes). Built/validated from fork `6996dd50f5ea06ac1f5ecb38c245139cb1508292`; core package/tag remain unchanged at `fe5fd7b`.

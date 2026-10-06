# GAT native inference worker (experimental)

This **separate JVM** loads existing Fiji StarDist SavedModel ZIPs using TensorFlow Java 1.2.0. It does not add TensorFlow 2 classes, protobuf classes, or native libraries to Fiji's classpath. StarDist's existing Java NMS remains in Fiji.

## Build and run

Requires Java 11 or newer and Maven. The packaged Apple Silicon worker requires **macOS 14 Sonoma or newer** and native ARM64 Java/Fiji. The TensorFlow Java 1.2.0 JNI bridge declares macOS 14.0 in its Mach-O load commands (the bundled TensorFlow core libraries declare 12.0); older macOS releases are not supported by this package.

```sh
# Apple Silicon distribution (default)
mvn clean package
# Linux x86-64 build for validation
mvn clean package -Dtensorflow.platform=linux-x86_64
```

The ZIP `target/gat-native-inference-macosx-arm64.zip` contains `gat-native-inference.jar` and its sibling `lib/` directory. Keep them together **outside Fiji/plugins and Fiji/jars**. The worker runs entirely locally and does not download models or dependencies at runtime.

```sh
java -jar gat-native-inference.jar --backend-info
java -jar gat-native-inference.jar --self-test
java -cp 'gat-native-inference.jar:lib/*' org.gatanalysis.inference.NativeInferenceMain model.zip input.bin output.bin 4
```

`--backend-info` reports JVM information without loading native libraries. `--self-test` loads TensorFlow and allocates a scalar tensor; it does not establish model inference or segmentation parity. Normal invocation requires four positional arguments: model ZIP, GATI input, new GATO output, requested tile count. Errors go to stderr and return a nonzero exit status. The output file is committed only when prediction has succeeded.

## Supported model and scientific compatibility

Supported exports have exactly one float32 input and output in the SavedModel `serve` / `serving_default` signature, NHWC layout, dynamic spatial dimensions, batch size one or dynamic, one input channel, and full-resolution combined output (probability channel first, followed by at least three radial distance channels). Other layouts, fixed-size models, raw downsampled grids, multiple outputs, multiclass outputs, and arbitrary TensorFlow models are outside the supported contract. Structural validation cannot prove that an arbitrary same-shaped model actually encodes StarDist probability/distances; use trusted Fiji StarDist exports. No model conversion or retraining occurs.

Preprocessing is ported from CSBDeep Fiji commit `00aeb1298d5650bcfe3c00f4d2451cad79d51038`, specifically `PercentileNormalizer`, `HistogramPercentile`, `DefaultTiling`, and `TiledView`. GAT's file-model parameters are fixed at 1.0/99.8 percentiles, block multiple 64, overlap 64, and batch size 1:

- Percentiles use nearest sorted sample with Java float arithmetic; values below the lower percentile are clamped to zero, even with `clip=false`; values above the upper percentile are not clipped
- Constant/near-constant images follow CSBDeep's factor fallback
- Tiling increments the longest rounded dimension, choosing X on ties; it stops when the requested count is met or tiles cannot be subdivided further
- MirrorDouble padding repeats boundary pixels; nested X-then-Y views are preserved
- The legacy integer division before tile-size rounding is intentionally preserved, including rare one-pixel crop/reflection behavior on odd sizes
- Overlap is removed rather than blended and the assembled output is fitted to the original image dimensions

Unit tests check these semantics and compare padding directly with ImgLib2 mirror views. TensorFlow 1.15 versus modern-runtime numeric parity must also be checked on actual author models, because changing CPU kernels can change values close to probability/NMS thresholds. Reusing Fiji NMS preserves its algorithm, but does not by itself guarantee identical final labels. Treat Apple Silicon support as experimental until the included validation results and actual hardware testing support the intended workload. CPU inference is the supported baseline; no Metal acceleration is promised.

## Current validation

See `validation/RESULTS.md` for the dated Linux legacy-runtime comparison and remaining hardware/coverage limits.

## Binary protocol, version 1

All integers and IEEE754 floats are **big-endian**, using Java DataInputStream/DataOutputStream conventions.

- Input: int `0x47415449` (GATI), int version=1, int width, int height, then width*height float32 raw single-channel pixels in row-major Y/X order
- Output: int `0x4741544f` (GATO), int version=1, int width, int height, int channels, then width*height*channels float32 values in row-major Y/X/channel-interleaved order

The worker rejects nonfinite values, inconsistent lengths, nonpositive/oversized shapes, unsafe or ambiguous model ZIPs, and an existing output file. Archives are extracted only to a temporary directory and limited to 20,000 entries and 1 GiB uncompressed. Pass `-Djava.io.tmpdir=<request-directory>` to ensure a supervising process can remove extracted models even after a native crash. A supervisor should enforce a timeout and clean its own request directory.

## Optional legacy numerical reference

`validation/legacy-tensorflow/` contains a separate TensorFlow 1.15 reference launcher. Its classpath must never include the modern worker's `lib/` directory. It shares the pure-Java preprocessing implementation so comparison isolates the neural-network runtime change; preprocessing is independently covered by the compatibility unit tests.

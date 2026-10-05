# TensorFlow 1.15 numerical reference (validation only)

This optional module runs the original inference runtime in a separate process. Build it from the repository root:

```sh
mvn -f native-inference/validation/legacy-tensorflow/pom.xml package
java -cp 'native-inference/validation/legacy-tensorflow/target/classes:native-inference/validation/legacy-tensorflow/target/lib/*' \
  org.gatanalysis.inference.LegacyTensorFlowMain model.zip input.bin legacy-output.bin 4
```

Run the modern worker against the same model, GATI input file and tile count to produce a separate output file. Compare GATO channels numerically and compare final labels using Fiji StarDist NMS with identical thresholds. See `../RESULTS.md` for the actual test matrix and limitations.

This module is for Linux x86-64 / other architectures supported by TensorFlow 1.15, **not native Apple Silicon**. Do not put the modern worker JAR or its `lib/` directory on this legacy process's classpath. The distributed modern JAR has a manifest Class-Path which Java/javac follows even if Maven dependency transitivity is disabled. Instead, this module explicitly includes only the pure-Java normalization, tiling, archive and protocol sources, excluding the modern entrypoint/predictor.

The reference shares preprocessing code to isolate the native-runtime change; it does not independently prove that preprocessing matches CSBDeep. Separate compatibility unit tests cover the ported CSBDeep behavior and actual ImgLib2 mirror views.

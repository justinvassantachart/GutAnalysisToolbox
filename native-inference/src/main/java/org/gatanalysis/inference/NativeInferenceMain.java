package org.gatanalysis.inference;

import java.nio.file.Files;
import java.nio.file.Path;

/** Local-only subprocess entry point. Diagnostics go to stderr; output is committed on success. */
public final class NativeInferenceMain {
    private NativeInferenceMain() {}

    public static void main(String[] args) {
        try {
            run(args);
        } catch (Throwable error) {
            System.err.println("GAT native inference failed: " + error.getClass().getSimpleName() + ": " + error.getMessage());
            error.printStackTrace(System.err);
            System.exit(1);
        }
    }

    private static void checkRuntime() {
        if (System.getProperty("os.name", "").toLowerCase(java.util.Locale.ROOT).contains("mac")) {
            String version = System.getProperty("os.version", "");
            try {
                if (Integer.parseInt(version.split("\\.")[0]) < 14)
                    throw new IllegalArgumentException("This TensorFlow Java 1.2.0 package requires macOS 14 Sonoma or newer; detected " + version);
            } catch (NumberFormatException e) {
                throw new IllegalArgumentException("Cannot verify macOS version; this package requires macOS 14 or newer", e);
            }
        }
    }

    static void run(String[] args) throws Exception {
        if (args.length == 1 && args[0].equals("--backend-info")) {
            System.out.println("GAT native inference worker; experimental; protocol version 1");
            System.out.println("Java " + System.getProperty("java.version") + "; "
                    + System.getProperty("os.name") + "/" + System.getProperty("os.arch"));
            System.out.println("TensorFlow Java 1.2.0 configured; native library not loaded by --backend-info");
            return;
        }
        if (args.length == 1 && args[0].equals("--self-test")) {
            checkRuntime();
            TensorFlowPredictor.selfTest();
            return;
        }
        if (args.length != 4)
            throw new IllegalArgumentException("Usage: NativeInferenceMain model.zip input.bin output.bin nTiles\n"
                    + "       NativeInferenceMain --backend-info | --self-test");
        checkRuntime();
        Path modelZip = Path.of(args[0]);
        Path inputFile = Path.of(args[1]);
        Path outputFile = Path.of(args[2]);
        if (Files.exists(outputFile)) throw new IllegalArgumentException("Output must be a new file");
        int tiles = Integer.parseInt(args[3]);
        ImageTensor input = TensorProtocol.readInput(inputFile);
        CsbdeepTiling tiling = new CsbdeepTiling(input.width, input.height, tiles);
        float[] normalized = CsbdeepNormalizer.normalize(input.values);
        System.err.println("GAT native inference: " + input.width + "x" + input.height
                + ", tiles " + tiling.tilesX + "x" + tiling.tilesY);
        try (ModelArchive archive = ModelArchive.extract(modelZip);
             TensorFlowPredictor predictor = new TensorFlowPredictor(archive.modelDirectory)) {
            ImageTensor output = tiling.infer(normalized, predictor);
            TensorProtocol.writeOutput(outputFile, output);
        }
    }
}

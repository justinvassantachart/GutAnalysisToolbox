package org.gatanalysis.inference;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;

/** Validation-only streaming jobs; same production preprocessing and predictor. */
final class BatchProtocol {
    private BatchProtocol() {}
    static void serve(TilePredictor predictor) throws Exception {
        System.out.println("READY");
        System.out.flush();
        try (BufferedReader input = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8))) {
            String line;
            while ((line = input.readLine()) != null) {
                if (line.equals("STOP")) break;
                String[] fields = line.split("\t", -1);
                if (fields.length != 4) throw new IllegalArgumentException("Expected case_id, input, output, tiles");
                long start = System.nanoTime();
                try {
                    runOne(fields, predictor);
                    System.out.println("DONE\t" + fields[0] + "\t" + ((System.nanoTime() - start) / 1_000_000));
                } catch (Exception failure) {
                    failure.printStackTrace(System.err);
                    System.out.println("ERROR\t" + fields[0] + "\t" + failure.toString().replace('\t', ' ').replace('\n', ' '));
                }
                System.out.flush();
                // Validation batches explicitly release Java arrays before another
                // process compares the large 97-channel predictions.
                System.gc();
            }
        }
    }
    private static void runOne(String[] fields, TilePredictor predictor) throws Exception {
        ImageTensor image = TensorProtocol.readInput(Path.of(fields[1]));
        CsbdeepTiling tiling = new CsbdeepTiling(image.width, image.height, Integer.parseInt(fields[3]));
        ImageTensor prediction = tiling.infer(CsbdeepNormalizer.normalize(image.values), predictor);
        TensorProtocol.writeOutput(Path.of(fields[2]), prediction);
    }
}

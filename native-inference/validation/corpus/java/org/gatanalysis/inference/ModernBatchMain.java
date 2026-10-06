package org.gatanalysis.inference;

import java.nio.file.Path;

/** Reuses exactly the production TensorFlowPredictor; keeps one model open for the batch. */
public final class ModernBatchMain {
    public static void main(String[] args) throws Exception {
        if (args.length != 1) throw new IllegalArgumentException("Expected model ZIP");
        try (ModelArchive archive = ModelArchive.extract(Path.of(args[0]));
             TensorFlowPredictor predictor = new TensorFlowPredictor(archive.modelDirectory)) {
            BatchProtocol.serve(predictor);
        }
    }
}

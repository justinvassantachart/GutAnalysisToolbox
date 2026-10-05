package org.gatanalysis.inference;

import java.nio.FloatBuffer;
import java.nio.file.Path;
import java.util.List;
import org.tensorflow.SavedModelBundle;
import org.tensorflow.Tensor;
import org.tensorflow.framework.ConfigProto;
import org.tensorflow.framework.GraphOptions;
import org.tensorflow.framework.MetaGraphDef;
import org.tensorflow.framework.OptimizerOptions;
import org.tensorflow.framework.RewriterConfig;
import org.tensorflow.framework.SignatureDef;

/** Diagnostic-only TF1.15 configuration, always in its own legacy-only JVM. */
public final class LegacySensitivityMain {
    public static void main(String[] args) throws Exception {
        if (args.length != 5) throw new IllegalArgumentException("Expected model.zip input.bin output.bin nTiles baseline|single-thread|single-thread-no-optimizations");
        try (ModelArchive archive = ModelArchive.extract(Path.of(args[0]));
             SavedModelBundle model = load(archive.modelDirectory, args[4])) {
            SignatureDef signature = MetaGraphDef.parseFrom(model.metaGraphDef()).getSignatureDefOrThrow("serving_default");
            String inputName = signature.getInputsMap().values().iterator().next().getName();
            String outputName = signature.getOutputsMap().values().iterator().next().getName();
            TilePredictor predictor = new TilePredictor() {
                public ImageTensor predict(ImageTensor image) {
                    try (Tensor<Float> input = Tensor.create(new long[] {1, image.height, image.width, 1}, FloatBuffer.wrap(image.values))) {
                        List<Tensor<?>> tensors = model.session().runner().feed(inputName, input).fetch(outputName).run();
                        try {
                            Tensor<?> tensor = tensors.get(0);
                            long[] shape = tensor.shape();
                            if (shape.length != 4 || shape[0] != 1 || shape[1] != image.height || shape[2] != image.width)
                                throw new IllegalArgumentException("Unexpected legacy output shape");
                            int channels = Math.toIntExact(shape[3]);
                            float[] values = new float[ImageTensor.elements(image.width, image.height, channels)];
                            tensor.writeTo(FloatBuffer.wrap(values));
                            return new ImageTensor(image.width, image.height, channels, values);
                        } finally { for (Tensor<?> tensor : tensors) tensor.close(); }
                    }
                }
                public void close() {}
            };
            ImageTensor input = TensorProtocol.readInput(Path.of(args[1]));
            ImageTensor output = new CsbdeepTiling(input.width, input.height, Integer.parseInt(args[3]))
                    .infer(CsbdeepNormalizer.normalize(input.values), predictor);
            TensorProtocol.writeOutput(Path.of(args[2]), output);
        }
    }
    private static SavedModelBundle load(Path path, String mode) {
        if (mode.equals("baseline")) return SavedModelBundle.load(path.toString(), "serve");
        if (!mode.equals("single-thread") && !mode.equals("single-thread-no-optimizations"))
            throw new IllegalArgumentException("Unknown control mode " + mode);
        ConfigProto.Builder config = ConfigProto.newBuilder().setIntraOpParallelismThreads(1).setInterOpParallelismThreads(1);
        if (mode.equals("single-thread-no-optimizations")) {
            config.setGraphOptions(GraphOptions.newBuilder()
                    .setRewriteOptions(RewriterConfig.newBuilder().setDisableMetaOptimizer(true))
                    .setOptimizerOptions(OptimizerOptions.newBuilder().setOptLevel(OptimizerOptions.Level.L0)
                            .setDoConstantFolding(false).setDoCommonSubexpressionElimination(false).setDoFunctionInlining(false)));
        }
        System.err.println("Legacy diagnostic configuration: " + mode);
        return SavedModelBundle.loader(path.toString()).withTags("serve").withConfigProto(config.build().toByteArray()).load();
    }
}

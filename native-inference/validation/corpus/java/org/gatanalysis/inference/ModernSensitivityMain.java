package org.gatanalysis.inference;

import java.nio.file.Path;
import org.tensorflow.Result;
import org.tensorflow.SavedModelBundle;
import org.tensorflow.ndarray.Shape;
import org.tensorflow.ndarray.buffer.DataBuffers;
import org.tensorflow.proto.ConfigProto;
import org.tensorflow.proto.GraphOptions;
import org.tensorflow.proto.OptimizerOptions;
import org.tensorflow.proto.RewriterConfig;
import org.tensorflow.proto.SignatureDef;
import org.tensorflow.types.TFloat32;

/** Diagnostic-only controls. Production inference, thresholds and NMS remain unchanged. */
public final class ModernSensitivityMain {
    public static void main(String[] args) throws Exception {
        if (args.length != 5) throw new IllegalArgumentException("Expected model.zip input.bin output.bin nTiles baseline|single-thread|single-thread-no-optimizations");
        try (ModelArchive archive = ModelArchive.extract(Path.of(args[0]));
             TilePredictor predictor = args[4].equals("baseline") ? new TensorFlowPredictor(archive.modelDirectory)
                     : configured(archive.modelDirectory, args[4])) {
            ImageTensor input = TensorProtocol.readInput(Path.of(args[1]));
            ImageTensor output = new CsbdeepTiling(input.width, input.height, Integer.parseInt(args[3]))
                    .infer(CsbdeepNormalizer.normalize(input.values), predictor);
            TensorProtocol.writeOutput(Path.of(args[2]), output);
        }
    }

    private static TilePredictor configured(Path modelPath, String mode) {
        if (!mode.equals("single-thread") && !mode.equals("single-thread-no-optimizations"))
            throw new IllegalArgumentException("Unknown control mode " + mode);
        ConfigProto.Builder config = ConfigProto.newBuilder().setIntraOpParallelismThreads(1).setInterOpParallelismThreads(1);
        if (mode.equals("single-thread-no-optimizations")) {
            config.setGraphOptions(GraphOptions.newBuilder()
                    .setRewriteOptions(RewriterConfig.newBuilder().setDisableMetaOptimizer(true))
                    .setOptimizerOptions(OptimizerOptions.newBuilder().setOptLevel(OptimizerOptions.Level.L0)
                            .setDoConstantFolding(false).setDoCommonSubexpressionElimination(false).setDoFunctionInlining(false)));
        }
        final SavedModelBundle model = SavedModelBundle.loader(modelPath.toString()).withTags("serve").withConfigProto(config.build()).load();
        try {
            SignatureDef signature = model.metaGraphDef().getSignatureDefOrThrow("serving_default");
            if (signature.getInputsCount() != 1 || signature.getOutputsCount() != 1) throw new IllegalArgumentException("Expected one model input/output");
            TensorFlowPredictor.validateSignatureTensor(signature.getInputsMap().values().iterator().next(), true);
            TensorFlowPredictor.validateSignatureTensor(signature.getOutputsMap().values().iterator().next(), false);
            String inputName = signature.getInputsMap().values().iterator().next().getName();
            String outputName = signature.getOutputsMap().values().iterator().next().getName();
            System.err.println("Modern diagnostic configuration: " + mode);
            return new TilePredictor() {
                public ImageTensor predict(ImageTensor image) {
                    try (TFloat32 input = TFloat32.tensorOf(Shape.of(1, image.height, image.width, 1), DataBuffers.of(image.values));
                         Result results = model.session().runner().feed(inputName, input).fetch(outputName).run()) {
                        TFloat32 tensor = (TFloat32) results.get(0);
                        Shape shape = tensor.shape();
                        if (shape.numDimensions() != 4 || shape.size(0) != 1 || shape.size(1) != image.height || shape.size(2) != image.width)
                            throw new IllegalArgumentException("Unexpected output shape " + shape);
                        int channels = Math.toIntExact(shape.size(3));
                        float[] data = new float[ImageTensor.elements(image.width, image.height, channels)];
                        tensor.copyTo(DataBuffers.of(data));
                        return new ImageTensor(image.width, image.height, channels, data);
                    }
                }
                public void close() { model.close(); }
            };
        } catch (RuntimeException | Error e) { model.close(); throw e; }
    }
}

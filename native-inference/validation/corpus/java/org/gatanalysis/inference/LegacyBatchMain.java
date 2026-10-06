package org.gatanalysis.inference;

import java.nio.FloatBuffer;
import java.nio.file.Path;
import java.util.List;
import org.tensorflow.SavedModelBundle;
import org.tensorflow.Tensor;
import org.tensorflow.TensorFlow;
import org.tensorflow.framework.MetaGraphDef;
import org.tensorflow.framework.SignatureDef;

/** Validation-only TF1.15 process, with no modern TensorFlow classes on its classpath. */
public final class LegacyBatchMain {
    public static void main(String[] args) throws Exception {
        if (args.length != 1) throw new IllegalArgumentException("Expected model ZIP");
        try (ModelArchive archive = ModelArchive.extract(Path.of(args[0]));
             SavedModelBundle model = SavedModelBundle.load(archive.modelDirectory.toString(), "serve")) {
            SignatureDef signature = MetaGraphDef.parseFrom(model.metaGraphDef()).getSignatureDefOrThrow("serving_default");
            String inputName = signature.getInputsMap().values().iterator().next().getName();
            String outputName = signature.getOutputsMap().values().iterator().next().getName();
            System.err.println("Legacy batch runtime: TensorFlow " + TensorFlow.version());
            BatchProtocol.serve(new TilePredictor() {
                @Override public ImageTensor predict(ImageTensor image) {
                    try (Tensor<Float> tensor = Tensor.create(new long[] {1, image.height, image.width, 1}, FloatBuffer.wrap(image.values))) {
                        List<Tensor<?>> outputs = model.session().runner().feed(inputName, tensor).fetch(outputName).run();
                        try {
                            Tensor<?> output = outputs.get(0);
                            long[] shape = output.shape();
                            if (shape.length != 4 || shape[0] != 1 || shape[1] != image.height || shape[2] != image.width)
                                throw new IllegalArgumentException("Unexpected legacy output shape");
                            int channels = Math.toIntExact(shape[3]);
                            float[] values = new float[ImageTensor.elements(image.width, image.height, channels)];
                            output.writeTo(FloatBuffer.wrap(values));
                            return new ImageTensor(image.width, image.height, channels, values);
                        } finally { for (Tensor<?> output : outputs) output.close(); }
                    }
                }
                @Override public void close() {}
            });
        }
    }
}

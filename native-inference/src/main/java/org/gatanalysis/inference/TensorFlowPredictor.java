package org.gatanalysis.inference;

import java.nio.file.Path;
import org.tensorflow.Result;
import org.tensorflow.SavedModelBundle;
import org.tensorflow.TensorFlow;
import org.tensorflow.ndarray.Shape;
import org.tensorflow.ndarray.buffer.DataBuffers;
import org.tensorflow.proto.DataType;
import org.tensorflow.proto.SignatureDef;
import org.tensorflow.proto.TensorInfo;
import org.tensorflow.types.TFloat32;

/** The only class which touches TensorFlow; it runs in its own JVM, never Fiji's classloader. */
final class TensorFlowPredictor implements TilePredictor {
    private final SavedModelBundle model;
    private final String inputName;
    private final String outputName;

    TensorFlowPredictor(Path directory) {
        model = SavedModelBundle.load(directory.toString(), "serve");
        try {
            SignatureDef signature = model.metaGraphDef().getSignatureDefOrThrow("serving_default");
            if (signature.getInputsCount() != 1 || signature.getOutputsCount() != 1)
                throw new IllegalArgumentException("Supported StarDist models must have exactly one input and one combined output");
            TensorInfo input = signature.getInputsMap().values().iterator().next();
            TensorInfo output = signature.getOutputsMap().values().iterator().next();
            validateSignatureTensor(input, true);
            validateSignatureTensor(output, false);
            inputName = input.getName();
            outputName = output.getName();
            System.err.println("GAT native backend: TensorFlow " + TensorFlow.version()
                    + ", input " + inputName + ", output " + outputName);
        } catch (RuntimeException | Error e) {
            model.close();
            throw e;
        }
    }

    static void validateSignatureTensor(TensorInfo tensor, boolean input) {
        if (tensor.getDtype() != DataType.DT_FLOAT || tensor.getName().isEmpty()
                || tensor.getTensorShape().getUnknownRank() || tensor.getTensorShape().getDimCount() != 4)
            throw new IllegalArgumentException("Expected dense float32 NHWC model signature");
        long batch = tensor.getTensorShape().getDim(0).getSize();
        long channels = tensor.getTensorShape().getDim(3).getSize();
        if (batch != -1 && batch != 1)
            throw new IllegalArgumentException("Only batch size 1 is supported");
        if (input && channels != 1)
            throw new IllegalArgumentException("Only single-channel StarDist input models are supported");
        if (!input && channels != -1 && channels < 4)
            throw new IllegalArgumentException("Expected probability followed by at least three distance channels");
        // CSBDeep tiles only dynamic spatial dimensions. Do not guess for fixed-size networks.
        if (tensor.getTensorShape().getDim(1).getSize() != -1
                || tensor.getTensorShape().getDim(2).getSize() != -1)
            throw new IllegalArgumentException("Only dynamic-height/width NHWC StarDist signatures are supported");
    }

    @Override public ImageTensor predict(ImageTensor image) {
        try (TFloat32 input = TFloat32.tensorOf(Shape.of(1, image.height, image.width, 1),
                DataBuffers.of(image.values));
             Result result = model.session().runner().feed(inputName, input).fetch(outputName).run()) {
            if (result.size() != 1 || !(result.get(0) instanceof TFloat32))
                throw new IllegalArgumentException("Model did not return one float32 tensor");
            TFloat32 output = (TFloat32) result.get(0);
            Shape shape = output.shape();
            if (shape.numDimensions() != 4 || shape.size(0) != 1
                    || shape.size(1) != image.height || shape.size(2) != image.width
                    || shape.size(3) < 4 || shape.size(3) > Integer.MAX_VALUE)
                throw new IllegalArgumentException("Unsupported output shape " + shape
                        + "; export a full-resolution Fiji StarDist SavedModel with combined probability/distances");
            int channels = Math.toIntExact(shape.size(3));
            float[] values = new float[ImageTensor.elements(image.width, image.height, channels)];
            output.copyTo(DataBuffers.of(values));
            for (float value : values)
                if (!Float.isFinite(value)) throw new IllegalArgumentException("Non-finite model prediction");
            return new ImageTensor(image.width, image.height, channels, values);
        }
    }

    @Override public void close() { model.close(); }

    static void selfTest() {
        try (TFloat32 value = TFloat32.scalarOf(42.0f)) {
            if (value.getFloat() != 42.0f) throw new IllegalStateException("Tensor allocation self-test failed");
        }
        System.out.println("Native TensorFlow " + TensorFlow.version() + " loaded successfully on "
                + System.getProperty("os.name") + "/" + System.getProperty("os.arch"));
        System.out.println("JNI loading verified; model inference and segmentation parity are not tested by this check.");
    }
}

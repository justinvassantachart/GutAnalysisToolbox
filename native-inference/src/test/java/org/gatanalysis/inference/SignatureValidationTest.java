package org.gatanalysis.inference;

import static org.junit.jupiter.api.Assertions.*;
import org.junit.jupiter.api.Test;
import org.tensorflow.proto.DataType;
import org.tensorflow.proto.TensorInfo;
import org.tensorflow.proto.TensorShapeProto;

class SignatureValidationTest {
    @Test void acceptsFijiFloatNhwcSignaturesWithoutLoadingNative() {
        assertDoesNotThrow(() -> TensorFlowPredictor.validateSignatureTensor(tensor(-1, -1, -1, 1), true));
        assertDoesNotThrow(() -> TensorFlowPredictor.validateSignatureTensor(tensor(-1, -1, -1, 97), false));
    }
    @Test void rejectsFixedSpatialDimensionsAndExtraInputChannels() {
        assertThrows(IllegalArgumentException.class, () -> TensorFlowPredictor.validateSignatureTensor(tensor(-1, 64, 64, 1), true));
        assertThrows(IllegalArgumentException.class, () -> TensorFlowPredictor.validateSignatureTensor(tensor(-1, -1, -1, 3), true));
    }
    @Test void rejectsWrongDtypeRankAndSparseOrUnnamedTensors() {
        assertThrows(IllegalArgumentException.class, () -> TensorFlowPredictor.validateSignatureTensor(tensor(-1, -1, -1, 1).toBuilder().setDtype(DataType.DT_DOUBLE).build(), true));
        assertThrows(IllegalArgumentException.class, () -> TensorFlowPredictor.validateSignatureTensor(tensor(-1, -1, 1), true));
        assertThrows(IllegalArgumentException.class, () -> TensorFlowPredictor.validateSignatureTensor(tensor(-1, -1, -1, 1).toBuilder().clearName().build(), true));
    }
    private TensorInfo tensor(long... dims) {
        TensorShapeProto.Builder shape = TensorShapeProto.newBuilder();
        for (long dim : dims) shape.addDim(TensorShapeProto.Dim.newBuilder().setSize(dim));
        return TensorInfo.newBuilder().setName("input:0").setDtype(DataType.DT_FLOAT).setTensorShape(shape).build();
    }
}

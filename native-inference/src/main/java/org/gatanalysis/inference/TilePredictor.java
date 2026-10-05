package org.gatanalysis.inference;

interface TilePredictor extends AutoCloseable {
    ImageTensor predict(ImageTensor input) throws Exception;
    @Override void close();
}

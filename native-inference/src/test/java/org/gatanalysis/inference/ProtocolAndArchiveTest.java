package org.gatanalysis.inference;

import static org.junit.jupiter.api.Assertions.*;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class ProtocolAndArchiveTest {
    @TempDir Path temp;

    @Test void readsBigEndianInputAndRejectsExtraBytes() throws Exception {
        Path input = input(2, 1, 3f, 7f);
        assertArrayEquals(new float[] {3, 7}, TensorProtocol.readInput(input).values);
        Files.write(input, new byte[] {0}, java.nio.file.StandardOpenOption.APPEND);
        assertThrows(IOException.class, () -> TensorProtocol.readInput(input));
    }

    @Test void rejectsInvalidShapeTruncationAndNonfinite() throws Exception {
        assertThrows(IOException.class, () -> TensorProtocol.readInput(input(-1, 2)));
        assertThrows(IOException.class, () -> TensorProtocol.readInput(input(Integer.MAX_VALUE, Integer.MAX_VALUE)));
        assertThrows(IOException.class, () -> TensorProtocol.readInput(input(2, 1, 1f)));
        assertThrows(IOException.class, () -> TensorProtocol.readInput(input(1, 1, Float.NaN)));
    }

    @Test void outputIsInterleavedAndNeverOverwritesInput() throws Exception {
        Path output = temp.resolve("output.bin");
        TensorProtocol.writeOutput(output, new ImageTensor(2, 1, 4, new float[] {1,2,3,4,5,6,7,8}));
        try (DataInputStream in = new DataInputStream(Files.newInputStream(output))) {
            assertEquals(TensorProtocol.OUTPUT_MAGIC, in.readInt());
            assertEquals(1, in.readInt());
            assertEquals(2, in.readInt()); assertEquals(1, in.readInt()); assertEquals(4, in.readInt());
            for (int i = 1; i <= 8; i++) assertEquals((float) i, in.readFloat());
            assertEquals(-1, in.read());
        }
        assertThrows(IOException.class, () -> TensorProtocol.writeOutput(output, new ImageTensor(1,1,4,new float[4])));
    }

    @Test void failedOutputLeavesNoPartialResult() {
        Path output = temp.resolve("invalid.bin");
        assertThrows(IOException.class, () -> TensorProtocol.writeOutput(output,
                new ImageTensor(1,1,4,new float[] {1,2,3,Float.NaN})));
        assertFalse(Files.exists(output));
    }

    @Test void modelExtractionAllowsOneNestedModelAndCleansUp() throws Exception {
        Path archive = zip("model/saved_model.pb", "model/variables/variables.index");
        Path root;
        try (ModelArchive extracted = ModelArchive.extract(archive)) {
            root = extracted.root;
            assertEquals(root.resolve("model"), extracted.modelDirectory);
            assertTrue(Files.exists(root.resolve("model/variables/variables.index")));
        }
        assertFalse(Files.exists(root));
    }

    @Test void modelExtractionRejectsTraversalAndAmbiguousModels() throws Exception {
        for (String name : new String[] {"../escape.pb", "/absolute.pb", "..\\escape.pb", "C:/escape.pb"}) {
            Path archive = zip(name);
            assertThrows(IOException.class, () -> ModelArchive.extract(archive));
        }
        assertThrows(IOException.class, () -> ModelArchive.extract(zip("a/saved_model.pb", "b/saved_model.pb")));
        assertThrows(IOException.class, () -> ModelArchive.extract(zip("config.json")));
    }

    @Test void informationalModeDoesNotNeedTensorFlowNative() throws Exception {
        NativeInferenceMain.run(new String[] {"--backend-info"});
    }

    private Path input(int width, int height, float... values) throws IOException {
        Path input = Files.createTempFile(temp, "input", ".bin");
        try (DataOutputStream out = new DataOutputStream(Files.newOutputStream(input))) {
            out.writeInt(TensorProtocol.INPUT_MAGIC); out.writeInt(1);
            out.writeInt(width); out.writeInt(height);
            for (float value : values) out.writeFloat(value);
        }
        return input;
    }

    private Path zip(String... names) throws IOException {
        Path archive = Files.createTempFile(temp, "model", ".zip");
        try (ZipOutputStream out = new ZipOutputStream(Files.newOutputStream(archive))) {
            for (String name : names) {
                out.putNextEntry(new ZipEntry(name)); out.write(new byte[] {1,2,3}); out.closeEntry();
            }
        }
        return archive;
    }
}

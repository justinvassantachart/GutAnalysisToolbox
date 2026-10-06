package Features.Inference;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import java.io.*;
import java.nio.file.*;
import java.util.List;
import static org.junit.jupiter.api.Assertions.*;

class NativeInferenceClientTest {
    @TempDir Path temporary;

    @Test void noisyWorkerIsDrainedWithoutUnboundedStorage() throws Exception {
        byte[] noisy = new byte[200000];
        java.util.Arrays.fill(noisy, (byte) 'x');
        byte[] end = "last diagnostic".getBytes("UTF-8");
        System.arraycopy(end, 0, noisy, noisy.length - end.length, end.length);
        try (NativeInferenceClient.BoundedDiagnostics output = new NativeInferenceClient.BoundedDiagnostics(new ByteArrayInputStream(noisy))) {
            output.await();
            assertEquals(8192, output.tail().length());
            assertTrue(output.tail().endsWith("last diagnostic"));
        }
    }

    @Test void inputProtocolIsVersionedBigEndianRowMajor() throws Exception {
        Path file = temporary.resolve("input.bin");
        NativeInferenceClient.writeInput(file, 2, 1, new float[]{2.5f, -1f});
        try (DataInputStream in = new DataInputStream(Files.newInputStream(file))) {
            assertEquals(0x47415449, in.readInt()); assertEquals(1, in.readInt());
            assertEquals(2, in.readInt()); assertEquals(1, in.readInt());
            assertEquals(2.5f, in.readFloat()); assertEquals(-1f, in.readFloat()); assertEquals(-1, in.read());
        }
    }
    @Test void invalidPixelsAndDimensionsFailBeforeInference() {
        Path file = temporary.resolve("invalid.bin");
        assertThrows(IllegalArgumentException.class, () -> NativeInferenceClient.writeInput(file, 2, 2, new float[3]));
        assertThrows(IllegalArgumentException.class, () -> NativeInferenceClient.writeInput(file, 1, 1, new float[]{Float.NaN}));
        assertThrows(IllegalArgumentException.class, () -> NativeInferenceClient.writeInput(file, 1, 1, new float[]{Float.POSITIVE_INFINITY}));
    }
    @Test void interleavedOutputBecomesSeparateProbabilityAndRayPlanes() throws Exception {
        Path file = prediction(2, 1, 4, new float[]{.1f, 1, 2, 3, .9f, 4, 5, 6});
        NativeInferenceClient.Prediction p = NativeInferenceClient.readOutput(file, 2, 1);
        assertArrayEquals(new float[]{.1f, .9f}, p.planes[0]);
        assertArrayEquals(new float[]{1, 4}, p.planes[1]);
        assertArrayEquals(new float[]{3, 6}, p.planes[3]);
    }
    @Test void outputCannotSilentlyChangeShape() throws Exception {
        Path file = prediction(2, 1, 4, new float[8]);
        assertThrows(IOException.class, () -> NativeInferenceClient.readOutput(file, 1, 2));
    }
    @Test void truncatedTrailingAndNonfiniteOutputFailClosed() throws Exception {
        Path truncated = prediction(2, 1, 4, new float[7]);
        assertThrows(IOException.class, () -> NativeInferenceClient.readOutput(truncated, 2, 1));
        Path trailing = prediction(2, 1, 4, new float[9]);
        assertThrows(IOException.class, () -> NativeInferenceClient.readOutput(trailing, 2, 1));
        Path nan = prediction(1, 1, 4, new float[]{Float.NaN, 1, 2, 3});
        assertThrows(IOException.class, () -> NativeInferenceClient.readOutput(nan, 1, 1));
    }
    @Test void unknownProtocolDoesNotProceedToNms() throws Exception {
        Path file = prediction(1, 1, 4, new float[4]);
        try (RandomAccessFile out = new RandomAccessFile(file.toFile(), "rw")) { out.seek(4); out.writeInt(99); }
        assertThrows(IOException.class, () -> NativeInferenceClient.readOutput(file, 1, 1));
    }
    @Test void commandUsesArgumentVectorNotShellAndIsolatedClasspath() {
        Path model = temporary.resolve("spaces ; ' $HOME model.zip");
        List<String> command = NativeInferenceClient.command(temporary, model, temporary.resolve("input"), temporary.resolve("output"), 4);
        assertEquals("-Djava.io.tmpdir=" + temporary.toAbsolutePath(), command.get(1));
        assertEquals("-cp", command.get(2));
        assertTrue(command.get(3).contains("gat-native-inference.jar"));
        assertTrue(command.get(3).contains("lib"));
        assertEquals(model.toAbsolutePath().toString(), command.get(5));
        assertEquals("4", command.get(8));
        assertFalse(command.contains("sh"));
    }
    private Path prediction(int width, int height, int channels, float[] values) throws Exception {
        Path file = Files.createTempFile(temporary, "output", ".bin");
        try (DataOutputStream out = new DataOutputStream(Files.newOutputStream(file))) {
            out.writeInt(0x4741544f); out.writeInt(1); out.writeInt(width); out.writeInt(height); out.writeInt(channels);
            for (float value : values) out.writeFloat(value);
        }
        return file;
    }
}

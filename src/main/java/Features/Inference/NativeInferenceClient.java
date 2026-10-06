package Features.Inference;

import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.stream.Stream;

/** Versioned local-file protocol; the worker has a completely separate JVM/classpath. */
public final class NativeInferenceClient {
    static final int INPUT_MAGIC = 0x47415449;
    static final int OUTPUT_MAGIC = 0x4741544f;
    static final int VERSION = 1;
    static final long MAX_PREDICTION_FLOATS = 268_435_456L;
    public static final String WORKER_DIRECTORY_PROPERTY = "gat.inference.directory";
    private NativeInferenceClient() { }

    public static Path workerDirectory(String fijiDirectory) {
        String configured = System.getProperty(WORKER_DIRECTORY_PROPERTY);
        if (configured != null && !configured.trim().isEmpty()) return Paths.get(configured).toAbsolutePath();
        if (fijiDirectory == null) throw new IllegalStateException("Cannot locate Fiji's installation directory.");
        return Paths.get(fijiDirectory, "gat-native-inference").toAbsolutePath();
    }

    public static void checkInstallation(String fijiDirectory) {
        InferenceBackend.requireWorkerJava();
        Path directory = workerDirectory(fijiDirectory);
        if (!Files.isRegularFile(directory.resolve("gat-native-inference.jar"))
                || !Files.isDirectory(directory.resolve("lib"))) {
            throw new IllegalStateException("GAT's isolated native-inference worker is missing from " + directory
                    + ". Extract the matching GAT native-inference test package into Fiji's root directory. "
                    + "Keep its lib folder outside Fiji/jars and Fiji/plugins. Nothing is downloaded automatically.");
        }
    }

    /** Output planes: probability first, followed by radial distances. */
    public static final class Prediction {
        public final int width, height;
        public final float[][] planes;
        Prediction(int width, int height, float[][] planes) {
            this.width = width; this.height = height; this.planes = planes;
        }
    }

    public static Prediction predict(String fijiDirectory, File modelZip, int width, int height,
                                     float[] pixels, int tiles) throws IOException, InterruptedException {
        checkInstallation(fijiDirectory);
        if (modelZip == null || !modelZip.isFile()) throw new IOException("StarDist model ZIP is missing: " + modelZip);
        if (tiles < 1) throw new IllegalArgumentException("Tile count must be positive.");
        Path temporary = Files.createTempDirectory("gat-inference-");
        Process process = null;
        BoundedDiagnostics diagnostics = null;
        try {
            Path input = temporary.resolve("input.bin");
            Path output = temporary.resolve("output.bin");
            writeInput(input, width, height, pixels);
            List<String> command = command(workerDirectory(fijiDirectory), modelZip.toPath(), input, output, tiles);
            ProcessBuilder builder = new ProcessBuilder(command).redirectErrorStream(true);
            // Neither TF1 nor unrelated caller classpaths are inherited by the worker.
            builder.environment().remove("CLASSPATH");
            builder.environment().put("CUDA_VISIBLE_DEVICES", "-1");
            long timeout = Long.getLong("gat.inference.timeoutSeconds", 900L);
            if (timeout < 1 || timeout > 86400) throw new IllegalArgumentException("Worker timeout must be 1–86400 seconds.");
            process = builder.start();
            diagnostics = new BoundedDiagnostics(process.getInputStream());
            if (!process.waitFor(timeout, TimeUnit.SECONDS)) {
                process.destroyForcibly();
                process.waitFor(5, TimeUnit.SECONDS);
                diagnostics.await();
                throw new IOException("GAT inference timed out after " + timeout + " seconds. "
                        + "Try a smaller crop or review the worker configuration. " + diagnostics.tail());
            }
            diagnostics.await();
            if (process.exitValue() != 0) throw new IOException("GAT native inference failed (exit "
                    + process.exitValue() + "). Fiji's legacy TensorFlow was not loaded. " + diagnostics.tail());
            return readOutput(output, width, height);
        } finally {
            if (process != null && process.isAlive()) {
                process.destroyForcibly();
                try { process.waitFor(5, TimeUnit.SECONDS); }
                catch (InterruptedException e) { Thread.currentThread().interrupt(); }
            }
            if (diagnostics != null) diagnostics.close();
            deleteTemporary(temporary);
        }
    }

    static List<String> command(Path directory, Path model, Path input, Path output, int tiles) {
        String javaName = System.getProperty("os.name", "").toLowerCase(Locale.ROOT).contains("win") ? "java.exe" : "java";
        String java = Paths.get(System.getProperty("java.home"), "bin", javaName).toString();
        String classpath = directory.resolve("gat-native-inference.jar") + File.pathSeparator + directory.resolve("lib").resolve("*");
        return Arrays.asList(java, "-Djava.io.tmpdir=" + input.toAbsolutePath().getParent(),
                "-cp", classpath, "org.gatanalysis.inference.NativeInferenceMain",
                model.toAbsolutePath().toString(), input.toAbsolutePath().toString(), output.toAbsolutePath().toString(), Integer.toString(tiles));
    }

    static void writeInput(Path target, int width, int height, float[] pixels) throws IOException {
        if (width < 1 || height < 1 || (long) width * height != pixels.length)
            throw new IllegalArgumentException("Image dimensions do not match pixel count.");
        try (DataOutputStream out = new DataOutputStream(new BufferedOutputStream(Files.newOutputStream(target)))) {
            out.writeInt(INPUT_MAGIC); out.writeInt(VERSION); out.writeInt(width); out.writeInt(height);
            for (float pixel : pixels) {
                if (!Float.isFinite(pixel)) throw new IllegalArgumentException("Input contains NaN or infinite pixels.");
                out.writeFloat(pixel);
            }
        }
    }

    static Prediction readOutput(Path source, int expectedWidth, int expectedHeight) throws IOException {
        try (DataInputStream in = new DataInputStream(new BufferedInputStream(Files.newInputStream(source)))) {
            if (in.readInt() != OUTPUT_MAGIC || in.readInt() != VERSION) throw new IOException("Unsupported native-inference response format.");
            int width = in.readInt(), height = in.readInt(), channels = in.readInt();
            if (width != expectedWidth || height != expectedHeight || channels < 4 || channels > 1024)
                throw new IOException("Invalid native-inference output dimensions/channels.");
            long pixels = (long) width * height, values = pixels * channels;
            if (pixels < 1 || pixels > Integer.MAX_VALUE || values > MAX_PREDICTION_FLOATS
                    || Files.size(source) != 20L + 4L * values) throw new IOException("Invalid or incomplete native-inference output length.");
            float[][] planes = new float[channels][(int) pixels];
            for (int p = 0; p < pixels; p++) for (int c = 0; c < channels; c++) {
                float value = in.readFloat();
                if (!Float.isFinite(value)) throw new IOException("Native inference produced non-finite predictions.");
                planes[c][p] = value;
            }
            return new Prediction(width, height, planes);
        }
    }

    /** Drain continuously even after the limit, retaining only the last 8 KiB. */
    static final class BoundedDiagnostics implements Closeable {
        private final byte[] buffer = new byte[8192];
        private final InputStream source;
        private final Thread reader;
        private int next, count;
        BoundedDiagnostics(InputStream source) {
            this.source = source;
            reader = new Thread(() -> {
                byte[] chunk = new byte[4096];
                try {
                    int size;
                    while ((size = source.read(chunk)) != -1) append(chunk, size);
                } catch (IOException ignored) { /* Process shutdown closes this pipe. */ }
            }, "GAT-worker-diagnostics");
            reader.setDaemon(true);
            reader.start();
        }
        private synchronized void append(byte[] bytes, int size) {
            for (int i = 0; i < size; i++) {
                buffer[next] = bytes[i];
                next = (next + 1) % buffer.length;
                count = Math.min(count + 1, buffer.length);
            }
        }
        void await() throws InterruptedException { reader.join(2000); }
        synchronized String tail() throws UnsupportedEncodingException {
            if (count == 0) return "No worker diagnostic was produced.";
            byte[] ordered = new byte[count];
            int start = (next - count + buffer.length) % buffer.length;
            for (int i = 0; i < count; i++) ordered[i] = buffer[(start + i) % buffer.length];
            return new String(ordered, "UTF-8");
        }
        @Override public void close() {
            try { source.close(); } catch (IOException ignored) { }
            try { reader.join(2000); }
            catch (InterruptedException e) { Thread.currentThread().interrupt(); }
        }
    }

    private static void deleteTemporary(Path directory) {
        try (Stream<Path> paths = Files.walk(directory)) {
            paths.sorted(Comparator.reverseOrder()).forEach(path -> {
                try { Files.deleteIfExists(path); }
                catch (IOException e) { path.toFile().deleteOnExit(); }
            });
        } catch (IOException ignored) { directory.toFile().deleteOnExit(); }
    }
}

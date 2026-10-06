package Features.Inference;

import ij.ImagePlus;
import ij.ImageStack;
import ij.process.ImageProcessor;
import java.awt.image.IndexColorModel;
import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.stream.Stream;

/** Local protocol for a separately licensed/native-classpath Template Matching worker. */
public final class NativeAlignmentClient {
    static final int INPUT_MAGIC = 0x47415441, OUTPUT_MAGIC = 0x47415453, VERSION = 2;
    static final long MAX_PIXELS = 67_108_864L;
    private NativeAlignmentClient() { }

    public static Path workerDirectory(String fijiDirectory) {
        String configured = System.getProperty("gat.alignment.directory");
        if (configured != null && !configured.trim().isEmpty()) return Paths.get(configured).toAbsolutePath();
        if (fijiDirectory == null) throw new IllegalStateException("Cannot locate Fiji's installation directory");
        return Paths.get(fijiDirectory, "gat-native-alignment").toAbsolutePath();
    }
    public static void checkInstallation(String fijiDirectory) {
        InferenceBackend.requireWorkerJava();
        Path directory = workerDirectory(fijiDirectory);
        if (!Files.isRegularFile(directory.resolve("gat-native-alignment.jar")) || !Files.isDirectory(directory.resolve("lib")))
            throw new IllegalStateException("The isolated native Template Matching worker is missing from " + directory
                    + ". Install the matching GAT preview alignment bundle; keep its libraries outside Fiji/jars and Fiji/plugins. No algorithm is substituted or downloaded automatically.");
    }
    public static double[][] predict(String fijiDirectory, ImagePlus image, int reference) throws IOException, InterruptedException {
        checkInstallation(fijiDirectory);
        Path temporary = Files.createTempDirectory("gat-alignment-");
        Process process = null;
        NativeInferenceClient.BoundedDiagnostics diagnostics = null;
        try {
            Path input = temporary.resolve("input.gata"), output = temporary.resolve("output.gats");
            writeInput(input, image, reference);
            Path directory = workerDirectory(fijiDirectory);
            String javaName = System.getProperty("os.name", "").toLowerCase(Locale.ROOT).contains("win") ? "java.exe" : "java";
            String java = Paths.get(System.getProperty("java.home"), "bin", javaName).toString();
            String classpath = directory.resolve("gat-native-alignment.jar") + File.pathSeparator + directory.resolve("lib/*");
            List<String> command = Arrays.asList(java, "-Xmx1g", "-Djava.awt.headless=true", "-Djava.io.tmpdir=" + temporary,
                    "-Dorg.bytedeco.javacpp.cachedir=" + temporary.resolve("javacpp"), "-cp", classpath,
                    "TemplateMatching.NativeAlignmentMain", input.toString(), output.toString());
            long timeout = Long.getLong("gat.alignment.timeoutSeconds", 900L);
            if (timeout < 1 || timeout > 86400) throw new IllegalArgumentException("Alignment timeout must be 1–86400 seconds");
            ProcessBuilder builder = new ProcessBuilder(command).redirectErrorStream(true);
            builder.environment().remove("CLASSPATH");
            process = builder.start();
            diagnostics = new NativeInferenceClient.BoundedDiagnostics(process.getInputStream());
            if (!process.waitFor(timeout, TimeUnit.SECONDS)) {
                process.destroyForcibly();process.waitFor(5, TimeUnit.SECONDS);diagnostics.await();
                throw new IOException("Native Template Matching timed out after " + timeout + " seconds; the original image was not changed. " + diagnostics.tail());
            }
            diagnostics.await();
            if (process.exitValue() != 0) throw new IOException("Native Template Matching failed (exit " + process.exitValue()
                    + "); the original image was not changed. " + diagnostics.tail());
            return readOutput(output, image.getStackSize(), image.getWidth(), image.getHeight(), reference);
        } finally {
            if (process != null && process.isAlive()) {
                process.destroyForcibly();
                try { process.waitFor(5, TimeUnit.SECONDS); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
            }
            if (diagnostics != null) diagnostics.close();
            try (Stream<Path> paths = Files.walk(temporary)) {
                paths.sorted(Comparator.reverseOrder()).forEach(path -> {
                    try { Files.deleteIfExists(path); } catch (IOException e) { path.toFile().deleteOnExit(); }
                });
            } catch (IOException e) { temporary.toFile().deleteOnExit(); }
        }
    }
    static void writeInput(Path output, ImagePlus image, int reference) throws IOException {
        if (image == null) throw new IllegalArgumentException("No alignment image");
        int width = image.getWidth(), height = image.getHeight(), frames = image.getStackSize(), bits = image.getBitDepth();
        long plane = (long) width * height;
        if (width < 2 || height < 2 || frames < 2 || frames > 10000 || (bits != 8 && bits != 16)
                || reference < 1 || reference > frames || plane > MAX_PIXELS || plane * frames > MAX_PIXELS)
            throw new IllegalArgumentException("Native Template Matching requires an 8/16-bit stack, valid reference slice and at most 67,108,864 total pixels");
        try (DataOutputStream out = new DataOutputStream(new BufferedOutputStream(Files.newOutputStream(output)))) {
            out.writeInt(INPUT_MAGIC);out.writeInt(VERSION);out.writeInt(width);out.writeInt(height);out.writeInt(frames);out.writeInt(bits);out.writeInt(reference);
            for (int z = 1; z <= frames; z++) {
                ImageProcessor pixels = image.getStack().getProcessor(z);
                if (!(pixels.getColorModel() instanceof IndexColorModel)
                        || ((IndexColorModel) pixels.getColorModel()).getMapSize() != 256)
                    throw new IllegalArgumentException("Native Template Matching requires ImageJ's 256-entry grayscale/indexed palette");
                IndexColorModel palette = (IndexColorModel) pixels.getColorModel();
                double minimum = pixels.getMin(), maximum = pixels.getMax();
                if (!Double.isFinite(minimum) || !Double.isFinite(maximum) || minimum > maximum)
                    throw new IllegalArgumentException("Native Template Matching requires a finite ordered display range");
                // The original 8-bit matcher uses getBufferedImage(), whose pixels
                // depend on BOTH the base palette and the current display range.
                out.writeDouble(minimum);
                out.writeDouble(maximum);
                for (int i = 0; i < 256; i++) out.writeInt(palette.getRGB(i));
                if (bits == 8) out.write((byte[]) pixels.getPixels());
                else for (short value : (short[]) pixels.getPixels()) out.writeShort(value);
            }
        }
    }
    static double[][] readOutput(Path input, int frames, int width, int height, int reference) throws IOException {
        if (Files.size(input) != 12L + 16L * frames) throw new IOException("Incomplete or extra native alignment response bytes");
        try (DataInputStream in = new DataInputStream(new BufferedInputStream(Files.newInputStream(input)))) {
            if (in.readInt() != OUTPUT_MAGIC || in.readInt() != VERSION || in.readInt() != frames)
                throw new IOException("Invalid native alignment response header; install the matching plugin and alignment worker together");
            double[][] shifts = new double[frames][2];
            for (int frame = 0; frame < frames; frame++) for (int axis = 0; axis < 2; axis++) {
                double value = in.readDouble();
                if (!Double.isFinite(value) || value != Math.rint(value) || Math.abs(value) > (axis == 0 ? width : height)
                        || frame == reference - 1 && value != 0)
                    throw new IOException("Invalid native alignment shift");
                shifts[frame][axis] = value;
            }
            return shifts;
        }
    }
    /** Build all translated copies first; never partially change the original on worker failure. */
    public static ImagePlus translatedCopy(ImagePlus original, double[][] shifts) {
        if (shifts == null || shifts.length != original.getStackSize()) throw new IllegalArgumentException("Wrong shift count");
        for (double[] shift : shifts) {
            if (shift == null || shift.length != 2) throw new IllegalArgumentException("Invalid shift pair");
            for (int axis = 0; axis < 2; axis++)
                if (!Double.isFinite(shift[axis]) || shift[axis] != Math.rint(shift[axis])
                        || Math.abs(shift[axis]) > (axis == 0 ? original.getWidth() : original.getHeight()))
                    throw new IllegalArgumentException("Invalid integer shift");
        }
        ImageStack stack = new ImageStack(original.getWidth(), original.getHeight());
        for (int z = 1; z <= original.getStackSize(); z++) {
            ImageProcessor copy = original.getStack().getProcessor(z).duplicate();
            copy.resetRoi();
            copy.translate(shifts[z - 1][0], shifts[z - 1][1]);
            stack.addSlice(original.getStack().getSliceLabel(z), copy);
        }
        ImagePlus aligned = original.createImagePlus();
        aligned.setStack(original.getTitle(), stack);
        aligned.setDimensions(original.getNChannels(), original.getNSlices(), original.getNFrames());
        aligned.setOpenAsHyperStack(original.getOpenAsHyperStack());
        aligned.setCalibration(original.getCalibration().copy());
        aligned.setPositionWithoutUpdate(original.getC(), original.getZ(), original.getT());
        aligned.setDisplayRange(original.getDisplayRangeMin(), original.getDisplayRangeMax());
        return aligned;
    }
}

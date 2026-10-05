import Features.Core.PluginCalls;
import Features.Tools.AlignStack;
import com.google.gson.GsonBuilder;
import ij.IJ;
import ij.ImagePlus;
import ij.ImageStack;
import ij.Menus;
import ij.WindowManager;
import ij.process.ByteProcessor;
import ij.process.ImageProcessor;
import java.io.InputStream;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;
import java.util.TreeSet;
import java.util.jar.JarFile;
import net.imagej.legacy.LegacyService;
import org.scijava.log.LogService;

/** Invokes the real GAT public APIs without modifying or replacing their logic. */
public final class BaselineNativeProbe {
    // Must run before ImageJ1 classes initialize so the actual legacy bridge works.
    static { LegacyService.preinit(); }
    private static final List<String> errors = Collections.synchronizedList(new ArrayList<>());
    private static final Map<String, Object> result = Collections.synchronizedMap(new LinkedHashMap<>());
    private static Path reportFile;
    private static boolean invoked;
    private static net.imagej.ImageJ imagej;
    private static final List<Map<String, Object>> commands = Collections.synchronizedList(new ArrayList<>());

    private static String hex(byte[] bytes) {
        StringBuilder s = new StringBuilder();
        for (byte b : bytes) s.append(String.format("%02x", b & 255));
        return s.toString();
    }
    private static String hash(Path path) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (InputStream input = Files.newInputStream(path)) {
            byte[] buffer = new byte[65536]; int count;
            while ((count = input.read(buffer)) != -1) digest.update(buffer, 0, count);
        }
        return hex(digest.digest());
    }
    private static String pixels(ImagePlus image) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        ByteBuffer word = ByteBuffer.allocate(4).order(ByteOrder.BIG_ENDIAN);
        for (int z = 1; z <= image.getStackSize(); z++) {
            ImageProcessor processor = image.getStack().getProcessor(z);
            for (int i = 0; i < image.getWidth() * image.getHeight(); i++) {
                word.clear(); word.putFloat(processor.getf(i)); digest.update(word.array());
            }
        }
        return hex(digest.digest());
    }
    private static String trace(Throwable error) {
        StringWriter text = new StringWriter(); error.printStackTrace(new PrintWriter(text));
        return text.toString();
    }
    private static void record(Throwable error) {
        String message = trace(error); errors.add(message); System.err.println(message); saveSnapshot();
    }
    private static void saveSnapshot() {
        if (reportFile == null) return;
        try {
            synchronized (result) {
                result.put("actual_gat_method_invoked", invoked);
                result.put("errors", new ArrayList<>(errors));
                result.put("imagej_command_dispatch", new ArrayList<>(commands));
                if (reportFile.toAbsolutePath().getParent() != null) Files.createDirectories(reportFile.toAbsolutePath().getParent());
                String json = new GsonBuilder().setPrettyPrinting().disableHtmlEscaping().serializeNulls().create().toJson(result);
                Files.writeString(reportFile, json + "\n");
            }
        } catch (Exception problem) { System.err.println("Could not persist probe snapshot: " + problem); }
    }
    private static Map<String, Object> codeSources() throws Exception {
        Map<String, Object> sources = new LinkedHashMap<>();
        for (String name : new String[]{"Features.Core.PluginCalls", "Features.Tools.AlignStack", "ij.IJ",
                "net.imagej.ImageJ", "de.csbdresden.CommandFromMacro", "de.csbdresden.stardist.StarDist2D",
                "de.csbdresden.csbdeep.commands.GenericNetwork", "net.imagej.tensorflow.DefaultTensorFlowService",
                "org.tensorflow.TensorFlow", "TemplateMatching.Align_slices", "TemplateMatching.cvMatch_Template",
                "org.bytedeco.javacv.Java2DFrameUtils", "org.bytedeco.javacpp.Loader", "org.bytedeco.javacpp.opencv_core"}) {
            Class<?> type = Class.forName(name, false, BaselineNativeProbe.class.getClassLoader());
            java.security.CodeSource code = type.getProtectionDomain().getCodeSource();
            java.net.URL locationURL = code == null ? null : code.getLocation();
            String location = locationURL == null ? "patched class; original resource="
                    + type.getResource("/" + name.replace('.', '/') + ".class") : locationURL.toString();
            sources.put(name, location); System.out.println("CLASS " + name + " " + location);
        }
        return sources;
    }
    private static List<Map<String, Object>> nativeInventory() throws Exception {
        List<Map<String, Object>> records = new ArrayList<>();
        for (String name : System.getProperty("java.class.path").split(java.io.File.pathSeparator)) {
            Path path = Path.of(name);
            if (!Files.isRegularFile(path) || !name.endsWith(".jar")) continue;
            if (!(path.getFileName().toString().contains("libtensorflow_jni") || path.getFileName().toString().contains("opencv"))) continue;
            try (JarFile jar = new JarFile(path.toFile())) {
                for (java.util.jar.JarEntry entry : Collections.list(jar.entries())) {
                    if (!entry.getName().endsWith(".dylib")) continue;
                    Map<String, Object> item = new LinkedHashMap<>();
                    item.put("jar", path.getFileName().toString()); item.put("entry", entry.getName());
                    try (InputStream input = jar.getInputStream(entry)) {
                        byte[] header = input.readNBytes(8); item.put("header_hex", hex(header));
                        if (header.length == 8) {
                            ByteBuffer words = ByteBuffer.wrap(header).order(ByteOrder.LITTLE_ENDIAN);
                            int magic = words.getInt(), cpu = words.getInt();
                            item.put("architecture", magic == 0xfeedfacf && cpu == 0x01000007 ? "x86_64"
                                    : magic == 0xfeedfacf && cpu == 0x0100000c ? "arm64" : "other-or-universal");
                        }
                    }
                    records.add(item);
                }
            }
        }
        return records;
    }
    private static void checkIsolation() throws Exception {
        ClassLoader loader = BaselineNativeProbe.class.getClassLoader();
        boolean fork = loader.getResource("Features/Inference/NativeStarDist.class") != null;
        boolean modern = loader.getResource("org/tensorflow/types/TFloat32.class") != null;
        result.put("fork_inference_classes_present", fork);
        result.put("modern_tensorflow_classes_present", modern);
        if (modern) throw new IllegalStateException("Modern TensorFlow is forbidden on this JVM classpath");
        if (fork && !Boolean.getBoolean("gat.probe.allowFork"))
            throw new IllegalStateException("Fork inference classes are forbidden in unchanged-baseline mode");
    }
    private static void captureTextWindows() {
        List<Map<String, Object>> windows = new ArrayList<>();
        for (java.awt.Frame frame : WindowManager.getNonImageWindows()) {
            if (!(frame instanceof ij.text.TextWindow)) continue;
            String title = frame.getTitle();
            String text = ((ij.text.TextWindow) frame).getTextPanel().getText();
            Map<String, Object> window = new LinkedHashMap<>();
            window.put("title", title); window.put("text", text); windows.add(window);
            // Executer displays caught plugin Throwables here instead of calling
            // IJ.handleException. Collect the real exception; do not infer JNI.
            if ("Exception".equals(title)) {
                String error = "IMAGEJ EXCEPTION WINDOW:\n" + text;
                if (!errors.contains(error)) { errors.add(error); System.err.println(error); }
            }
        }
        result.put("imagej_text_windows", windows); saveSnapshot();
    }
    private static void initialize(boolean stardist) throws Exception {
        IJ.setExceptionHandler(BaselineNativeProbe::record);
        Thread.setDefaultUncaughtExceptionHandler((thread, error) -> record(error));
        IJ.redirectErrorMessages(true);
        IJ.debugMode = Boolean.getBoolean("gat.probe.debug");
        if (stardist || Boolean.getBoolean("gat.probe.fullLegacyContext")) {
            imagej = new net.imagej.ImageJ();
            imagej.log().addLogListener(message -> {
                if (message.level() <= LogService.ERROR) {
                    errors.add("SCIJAVA: " + message.text()); saveSnapshot();
                    if (message.throwable() != null) record(message.throwable());
                }
            });
            imagej.ui().showUI("legacy");
            if (stardist) {
                // Published plugin supplies both command code and SciJava metadata.
                if (imagej.command().getCommand("de.csbdresden.CommandFromMacro") == null
                        || imagej.command().getCommand("de.csbdresden.stardist.StarDist2D") == null)
                    throw new IllegalStateException("Real StarDist/SciJava command registration unavailable");
                result.put("command_from_macro_menu", String.valueOf(Menus.getCommands().get("Command From Macro")));
                if (!Menus.getCommands().containsKey("Command From Macro"))
                    throw new IllegalStateException("Real Command From Macro was not registered with ImageJ1");
            }
        } else {
            new ij.ImageJ(ij.ImageJ.NO_SHOW);
        }
        if (!stardist) {
            Menus.getCommands().put("Align slices in stack...", "TemplateMatching.Align_slices");
            result.put("alignment_menu", String.valueOf(Menus.getCommands().get("Align slices in stack...")));
        }
        result.put("imagej_plugin_classloader", IJ.getClassLoader().getClass().getName());
        Object hooks = IJ.class.getField("_hooks").get(null);
        result.put("legacy_hooks_class", hooks == null ? null : hooks.getClass().getName());
        ij.Executer.addCommandListener(command -> {
            Map<String, Object> dispatch = new LinkedHashMap<>();
            dispatch.put("command", command); dispatch.put("thread", Thread.currentThread().getName());
            dispatch.put("macro_options", ij.Macro.getOptions());
            ImagePlus current = WindowManager.getCurrentImage();
            dispatch.put("current_image", current == null ? null : current.getTitle());
            dispatch.put("current_image_locked", current == null ? null : current.isLocked());
            commands.add(dispatch); saveSnapshot();
            return command;
        });
        IJ.setExceptionHandler(BaselineNativeProbe::record);
    }
    private static void stardist(Path inputFile, Path model) throws Exception {
        result.put("input_sha256", hash(inputFile)); result.put("model_sha256", hash(model));
        ImagePlus input = IJ.openImage(inputFile.toString());
        if (input == null || input.getWidth() != 175 || input.getHeight() != 175 || input.getBitDepth() != 8)
            throw new IllegalArgumentException("Expected original 175x175 8-bit public Hu fixture");
        result.put("input_pixel_sha256", pixels(input));
        result.put("requested_tiles", PluginCalls.suggestTiles(input.getWidth(), input.getHeight()));
        result.put("probability_threshold", 0.5); result.put("nms_threshold", 0.3);
        input.setTitle("baseline_public_Hu");
        invoked = true; result.put("stage", "calling_actual_GAT_StarDist"); saveSnapshot();
        ImagePlus labels = PluginCalls.runStarDist2DLabel(input, model.toString(), 0.5, 0.3);
        captureTextWindows();
        result.put("returned_input_fallback", labels == input);
        result.put("output_bit_depth", labels == null ? null : labels.getBitDepth());
        if (labels == null || labels == input || labels.getBitDepth() != 16
                || labels.getWidth() != 175 || labels.getHeight() != 175 || labels.getStackSize() != 1)
            throw new AssertionError("Actual GAT call did not return a new 175x175 16-bit label raster; unchanged input fallback is not success");
        short[] raster = (short[]) labels.getProcessor().getPixels();
        Set<Integer> distinct = new TreeSet<>();
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        for (short label : raster) {
            int value = label & 65535; if (value != 0) distinct.add(value);
            digest.update((byte) (value >>> 8)); digest.update((byte) value);
        }
        result.put("object_count", distinct.size()); result.put("raw_label_sha256", hex(digest.digest()));
        if (distinct.isEmpty()) throw new AssertionError("No objects returned for the public Hu fixture");
    }
    private static ImagePlus synthetic() {
        int width = 128, height = 96;
        ByteProcessor base = new ByteProcessor(width, height); Random random = new Random(8291);
        for (int y = 10; y < height - 10; y++) for (int x = 10; x < width - 10; x++) base.set(x, y, random.nextInt(200) + 1);
        ImageStack stack = new ImageStack(width, height);
        for (int[] shift : new int[][]{{0, 0}, {3, -2}, {-4, 5}, {0, 0}}) {
            ImageProcessor frame = base.duplicate(); frame.translate(shift[0], shift[1]); stack.addSlice(frame);
        }
        return new ImagePlus("baseline_synthetic8", stack);
    }
    private static void alignment() throws Exception {
        ImagePlus input = synthetic(); String before = pixels(input);
        result.put("fixture", "seed8291-128x96-byte-shifts_0_0_3_-2_-4_5_0_0");
        result.put("input_pixel_sha256", before); result.put("frames", input.getStackSize());
        input.show(); input.setSlice(1);
        result.put("input_locked_before_dispatch", input.isLocked());
        result.put("input_locked_by_other_thread", input.isLockedByAnotherThread());
        Object filter = Class.forName("TemplateMatching.Align_slices", true, IJ.getClassLoader()).getDeclaredConstructor().newInstance();
        result.put("separate_setup_control_filter_classloader", filter.getClass().getClassLoader().getClass().getName());
        result.put("separate_setup_control_is_plugin_filter", filter instanceof ij.plugin.filter.PlugInFilter);
        if (!(filter instanceof ij.plugin.filter.PlugInFilter)) throw new IllegalStateException("Published filter has incompatible ImageJ class identity");
        result.put("separate_setup_control_flags", ((ij.plugin.filter.PlugInFilter) filter).setup("", input));
        invoked = true; result.put("stage", "calling_actual_GAT_alignment"); saveSnapshot();
        AlignStack.alignTemplateMatching(input, 1);
        captureTextWindows();
        String after = pixels(input); result.put("aligned_pixel_sha256", after);
        result.put("unchanged_input", before.equals(after));
        String expected = "8be9c6ad7c4c28d68b07f0b45c562deb9d29e4febf030b0ad24dcb198ea7fa9c";
        result.put("expected_aligned_pixel_sha256", expected);
        if (before.equals(after)) throw new AssertionError("Alignment left shifted input unchanged");
        if (!expected.equals(after)) throw new AssertionError("Alignment pixels differ from the same-fixture original Linux reference");
    }
    public static void main(String[] args) throws Exception {
        if (!((args.length == 4 && args[0].equals("stardist")) || (args.length == 2 && args[0].equals("alignment"))))
            throw new IllegalArgumentException("stardist Hu.tif model.zip report.json | alignment report.json");
        String mode = args[0]; Path report = Path.of(args[args.length - 1]); reportFile = report;
        result.put("probe", mode); result.put("java_version", System.getProperty("java.version"));
        result.put("system_classloader", ClassLoader.getSystemClassLoader().getClass().getName());
        result.put("probe_classloader", BaselineNativeProbe.class.getClassLoader().getClass().getName());
        result.put("thread_context_classloader", Thread.currentThread().getContextClassLoader().getClass().getName());
        result.put("full_legacy_context", Boolean.getBoolean("gat.probe.fullLegacyContext"));
        result.put("os", System.getProperty("os.name")); result.put("os_version", System.getProperty("os.version"));
        result.put("java_arch", System.getProperty("os.arch")); result.put("allow_fork", Boolean.getBoolean("gat.probe.allowFork"));
        long start = System.nanoTime();
        result.put("status", "running"); result.put("stage", "validating_runtime"); saveSnapshot();
        try {
            checkIsolation(); result.put("code_sources", codeSources()); result.put("native_inventory", nativeInventory());
            if (java.awt.GraphicsEnvironment.isHeadless()) {
                result.put("status", "unavailable"); result.put("reason", "A GUI-capable display is required for the original IJ.run integration");
            } else {
                result.put("stage", "initializing_real_plugins"); saveSnapshot();
                initialize(mode.equals("stardist"));
                if (mode.equals("stardist")) stardist(Path.of(args[1]), Path.of(args[2])); else alignment();
                result.put("status", errors.isEmpty() ? "success" : "workflow_failure");
            }
        } catch (Throwable error) {
            record(error); result.put("status", invoked ? "workflow_failure" : "setup_failure");
        } finally {
            captureTextWindows();
            result.put("actual_gat_method_invoked", invoked);
            result.put("elapsed_milliseconds", (System.nanoTime() - start) / 1000000);
            String ijError = IJ.getErrorMessage(); if (ijError != null && !ijError.isEmpty()) errors.add("IMAGEJ: " + ijError);
            result.put("imagej_log", IJ.getLog()); result.put("errors", new ArrayList<>(errors));
            result.put("imagej_command_dispatch", new ArrayList<>(commands));
            if (!errors.isEmpty() && "success".equals(result.get("status"))) result.put("status", "workflow_failure");
            String json = new GsonBuilder().setPrettyPrinting().disableHtmlEscaping().serializeNulls().create().toJson(result);
            if (report.toAbsolutePath().getParent() != null) Files.createDirectories(report.toAbsolutePath().getParent());
            Files.writeString(report, json + "\n"); System.out.println(json);
        }
        // Processes are intentionally isolated; close GUI/event threads even after a plugin error.
        System.exit("success".equals(result.get("status")) ? 0 : 2);
    }
}

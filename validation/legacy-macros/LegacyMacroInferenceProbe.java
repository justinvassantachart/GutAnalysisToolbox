import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import ij.IJ;
import ij.ImagePlus;
import ij.Menus;
import ij.WindowManager;
import ij.gui.Roi;
import ij.plugin.frame.RoiManager;
import ij.process.ByteProcessor;
import ij.process.FloatProcessor;
import ij.process.ShortProcessor;
import ij.process.ImageProcessor;
import ij.process.FloatPolygon;
import java.io.DataOutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import net.imagej.Dataset;
import net.imagej.legacy.LegacyService;
import net.imglib2.type.numeric.RealType;
import org.scijava.event.EventHandler;
import org.scijava.module.Module;
import org.scijava.module.event.ModuleExecutedEvent;

/** Actual registered Command From Macro, exact legacy call line, one public case.
 * No production classes are statically imported, so original runs exclude them.
 * This exercises the macro inference boundary, not a complete analysis macro.
 */
public final class LegacyMacroInferenceProbe {
    static { LegacyService.preinit(); }
    private static final Gson JSON = new GsonBuilder().serializeNulls().setPrettyPrinting().create();
    private static final Map<String, Object> report = new LinkedHashMap<>();
    private static final List<String> errors = Collections.synchronizedList(new ArrayList<>());
    private static final Map<Long, String> workerProcesses = Collections.synchronizedMap(new LinkedHashMap<>());
    private static Path output;
    private static volatile boolean watching;

    public static final class ModuleObserver {
        final String target;
        volatile Module module;
        int matchingExecutions;
        ModuleObserver(String target) { this.target = target; }
        @EventHandler public void executed(ModuleExecutedEvent event) {
            Module current = event.getModule();
            if (current.getDelegateObject().getClass().getName().equals(target)) {
                module = current; matchingExecutions++;
            }
        }
    }

    @SuppressWarnings("unchecked")
    public static void main(String[] args) throws Exception {
        if (args.length != 1) throw new IllegalArgumentException("case-config.json");
        Map<String, Object> config = JSON.fromJson(Files.readString(Path.of(args[0])), Map.class);
        output = Path.of((String) config.get("output"));
        Files.createDirectory(output);
        String variant = (String) config.get("variant");
        boolean nativeVariant = variant.equals("native");
        if (!nativeVariant && !variant.equals("original")) throw new IllegalArgumentException("original or native required");
        String target = nativeVariant ? "Features.Macros.LegacyMacroStarDist" : "de.csbdresden.stardist.StarDist2D";
        report.put("schema_version", 1); report.put("scope", "registered-legacy-macro-inference-boundary");
        report.put("whole_analysis_macro_executed", false);
        report.put("variant", variant); report.put("case", config.get("case"));
        report.put("os", System.getProperty("os.name")); report.put("arch", System.getProperty("os.arch"));
        report.put("java_version", System.getProperty("java.version"));
        report.put("system_classloader", ClassLoader.getSystemClassLoader().getClass().getName());
        report.put("status", "SETTING_UP"); checkpoint();
        int exit = 2;
        net.imagej.ImageJ imagej = null;
        try {
            if (java.awt.GraphicsEnvironment.isHeadless()) throw new IllegalStateException("Actual AWT macro/ROI display is required");
            ClassLoader loader = LegacyMacroInferenceProbe.class.getClassLoader();
            if (loader.getResource("org/tensorflow/types/TFloat32.class") != null)
                throw new IllegalStateException("Modern TensorFlow must stay in the separate worker JVM");
            boolean forkAvailable = loader.getResource("Features/Macros/LegacyMacroStarDist.class") != null;
            if (forkAvailable != nativeVariant) throw new IllegalStateException("Original/native classpath isolation failed");
            if (nativeVariant) {
                String property = (String) Class.forName("Features.Inference.InferenceBackend").getField("PROPERTY").get(null);
                if (!property.equals("gat.stardist.backend") || !System.getProperty(property, "").equals("native")
                        || !Boolean.TRUE.equals(Class.forName("Features.Inference.InferenceBackend")
                        .getMethod("useNativeWorker").invoke(null)))
                    throw new IllegalStateException("Native adapter must execute its real native branch even on Linux");
                report.put("backend_property", property); report.put("backend_value", System.getProperty(property));
            }
            IJ.setExceptionHandler(error -> errors.add(error.toString()));
            IJ.redirectErrorMessages(true);
            imagej = new net.imagej.ImageJ();
            imagej.ui().showUI("legacy");
            if (!nativeVariant && (IJ.getClassLoader().getResource("Features/Macros/LegacyMacroStarDist.class") != null
                    || IJ.getClassLoader().getResource("Features/Inference/NativeStarDist.class") != null))
                throw new IllegalStateException("Original ImageJ plugin loader can see fork production classes");
            if (imagej.command().getCommand("de.csbdresden.CommandFromMacro") == null
                    || imagej.command().getCommand(target) == null
                    || !Menus.getCommands().containsKey("Command From Macro"))
                throw new IllegalStateException("Actual discovered Command From Macro/target menu registration unavailable");
            report.put("command_from_macro_menu", String.valueOf(Menus.getCommands().get("Command From Macro")));
            report.put("target_class", provenance(Class.forName(target)));
            report.put("command_bridge_class", provenance(Class.forName("de.csbdresden.CommandFromMacro")));
            ModuleObserver observer = new ModuleObserver(target);
            imagej.event().subscribe(observer);
            imagej.log().addLogListener(message -> {
                if (watching && message.level() <= org.scijava.log.LogService.ERROR) {
                    errors.add(message.text());
                    if (message.throwable() != null) errors.add(message.throwable().toString());
                }
            });
            List<String> dispatched = Collections.synchronizedList(new ArrayList<>());
            ij.Executer.addCommandListener(command -> { dispatched.add(command); return command; });
            Map<String, Object> caseSpec = (Map<String, Object>) config.get("case");
            Path fixture = Path.of((String) config.get("fixture"));
            Path model = Path.of((String) config.get("model"));
            report.put("fixture_sha256", hash(fixture)); report.put("model_sha256", hash(model));
            ImagePlus input = prepareInput(fixture, caseSpec);
            ImagePlus unrelated = new ImagePlus("unrelated-image-sentinel", new ByteProcessor(17, 13));
            unrelated.show();
            input.show();
            String scaleMacro = scaleMacro(input, caseSpec);
            report.put("preparation_macro", scaleMacro);
            if (!scaleMacro.isEmpty()) {
                IJ.runMacro(scaleMacro);
                input = WindowManager.getCurrentImage();
                if (input == null || !input.getTitle().equals("macro-input-rescaled"))
                    throw new IllegalStateException("Actual Scale... did not select its requested output");
            }
            report.put("prepared_input", imageSnapshot(input));
            String before = pixels(input);
            RoiManager manager = RoiManager.getInstance2();
            if (manager == null) manager = new RoiManager();
            manager.reset();
            Set<Integer> beforeIds = ids();
            String line = (String) config.get("macro_line");
            if (!line.contains("command=[" + target + "]") || !line.stripLeading().startsWith("run(\"Command From Macro\","))
                throw new IllegalArgumentException("Wrong actual legacy macro call line");
            String macro = "img_seg=" + quote(input.getTitle()) + ";\nmodel_file=" + quote(model.toString())
                    + ";\nn_tiles=" + integer(caseSpec, "tiles") + ";\nprobability=" + number(caseSpec, "probability")
                    + ";\noverlap=" + number(caseSpec, "nms") + ";\n" + line + "\n";
            report.put("macro_source", macro); Files.writeString(output.resolve("invoked.ijm"), macro);
            watching = true;
            Thread watcher = new Thread(() -> {
                while (watching) {
                    ProcessHandle.current().descendants().forEach(child -> child.info().commandLine().ifPresent(command -> {
                        if (command.contains("org.gatanalysis.inference.NativeInferenceMain")) workerProcesses.put(child.pid(), command);
                    }));
                    try { Thread.sleep(10); } catch (InterruptedException stopped) { return; }
                }
            }, "native-worker-observation");
            watcher.setDaemon(true); watcher.start();
            report.put("status", "RUNNING_ACTUAL_MACRO_COMMAND"); checkpoint();
            long start = System.nanoTime();
            String macroReturn = IJ.runMacro(macro);
            report.put("seconds", (System.nanoTime() - start) / 1e9);
            watching = false; watcher.join(1000);
            report.put("macro_return", macroReturn); report.put("dispatched_commands", dispatched);
            report.put("worker_processes", workerProcesses);
            report.put("matching_module_executions", observer.matchingExecutions);
            if (observer.module == null || observer.matchingExecutions != 1)
                throw new IllegalStateException("Actual target module did not complete exactly once");
            if (!dispatched.contains("Command From Macro")) throw new IllegalStateException("Bridge command was not dispatched by actual IJ macro");
            if (nativeVariant && workerProcesses.size() != 1)
                throw new IllegalStateException("Expected one genuinely observed native inference worker; fallback/proxy evidence is insufficient");
            if (!nativeVariant && !workerProcesses.isEmpty()) throw new IllegalStateException("Original control unexpectedly used native worker");
            Dataset label = (Dataset) observer.module.getOutput("label");
            if (label == null) throw new IllegalStateException("Actual command returned no label dataset");
            report.put("label", saveLabel(label));
            report.put("roi_manager", roiSnapshot(RoiManager.getInstance2()));
            report.put("auxiliary_outputs_absent", observer.module.getOutput("prob") == null && observer.module.getOutput("dist") == null);
            List<Object> displays = new ArrayList<>();
            for (int id : ids()) if (!beforeIds.contains(id)) displays.add(imageSnapshot(WindowManager.getImage(id)));
            report.put("new_image_windows", displays);
            boolean displayedLabels = false;
            for (int id : ids()) if (!beforeIds.contains(id)) {
                ImagePlus image = WindowManager.getImage(id);
                if (image.getWidth() == input.getWidth() && image.getHeight() == input.getHeight()
                        && image.getBitDepth() == 16 && pixels(image).equals(report.get("label_pixels_f32be_sha256"))) displayedLabels = true;
            }
            report.put("label_display_verified", displayedLabels);
            report.put("input_unchanged", before.equals(pixels(input)));
            report.put("unrelated_image_unchanged", WindowManager.getImage(unrelated.getID()) == unrelated && unrelated.getProcessor().getStats().max == 0);
            String imagejLog = IJ.getLog(); Files.writeString(output.resolve("imagej.log"), imagejLog == null ? "" : imagejLog);
            for (java.awt.Frame frame : WindowManager.getNonImageWindows()) if (frame instanceof ij.text.TextWindow && frame.getTitle().equals("Exception"))
                errors.add(((ij.text.TextWindow) frame).getTextPanel().getText());
            if (!errors.isEmpty() || !displayedLabels || !Boolean.TRUE.equals(report.get("input_unchanged"))
                    || !Boolean.TRUE.equals(report.get("unrelated_image_unchanged")) || !Boolean.TRUE.equals(report.get("auxiliary_outputs_absent")))
                throw new IllegalStateException("Actual command/output integrity checks failed");
            report.put("status", "PASS_MACRO_INFERENCE_CASE");
            exit = 0;
        } catch (Throwable failure) {
            report.put("error", failure.toString()); failure.printStackTrace();
            report.put("status", report.get("status").equals("SETTING_UP") ? "BLOCKED_SETUP" : "FAIL_MACRO_INFERENCE_CASE");
        } finally {
            watching = false; report.put("errors", errors); checkpoint();
            if (imagej != null) imagej.dispose();
        }
        System.exit(exit);
    }

    private static ImagePlus prepareInput(Path fixture, Map<String, Object> spec) {
        ImagePlus publicImage = IJ.openImage(fixture.toString());
        if (publicImage == null || publicImage.getWidth() != 175 || publicImage.getHeight() != 175 || publicImage.getBitDepth() != 8)
            throw new IllegalArgumentException("Pinned public 175x175 Hu input required");
        List<?> shape = (List<?>) spec.get("shape");
        int w = ((Number) shape.get(0)).intValue(), h = ((Number) shape.get(1)).intValue();
        int bits = integer(spec, "dtype");
        ImageProcessor source = publicImage.getProcessor();
        source.setRoi((175 - w) / 2, (175 - h) / 2, w, h);
        ImageProcessor cropped = source.crop();
        ImageProcessor target = bits == 8 ? new ByteProcessor(w, h) : bits == 16 ? new ShortProcessor(w, h) : new FloatProcessor(w, h);
        for (int p = 0; p < w * h; p++) {
            float value = cropped.getf(p);
            target.setf(p, bits == 8 ? value : bits == 16 ? value * 257 : value * .37f - 17.25f);
        }
        ImagePlus result = new ImagePlus("macro-input", target);
        result.getCalibration().setUnit("um"); result.getCalibration().pixelWidth = .568; result.getCalibration().pixelHeight = .713;
        return result;
    }

    private static String scaleMacro(ImagePlus input, Map<String, Object> spec) {
        double scale = number(spec, "scale");
        if (scale == 1) return "";
        int w = (int) Math.round(input.getWidth() * scale), h = (int) Math.round(input.getHeight() * scale);
        return "selectWindow(" + quote(input.getTitle()) + ");\nrun(\"Scale...\", \"x=- y=- width=" + w
                + " height=" + h + " interpolation=None create title=macro-input-rescaled\");\n";
    }

    private static Map<String, Object> saveLabel(Dataset label) throws Exception {
        Map<String, Object> result = new LinkedHashMap<>();
        List<Object> shape = new ArrayList<>(), axes = new ArrayList<>();
        for (int d = 0; d < label.numDimensions(); d++) {
            shape.add(label.dimension(d)); axes.add(Arrays.asList(label.axis(d).type().getLabel(), label.axis(d).unit(),
                    label.axis(d).calibratedValue(0), label.axis(d).calibratedValue(1)));
        }
        result.put("shape", shape); result.put("axes", axes); result.put("dtype", label.getType().getClass().getName());
        result.put("name", label.getName());
        Map<Integer, Integer> areas = new LinkedHashMap<>();
        Path file = output.resolve("labels.f32be");
        try (DataOutputStream out = new DataOutputStream(Files.newOutputStream(file))) {
            for (RealType<?> pixel : label.getImgPlus()) {
                float value = pixel.getRealFloat();
                if (!Float.isFinite(value) || value < 0 || value != Math.rint(value)) throw new IllegalStateException("Invalid label value");
                out.writeFloat(value); if (value != 0) areas.merge((int) value, 1, Integer::sum);
            }
        }
        result.put("areas_by_label_id", areas); result.put("object_count", areas.size());
        result.put("pixels_f32be_sha256", hash(file)); report.put("label_pixels_f32be_sha256", hash(file));
        return result;
    }

    private static List<Object> roiSnapshot(RoiManager manager) {
        if (manager == null) throw new IllegalStateException("No global ROI Manager");
        List<Object> result = new ArrayList<>();
        for (Roi roi : manager.getRoisAsArray()) {
            List<Object> points = new ArrayList<>(); FloatPolygon polygon = roi.getFloatPolygon();
            for (int p = 0; p < polygon.npoints; p++) points.add(Arrays.asList(polygon.xpoints[p], polygon.ypoints[p]));
            result.add(Arrays.asList(roi.getName(), roi.getType(), roi.getPosition(), roi.getCPosition(), roi.getZPosition(), roi.getTPosition(), points));
        }
        return result;
    }

    private static Map<String, Object> imageSnapshot(ImagePlus image) throws Exception {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("title", image.getTitle()); result.put("width", image.getWidth()); result.put("height", image.getHeight());
        result.put("channels", image.getNChannels()); result.put("slices", image.getNSlices()); result.put("frames", image.getNFrames());
        result.put("bits", image.getBitDepth()); result.put("pixel_sha256", pixels(image));
        result.put("pixel_width", image.getCalibration().pixelWidth); result.put("pixel_height", image.getCalibration().pixelHeight);
        result.put("unit", image.getCalibration().getUnit());
        return result;
    }

    private static Set<Integer> ids() {
        Set<Integer> result = new TreeSet<>(); int[] ids = WindowManager.getIDList();
        if (ids != null) for (int id : ids) result.add(id); return result;
    }

    private static String pixels(ImagePlus image) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        for (int z = 1; z <= image.getStackSize(); z++) for (int p = 0; p < image.getWidth() * image.getHeight(); p++) {
            int bits = Float.floatToIntBits(image.getStack().getProcessor(z).getf(p));
            digest.update((byte) (bits >>> 24)); digest.update((byte) (bits >>> 16)); digest.update((byte) (bits >>> 8)); digest.update((byte) bits);
        }
        return hex(digest.digest());
    }

    private static String hash(Path path) throws Exception { return hex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(path))); }
    private static String hex(byte[] bytes) { StringBuilder out = new StringBuilder(); for (byte b : bytes) out.append(String.format("%02x", b & 255)); return out.toString(); }
    private static String quote(String value) { return "\"" + value.replace("\\", "\\\\").replace("\"", "\\\"") + "\""; }
    private static int integer(Map<String, Object> spec, String key) { return ((Number) spec.get(key)).intValue(); }
    private static double number(Map<String, Object> spec, String key) { return ((Number) spec.get(key)).doubleValue(); }
    private static Map<String, Object> provenance(Class<?> type) throws Exception {
        Map<String, Object> result = new LinkedHashMap<>(); result.put("name", type.getName());
        result.put("code_source", type.getProtectionDomain().getCodeSource().getLocation().toString());
        try (java.io.InputStream input = type.getResourceAsStream("/" + type.getName().replace('.', '/') + ".class")) {
            result.put("class_sha256", hex(MessageDigest.getInstance("SHA-256").digest(input.readAllBytes())));
        }
        return result;
    }
    private static void checkpoint() throws Exception { Files.writeString(output.resolve("report.json"), JSON.toJson(report) + "\n"); }
}

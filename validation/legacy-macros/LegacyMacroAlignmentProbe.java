import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import ij.IJ;
import ij.ImagePlus;
import ij.ImageStack;
import ij.Menus;
import ij.WindowManager;
import ij.measure.ResultsTable;
import ij.process.ByteProcessor;
import ij.process.ShortProcessor;
import ij.process.FloatProcessor;
import ij.process.ImageProcessor;
import ij.text.TextWindow;
import java.io.ByteArrayOutputStream;
import java.io.DataOutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.*;
import net.imagej.legacy.LegacyService;

/** Actual macro dispatch, AWT state and exported motion CSV. Public synthetic
 * inputs only. This does not execute the surrounding calcium-analysis macro. */
public final class LegacyMacroAlignmentProbe {
    static { LegacyService.preinit(); }
    private static final Gson JSON = new GsonBuilder().serializeNulls().setPrettyPrinting().create();
    private static final Map<String, Object> report = new LinkedHashMap<>();
    private static final List<Object> cases = new ArrayList<>();
    private static final List<String> errors = Collections.synchronizedList(new ArrayList<>());
    private static final List<String> dispatched = Collections.synchronizedList(new ArrayList<>());
    private static final Map<Long, String> workers = Collections.synchronizedMap(new LinkedHashMap<>());
    private static volatile boolean watching;
    private static final String NATIVE_TYPE_ERROR = "java.lang.IllegalArgumentException: Native Template Matching requires an 8/16-bit stack, valid reference slice, at most 67,108,864 pixels per plane and the bounded stack-memory budget (512 MiB raw pixels; 768 MiB estimated Java working set)";
    private static final String NATIVE_GUARD_MESSAGE = "MacroFork alignment failed: GAT_ALIGNMENT_ERROR: " + NATIVE_TYPE_ERROR;
    private static final String ORIGINAL_TYPE_ERROR = "\"Align slices in stack...\" requires an image of type: 8-bit grayscale 16-bit grayscale";

    @SuppressWarnings("unchecked")
    public static void main(String[] args) throws Exception {
        if (args.length != 1) throw new IllegalArgumentException("RUN_CONFIG_JSON");
        Map<String, Object> config = JSON.fromJson(Files.readString(Path.of(args[0])), Map.class);
        String variant = (String) config.get("variant"); boolean nativeMode = variant.equals("native");
        boolean adapterMode = !variant.equals("original");
        if (!(nativeMode || variant.equals("original") || variant.equals("legacy-delegate"))) throw new IllegalArgumentException("Invalid variant");
        Path output = Path.of((String) config.get("output")); Files.createDirectory(output);
        report.put("schema_version", 1); report.put("scope", "registered-legacy-macro-alignment-boundary");
        report.put("whole_calcium_macro_executed", false); report.put("variant", variant);
        report.put("os", System.getProperty("os.name")); report.put("arch", System.getProperty("os.arch"));
        report.put("java", System.getProperty("java.version")); report.put("cases", cases);
        report.put("macro_source", config.get("macro_source")); report.put("schedule", config.get("schedule"));
        report.put("backend", System.getProperty("gat.alignment.backend", "unset"));
        report.put("status", "SETTING_UP"); checkpoint(output);
        net.imagej.ImageJ imagej = null; int exit = 2;
        try {
            if (java.awt.GraphicsEnvironment.isHeadless()) throw new IllegalStateException("Actual AWT required");
            ClassLoader loader = LegacyMacroAlignmentProbe.class.getClassLoader();
            if ((loader.getResource("Features/Macros/LegacyTemplateMatching.class") != null) != adapterMode)
                throw new IllegalStateException("Original/adapter classpath isolation failed");
            if (adapterMode && !(nativeMode ? "native" : "legacy").equals(System.getProperty("gat.alignment.backend")))
                throw new IllegalStateException("Intended adapter backend must be explicitly selected");
            if (loader.getResource("TemplateMatching/NativeAlignmentMain.class") != null)
                throw new IllegalStateException("Native worker classes leaked into parent JVM");
            IJ.setExceptionHandler(error -> errors.add(error.toString())); IJ.redirectErrorMessages(true);
            imagej = new net.imagej.ImageJ(); imagej.ui().showUI("legacy");
            if (!adapterMode && IJ.getClassLoader().getResource("Features/Macros/LegacyTemplateMatching.class") != null)
                throw new IllegalStateException("Original plugin loader sees fork classes");
            if (!Menus.getCommands().containsKey("Align slices in stack..."))
                throw new IllegalStateException("Original Template Matching menu command is not installed");
            report.put("original_menu", Menus.getCommands().get("Align slices in stack..."));
            report.put("target_class", provenance(Class.forName(adapterMode
                    ? "Features.Macros.LegacyTemplateMatching" : "TemplateMatching.Align_slices")));
            ij.Executer.addCommandListener(command -> { dispatched.add(command); return command; });
            imagej.log().addLogListener(message -> {
                if (watching && message.level() <= org.scijava.log.LogService.ERROR) {
                    errors.add(message.text());
                    if (message.throwable() != null) errors.add(message.throwable().toString());
                }
            });
            ImagePlus sentinel = new ImagePlus("unrelated-alignment-sentinel", new ByteProcessor(13, 11));
            sentinel.show(); Map<String, Object> sentinelBefore = snapshot(sentinel);
            Map<String, Object> schedule = (Map<String, Object>) config.get("schedule");
            for (Map<String, Object> spec : (List<Map<String, Object>>) schedule.get("cases")) {
                String name = (String) spec.get("id"); int bits = integer(spec, "bits"), reference = integer(spec, "reference");
                boolean rejected = spec.get("expected").equals("rejected");
                ImagePlus input = synthetic(spec, schedule); input.setTitle(name);
                input.getCalibration().setUnit("um"); input.getCalibration().pixelWidth = .37;
                input.getCalibration().pixelHeight = .63; input.getCalibration().pixelDepth = 2.5;
                input.getCalibration().frameInterval = 1.25; input.show();
                String line = ((String) config.get("macro_line")).replace("ref.slice=3", "ref.slice=" + reference);
                String macro = "selectWindow(\"" + name + "\");\nsizeX=" + input.getWidth() + ";sizeY=" + input.getHeight()
                        + ";\nx_size=floor(sizeX*0.7);\ny_size=floor(sizeY*0.7);\nx0=floor(sizeX/6);\ny0=floor(sizeY/6);\n" + line + "\nprint(\"GAT_ALIGNMENT_AFTER_BOUNDARY_" + name + "\");\n";
                Files.writeString(output.resolve(name + ".ijm"), macro);
                Map<String, Object> row = new LinkedHashMap<>(); cases.add(row);
                row.put("case", spec); row.put("invoked_macro_sha256", hash(macro.getBytes(java.nio.charset.StandardCharsets.UTF_8)));
                row.put("input", snapshot(input)); Files.write(output.resolve(name + "-input.f32be"), pixels(input));
                row.put("status", "RUNNING"); checkpoint(output);
                if (WindowManager.getWindow("Exception") != null) throw new IllegalStateException("Unexpected pre-existing Exception window");
                errors.clear(); workers.clear(); dispatched.clear(); IJ.redirectErrorMessages(true);
                IJ.getErrorMessage();
                String beforeLog = IJ.getLog() == null ? "" : IJ.getLog();
                List<String> dialogs = Collections.synchronizedList(new ArrayList<>());
                List<String> guardDialogs = Collections.synchronizedList(new ArrayList<>());
                Set<java.awt.Window> acknowledged = Collections.newSetFromMap(new IdentityHashMap<>());
                Set<java.awt.Window> observedDialogs = Collections.newSetFromMap(new IdentityHashMap<>());
                Thread macroThread = Thread.currentThread();
                watching = true;
                Thread observer = new Thread(() -> {
                    while (watching) {
                        if (rejected && !nativeMode) {
                            for (java.awt.Window candidate : java.awt.Window.getWindows()) {
                                if (!(candidate instanceof ij.gui.GenericDialog) || !candidate.isVisible() || acknowledged.contains(candidate)) continue;
                                ij.gui.GenericDialog dialog = (ij.gui.GenericDialog) candidate;
                                if (!dialog.getTitle().equals("Macro Error")) continue;
                                try {
                                    String message = dialogMessage(dialog);
                                    if (observedDialogs.add(dialog)) recordDialog(output, name, "observed", dialog, message, macroThread);
                                    if (!message.trim().replaceAll("\\s+", " ").startsWith(ORIGINAL_TYPE_ERROR + " in line ")) continue;
                                    if (!LegacyMacroModalState.ready(macroThread.getState(), macroThread.getStackTrace())) continue;
                                    recordDialog(output, name, "acknowledging-ready-modal", dialog, message, macroThread);
                                    acknowledged.add(candidate); dialogs.add(message);
                                    java.awt.EventQueue.invokeLater(() -> {
                                        java.awt.Button okay = dialog.getButtons()[0];
                                        if (okay == null) errors.add("Observed error dialog has no OK button");
                                        else dialog.actionPerformed(new java.awt.event.ActionEvent(okay, java.awt.event.ActionEvent.ACTION_PERFORMED, okay.getLabel()));
                                    });
                                } catch (Exception failure) { errors.add("Cannot observe expected Macro Error: " + failure); }
                            }
                        }
                        if (rejected && nativeMode) {
                            for (java.awt.Window candidate : java.awt.Window.getWindows()) {
                                if (!(candidate instanceof ij.gui.MessageDialog) || !candidate.isVisible() || acknowledged.contains(candidate)) continue;
                                ij.gui.MessageDialog dialog = (ij.gui.MessageDialog) candidate;
                                if (!dialog.getTitle().equals("Macro")) continue;
                                try {
                                    java.lang.reflect.Field label = ij.gui.MessageDialog.class.getDeclaredField("label");
                                    label.setAccessible(true);
                                    String message = componentText((java.awt.Component) label.get(dialog));
                                    if (observedDialogs.add(dialog)) recordDialog(output, name, "observed", dialog, message, macroThread);
                                    if (!message.equals(NATIVE_GUARD_MESSAGE)) continue;
                                    java.lang.reflect.Field button = ij.gui.MessageDialog.class.getDeclaredField("button");
                                    button.setAccessible(true);
                                    java.awt.Button okay = (java.awt.Button) button.get(dialog);
                                    if (!LegacyMacroModalState.ready(macroThread.getState(), macroThread.getStackTrace())) continue;
                                    recordDialog(output, name, "acknowledging-ready-modal", dialog, message, macroThread);
                                    acknowledged.add(candidate); guardDialogs.add(message);
                                    java.awt.EventQueue.invokeLater(() -> dialog.actionPerformed(new java.awt.event.ActionEvent(okay,
                                            java.awt.event.ActionEvent.ACTION_PERFORMED, okay.getLabel())));
                                } catch (Exception failure) { errors.add("Cannot observe expected guarded macro exit: " + failure); }
                            }
                        }
                        ProcessHandle.current().descendants().forEach(child -> child.info().commandLine().ifPresent(command -> {
                            if (command.contains("TemplateMatching.NativeAlignmentMain")) workers.put(child.pid(), command);
                        }));
                        try { Thread.sleep(5); } catch (InterruptedException end) { return; }
                    }
                }, "alignment-worker-observer"); observer.setDaemon(true); observer.start();
                String returned = null; String thrown = null;
                try { returned = IJ.runMacro(macro); }
                catch (Throwable failure) { thrown = failure.toString(); }
                finally { watching = false; observer.join(1000); }
                String errorMessage = IJ.getErrorMessage();
                String afterLog = IJ.getLog() == null ? "" : IJ.getLog();
                String logDelta = afterLog.startsWith(beforeLog) ? afterLog.substring(beforeLog.length()) : afterLog;
                TextWindow exceptionWindow = WindowManager.getWindow("Exception") instanceof TextWindow
                        ? (TextWindow) WindowManager.getWindow("Exception") : null;
                String exceptionText = exceptionWindow == null ? "" : exceptionWindow.getTextPanel().getText();
                row.put("observed_macro_error_dialogs", new ArrayList<>(dialogs));
                row.put("observed_macro_guard_dialogs", new ArrayList<>(guardDialogs));
                row.put("exception_window", exceptionText);
                row.put("exception_window_visible", exceptionWindow != null && exceptionWindow.isVisible());
                row.put("continuation_observed", logDelta.contains("GAT_ALIGNMENT_AFTER_BOUNDARY_" + name));
                if (exceptionWindow != null) exceptionWindow.close(false);
                row.put("macro_return", returned); row.put("macro_thrown", thrown); row.put("ij_error", errorMessage);
                row.put("errors", new ArrayList<>(errors)); row.put("log", logDelta);
                row.put("dispatched_commands", new ArrayList<>(dispatched)); row.put("worker_processes", new LinkedHashMap<>(workers));
                row.put("output", snapshot(input)); Files.write(output.resolve(name + "-aligned.f32be"), pixels(input));
                row.put("sentinel_unchanged", WindowManager.getImage(sentinel.getID()) == sentinel && sentinelBefore.equals(snapshot(sentinel)));
                if (!Boolean.TRUE.equals(row.get("sentinel_unchanged"))) throw new IllegalStateException("Unrelated image mutated");
                if (Collections.frequency(dispatched, "Align slices in stack...") != (nativeMode ? 0 : 1))
                    throw new IllegalStateException("Actual original menu execution count differs");
                if (rejected) {
                    String expectedMarker = "GAT_ALIGNMENT_AFTER_BOUNDARY_" + name;
                    String remainingLog = logDelta.replace(expectedMarker, "").trim().replaceAll("\\s+", " ");
                    boolean diagnosticMatches = nativeMode
                            ? guardDialogs.size() == 1 && guardDialogs.get(0).equals(NATIVE_GUARD_MESSAGE)
                                && dialogs.isEmpty() && exceptionText.isEmpty() && remainingLog.isEmpty()
                                && (errorMessage == null || errorMessage.isEmpty())
                            : dialogs.size() == 1 && dialogs.get(0).trim().replaceAll("\\s+", " ").startsWith(ORIGINAL_TYPE_ERROR + " in line ")
                                && guardDialogs.isEmpty() && remainingLog.isEmpty() && exceptionText.isEmpty()
                                && (errorMessage == null || errorMessage.isEmpty());
                    diagnosticMatches &= errors.isEmpty() && (thrown == null || thrown.equals("java.lang.RuntimeException: Macro canceled"));
                    row.put("unsupported_type_diagnostic", diagnosticMatches);
                    row.put("input_unchanged", row.get("input").equals(row.get("output")));
                    row.put("results_absent", WindowManager.getWindow("Results") == null);
                    if (!diagnosticMatches || !Boolean.TRUE.equals(row.get("input_unchanged"))
                            || !Boolean.TRUE.equals(row.get("results_absent")) || !workers.isEmpty())
                        throw new IllegalStateException("Unsupported 32-bit input was not cleanly rejected");
                    row.put("status", "PASS_UNSUPPORTED_TYPE_CONTROL");
                } else {
                    if (thrown != null || !guardDialogs.isEmpty() || !dialogs.isEmpty() || !exceptionText.isEmpty() || !Boolean.TRUE.equals(row.get("continuation_observed")) || "[aborted]".equals(returned) || !errors.isEmpty()
                            || errorMessage != null && !errorMessage.isEmpty()
                            || logDelta.matches("(?s).*(?i:exception|\\[error\\]|no such method|unsatisfiedlink).*"))
                        throw new IllegalStateException("Runtime/macro error during positive alignment case");
                    if (workers.size() != (nativeMode ? 1 : 0)) throw new IllegalStateException("Wrong native worker execution count");
                    if (!(WindowManager.getWindow("Results") instanceof TextWindow))
                        throw new IllegalStateException("Actual visible Results table missing");
                    TextWindow window = (TextWindow) WindowManager.getWindow("Results");
                    ResultsTable table = window.getTextPanel().getResultsTable();
                    row.put("headings", table.getHeadings()); row.put("rows", tableRows(table));
                    row.put("results_visible", window.isVisible());
                    table.saveAs(output.resolve(name + ".csv").toString());
                    ResultsTable reopened = ResultsTable.open(output.resolve(name + ".csv").toString());
                    if (table.size() != 3 || !tableRows(table).equals(tableRows(reopened)))
                        throw new IllegalStateException("Motion CSV roundtrip differs");
                    row.put("csv_roundtrip", true); row.put("csv_sha256", hash(Files.readAllBytes(output.resolve(name + ".csv"))));
                    row.put("status", "PASS_ALIGNMENT_CASE"); window.close(false);
                }
                checkpoint(output); input.changes = false; input.close();
            }
            report.put("status", "PASS_ALIGNMENT_BOUNDARY"); exit = 0;
        } catch (Throwable failure) {
            report.put("error", failure.toString()); failure.printStackTrace();
            report.put("status", cases.isEmpty() ? "BLOCKED_SETUP" : "FAIL_ALIGNMENT_BOUNDARY");
        } finally {
            watching = false; checkpoint(output);
            Files.writeString(output.resolve("imagej.log"), IJ.getLog() == null ? "" : IJ.getLog());
            if (imagej != null) imagej.dispose();
        }
        System.exit(exit);
    }

    static void recordDialog(Path output, String name, String phase, java.awt.Dialog dialog, String message, Thread caller) throws Exception {
        Map<String, Object> row = new LinkedHashMap<>();
        Thread.State state = caller.getState(); StackTraceElement[] trace = caller.getStackTrace();
        row.put("phase", phase); row.put("class", dialog.getClass().getName()); row.put("title", dialog.getTitle());
        row.put("message", message); row.put("visible", dialog.isVisible()); row.put("displayable", dialog.isDisplayable());
        row.put("caller_state", state.toString()); row.put("modal_ready", LegacyMacroModalState.ready(state, trace));
        List<String> frames = new ArrayList<>();
        for (StackTraceElement frame : trace) frames.add(frame.getClassName() + "." + frame.getMethodName());
        row.put("caller_stack", frames);
        Files.writeString(output.resolve(name + ".dialogs.jsonl"), new Gson().toJson(row) + "\n",
                java.nio.file.StandardOpenOption.CREATE, java.nio.file.StandardOpenOption.APPEND);
    }

    /** Observe the actual rendered diagnostic, not a replacement error handler. */
    static String dialogMessage(ij.gui.GenericDialog dialog) throws Exception {
        return componentText(dialog.getMessage());
    }
    static String componentText(java.awt.Component component) throws Exception {
        if (component instanceof java.awt.Label) return ((java.awt.Label) component).getText();
        if (component instanceof ij.gui.MultiLineLabel) {
            java.lang.reflect.Field lines = ij.gui.MultiLineLabel.class.getDeclaredField("lines");
            lines.setAccessible(true);
            return String.join("\n", (String[]) lines.get(component));
        }
        throw new IllegalStateException("Unexpected error-message widget: " + component);
    }

    static List<Object> tableRows(ResultsTable table) {
        List<Object> rows = new ArrayList<>();
        for (int r = 0; r < table.size(); r++) rows.add(Arrays.asList(table.getValue("Slice", r), table.getValue("dX", r), table.getValue("dY", r)));
        return rows;
    }
    @SuppressWarnings("unchecked")
    static ImagePlus synthetic(Map<String, Object> spec, Map<String, Object> schedule) {
        int w = integer(spec, "width"), h = integer(spec, "height"), bits = integer(spec, "bits");
        ImageProcessor base = bits == 8 ? new ByteProcessor(w, h) : bits == 16 ? new ShortProcessor(w, h) : new FloatProcessor(w, h);
        Random rng = new Random(integer(schedule, "seed"));
        for (int y = 10; y < h - 10; y++) for (int x = 10; x < w - 10; x++) {
            float value = rng.nextInt(bits == 8 ? 200 : 50000) + 1;
            base.setf(x, y, bits == 32 ? value * .37f - 17.25f : value);
        }
        ImageStack stack = new ImageStack(w, h); int number = 0;
        for (List<Number> shift : (List<List<Number>>) schedule.get("shifts")) {
            ImageProcessor frame = base.duplicate(); frame.translate(shift.get(0).intValue(), shift.get(1).intValue());
            stack.addSlice("synthetic-plane-" + (++number), frame);
        }
        ImagePlus result = new ImagePlus("synthetic", stack);
        result.setDisplayRange(bits == 8 ? 10 : 100, bits == 8 ? 180 : bits == 16 ? 42000 : 15000);
        return result;
    }
    static Map<String, Object> snapshot(ImagePlus image) throws Exception {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("pixels_f32be_sha256", hash(pixels(image))); result.put("dimensions", Arrays.stream(image.getDimensions()).boxed().collect(java.util.stream.Collectors.toList()));
        result.put("bit_depth", image.getBitDepth()); result.put("title", image.getTitle());
        result.put("display_range", Arrays.asList(image.getDisplayRangeMin(), image.getDisplayRangeMax()));
        result.put("position", Arrays.asList(image.getC(), image.getZ(), image.getT(), image.getCurrentSlice()));
        result.put("open_as_hyperstack", image.getOpenAsHyperStack());
        List<String> labels = new ArrayList<>();
        for (int z = 1; z <= image.getStackSize(); z++) labels.add(image.getStack().getSliceLabel(z));
        result.put("slice_labels", labels);
        result.put("template_roi", image.getRoi() == null ? null : Arrays.asList(image.getRoi().getBounds().x,
                image.getRoi().getBounds().y, image.getRoi().getBounds().width, image.getRoi().getBounds().height));
        result.put("calibration", Arrays.asList(image.getCalibration().pixelWidth, image.getCalibration().pixelHeight,
                image.getCalibration().pixelDepth, image.getCalibration().frameInterval, image.getCalibration().getUnit()));
        return result;
    }
    static byte[] pixels(ImagePlus image) throws Exception {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        try (DataOutputStream out = new DataOutputStream(bytes)) {
            for (int z = 1; z <= image.getStackSize(); z++) {
                ImageProcessor ip = image.getStack().getProcessor(z);
                for (int p = 0; p < ip.getPixelCount(); p++) out.writeFloat(ip.getf(p));
            }
        }
        return bytes.toByteArray();
    }
    static String hash(byte[] bytes) throws Exception { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes)); }
    static int integer(Map<String, Object> row, String key) { return ((Number) row.get(key)).intValue(); }
    static Map<String, String> provenance(Class<?> type) throws Exception {
        Map<String, String> result = new LinkedHashMap<>(); result.put("name", type.getName());
        result.put("code_source", type.getProtectionDomain().getCodeSource().getLocation().toString());
        try (java.io.InputStream in = type.getResourceAsStream("/" + type.getName().replace('.', '/') + ".class")) {
            result.put("sha256", hash(in.readAllBytes()));
        }
        return result;
    }
    static void checkpoint(Path output) throws Exception { Files.writeString(output.resolve("report.json"), JSON.toJson(report) + "\n"); }
}

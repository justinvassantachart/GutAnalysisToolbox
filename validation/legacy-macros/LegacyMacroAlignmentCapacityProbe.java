import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import ij.IJ;
import ij.ImagePlus;
import ij.ImageStack;
import ij.Menus;
import ij.WindowManager;
import ij.measure.ResultsTable;
import ij.process.ByteProcessor;
import ij.text.TextWindow;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.*;
import net.imagej.legacy.LegacyService;

/** Separate bounded original/native capacity experiment, never a broad parity pass.
 * Pixel validation and hashing stream one byte plane; no float-stack copy. */
public final class LegacyMacroAlignmentCapacityProbe {
    static { LegacyService.preinit(); }
    static final int W = 512, H = 512, N = 257, REF = 3;
    static final int[][] SHIFTS = {{0, 0}, {3, -2}, {-4, 5}, {0, 0}};
    static final Gson JSON = new GsonBuilder().serializeNulls().setPrettyPrinting().create();
    static final Map<String, Object> report = new LinkedHashMap<>();
    static final List<String> errors = Collections.synchronizedList(new ArrayList<>());
    static final List<String> commands = Collections.synchronizedList(new ArrayList<>());
    static volatile boolean observing;
    static final Map<Long, String> workers = Collections.synchronizedMap(new LinkedHashMap<>());

    @SuppressWarnings("unchecked")
    public static void main(String[] args) throws Exception {
        Map<String, Object> config = JSON.fromJson(Files.readString(Path.of(args[0])), Map.class);
        String variant = (String) config.getOrDefault("variant", "original");
        boolean nativeMode = variant.equals("native");
        if (!nativeMode && !variant.equals("original")) throw new IllegalArgumentException("Invalid variant");
        Path output = Path.of((String) config.get("output")); Files.createDirectory(output);
        report.put("schema_version", 1); report.put("scope", "original-alignment-capacity-counterexample");
        report.put("whole_calcium_macro_executed", false); report.put("native_executed", nativeMode); report.put("variant", variant);
        report.put("dimensions", Arrays.asList(W, H, N)); report.put("bit_depth", 8);
        report.put("total_pixels", (long) W * H * N); report.put("raw_pixel_bytes", (long) W * H * N); report.put("previous_native_total_pixel_cap", 67108864);
        report.put("seed", 8291); report.put("reference", REF); report.put("macro_source", config.get("macro_source"));
        report.put("status", "SETTING_UP"); checkpoint(output);
        net.imagej.ImageJ imagej = null; int exit = 2;
        try {
            if (java.awt.GraphicsEnvironment.isHeadless()) throw new IllegalStateException("Real AWT required");
            ClassLoader loader = LegacyMacroAlignmentCapacityProbe.class.getClassLoader();
            if ((loader.getResource("Features/Macros/LegacyTemplateMatching.class") != null) != nativeMode
                    || loader.getResource("TemplateMatching/NativeAlignmentMain.class") != null)
                throw new IllegalStateException("Original/native parent classpath isolation failed");
            if (nativeMode && !"native".equals(System.getProperty("gat.alignment.backend")))
                throw new IllegalStateException("Native backend must be explicitly forced");
            if (nativeMode) try (java.io.InputStream stream = Class.forName("Features.Macros.LegacyTemplateMatching")
                    .getResourceAsStream("/Features/Macros/LegacyTemplateMatching.class")) {
                report.put("adapter_class_sha256", hex(MessageDigest.getInstance("SHA-256").digest(stream.readAllBytes())));
            }
            IJ.setExceptionHandler(error -> errors.add(error.toString())); IJ.redirectErrorMessages(true);
            imagej = new net.imagej.ImageJ(); imagej.ui().showUI("legacy");
            if (!nativeMode && IJ.getClassLoader().getResource("Features/Macros/LegacyTemplateMatching.class") != null)
                throw new IllegalStateException("Original plugin loader contaminated by fork");
            Object command = Menus.getCommands().get("Align slices in stack...");
            if (command == null || !command.toString().contains("TemplateMatching.Align_slices"))
                throw new IllegalStateException("Pinned real original command is not installed");
            report.put("original_menu", command);
            Class<?> plugin = Class.forName("TemplateMatching.Align_slices");
            try (java.io.InputStream stream = plugin.getResourceAsStream("/TemplateMatching/Align_slices.class")) {
                report.put("plugin_class_sha256", hex(MessageDigest.getInstance("SHA-256").digest(stream.readAllBytes())));
            }
            ij.Executer.addCommandListener(value -> { commands.add(value); return value; });
            imagej.log().addLogListener(message -> {
                if (observing && message.level() <= org.scijava.log.LogService.ERROR) {
                    errors.add(message.text());
                    if (message.throwable() != null) errors.add(message.throwable().toString());
                }
            });
            byte[] base = new byte[W * H]; Random random = new Random(8291);
            for (int y = 10; y < H - 10; y++) for (int x = 10; x < W - 10; x++)
                base[y * W + x] = (byte) (1 + random.nextInt(200));
            ImageStack stack = new ImageStack(W, H);
            for (int z = 0; z < N; z++) stack.addSlice("capacity-plane-" + (z + 1), new ByteProcessor(W, H, inputPlane(base, z), null));
            ImagePlus input = new ImagePlus("capacity512x512x257", stack); input.setDisplayRange(10, 180);
            input.getCalibration().pixelWidth = .37; input.getCalibration().pixelHeight = .63;
            input.getCalibration().pixelDepth = 2.5; input.getCalibration().setUnit("um"); input.show();
            report.put("input_u8_sha256", digest(input));
            String macro = "selectWindow(\"capacity512x512x257\");\nsizeX=512;sizeY=512;\n"
                    + "x_size=floor(sizeX*0.7);\ny_size=floor(sizeY*0.7);\nx0=floor(sizeX/6);\ny0=floor(sizeY/6);\n"
                    + config.get("macro_line") + "\nprint(\"GAT_CAPACITY_AFTER_ALIGNMENT\");\n";
            Files.writeString(output.resolve("invoked.ijm"), macro);
            report.put("invoked_macro_sha256", hex(MessageDigest.getInstance("SHA-256").digest(macro.getBytes(java.nio.charset.StandardCharsets.UTF_8))));
            String before = IJ.getLog() == null ? "" : IJ.getLog(); errors.clear(); commands.clear(); IJ.getErrorMessage();
            report.put("status", "RUNNING"); checkpoint(output); observing = true;
            Thread observer = new Thread(() -> {
                while (observing) {
                    ProcessHandle.current().descendants().forEach(child -> child.info().commandLine().ifPresent(value -> {
                        if (value.contains("TemplateMatching.NativeAlignmentMain")) workers.put(child.pid(), value);
                    }));
                    try { Thread.sleep(5); } catch (InterruptedException stop) { return; }
                }
            }, "capacity-worker-observer"); observer.setDaemon(true); observer.start();
            String returned;
            try { returned = IJ.runMacro(macro); } finally { observing = false; observer.join(1000); }
            report.put("worker_processes", new LinkedHashMap<>(workers));
            String after = IJ.getLog() == null ? "" : IJ.getLog();
            String log = after.startsWith(before) ? after.substring(before.length()) : after;
            String error = IJ.getErrorMessage(); report.put("macro_return", returned); report.put("ij_error", error);
            report.put("errors", errors); report.put("commands", commands); report.put("log", log);
            if (!errors.isEmpty() || error != null && !error.isEmpty() || "[aborted]".equals(returned)
                    || !log.contains("GAT_CAPACITY_AFTER_ALIGNMENT")
                    || log.matches("(?s).*(?i:exception|\\[error\\]|no such method|unsatisfiedlink).*"))
                throw new IllegalStateException("Original macro errored or did not continue");
            if (Collections.frequency(commands, "Align slices in stack...") != (nativeMode ? 0 : 1) || workers.size() != (nativeMode ? 1 : 0))
                throw new IllegalStateException("Wrong original dispatch/native worker execution count");
            if (input.getStackSize() != N || input.getBitDepth() != 8 || input.getCurrentSlice() != REF
                    || input.getDisplayRangeMin() != 10 || input.getDisplayRangeMax() != 180
                    || input.getCalibration().pixelWidth != .37 || input.getCalibration().pixelHeight != .63
                    || input.getCalibration().pixelDepth != 2.5 || input.getRoi() == null
                    || !input.getRoi().getBounds().equals(new java.awt.Rectangle(85, 85, 358, 358)))
                throw new IllegalStateException("Original output metadata changed unexpectedly");
            long changed = 0;
            MessageDigest expected = MessageDigest.getInstance("SHA-256");
            for (int z = 0; z < N; z++) {
                byte[] source = inputPlane(base, z), actual = (byte[]) input.getStack().getPixels(z + 1);
                int dx = SHIFTS[REF - 1][0] - SHIFTS[z % SHIFTS.length][0];
                int dy = SHIFTS[REF - 1][1] - SHIFTS[z % SHIFTS.length][1];
                byte[] want = shifted(source, dx, dy); expected.update(want);
                for (int p = 0; p < actual.length; p++) if (actual[p] != want[p]) changed++;
                if (!input.getStack().getSliceLabel(z + 1).equals("capacity-plane-" + (z + 1)))
                    throw new IllegalStateException("Slice label changed");
            }
            report.put("output_u8_sha256", digest(input)); report.put("expected_output_u8_sha256", hex(expected.digest()));
            report.put("incorrect_pixels", changed);
            if (changed != 0) throw new IllegalStateException("Original pixels differ from independent integer-shift oracle");
            if (!(WindowManager.getWindow("Results") instanceof TextWindow)) throw new IllegalStateException("Real Results absent");
            TextWindow window = (TextWindow) WindowManager.getWindow("Results"); ResultsTable table = window.getTextPanel().getResultsTable();
            if (!window.isVisible() || table.size() != N - 1 || !Arrays.equals(table.getHeadings(), new String[]{"Slice", "dX", "dY"}))
                throw new IllegalStateException("Wrong real Results shape or visibility");
            List<List<Double>> rows = new ArrayList<>();
            for (int r = 0; r < N - 1; r++) {
                int slice = r < REF - 1 ? REF - 1 - r : r + 2;
                double dx = SHIFTS[REF - 1][0] - SHIFTS[(slice - 1) % SHIFTS.length][0];
                double dy = SHIFTS[REF - 1][1] - SHIFTS[(slice - 1) % SHIFTS.length][1];
                if (table.getValue("Slice", r) != slice || table.getValue("dX", r) != dx || table.getValue("dY", r) != dy)
                    throw new IllegalStateException("Wrong real motion value/traversal row " + r);
                rows.add(Arrays.asList((double) slice, dx, dy));
            }
            Path csv = output.resolve("motion.csv"); table.saveAs(csv.toString()); ResultsTable reopened = ResultsTable.open(csv.toString());
            if (reopened.size() != rows.size()) throw new IllegalStateException("CSV row count changed");
            for (int r = 0; r < rows.size(); r++) for (int c = 0; c < 3; c++)
                if (reopened.getValue(new String[]{"Slice", "dX", "dY"}[c], r) != rows.get(r).get(c))
                    throw new IllegalStateException("CSV roundtrip mismatch");
            report.put("rows", rows); report.put("csv_roundtrip", true);
            report.put("status", nativeMode ? "PASS_NATIVE_CAPACITY_CONTROL" : "PASS_ORIGINAL_CAPACITY_COUNTEREXAMPLE"); exit = 0;
        } catch (Throwable failure) {
            report.put("status", "INCONCLUSIVE_OR_FAILED_CAPACITY"); report.put("error", failure.toString()); failure.printStackTrace();
        } finally {
            observing = false; checkpoint(output); if (imagej != null) imagej.dispose();
        }
        System.exit(exit);
    }
    static byte[] inputPlane(byte[] base, int z) { int[] shift = SHIFTS[z % SHIFTS.length]; return shifted(base, shift[0], shift[1]); }
    static byte[] shifted(byte[] source, int dx, int dy) {
        byte[] output = new byte[W * H];
        for (int y = 0; y < H; y++) for (int x = 0; x < W; x++) {
            int sx = x - dx, sy = y - dy;
            if (sx >= 0 && sx < W && sy >= 0 && sy < H) output[y * W + x] = source[sy * W + sx];
        }
        return output;
    }
    static String digest(ImagePlus image) throws Exception {
        MessageDigest hash = MessageDigest.getInstance("SHA-256");
        for (int z = 1; z <= N; z++) hash.update((byte[]) image.getStack().getPixels(z));
        return hex(hash.digest());
    }
    static String hex(byte[] bytes) { return HexFormat.of().formatHex(bytes); }
    static void checkpoint(Path path) throws Exception { Files.writeString(path.resolve("report.json"), JSON.toJson(report) + "\n"); }
}

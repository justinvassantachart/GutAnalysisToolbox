import ij.*;
import ij.gui.Roi;
import ij.io.FileSaver;
import ij.io.Opener;
import ij.io.RoiDecoder;
import ij.macro.Interpreter;
import ij.measure.Calibration;
import ij.process.ByteProcessor;
import ij.process.FloatPolygon;
import ij.process.ImageProcessor;
import services.multiplex.config.MultiplexConfig;
import services.multiplex.core.MultiplexRegistrationService;

import java.awt.*;
import java.awt.event.ActionEvent;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import java.util.List;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;
import javax.swing.*;

/** Acceptance probe of the unmodified full GAT service. Only synthetic files in an isolated JVM. */
public final class MultiplexFullProbe {
    private static final int W = 256, H = 256;
    private static final int[][] SHIFTS = {{0, 0}, {7, -5}, {-6, 8}};
    private static Path out, inputs, results;
    private static WorkflowReport report;
    private static final Map<String, String> inputHashes = new LinkedHashMap<>();
    private static final Map<String, String> exportsBeforeCancel = new LinkedHashMap<>();
    private static final Map<String, ImageProcessor> expected = new LinkedHashMap<>();
    private static final List<String> commands = Collections.synchronizedList(new ArrayList<>());
    private static final Set<Window> answered = Collections.newSetFromMap(new IdentityHashMap<Window, Boolean>());
    private static final Set<Window> unexpected = Collections.newSetFromMap(new IdentityHashMap<Window, Boolean>());
    private static final Map<Window, Integer> activeTicks = new IdentityHashMap<>();
    private static volatile boolean cancelledOpenResults, acknowledgedDone;
    private static Calibration inputCalibration;
    private static javax.swing.Timer controller;

    public static void main(String[] args) throws Exception {
        Locale.setDefault(Locale.US);
        out = Paths.get(args[0]).toAbsolutePath();
        String mode = args[1];
        Files.createDirectories(out);
        inputs = Files.createDirectories(out.resolve("inputs"));
        results = out.resolve("output/Results");
        report = new WorkflowReport("multiplex-full-" + mode, out, "report.json");
        phase("initialization");
        if ("controls".equals(mode)) {
            fixtureControls();
            existingResultsControl();
            dialogMatchingControls();
            report.notRun("complete_workflow", "MultiplexRegistrationService.run including registration/export", "Headless controls are not a full-service runtime pass");
            finish(); return;
        }
        if (!initializeImageJ()) { finish(); return; }
        if ("display-probe".equals(mode)) {
            checkpointedTest("awt_display", "ImageJ application and actual AWT display initialization", "AWT", () -> {
                Dimension size = Toolkit.getDefaultToolkit().getScreenSize();
                WorkflowReport.check(size.width > 0 && size.height > 0, "Invalid screen size");
                return WorkflowReport.values("screen_width", size.width, "screen_height", size.height);
            });
            finish(); return;
        }
        if ("no-files".equals(mode) || "missing-marker".equals(mode)) {
            if ("missing-marker".equals(mode)) {
                save(new ImagePlus("Layer1_MarkerA", independentPattern(1, 0)), inputs.resolve("Layer1_MarkerA.tif"));
                inputHashes.put("Layer1_MarkerA.tif", hash(inputs.resolve("Layer1_MarkerA.tif")));
            }
            earlyFailure(mode);
            finish(); return;
        }
        createFixture();
        if ("missing-round".equals(mode)) {
            Files.delete(inputs.resolve("Layer3_Hu.tif"));
            inputHashes.remove("Layer3_Hu.tif");
            lateFailure();
            finish(); return;
        }
        WorkflowReport.check("full-sift".equals(mode) || "full-mops".equals(mode), "Unknown mode: " + mode);
        installSuccessDialogController();
        int steps = "full-mops".equals(mode) ? 31 : 3;
        phase("service_run");
        checkpointedTest("service_return", "Actual MultiplexRegistrationService.run; unchanged production classes", "SIFT/MOPS then Landmark Correspondences affine", () -> {
            new MultiplexRegistrationService(config(steps)).run();
            return WorkflowReport.values("steps_per_scale_octave", steps, "rounds", 3, "input_files", 9);
        });
        report.write();
        phase("output_assertions");
        validateOutput(mode);
        report.notRun("computation_cancellation", "Interrupted computation / cancel button", "The existing service and pane expose no computation cancellation contract; the final open-results Cancel is checked separately");
        report.notRun("block_matching_fallback", "Extract Block Matching Correspondences", "No command with this name exists in the pinned mpicbg plugins.config; no substitute is registered");
        finish();
    }

    @SuppressWarnings({"unchecked", "rawtypes"})
    private static boolean initializeImageJ() throws Exception {
        phase("display_setup");
        try {
            if (GraphicsEnvironment.isHeadless()) throw new HeadlessException("No working AWT display");
            Toolkit.getDefaultToolkit().getScreenSize();
            ImageJ app = new ImageJ(ImageJ.NO_SHOW);
            app.exitWhenQuitting(false);
            // Exact official mappings; runner verifies them against the pinned plugins.config.
            Map map = Menus.getCommands();
            map.put("Extract SIFT Correspondences", "SIFT_ExtractPointRoi");
            map.put("Extract MOPS Correspondences", "MOPS_ExtractPointRoi");
            map.put("Landmark Correspondences", "Transform_Roi");
            for (String name : new String[]{"SIFT_ExtractPointRoi", "MOPS_ExtractPointRoi", "Transform_Roi", "mpicbg.ij.SIFT", "Jama.Matrix"}) Class.forName(name);
            Executer.addCommandListener(command -> { commands.add(command); System.out.println("REAL_COMMAND " + command); return command; });
            return true;
        } catch (Throwable e) {
            report.blocked("display_setup", "AWT/ImageJ startup, before any full-service invocation", e.toString());
            phase("blocked_setup");
            return false;
        }
    }

    private static MultiplexConfig config(int steps) throws Exception {
        Files.createDirectories(out.resolve("output"));
        return new MultiplexConfig.Builder().imageFolder(inputs.toFile()).saveFolder(out.resolve("output").toFile())
                .commonMarker("Hu").layerKeyword("Layer").multiplexRounds(3)
                .fineTuneParams(true).minimalInlierRatio(0.5).stepsPerScaleOctave(steps).build();
    }

    private static void fixtureControls() throws Exception {
        createFixture();
        checkpointedTest("fixture_roundtrip", "Synthetic inputs only; no registration invocation", "ImageJ TIFF save/reopen", () -> {
            for (String name : inputHashes.keySet()) {
                ImagePlus image = open(inputs.resolve(name));
                WorkflowReport.check(image.getWidth() == W && image.getHeight() == H && image.getBitDepth() == 8 && image.getStackSize() == 1, "Wrong fixture dimensions: " + name);
                requireCalibration(image);
            }
            return WorkflowReport.values("files", inputHashes.size(), "width", W, "height", H, "bit_depth", 8, "hashes", inputHashes);
        });
        checkpointedTest("alignment_detector_negative_controls", "Acceptance comparator itself, not a production workflow", "Correct, unchanged, inverse and wrong-channel synthetic controls", () -> {
            ImageProcessor reference = expected.get("Layer2_MarkerA.tif");
            ImageProcessor shifted = open(inputs.resolve("Layer2_MarkerA.tif")).getProcessor();
            double before = mse(reference, shifted);
            WorkflowReport.check(before > 100, "Fixture too weak");
            WorkflowReport.check(mse(reference, reference) == 0, "Comparator identity failed");
            WorkflowReport.check(!aligned(before, mse(reference, shifted)), "Unchanged source falsely passed");
            WorkflowReport.check(!aligned(before, mse(reference, translated(shifted, 7, -5))), "Inverse transform falsely passed");
            WorkflowReport.check(!aligned(before, mse(reference, pattern())), "Copied common-marker channel falsely passed");
            WorkflowReport.check(aligned(before, mse(reference, translated(shifted, -7, 5))), "Known correct transform failed");
            return WorkflowReport.values("initial_mse", before, "identity_mse", 0, "negative_controls", 3);
        });
    }

    private static void existingResultsControl() throws Exception {
        Files.createDirectories(results);
        Path sentinel = results.resolve("owner-sentinel.txt");
        Files.write(sentinel, "must remain unchanged\n".getBytes(StandardCharsets.UTF_8));
        final String before = hash(sentinel);
        checkpointedTest("existing_results_refused", "Actual service early overwrite guard, reached without AWT", "MultiplexRegistrationService.run", () -> {
            boolean prior = Interpreter.batchMode;
            try {
                new MultiplexRegistrationService(config(3)).run();
                throw new AssertionError("Existing Results was not refused");
            } catch (IllegalStateException expectedFailure) {
                WorkflowReport.check(expectedFailure.getMessage().contains("Remove Results folder"), "Wrong failure: " + expectedFailure);
            }
            WorkflowReport.check(Interpreter.batchMode == prior, "Batch flag not restored after overwrite refusal");
            WorkflowReport.check(hash(sentinel).equals(before), "Existing owner data changed");
            try (java.util.stream.Stream<Path> files = Files.list(results)) { WorkflowReport.check(files.count() == 1, "Overwrite refusal wrote extra output"); }
            return WorkflowReport.values("sentinel_preserved", true, "batch_mode_restored", true, "complete_workflow_executed", false);
        });
    }

    private static void earlyFailure(String mode) throws Exception {
        phase("service_run");
        checkpointedTest("expected_input_failure", "Actual service no-files / missing-common failure and output handling", "MultiplexRegistrationService.run", () -> {
            boolean prior = Interpreter.batchMode;
            try { new MultiplexRegistrationService(config(3)).run(); throw new AssertionError("Expected input failure did not occur"); }
            catch (IllegalArgumentException e) {
                String wanted = "no-files".equals(mode) ? "No .tif files" : "No files matching common marker";
                WorkflowReport.check(e.getMessage().contains(wanted), "Wrong failure: " + e);
            }
            WorkflowReport.check(Interpreter.batchMode == prior, "Failure did not restore batch mode");
            WorkflowReport.check(Files.isDirectory(results), "Expected Results directory is missing");
            try (java.util.stream.Stream<Path> files = Files.list(results)) { WorkflowReport.check(files.count() == 0, "Invalid inputs emitted output artifacts"); }
            requireSourcesUnchanged();
            return WorkflowReport.values("results_directory_left_empty", true, "retry_requires_removing_empty_results", true, "success_artifacts_written", false, "batch_mode_restored", true, "source_files_unchanged", true);
        });
    }

    private static void lateFailure() throws Exception {
        phase("service_run");
        checkpointedTest("missing_round_failure", "Real service after one landmark pair, no round-3 common marker", "MultiplexRegistrationService.run", () -> {
            boolean prior = Interpreter.batchMode;
            try { new MultiplexRegistrationService(config(3)).run(); throw new AssertionError("Missing round-3 landmarks were silently accepted"); }
            catch (IllegalStateException e) { WorkflowReport.check(e.getMessage().contains("ROI correspondences missing for round 3"), "Wrong failure: " + e); }
            WorkflowReport.check(Interpreter.batchMode == prior, "Failure did not restore batch mode");
            WorkflowReport.check(!Files.exists(results.resolve("Aligned_Stack.tif")) && !Files.exists(results.resolve("landmark_correspondences.zip")), "Failure emitted final success artifacts");
            requireSourcesUnchanged();
            return WorkflowReport.values("partial_common_qc_exists", Files.exists(results.resolve("hu_stack.tif")), "aligned_and_roi_exports_absent", true, "source_files_unchanged", true, "batch_mode_restored", true);
        });
    }

    private static void validateOutput(String mode) throws Exception {
        checkpointedTest("saved_dimensions_and_labels", "Saved and reopened Aligned_Stack, every emitted channel", "ImageJ TIFF hyperstack", () -> {
            ImagePlus image = open(results.resolve("Aligned_Stack.tif"));
            WorkflowReport.check(image.getWidth() == W && image.getHeight() == H && image.getBitDepth() == 8 && image.getNChannels() == 7 && image.getNSlices() == 1 && image.getNFrames() == 1, "Wrong final dimensions: " + Arrays.toString(image.getDimensions()));
            int plane = 1;
            for (String name : expected.keySet()) { WorkflowReport.check(name.equals(image.getStack().getSliceLabel(plane++)), "Wrong or missing slice label for " + name); }
            return WorkflowReport.values("width", W, "height", H, "channels", 7, "slices", 1, "frames", 1, "bit_depth", 8, "labels", expected.keySet());
        });
        checkpointedTest("every_round_and_channel_transform", "Independent expected pixels, including round 1 and both later-round marker channels", "Affine translation direction / channel propagation", () -> {
            ImagePlus image = open(results.resolve("Aligned_Stack.tif"));
            WorkflowReport.check(image.getStackSize() == expected.size(), "Wrong channel count");
            List<Map<String, Object>> metrics = new ArrayList<>();
            int plane = 1;
            for (Map.Entry<String, ImageProcessor> entry : expected.entrySet()) {
                String name = entry.getKey();
                ImageProcessor actual = image.getStack().getProcessor(plane++);
                double before = mse(entry.getValue(), open(inputs.resolve(name)).getProcessor());
                double after = mse(entry.getValue(), actual);
                metrics.add(WorkflowReport.values("source_file", name, "before_mse", before, "after_mse", after));
                System.out.println("CHANNEL_METRIC " + WorkflowReport.json(metrics.get(metrics.size() - 1)));
                if (name.startsWith("Layer1_")) WorkflowReport.check(fullMse(entry.getValue(), actual) == 0, "Round-1 pixels changed: " + name);
                else WorkflowReport.check(before > 100 && aligned(before, after), "Wrong/missing transform for " + name + ": before=" + before + ", after=" + after);
            }
            return WorkflowReport.values("channels", metrics, "roi_alignment_margin", 24, "required_mse_reduction", 0.85);
        });
        checkpointedTest("saved_calibration", "Reopened output compared with reopened input TIFF, including rational resolution rounding", "Spatial and temporal metadata preservation", () -> {
            ImagePlus aligned = open(results.resolve("Aligned_Stack.tif"));
            ImagePlus common = open(results.resolve("hu_stack.tif"));
            System.out.println("CALIBRATION_INPUT " + calibration(inputCalibration));
            System.out.println("CALIBRATION_ALIGNED " + calibration(aligned.getCalibration()));
            System.out.println("CALIBRATION_COMMON " + calibration(common.getCalibration()));
            requireCalibration(aligned); requireCalibration(common);
            return WorkflowReport.values("input", calibration(inputCalibration), "aligned", calibration(aligned.getCalibration()), "common", calibration(common.getCalibration()));
        });
        checkpointedTest("common_marker_qc", "Every saved common-marker round remains unwarped for QC", "Saved/reopened hu_stack", () -> {
            ImagePlus common = open(results.resolve("hu_stack.tif"));
            WorkflowReport.check(common.getWidth() == W && common.getHeight() == H && common.getStackSize() == 3, "Wrong common stack shape");
            for (int round = 1; round <= 3; round++) {
                String name = "Layer" + round + "_Hu.tif";
                WorkflowReport.check(name.equals(common.getStack().getSliceLabel(round)), "Wrong common stack label");
                WorkflowReport.check(fullMse(open(inputs.resolve(name)).getProcessor(), common.getStack().getProcessor(round)) == 0, "QC pixels changed: " + name);
            }
            return WorkflowReport.values("rounds", 3, "common_marker_later_rounds_in_final_stack", false, "existing_output_contract", "Final output contains reference Hu plus six non-common channels; later Hu images are in unwarped QC stack");
        });
        checkpointedTest("landmark_zip_roundtrip", "Persisted ZIP decoded independently of the live ROI Manager", "ROI pair order, names, point count and known displacement", () -> {
            List<Map<String, Object>> metrics = new ArrayList<>();
            try (ZipFile zip = new ZipFile(results.resolve("landmark_correspondences.zip").toFile())) {
                WorkflowReport.check(zip.size() == 4, "Wrong ZIP entry count: " + zip.size());
                for (int pair = 1; pair <= 2; pair++) {
                    Roi a = readRoi(zip, "hu_" + pair + "_ref.roi"), b = readRoi(zip, "hu_" + pair + "_target.roi");
                    WorkflowReport.check(a.getType() == Roi.POINT && b.getType() == Roi.POINT, "Non-point correspondence");
                    FloatPolygon x = a.getFloatPolygon(), y = b.getFloatPolygon();
                    WorkflowReport.check(x.npoints >= 7 && x.npoints == y.npoints, "Insufficient/unequal point counts");
                    double error = 0;
                    for (int i = 0; i < x.npoints; i++) error += Math.hypot(y.xpoints[i] - x.xpoints[i] - SHIFTS[pair][0], y.ypoints[i] - x.ypoints[i] - SHIFTS[pair][1]);
                    error /= x.npoints;
                    WorkflowReport.check(error < 1, "Wrong landmark direction/order for pair " + pair + ": error=" + error);
                    metrics.add(WorkflowReport.values("pair", pair, "point_count", x.npoints, "mean_translation_error_px", error, "dx", SHIFTS[pair][0], "dy", SHIFTS[pair][1]));
                }
            }
            return WorkflowReport.values("pairs", metrics);
        });
        checkpointedTest("source_files_preserved", "SHA-256 of all nine original inputs before/after service", "Source immutability", () -> { requireSourcesUnchanged(); return WorkflowReport.values("hashes", inputHashes); });
        checkpointedTest("real_command_route", "Observed command listener, never replaces or intercepts a command", "Plugin route", () -> {
            long sift = countCommand("Extract SIFT Correspondences"), mops = countCommand("Extract MOPS Correspondences"), warp = countCommand("Landmark Correspondences");
            WorkflowReport.check(warp == 4, "Expected four later-round channel warps, got " + warp);
            if ("full-mops".equals(mode)) WorkflowReport.check(sift == 0 && mops == 2, "Did not reach intended MOPS fallback route");
            else WorkflowReport.check(sift >= 2 && mops == 0, "Fixture did not take the intended first-choice SIFT path");
            return WorkflowReport.values("sift_calls", sift, "mops_calls", mops, "landmark_warps", warp);
        });
        long dialogDeadline = System.currentTimeMillis() + 5000;
        while ((!cancelledOpenResults || !acknowledgedDone) && System.currentTimeMillis() < dialogDeadline) Thread.sleep(100);
        SwingUtilities.invokeAndWait(() -> {});
        if (!cancelledOpenResults || !acknowledgedDone) {
            report.blocked("final_dialog_cancel_preserves_results", "Test-owned final dialog controller",
                    "Harness did not observe both responses; this does not establish an algorithm failure. Open-results Cancel=" + cancelledOpenResults + ", Done OK=" + acknowledgedDone);
            return;
        }
        checkpointedTest("final_dialog_cancel_preserves_results", "Cancel only the test-owned open-results dialog after successful export", "Actual final Cancel button, no computation-cancellation claim", () -> {
            WorkflowReport.check(!Interpreter.batchMode, "Batch mode not restored after final prompts");
            WorkflowReport.check(Files.isRegularFile(results.resolve("Aligned_Stack.tif")) && Files.isRegularFile(results.resolve("landmark_correspondences.zip")), "Cancel removed saved results");
            WorkflowReport.check(exportsBeforeCancel.size() == 3, "No complete pre-Cancel output hash snapshot");
            for (Map.Entry<String, String> entry : exportsBeforeCancel.entrySet()) WorkflowReport.check(entry.getValue().equals(hash(results.resolve(entry.getKey()))), "Final Cancel changed output bytes: " + entry.getKey());
            return WorkflowReport.values("open_results_response", "Cancel", "done_response", "OK", "batch_mode_restored", true, "computation_cancel_tested", false, "output_hashes_unchanged", exportsBeforeCancel);
        });
    }

    private static void createFixture() throws Exception {
        ByteProcessor common = pattern();
        for (int round = 1; round <= 3; round++) {
            for (int marker = 0; marker < 3; marker++) {
                String name = "Layer" + round + "_" + (marker == 0 ? "Hu" : marker == 1 ? "MarkerA" : "MarkerB") + ".tif";
                ImageProcessor base = marker == 0 ? common : independentPattern(round, marker);
                ImagePlus image = new ImagePlus(name, translated(base, SHIFTS[round - 1][0], SHIFTS[round - 1][1]));
                Calibration cal = image.getCalibration(); cal.pixelWidth = 0.5; cal.pixelHeight = 0.75; cal.pixelDepth = 2.0; cal.frameInterval = 1.25; cal.setUnit("um");
                save(image, inputs.resolve(name));
                inputHashes.put(name, hash(inputs.resolve(name)));
                if (round == 1 || marker != 0) expected.put(name, base.duplicate());
            }
        }
        inputCalibration = open(inputs.resolve("Layer1_Hu.tif")).getCalibration().copy();
        Files.write(out.resolve("fixture-manifest.json"), (WorkflowReport.json(WorkflowReport.values("pattern_seed", 17012026L, "round_shifts", SHIFTS, "input_sha256", inputHashes, "final_labels", expected.keySet(), "calibration", calibration(inputCalibration))) + "\n").getBytes(StandardCharsets.UTF_8));
    }

    // Exact common-marker generator from RegistrationMorphologySmoke.java, pinned in provenance.json.
    private static ByteProcessor pattern() {
        ByteProcessor p = new ByteProcessor(W, H);
        Random random = new Random(17012026L);
        for (int i=0; i<85; i++) {
            int x=25+random.nextInt(W-50), y=25+random.nextInt(H-50);
            int w=3+random.nextInt(13), h=3+random.nextInt(13), value=55+random.nextInt(200);
            rectangle(p, x, y, w, h, value);
            if (i % 3 == 0) rectangle(p, x, y, 2, h+6, Math.max(1,value-35));
        }
        p.blurGaussian(0.8);
        return p;
    }

    private static ByteProcessor independentPattern(int round, int marker) {
        ByteProcessor p = new ByteProcessor(W, H);
        Random random = new Random(29092026L + 101 * round + 13 * marker);
        for (int i = 0; i < 60; i++) {
            int x = 28 + random.nextInt(W - 70), y = 28 + random.nextInt(H - 70);
            rectangle(p, x, y, 4 + random.nextInt(15), 3 + random.nextInt(11), 40 + random.nextInt(210));
        }
        p.blurGaussian(0.8);
        return p;
    }

    private static void rectangle(ImageProcessor p, int x, int y, int w, int h, int v) {
        for (int yy=y; yy<y+h; yy++) for (int xx=x; xx<x+w; xx++) p.set(xx, yy, v);
    }
    private static ByteProcessor translated(ImageProcessor p, int dx, int dy) {
        ByteProcessor moved = new ByteProcessor(p.getWidth(), p.getHeight());
        for (int y=0; y<p.getHeight(); y++) for (int x=0; x<p.getWidth(); x++) {
            int sx=x-dx, sy=y-dy;
            if (sx>=0 && sx<p.getWidth() && sy>=0 && sy<p.getHeight()) moved.set(x,y,p.get(sx,sy));
        }
        return moved;
    }
    private static double mse(ImageProcessor a, ImageProcessor b) { return mse(a, b, 24); }
    private static double fullMse(ImageProcessor a, ImageProcessor b) { return mse(a, b, 0); }
    private static double mse(ImageProcessor a, ImageProcessor b, int margin) {
        WorkflowReport.check(a.getWidth() == b.getWidth() && a.getHeight() == b.getHeight(), "MSE dimensions differ");
        double sum = 0; int n = 0;
        for (int y = margin; y < H - margin; y++) for (int x = margin; x < W - margin; x++) { double d = a.getf(x, y) - b.getf(x, y); sum += d * d; n++; }
        return sum / n;
    }
    private static boolean aligned(double before, double after) { return Double.isFinite(after) && after < before * 0.15; }
    private static void save(ImagePlus image, Path path) { WorkflowReport.check(new FileSaver(image).saveAsTiff(path.toString()), "Cannot save fixture: " + path); }
    private static ImagePlus open(Path path) {
        WorkflowReport.check(Files.isRegularFile(path), "Missing TIFF: " + path);
        ImagePlus image = new Opener().openImage(path.toString()); WorkflowReport.check(image != null, "Cannot reopen TIFF: " + path); return image;
    }
    private static String hash(Path path) throws Exception {
        byte[] bytes = MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(path)); StringBuilder hex = new StringBuilder();
        for (byte b : bytes) hex.append(String.format("%02x", b & 255)); return hex.toString();
    }
    private static void requireSourcesUnchanged() throws Exception {
        for (Map.Entry<String, String> entry : inputHashes.entrySet()) WorkflowReport.check(entry.getValue().equals(hash(inputs.resolve(entry.getKey()))), "Source modified: " + entry.getKey());
    }
    private static Map<String, Object> calibration(Calibration c) { return WorkflowReport.values("pixel_width", c.pixelWidth, "pixel_height", c.pixelHeight, "pixel_depth", c.pixelDepth, "frame_interval", c.frameInterval, "unit", c.getUnit()); }
    private static void requireCalibration(ImagePlus image) { WorkflowReport.check(calibration(inputCalibration).equals(calibration(image.getCalibration())), "Calibration lost on " + image.getTitle() + ": expected=" + calibration(inputCalibration) + ", actual=" + calibration(image.getCalibration())); }
    private static long countCommand(String name) { synchronized (commands) { return commands.stream().filter(name::equals).count(); } }
    private static Roi readRoi(ZipFile zip, String name) throws Exception {
        ZipEntry entry = zip.getEntry(name); WorkflowReport.check(entry != null, "Missing ROI: " + name);
        try (java.io.InputStream in = zip.getInputStream(entry)) { Roi roi = new RoiDecoder(in.readAllBytes(), name).getRoi(); WorkflowReport.check(roi != null, "Cannot decode ROI: " + name); return roi; }
    }
    private static void checkpointedTest(String id, String scope, String algorithm, WorkflowReport.CheckedAction action) throws Exception {
        report.test(id, scope, algorithm, action);
        report.write(); // Preserve reached evidence before any subsequent GUI/file operation can block.
    }
    private static void phase(String name) throws Exception { Files.write(out.resolve("phase.json"), (WorkflowReport.json(WorkflowReport.values("phase", name, "time_utc", java.time.Instant.now().toString())) + "\n").getBytes(StandardCharsets.UTF_8)); }

    private static void visit(Component component, List<Component> all) { all.add(component); if (component instanceof Container) for (Component child : ((Container) component).getComponents()) visit(child, all); }
    private static String expectedOpenResultsMessage() {
        return "<html><b>Multiplex Registration finished.</b><br/>Results saved in:<br/>" + results + "</html>";
    }
    private static JOptionPane matchingOpenResultsPane(List<Component> all) {
        JOptionPane pane = null;
        for (Component component : all) if (component instanceof JOptionPane) {
            if (pane != null) return null; // Never pick one among multiple competing panes.
            pane = (JOptionPane) component;
        }
        if (pane == null || pane.getMessageType() != JOptionPane.INFORMATION_MESSAGE || pane.getOptionType() != JOptionPane.OK_CANCEL_OPTION) return null;
        int exactMessages = 0;
        for (Component component : all) if (component instanceof JLabel && SwingUtilities.isDescendingFrom(component, pane)
                && expectedOpenResultsMessage().equals(((JLabel) component).getText())) exactMessages++;
        return exactMessages == 1 ? pane : null;
    }
    private static List<Component> promptComponents(String message, int type, int options) {
        JPanel panel = new JPanel(); panel.add(new JLabel(message));
        JOptionPane pane = new JOptionPane(panel, type, options);
        List<Component> all = new ArrayList<>(); visit(pane, all); return all;
    }
    private static void dialogMatchingControls() throws Exception {
        checkpointedTest("dialog_controller_contract", "Lightweight Swing prompt matcher only; no dialog click or service success inferred", "Exact upstream success text / pane type / option contract", () -> {
            String message = expectedOpenResultsMessage();
            WorkflowReport.check(matchingOpenResultsPane(promptComponents(message, JOptionPane.INFORMATION_MESSAGE, JOptionPane.OK_CANCEL_OPTION)) != null, "Exact intended prompt rejected");
            WorkflowReport.check(matchingOpenResultsPane(promptComponents("Unexpected prefix: " + message, JOptionPane.INFORMATION_MESSAGE, JOptionPane.OK_CANCEL_OPTION)) == null, "Near-message prefix accepted");
            WorkflowReport.check(matchingOpenResultsPane(promptComponents(message.replace(results.toString(), results + "-other"), JOptionPane.INFORMATION_MESSAGE, JOptionPane.OK_CANCEL_OPTION)) == null, "Similar but wrong output path accepted");
            WorkflowReport.check(matchingOpenResultsPane(promptComponents(message, JOptionPane.ERROR_MESSAGE, JOptionPane.OK_CANCEL_OPTION)) == null, "Error-type prompt accepted");
            WorkflowReport.check(matchingOpenResultsPane(promptComponents(message, JOptionPane.INFORMATION_MESSAGE, JOptionPane.YES_NO_OPTION)) == null, "Different option configuration accepted");
            List<Component> multiple = promptComponents(message, JOptionPane.INFORMATION_MESSAGE, JOptionPane.OK_CANCEL_OPTION);
            multiple.add(new JOptionPane("unrelated", JOptionPane.INFORMATION_MESSAGE, JOptionPane.OK_CANCEL_OPTION));
            WorkflowReport.check(matchingOpenResultsPane(multiple) == null, "Competing second pane accepted");
            return WorkflowReport.values("exact_message_positive_control", true, "negative_controls", 5, "dialog_action_executed", false);
        });
    }
    private static void installSuccessDialogController() {
        controller = new javax.swing.Timer(150, event -> {
            for (Window window : Window.getWindows()) {
                if (!(window instanceof Dialog) || !window.isShowing() || answered.contains(window)) continue;
                Dialog dialog = (Dialog) window;
                boolean openPrompt = "Open results?".equals(dialog.getTitle());
                boolean donePrompt = "Multiplex Registration".equals(dialog.getTitle()) && dialog instanceof ij.gui.MessageDialog;
                if (!openPrompt && !donePrompt) {
                    if (unexpected.add(window)) System.out.println("DIALOG_UNHANDLED title=" + dialog.getTitle() + "; no automatic response");
                    continue;
                }
                if (!dialog.isActive() || !dialog.isModal()) { activeTicks.remove(window); continue; }
                int ticks = activeTicks.getOrDefault(window, 0) + 1; activeTicks.put(window, ticks); if (ticks < 2) continue;
                // Never answer a similarly titled error: all three expected outputs must already exist.
                if (!Files.isRegularFile(results.resolve("Aligned_Stack.tif")) || !Files.isRegularFile(results.resolve("hu_stack.tif")) || !Files.isRegularFile(results.resolve("landmark_correspondences.zip"))) continue;
                List<Component> all = new ArrayList<>(); visit(window, all);
                if (openPrompt) {
                    JButton cancel = null;
                    JOptionPane pane = matchingOpenResultsPane(all);
                    if (pane == null) continue;
                    for (Component c : all) {
                        if (c instanceof JButton && SwingUtilities.isDescendingFrom(c, pane) && c.isShowing() && c.isEnabled() && "Cancel".equals(((JButton) c).getText())) cancel = (JButton) c;
                    }
                    if (cancel == null) continue;
                    try {
                        for (String filename : new String[]{"Aligned_Stack.tif", "hu_stack.tif", "landmark_correspondences.zip"}) exportsBeforeCancel.put(filename, hash(results.resolve(filename)));
                    } catch (Exception error) {
                        if (unexpected.add(window)) System.out.println("DIALOG_UNHANDLED title=Open results? output hash failure=" + error);
                        continue;
                    }
                    answered.add(window); System.out.println("DIALOG_CLICK title=Open results? button=Cancel path=" + results);
                    cancel.doClick(); cancelledOpenResults = Integer.valueOf(JOptionPane.CANCEL_OPTION).equals(pane.getValue());
                    System.out.println("DIALOG_VALUE title=Open results? value=" + pane.getValue());
                } else {
                    Button ok = null; boolean exactMessage = false;
                    for (Component c : all) {
                        if (c instanceof Button && c.isShowing() && c.isEnabled() && "OK".equals(((Button) c).getLabel())) ok = (Button) c;
                        // This AWT Canvas has no text getter. Read only its pinned ImageJ label;
                        // never mutate private fields or dispatch to an unverified dialog.
                        if (c instanceof ij.gui.MultiLineLabel) {
                            try {
                                java.lang.reflect.Field lines = ij.gui.MultiLineLabel.class.getDeclaredField("lines");
                                lines.setAccessible(true);
                                String message = String.join("\n", (String[]) lines.get(c));
                                exactMessage = ("Done.\nSaved to: " + results).equals(message);
                            } catch (ReflectiveOperationException | RuntimeException error) {
                                if (unexpected.add(window)) System.out.println("DIALOG_UNHANDLED title=Multiplex Registration label inspection=" + error);
                            }
                        }
                    }
                    if (ok == null || !exactMessage) continue;
                    answered.add(window); System.out.println("DIALOG_CLICK title=Multiplex Registration button=OK path=" + results);
                    ok.dispatchEvent(new ActionEvent(ok, ActionEvent.ACTION_PERFORMED, ok.getActionCommand())); acknowledgedDone = !window.isShowing();
                }
            }
        });
        controller.start();
    }
    private static void finish() throws Exception {
        if (controller != null) controller.stop();
        report.write();
        Files.write(out.resolve("commands.json"), (WorkflowReport.json(commands) + "\n").getBytes(StandardCharsets.UTF_8));
        phase("complete");
        System.out.println("REPORT=" + out.resolve("report.json"));
        System.exit(report.failures() > 0 ? 1 : 0);
    }
}

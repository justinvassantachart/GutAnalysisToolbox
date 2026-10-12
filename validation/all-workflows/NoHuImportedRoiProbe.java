import Features.AnalyseWorkflows.NeuronsMultiNoHuPipeline;
import Features.Core.Params;
import ij.IJ;
import ij.ImageJ;
import ij.ImagePlus;
import ij.ImageStack;
import ij.Menus;
import ij.WindowManager;
import ij.gui.Roi;
import ij.io.FileSaver;
import ij.io.RoiDecoder;
import ij.io.RoiEncoder;
import ij.macro.Interpreter;
import ij.plugin.PlugIn;
import ij.plugin.frame.RoiManager;
import ij.process.ByteProcessor;
import java.awt.*;
import java.awt.event.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import java.util.List;
import java.util.concurrent.atomic.AtomicReference;
import java.util.zip.*;
import javax.swing.*;

/** Validation only. Real no-Hu pipeline, genuine imported ROIs, no inference or mocks.
 * Run each case in a disposable AWT Fiji process, under an external process deadline.
 * This deliberately does not certify automatic segmentation or cancel behavior. */
public final class NoHuImportedRoiProbe implements PlugIn {
    private static final int W = 64, H = 48;
    private static final String BASE = "synthetic-nohu";
    private static final Rectangle A1 = new Rectangle(8, 8, 12, 12);
    private static final Rectangle A2 = new Rectangle(42, 8, 12, 12);
    private static final Rectangle B1 = new Rectangle(14, 8, 12, 12);
    private static final Rectangle B2 = new Rectangle(42, 30, 12, 12);
    private final Map<String,Object> report = new LinkedHashMap<>();
    private final List<Map<String,Object>> checks = new ArrayList<>();
    private final List<Map<String,Object>> dialogs = Collections.synchronizedList(new ArrayList<>());
    private final AtomicReference<Throwable> pluginError = new AtomicReference<>();
    private final AtomicReference<Throwable> controllerError = new AtomicReference<>();
    private final Set<Window> handled = Collections.newSetFromMap(new IdentityHashMap<Window,Boolean>());
    private volatile boolean watching = true, finishedDialog;
    private int reviewCount;
    private Path output;
    private String scenario;
    private interface Action { Object run() throws Exception; }

    public static void main(String[] args) throws Exception {
        if (args.length != 3) throw new IllegalArgumentException("output-directory subtype-model.zip unchanged|delete-one|delete-all");
        int result = new NoHuImportedRoiProbe().execute(Paths.get(args[0]), Paths.get(args[1]), args[2]);
        System.exit(result);
    }

    /** IJ1 run(command, options) does not pass options to PlugIn.run(arg).
     * Use a real macro call() boundary for the explicit three-line argument. */
    public static String runMacro(String argument) {
        new NoHuImportedRoiProbe().run(argument);
        return "unreachable-after-disposable-process-exit";
    }

    /** Dedicated disposable Fiji process only: exits the process after reporting.
     * IJ.runPlugIn("NoHuImportedRoiProbe", output + "\n" + model + "\n" + scenario). */
    @Override public void run(String argument) {
        try {
            String[] args = argument.split("\n", -1);
            if (args.length != 3) throw new IllegalArgumentException("Expected output, model and scenario on three lines");
            System.exit(execute(Paths.get(args[0]), Paths.get(args[1]), args[2]));
        } catch (Throwable error) {
            error.printStackTrace(); IJ.log("NoHuImportedRoiProbe failed: " + error);
            if (output != null && Files.isDirectory(output)) try {
                report.put("status", "FAIL_HARNESS"); report.put("error", error.toString()); checkpoint("fatal-error");
            } catch (Throwable persistenceError) { persistenceError.printStackTrace(); }
            System.exit(2);
        }
    }

    private int execute(Path directory, Path model, String testCase) throws Exception {
        output = directory.toAbsolutePath();
        scenario = testCase;
        if (!Arrays.asList("unchanged", "delete-one", "delete-all").contains(scenario))
            throw new IllegalArgumentException("Unknown case: " + scenario);
        if (Files.exists(output)) try (java.util.stream.Stream<Path> entries = Files.list(output)) {
            if (entries.findAny().isPresent()) throw new IllegalArgumentException("Output directory must be empty");
        }
        Files.createDirectories(output);
        report.put("schema_version", 1);
        report.put("scope", "Real complete no-Hu imported-ROI pipeline; inference, ganglia, spatial and cancellation excluded");
        report.put("case", scenario);
        report.put("production_source", NeuronsMultiNoHuPipeline.class.getProtectionDomain().getCodeSource().getLocation().toString());
        report.put("java", System.getProperty("java.version"));
        report.put("os", System.getProperty("os.name"));
        report.put("arch", System.getProperty("os.arch"));
        report.put("checks", checks);
        report.put("dialogs", dialogs);
        report.put("status", "RUNNING");
        checkpoint("setup");
        if (GraphicsEnvironment.isHeadless()) return blocked("AWT display unavailable");
        if (!Files.isRegularFile(model)) return blocked("Pinned subtype model file is required by production validation, though inference is unused");
        report.put("unused_subtype_model_sha256", sha(Files.readAllBytes(model)));
        if (IJ.getInstance() == null) {
            ImageJ application = new ImageJ(ImageJ.NO_SHOW);
            application.exitWhenQuitting(false);
        }
        IJ.redirectErrorMessages(true);
        IJ.setExceptionHandler(pluginError::set);
        Map<?,?> commands = Menus.getCommands();
        Map<String,Object> registrations = new LinkedHashMap<>();
        for (String name : new String[]{"Connected Components Labeling", "Label Map to ROIs"}) {
            Object registration = commands == null ? null : commands.get(name);
            registrations.put(name, registration);
            if (registration == null) return blocked("Missing actual installed ImageJ command: " + name);
        }
        report.put("actual_command_registrations", registrations);
        // No menu entries or production implementations are injected by this probe.
        if (RoiManager.getInstance2() != null) return blocked("Use a fresh process: preexisting ROI Manager would be modified by production");
        Files.createDirectories(output.resolve("inputs"));
        Path roiA = output.resolve("inputs/A.zip"), roiB = output.resolve("inputs/B.zip");
        writeRois(roiA, new Rectangle[]{A1, A2});
        writeRois(roiB, new Rectangle[]{B1, B2});
        String roiAHash = sha(Files.readAllBytes(roiA)), roiBHash = sha(Files.readAllBytes(roiB));
        ImagePlus source = fixture();
        String sourceHash = pixelHash(source);
        Path input = output.resolve("inputs/source.tif");
        require(new FileSaver(source).saveAsTiffStack(input.toString()), "Cannot save synthetic input");
        String inputHash = sha(Files.readAllBytes(input));
        report.put("fixture", map("width", W, "height", H, "channels", 2, "z", 1, "t", 1,
                "source_pixel_sha256", sourceHash, "source_file_sha256", inputHash,
                "A_zip_sha256", roiAHash, "B_zip_sha256", roiBHash));
        ImagePlus sentinel = new ImagePlus("unrelated-window-sentinel", new ByteProcessor(5, 3));
        sentinel.getProcessor().set(7, 117); sentinel.show();
        String sentinelHash = pixelHash(sentinel);
        source.show(); WindowManager.setCurrentWindow(source.getWindow());
        IJ.setForegroundColor(255, 255, 255); IJ.setBackgroundColor(0, 0, 0);
        Params p = new Params();
        p.imagePath = null; p.outputDir = output.resolve("outputs").toString();
        p.cellCountsPerGanglia = false; p.doSpatialAnalysis = false;
        p.useClij2EDF = false; p.rescaleToTrainingPx = false;
        p.neuronSegMinMicron = null; p.neuronSegLowerLimitUm = null;
        p.saveFlattenedOverlay = true; p.requireMicronUnits = true;
        NeuronsMultiNoHuPipeline.MultiParams mp = new NeuronsMultiNoHuPipeline.MultiParams();
        mp.base = p; mp.subtypeModelZip = model.toAbsolutePath().toString();
        mp.markers.add(new NeuronsMultiNoHuPipeline.MarkerSpec("A", 1).withCustomRois(roiA.toFile()));
        mp.markers.add(new NeuronsMultiNoHuPipeline.MarkerSpec("B", 2).withCustomRois(roiB.toFile()));
        Thread controller = new Thread(this::watchDialogs, "nohu-known-dialog-controller");
        controller.setDaemon(true); controller.start();
        try {
            checkpoint("entering-production-pipeline");
            new NeuronsMultiNoHuPipeline().run(mp);
            report.put("pipeline_returned", true);
            long deadline = System.nanoTime() + 5_000_000_000L;
            while (!finishedDialog && controllerError.get() == null && System.nanoTime() < deadline) Thread.sleep(25);
            checkpoint("checking-saved-outputs");
            check("known_dialogs_accepted", () -> {
                require(controllerError.get() == null, "Dialog controller: " + controllerError.get());
                require(reviewCount == 2 && finishedDialog, "Required two reviews and final End click");
                return map("reviews", reviewCount, "final_end_clicked", finishedDialog);
            });
            check("no_plugin_error", () -> {
                String message = IJ.getErrorMessage();
                require(pluginError.get() == null, "Plugin exception: " + pluginError.get());
                require(message == null || message.isEmpty(), "ImageJ error: " + message); return true;
            });
            Path result = output.resolve("outputs/Analysis/" + BASE);
            Rectangle[] expectedA = scenario.equals("delete-all") ? new Rectangle[]{}
                    : scenario.equals("delete-one") ? new Rectangle[]{A2} : new Rectangle[]{A1, A2};
            Rectangle[] expectedCombo = scenario.equals("unchanged") ? new Rectangle[]{A1.intersection(B1)} : new Rectangle[]{};
            check("marker_A_export", () -> verifyRois(result.resolve("A_ROIs_" + BASE + ".zip"), expectedA));
            check("marker_B_export", () -> verifyRois(result.resolve("B_ROIs_" + BASE + ".zip"), new Rectangle[]{B1,B2}));
            check("combo_export", () -> verifyRois(result.resolve("A+B_ROIs_" + BASE + ".zip"), expectedCombo));
            check("csv_exact_counts", () -> {
                String actual = Files.readString(result.resolve("Analysis_NoHu_" + BASE + "_cell_counts_multi.csv"));
                String normalized = actual.replace("\r\n", "\n");
                String expected = "File name,A,B,A+B\n" + BASE + "," + expectedA.length + ",2," + expectedCombo.length + "\n";
                report.put("actual_summary_csv", normalized);
                require(expected.equals(normalized), "Summary differs. Expected " + expected + " but got " + normalized);
                return normalized;
            });
            check("max_tiff_reopen", () -> {
                ImagePlus saved = IJ.openImage(result.resolve("MAX_" + BASE + ".tif").toString());
                require(saved != null, "MAX TIFF missing/unreadable");
                try {
                    require(saved.getWidth() == W && saved.getHeight() == H && saved.getNChannels() == 2
                            && saved.getNSlices() == 1 && saved.getNFrames() == 1, "MAX C/Z/T/dimensions changed");
                    require(sourceHash.equals(pixelHash(saved)), "MAX pixels changed despite Z=1");
                    calibration(saved); return map("pixel_sha256", pixelHash(saved), "channels", saved.getNChannels());
                } finally { saved.close(); }
            });
            check("overlay_tiff_reopen", () -> {
                List<String> names = new ArrayList<>(); names.add("B");
                if (expectedA.length > 0) names.add("A"); if (expectedCombo.length > 0) names.add("A+B");
                Map<String,Object> evidence = new LinkedHashMap<>();
                for (String marker : names) {
                    Path file = result.resolve("MAX_" + BASE + "_" + marker + "_overlay.tif");
                    ImagePlus saved = IJ.openImage(file.toString());
                    require(saved != null, "Overlay missing: " + marker);
                    try {
                        require(saved.getWidth() == W && saved.getHeight() == H && saved.getBitDepth() == 24,
                                "Overlay geometry/type wrong: " + marker);
                        calibration(saved); evidence.put(marker, sha(Files.readAllBytes(file)));
                    } finally { saved.close(); }
                }
                return evidence;
            });
            check("source_and_inputs_unchanged", () -> {
                require(sourceHash.equals(pixelHash(source)), "Source image pixels modified"); calibration(source);
                require(source.getNChannels() == 2 && source.getNSlices() == 1 && source.getNFrames() == 1, "Source C/Z/T changed");
                require(inputHash.equals(sha(Files.readAllBytes(input))), "Source TIFF modified");
                require(roiAHash.equals(sha(Files.readAllBytes(roiA))) && roiBHash.equals(sha(Files.readAllBytes(roiB))), "Input ROI ZIP modified");
                require(sentinel.getWindow() != null && sentinelHash.equals(pixelHash(sentinel)), "Unrelated window modified/closed");
                return true;
            });
            check("batch_mode_restored", () -> { require(!Interpreter.batchMode, "Batch mode remained enabled"); return true; });
        } catch (Throwable error) {
            checks.add(map("id", "production_invocation", "status", "FAIL", "error", error.toString()));
            error.printStackTrace();
        } finally {
            watching = false; controller.join(2000);
            if (controllerError.get() != null) report.put("dialog_controller_error", controllerError.get().toString());
        }
        boolean failed = checks.stream().anyMatch(row -> "FAIL".equals(row.get("status")));
        report.put("status", failed ? "FAIL" : "PASS_IMPORTED_ROI_SCOPE");
        report.put("automatic_inference", "NOT_RUN"); report.put("cancellation", "NOT_RUN_NO_PRODUCTION_CANCEL_CONTRACT");
        checkpoint("complete");
        return failed ? 1 : 0;
    }

    private void watchDialogs() {
        while (watching) {
            try { EventQueue.invokeAndWait(this::handleKnownDialogs); Thread.sleep(25); }
            catch (Throwable error) { controllerError.compareAndSet(null, error); return; }
        }
    }
    private void handleKnownDialogs() {
        for (Window w : Window.getWindows()) {
            if (!(w instanceof Dialog) || !w.isShowing() || handled.contains(w)) continue;
            String title = ((Dialog)w).getTitle();
            if (title.equals("Review: A (review)") || title.equals("Review: B (review)")) {
                RoiManager rm = RoiManager.getInstance2();
                require(rm != null, "Review opened without actual ROI Manager");
                boolean first = title.equals("Review: A (review)");
                require(reviewCount == (first ? 0 : 1), "Unexpected review order/repetition");
                verifyRaster(rm.getRoisAsArray(), first ? new Rectangle[]{A1,A2} : new Rectangle[]{B1,B2});
                String action = "accept unchanged";
                if (first && !scenario.equals("unchanged")) {
                    rm.reset(); if (scenario.equals("delete-one")) rm.addRoi(new Roi(A2));
                    action = scenario.equals("delete-one") ? "delete first A ROI; retain second" : "delete every A ROI";
                }
                Map<String,Object> event = map("title", title, "action", action, "remaining_rois", rm.getCount());
                dialogs.add(event); handled.add(w); reviewCount++;
                click(w, "OK"); event.put("button_action_dispatched", true);
            } else if (title.equals("Workflow finished")) {
                require(componentText(w).contains(output.resolve("outputs/Analysis/" + BASE).toString()),
                        "Final dialog refers to an unexpected output");
                dialogs.add(map("title", title, "action", "End")); handled.add(w);
                click(w, "End"); finishedDialog = true;
            }
            // Every other dialog is left untouched. A process deadline means incomplete evidence.
        }
    }
    private static void click(Component component, String label) {
        if (component instanceof AbstractButton && label.equals(((AbstractButton)component).getText().trim())) {
            ((AbstractButton)component).doClick(); return;
        }
        if (component instanceof Button && label.equals(((Button)component).getLabel().trim())) {
            Button button = (Button)component;
            for (ActionListener listener : button.getActionListeners())
                listener.actionPerformed(new ActionEvent(button, ActionEvent.ACTION_PERFORMED, button.getActionCommand()));
            return;
        }
        if (component instanceof Container) for (Component child : ((Container)component).getComponents())
            if (hasButton(child,label)) { click(child,label); return; }
        throw new AssertionError("Required real dialog button absent: " + label);
    }
    private static boolean hasButton(Component c, String s) {
        if (c instanceof AbstractButton && s.equals(((AbstractButton)c).getText().trim())) return true;
        if (c instanceof Button && s.equals(((Button)c).getLabel().trim())) return true;
        if (c instanceof Container) for (Component child:((Container)c).getComponents()) if (hasButton(child,s)) return true;
        return false;
    }
    private static String componentText(Component c) {
        String s = c instanceof JLabel ? ((JLabel)c).getText() : "";
        if (c instanceof JOptionPane) s += String.valueOf(((JOptionPane)c).getMessage());
        if (c instanceof Container) for (Component child:((Container)c).getComponents()) s += componentText(child);
        return s;
    }
    private static ImagePlus fixture() {
        ImageStack stack = new ImageStack(W,H);
        for (int c=0;c<2;c++) {
            byte[] pixels = new byte[W*H];
            for(int y=0;y<H;y++)for(int x=0;x<W;x++)pixels[y*W+x]=(byte)(20+c*70+(x*3+y*5)%90);
            stack.addSlice("channel-" + (c+1),new ByteProcessor(W,H,pixels,null));
        }
        ImagePlus image = new ImagePlus(BASE + ".tif",stack);
        image.setDimensions(2,1,1); image.setOpenAsHyperStack(true);
        image.getCalibration().pixelWidth=.5; image.getCalibration().pixelHeight=.5;
        image.getCalibration().setUnit("um"); image.getCalibration().frameInterval=2;
        return image;
    }
    private static void calibration(ImagePlus image) {
        require(Math.abs(image.getCalibration().pixelWidth-.5)<1e-6 && Math.abs(image.getCalibration().pixelHeight-.5)<1e-6,
                "Spatial calibration was lost");
        require(Features.Core.PluginCalls.isMicronUnit(image.getCalibration().getUnit()), "Micron units were lost");
    }
    private static void writeRois(Path path, Rectangle[] boxes) throws Exception {
        try (ZipOutputStream zip=new ZipOutputStream(Files.newOutputStream(path))) {
            for(int i=0;i<boxes.length;i++) {
                Roi roi=new Roi(boxes[i]); roi.setName("input-"+(i+1));
                byte[] encoded=RoiEncoder.saveAsByteArray(roi);
                zip.putNextEntry(new ZipEntry("input-"+(i+1)+".roi"));zip.write(encoded);zip.closeEntry();
            }
        }
    }
    private static Object verifyRois(Path path, Rectangle[] expected) throws Exception {
        if(expected.length==0) {
            require(!Files.exists(path),"Unexpected nonempty ROI export: "+path.getFileName());
            return map("count",0,"zip_present",false);
        }
        List<Roi> rois=new ArrayList<>(); List<String> names=new ArrayList<>();
        try(ZipInputStream zip=new ZipInputStream(Files.newInputStream(path))) {
            ZipEntry e;while((e=zip.getNextEntry())!=null) {
                require(!e.isDirectory()&&e.getName().endsWith(".roi"),"Unexpected ROI ZIP member");
                byte[] bytes=zip.readAllBytes();require(bytes.length>0&&bytes.length<65536,"Unexpected ROI size");
                Roi roi=new RoiDecoder(bytes,e.getName()).getRoi();require(roi!=null,"Unreadable ROI");
                rois.add(roi);names.add(roi.getName());
            }
        }
        verifyRaster(rois.toArray(new Roi[0]),expected);
        return map("count",rois.size(),"names",names,"file_sha256",sha(Files.readAllBytes(path)),
                "foreground_pixel_sha256",sha(raster(rois.toArray(new Roi[0]))));
    }
    private static void verifyRaster(Roi[] actual,Rectangle[] expected) {
        require(actual.length==expected.length,"ROI count differs: "+actual.length+" vs "+expected.length);
        Roi[] want=new Roi[expected.length];for(int i=0;i<want.length;i++)want[i]=new Roi(expected[i]);
        require(Arrays.equals(raster(actual),raster(want)),"Reopened/seeded ROI foreground differs from exact rectangles");
        // Distinct object shapes also match; a same-union split/merge cannot pass.
        List<String>a=new ArrayList<>(),b=new ArrayList<>();
        for(Roi r:actual)a.add(sha(raster(new Roi[]{r})));for(Roi r:want)b.add(sha(raster(new Roi[]{r})));
        Collections.sort(a);Collections.sort(b);require(a.equals(b),"Per-object ROI geometry differs");
    }
    private static byte[] raster(Roi[] rois) {
        byte[] pixels=new byte[W*H];for(Roi roi:rois)for(int y=0;y<H;y++)for(int x=0;x<W;x++)if(roi.contains(x,y))pixels[y*W+x]=1;
        return pixels;
    }
    private static String pixelHash(ImagePlus image) {
        try {
            ByteArrayOutputStream bytes=new ByteArrayOutputStream();DataOutputStream out=new DataOutputStream(bytes);
            for(int z=1;z<=image.getStackSize();z++)for(int i=0;i<image.getWidth()*image.getHeight();i++)
                out.writeFloat(image.getStack().getProcessor(z).getf(i));
            return sha(bytes.toByteArray());
        } catch(IOException impossible){throw new AssertionError(impossible);}
    }
    private static String sha(byte[] bytes) {
        try {StringBuilder out=new StringBuilder();for(byte b:MessageDigest.getInstance("SHA-256").digest(bytes))out.append(String.format("%02x",b&255));return out.toString();}
        catch(Exception impossible){throw new AssertionError(impossible);}
    }
    private void check(String id, Action action) throws Exception {
        try {checks.add(map("id",id,"status","PASS","actual",action.run()));}
        catch(Throwable error){checks.add(map("id",id,"status","FAIL","error",error.toString()));error.printStackTrace();}
        checkpoint("checking-saved-outputs");
    }
    private int blocked(String reason) throws Exception {report.put("status","BLOCKED_SETUP");report.put("reason",reason);checkpoint("blocked");return 2;}
    private void checkpoint(String phase) throws Exception {
        report.put("phase",phase);
        Path temporary=output.resolve("report.json.tmp");
        Files.writeString(temporary,json(report)+"\n",StandardCharsets.UTF_8);
        Files.move(temporary,output.resolve("report.json"),StandardCopyOption.REPLACE_EXISTING,StandardCopyOption.ATOMIC_MOVE);
    }
    private static void require(boolean yes,String message){if(!yes)throw new AssertionError(message);}
    private static Map<String,Object> map(Object... pairs){Map<String,Object>m=new LinkedHashMap<>();for(int i=0;i<pairs.length;i+=2)m.put((String)pairs[i],pairs[i+1]);return m;}
    private static String json(Object o) {
        if(o==null)return "null";if(o instanceof Boolean||o instanceof Number)return o.toString();
        if(o instanceof Map){List<String>x=new ArrayList<>();for(Map.Entry<?,?>e:((Map<?,?>)o).entrySet())x.add(json(e.getKey())+":"+json(e.getValue()));return "{"+String.join(",",x)+"}";}
        if(o instanceof List){List<String>x=new ArrayList<>();synchronized(o){for(Object e:(List<?>)o)x.add(json(e));}return "["+String.join(",",x)+"]";}
        StringBuilder s=new StringBuilder("\"");for(char c:o.toString().toCharArray()){if(c=='\\'||c=='\"')s.append('\\').append(c);else if(c<32)s.append(String.format("\\u%04x",(int)c));else s.append(c);}return s.append('"').toString();
    }
}

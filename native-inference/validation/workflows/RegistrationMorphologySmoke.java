import Features.Core.Params;
import Features.Core.PluginCalls;
import Features.Tools.AlignStack;
import Features.Tools.AlignStackBatch;
import ij.IJ;
import ij.ImageJ;
import ij.ImagePlus;
import ij.ImageStack;
import ij.Menus;
import ij.WindowManager;
import ij.gui.Roi;
import ij.io.FileSaver;
import ij.io.Opener;
import ij.plugin.frame.RoiManager;
import ij.process.ByteProcessor;
import ij.process.ImageProcessor;
import ij.process.ShortProcessor;
import ij.process.FloatPolygon;
import services.multiplex.core.FeatureMatching;

import java.awt.GraphicsEnvironment;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;
import java.util.Collection;
import java.util.Locale;
import java.util.Map;
import java.util.Random;

/**
 * Real-image integration checks, deliberately separate from native inference.
 * Run in a fresh JVM with built GAT classes, ImageJ, official MorphoLibJ,
 * StackReg/TurboReg, mpicbg and mpicbg_ plus JAMA on the classpath.
 *
 * Command registrations below bind the SAME names/classes published by the
 * upstream plugins; no mock plugins or substituted algorithms are used.
 * Command tests need AWT (macOS GUI session, or a Linux X server). A headless
 * run records BLOCKED rather than pretending plugin class loading is a pass.
 * Library controls still run headlessly and have explicitly narrower scope.
 */
public final class RegistrationMorphologySmoke {
    private static final int W = 256, H = 256, DX = 7, DY = -5;
    private static volatile Throwable pluginFailure;
    private static WorkflowReport report;
    private static Path output;
    private static String guiBlocker;

    public static void main(String[] args) throws Exception {
        output = Paths.get(args.length == 0 ? "registration-morphology-results" : args[0]);
        Files.createDirectories(output);
        report = new WorkflowReport("registration-morphology", output, "registration-morphology.json");
        Locale.setDefault(Locale.US);
        libraryMorphology();
        librarySiftFixture();
        flushReport();
        initializeImageJ();
        commandTest("morpholibj_size_gat", "GAT PluginCalls.labelMinSizeFilterPx on real 16-bit pixels", "Label Size Filtering", new String[]{"inra.ijpb.plugins.LabelSizeFilteringPlugin"}, () -> {
            ImagePlus labels = labels();
            ImagePlus result = PluginCalls.labelMinSizeFilterPx(labels, 16);
            checkPluginFailure();
            checkLabels(result, 0, 16, 36);
            calibration(result);
            return WorkflowReport.values("threshold_px", 16, "kept_label2_pixels", 16, "kept_label3_pixels", 36, "boundary_is_inclusive", true);
        });
        commandTest("morpholibj_border_gat", "GAT PluginCalls.removeBorderLabels on real 16-bit pixels", "Remove Border Labels", new String[]{"inra.ijpb.plugins.RemoveBorderLabelsPlugin"}, () -> {
            ImagePlus result = PluginCalls.removeBorderLabels(labels());
            checkPluginFailure();
            checkLabels(result, 4, 16, 0);
            calibration(result);
            return WorkflowReport.values("kept_interior_labels", 2, "removed_border_label_pixels", 36);
        });
        commandTest("sift_gat_helper", "Actual GAT AlignStack.alignSIFT command, plugin output pixels", "Affine SIFT", new String[]{"SIFT_Align", "mpicbg.ij.SIFT", "Jama.Matrix"}, () -> {
            ImagePlus source = pair("sift-helper");
            source.show();
            int[] before = WindowManager.getIDList();
            double initial = stackMse(source);
            String originalPixels = pixelHash(source);
            source.getCalibration().pixelWidth = 0.5;
            source.getCalibration().pixelHeight = 0.75;
            source.getCalibration().frameInterval = 1.25;
            AlignStack.alignSIFT(source, false);
            checkPluginFailure();
            ImagePlus aligned = newStack(before, source);
            // Supports a future GAT fix that copies the result into the source.
            if (aligned == null) aligned = source;
            double after = stackMse(aligned);
            requireAlignment(initial, after);
            WorkflowReport.check(originalPixels.equals(pixelHash(source)), "SIFT changed source pixels");
            WorkflowReport.check(aligned.getCalibration().pixelWidth == 0.5
                    && aligned.getCalibration().pixelHeight == 0.75
                    && aligned.getCalibration().frameInterval == 1.25, "SIFT result lost calibration/timing");
            save(aligned, output.resolve("sift-helper-aligned.tif"));
            return WorkflowReport.values("initial_mse", initial, "aligned_mse", after, "source_mse_after_helper", stackMse(source), "returned_as_new_image", aligned != source, "frames", aligned.getStackSize());
        });
        commandTest("sift_gat_saved_workflow", "GAT AlignStack.run including TIFF save and re-open; ten-frame fixture", "Affine SIFT", new String[]{"SIFT_Align", "mpicbg.ij.SIFT", "Jama.Matrix"}, () -> {
            Path dir = Files.createDirectories(output.resolve("sift-saved-workflow"));
            ImageStack stack = new ImageStack(W, H);
            ByteProcessor reference = pattern();
            for (int i=0; i<10; i++) stack.addSlice(i % 2 == 0 ? reference.duplicate() : translated(reference, DX, DY));
            ImagePlus source = new ImagePlus("sift-workflow-input", stack);
            source.setDimensions(1, 1, 10);
            source.setOpenAsHyperStack(true);
            Path input = dir.resolve("sift-workflow-input.tif");
            save(source, input);
            double initial = stackMse(source);
            Params p = new Params();
            p.imagePath = input.toAbsolutePath().toString();
            p.outputDir = dir.toAbsolutePath().toString();
            p.referenceFrame = 1;
            p.useSIFT = true;
            p.useTemplateMatching = false;
            p.saveAlignedStack = true;
            AlignStack.AlignResult result = new AlignStack().run(p);
            checkPluginFailure();
            Path saved = dir.resolve("sift-workflow-input_aligned.tif");
            WorkflowReport.check(Files.isRegularFile(saved), "GAT did not save the expected aligned TIFF: " + saved);
            ImagePlus reopened = new Opener().openImage(saved.toString());
            WorkflowReport.check(reopened != null && reopened.getStackSize() == 10, "Saved output is missing or lost frames");
            double savedMse = stackMse(reopened);
            // Detects the historical bug: the plugin creates a new aligned image,
            // while GAT returns and saves the unchanged input image.
            requireAlignment(initial, savedMse);
            requireAlignment(initial, stackMse(result.alignedStack));
            return WorkflowReport.values("initial_mse", initial, "saved_mse", savedMse, "saved_file", saved.toString(), "frames", 10);
        });
        commandTest("sift_gat_batch_channel1", "GAT AlignStackBatch.runBatch, actual two-channel 12-frame TIFF and saved output", "Affine SIFT with deterministic channel 1", new String[]{"SIFT_Align", "mpicbg.ij.SIFT", "Jama.Matrix"}, () -> {
            Path inputDir = Files.createDirectories(output.resolve("sift-batch-input"));
            Path outputDir = Files.createDirectories(output.resolve("sift-batch-output"));
            ImageStack multi = new ImageStack(W, H);
            ImageStack expectedFirst = new ImageStack(W, H);
            ByteProcessor reference = pattern();
            for (int i = 0; i < 12; i++) {
                ImageProcessor first = i % 2 == 0 ? reference.duplicate() : translated(reference, DX, DY);
                multi.addSlice(first);
                ByteProcessor other = new ByteProcessor(W, H);
                other.setValue(19); other.fill();
                multi.addSlice(other);
                expectedFirst.addSlice(first.duplicate());
            }
            ImagePlus input = new ImagePlus("batch-input", multi);
            input.setDimensions(2, 1, 12); input.setOpenAsHyperStack(true);
            input.setPosition(2, 1, 12);
            input.getCalibration().pixelWidth = 0.5;
            input.getCalibration().pixelHeight = 0.75;
            input.getCalibration().frameInterval = 1.25;
            Path inputPath = inputDir.resolve("batch-input.tif");
            save(input, inputPath);
            byte[] originalFile = Files.readAllBytes(inputPath);
            ImagePlus reopenedInput = new Opener().openImage(inputPath.toString());
            Params p = new Params();
            p.inputDir = inputDir.toAbsolutePath().toString();
            p.outputDir = outputDir.toAbsolutePath().toString();
            p.fileExt = ".tif"; p.useSIFT = true; p.useTemplateMatching = false; p.useStackReg = false;
            p.referenceFrame = 1;
            AlignStackBatch.runBatch(p);
            checkPluginFailure();
            Path saved = outputDir.resolve("batch-input.tif_aligned.tif");
            WorkflowReport.check(Files.isRegularFile(saved), "Missing batch aligned output");
            ImagePlus reopened = new Opener().openImage(saved.toString());
            WorkflowReport.check(reopened != null && reopened.getNChannels() == 1
                    && reopened.getNSlices() == 1 && reopened.getNFrames() == 12,
                    "Batch output did not preserve channel-1/time dimensions");
            WorkflowReport.check(reopened.getCalibration().pixelWidth == reopenedInput.getCalibration().pixelWidth
                    && reopened.getCalibration().pixelHeight == reopenedInput.getCalibration().pixelHeight
                    && reopened.getCalibration().frameInterval == reopenedInput.getCalibration().frameInterval
                    && reopened.getCalibration().getUnit().equals(reopenedInput.getCalibration().getUnit()),
                    "Batch output lost calibration/frame interval");
            double initial = stackMse(new ImagePlus("expected-first", expectedFirst));
            double after = stackMse(reopened);
            requireAlignment(initial, after);
            double firstFrameError = 0;
            for (int i = 0; i < W * H; i++) {
                double difference = reopened.getStack().getProcessor(1).getf(i) - reference.getf(i);
                firstFrameError += difference * difference;
            }
            WorkflowReport.check(firstFrameError == 0, "Batch used the wrong channel/reference pixels");
            WorkflowReport.check(java.util.Arrays.equals(originalFile, Files.readAllBytes(inputPath)), "Batch overwrote original input file");
            return WorkflowReport.values("input_channels", 2, "output_channels", 1, "frames", 12,
                    "initial_mse", initial, "saved_mse", after, "first_frame_squared_error", firstFrameError,
                    "input_file_unchanged", true, "pixel_width", reopened.getCalibration().pixelWidth,
                    "pixel_height", reopened.getCalibration().pixelHeight, "frame_interval", reopened.getCalibration().frameInterval,
                    "calibration_comparator", "Reopened source TIFF; rational TIFF resolution can round 0.75",
                    "evidence", output.relativize(saved).toString());
        });
        commandTest("stackreg_turboreg_gat_helper", "Direct GAT AlignStack.alignStackReg helper only; NOT GAT batch implementation", "StackReg rigid-body with TurboReg", new String[]{"StackReg_", "TurboReg_"}, () -> {
            ImagePlus source = pair("stackreg-direct-helper");
            source.show();
            double initial = stackMse(source);
            AlignStack.alignStackReg(source, 1);
            checkPluginFailure();
            double after = stackMse(source);
            requireAlignment(initial, after);
            save(source, output.resolve("stackreg-helper-aligned.tif"));
            return WorkflowReport.values("initial_mse", initial, "aligned_mse", after, "stackreg_batch_validated", false);
        });
        report.blocked("stackreg_gat_batch", "GAT AlignStackBatch.processFile", "GAT explicitly throws UnsupportedOperationException for StackReg batch registration; direct plugin/helper success does not implement or validate batch mode.");
        commandTest("multiplex_gat_feature_matching", "GAT FeatureMatching.matchWithFallbacks and ROI Manager landmarks only", "SIFT first-choice correspondence extraction", new String[]{"SIFT_ExtractPointRoi", "MOPS_ExtractPointRoi", "mpicbg.ij.SIFT", "Jama.Matrix"}, () -> {
            RoiManager rm = RoiManager.getInstance2();
            if (rm == null) rm = new RoiManager();
            rm.reset();
            ImagePlus ref = new ImagePlus("multiplex-reference", pattern());
            ImagePlus target = new ImagePlus("multiplex-target", translated(ref.getProcessor(), DX, DY));
            ref.show(); target.show();
            WorkflowReport.check(ref.getRoi() == null && target.getRoi() == null, "Fixture must not start with pre-existing ROIs");
            boolean matched = FeatureMatching.matchWithFallbacks(ref, target, "hu", 1, 0.5, 3);
            checkPluginFailure();
            WorkflowReport.check(matched && rm.getCount() == 2, "GAT did not store exactly one landmark pair");
            WorkflowReport.check("hu_1_ref".equals(rm.getName(0)) && "hu_1_target".equals(rm.getName(1)), "Landmark ROI naming/order differs");
            Roi a = rm.getRoi(0), b = rm.getRoi(1);
            WorkflowReport.check(a.getType() == Roi.POINT && b.getType() == Roi.POINT, "Selections are not landmark point ROIs");
            FloatPolygon pa = a.getFloatPolygon(), pb = b.getFloatPolygon();
            WorkflowReport.check(pa.npoints >= 7 && pa.npoints == pb.npoints, "Insufficient or unequal landmark counts");
            double error = 0;
            for (int i=0; i<pa.npoints; i++) error += Math.hypot(pb.xpoints[i]-pa.xpoints[i]-DX, pb.ypoints[i]-pa.ypoints[i]-DY);
            error /= pa.npoints;
            WorkflowReport.check(error < 1.0, "Landmark mean translation error=" + error + " pixels");
            return WorkflowReport.values("matched_landmarks", pa.npoints, "known_dx", DX, "known_dy", DY, "mean_translation_error_px", error, "full_multiplex_export_validated", false);
        });
        report.notRun("multiplex_full_export", "MultiplexRegistrationService.run", "Focused real landmark test above does not cover every round/channel warp, naming combination, and exported hyperstack.");
        report.notRun("multiplex_mops_block_fallbacks", "GAT feature matching fallback branches", "The translated fixture targets the first-choice SIFT route; MOPS and Block Matching are not claimed tested.");
        report.write();
        closeImages();
        System.out.println("REPORT=" + output.resolve("registration-morphology.json").toAbsolutePath());
        // ImageJ/AWT can retain event-dispatch threads after all images close.
        System.exit(report.failures() > 0 ? 1 : 0);
    }

    private static void libraryMorphology() {
        String id = "morpholibj_library_control";
        try {
            Class.forName("inra.ijpb.plugins.LabelSizeFilteringPlugin$Operation");
        } catch (Throwable e) {
            report.blocked(id, "Official MorphoLibJ algorithm API only, not GAT command bridge", describe(e)); return;
        }
        report.test(id, "Official MorphoLibJ algorithm API only, not GAT command bridge", "Label-size and border-label controls", () -> {
            Class<?> op = Class.forName("inra.ijpb.plugins.LabelSizeFilteringPlugin$Operation");
            Object ge = op.getField("GE").get(null);
            ImagePlus filtered = (ImagePlus)op.getMethod("applyTo", ImagePlus.class, int.class).invoke(ge, labels(), 16);
            checkLabels(filtered, 0, 16, 36);
            Class<?> border = Class.forName("inra.ijpb.plugins.RemoveBorderLabelsPlugin");
            ImagePlus stripped = (ImagePlus)border.getMethod("remove", ImagePlus.class, boolean.class, boolean.class, boolean.class, boolean.class, boolean.class, boolean.class)
                    .invoke(null, labels(), true, true, true, true, false, false);
            checkLabels(stripped, 4, 16, 0);
            return WorkflowReport.values("pixel_assertions", 6144, "gat_plugin_bridge_validated", false);
        });
    }

    private static void librarySiftFixture() {
        String id = "sift_library_fixture_control";
        try { Class.forName("mpicbg.ij.SIFT"); Class.forName("Jama.Matrix"); }
        catch (Throwable e) { report.blocked(id, "Official mpicbg algorithm only, not GAT command bridge", describe(e)); return; }
        report.test(id, "Official mpicbg algorithm only, not GAT command bridge", "SIFT affine known-translation control, descriptor sizes 4 and 8", () -> {
            Class<?> paramClass = Class.forName("mpicbg.imagefeatures.FloatArray2DSIFT$Param");
            Class<?> transformClass = Class.forName("mpicbg.imagefeatures.FloatArray2DSIFT");
            Class<?> siftClass = Class.forName("mpicbg.ij.SIFT");
            Class<?> featureClass = Class.forName("mpicbg.imagefeatures.Feature");
            Class<?> modelClass = Class.forName("mpicbg.models.AffineModel2D");
            List<Map<String,Object>> results = new ArrayList<>();
            for (int descriptor : new int[]{4, 8}) {
                Object params = paramClass.getConstructor().newInstance();
                paramClass.getField("initialSigma").setFloat(params, 1.6f);
                paramClass.getField("steps").setInt(params, descriptor == 8 ? 4 : 3);
                paramClass.getField("minOctaveSize").setInt(params, descriptor == 8 ? 64 : 32);
                paramClass.getField("maxOctaveSize").setInt(params, W);
                paramClass.getField("fdSize").setInt(params, descriptor);
                paramClass.getField("fdBins").setInt(params, 8);
                Object sift = siftClass.getConstructor(transformClass).newInstance(transformClass.getConstructor(paramClass).newInstance(params));
                List<Object> a=new ArrayList<>(), b=new ArrayList<>(), candidates=new ArrayList<>(), inliers=new ArrayList<>();
                ImageProcessor ref=pattern(), target=translated(ref, DX, DY);
                siftClass.getMethod("extractFeatures", ImageProcessor.class, Collection.class).invoke(sift, ref, a);
                siftClass.getMethod("extractFeatures", ImageProcessor.class, Collection.class).invoke(sift, target, b);
                featureClass.getMethod("matchFeatures", List.class, List.class, List.class, double.class).invoke(null, a, b, candidates, 0.92);
                Object model=modelClass.getConstructor().newInstance();
                boolean fitted=(Boolean)modelClass.getMethod("filterRansac", List.class, Collection.class, int.class, double.class, double.class, int.class)
                        .invoke(model, candidates, inliers, 1000, 25.0, descriptor == 8 ? 0.7 : 0.5, 7);
                WorkflowReport.check(fitted && inliers.size() >= 7, "Fixture did not yield sufficient affine inliers for descriptor " + descriptor);
                double[] origin=(double[])modelClass.getMethod("apply", double[].class).invoke(model, (Object)new double[]{0, 0});
                double error=Math.hypot(origin[0]-DX, origin[1]-DY);
                WorkflowReport.check(error < 1.0, "SIFT fixture fitted the wrong translation: error=" + error);
                results.add(WorkflowReport.values("descriptor_size",descriptor,"reference_features",a.size(),"target_features",b.size(),"inliers",inliers.size(),"fitted_dx",origin[0],"fitted_dy",origin[1],"translation_error_px",error));
            }
            return WorkflowReport.values("configurations", results, "gat_plugin_bridge_validated", false);
        });
    }

    private static void flushReport() {
        try { report.write(); }
        catch (Exception e) { throw new IllegalStateException("Cannot persist workflow evidence", e); }
    }

    @SuppressWarnings("unchecked")
    private static void initializeImageJ() {
        try {
            if (GraphicsEnvironment.isHeadless()) throw new java.awt.HeadlessException("No graphics session available; ImageJ GenericDialog and plugin windows require AWT");
            ImageJ app = new ImageJ(ImageJ.NO_SHOW);
            app.exitWhenQuitting(false);
            IJ.redirectErrorMessages(true);
            IJ.setExceptionHandler(t -> pluginFailure = t);
            Map commands = Menus.getCommands();
            commands.put("Label Size Filtering", "inra.ijpb.plugins.LabelSizeFilteringPlugin");
            commands.put("Remove Border Labels", "inra.ijpb.plugins.RemoveBorderLabelsPlugin");
            commands.put("Linear Stack Alignment with SIFT", "SIFT_Align");
            commands.put("Extract SIFT Correspondences", "SIFT_ExtractPointRoi");
            commands.put("Extract MOPS Correspondences", "MOPS_ExtractPointRoi");
            commands.put("StackReg", "StackReg_");
            commands.put("TurboReg", "TurboReg_");
            commands.put("Collect Garbage", "CollectGarbage_"); // Actual official Fiji/VIB plugin used by unchanged GAT.
        } catch (Throwable t) { guiBlocker = describe(t); }
    }

    private static void commandTest(String id, String scope, String algorithm, String[] classes, WorkflowReport.CheckedAction action) {
        if (guiBlocker != null) { report.blocked(id, scope, guiBlocker); flushReport(); return; }
        for (String name : classes) {
            try { Class.forName(name); }
            catch (Throwable e) { report.blocked(id, scope, "Dependency " + name + ": " + describe(e)); flushReport(); return; }
        }
        pluginFailure = null;
        IJ.getErrorMessage(); // clear a preceding plugin error before this check
        report.test(id, scope, algorithm, () -> {
            try { return action.run(); }
            finally { closeImages(); }
        });
        flushReport();
    }

    private static void checkPluginFailure() {
        if (pluginFailure != null) throw new AssertionError("ImageJ plugin failed: " + describe(pluginFailure), pluginFailure);
        String error = IJ.getErrorMessage();
        if (error != null && !error.isEmpty()) throw new AssertionError("ImageJ error: " + error);
    }

    private static ImagePlus labels() {
        ShortProcessor p = new ShortProcessor(64, 48);
        rectangle(p, 8, 8, 2, 2, 1);
        rectangle(p, 22, 12, 4, 4, 2);
        rectangle(p, 0, 28, 6, 6, 3);
        ImagePlus image = new ImagePlus("synthetic-labels", p);
        image.getCalibration().pixelWidth = 0.5;
        image.getCalibration().pixelHeight = 0.75;
        image.getCalibration().setUnit("um");
        return image;
    }

    private static void rectangle(ImageProcessor p, int x, int y, int w, int h, int v) {
        for (int yy=y; yy<y+h; yy++) for (int xx=x; xx<x+w; xx++) p.set(xx, yy, v);
    }

    private static void checkLabels(ImagePlus result, int n1, int n2, int n3) {
        WorkflowReport.check(result != null && result.getBitDepth() == 16 && result.getWidth() == 64 && result.getHeight() == 48, "Wrong label output shape/type");
        int[] expected = {64*48-n1-n2-n3, n1, n2, n3};
        int[] actual = new int[4];
        for (int i=0; i<64*48; i++) {
            int v=result.getProcessor().get(i);
            WorkflowReport.check(v >= 0 && v <= 3, "Unexpected label ID=" + v);
            actual[v]++;
            int x=i%64, y=i/64;
            int original=(x>=8 && x<10 && y>=8 && y<10) ? 1 : (x>=22 && x<26 && y>=12 && y<16) ? 2 : (x<6 && y>=28 && y<34) ? 3 : 0;
            int wanted=(original == 1 && n1 == 0 || original == 2 && n2 == 0 || original == 3 && n3 == 0) ? 0 : original;
            WorkflowReport.check(v == wanted, "Unexpected label pixel at " + x + "," + y + ": " + v + " != " + wanted);
        }
        for (int i=0; i<4; i++) WorkflowReport.check(actual[i] == expected[i], "Wrong area for label " + i + ": " + actual[i]);
    }

    private static void calibration(ImagePlus image) {
        WorkflowReport.check(image.getCalibration().pixelWidth == 0.5 && image.getCalibration().pixelHeight == 0.75, "GAT discarded label calibration");
    }

    private static String pixelHash(ImagePlus image) throws Exception {
        java.security.MessageDigest digest = java.security.MessageDigest.getInstance("SHA-256");
        for (int plane = 1; plane <= image.getStackSize(); plane++) {
            ImageProcessor processor = image.getStack().getProcessor(plane);
            for (int i = 0; i < image.getWidth() * image.getHeight(); i++) {
                int bits = Float.floatToIntBits(processor.getf(i));
                digest.update((byte) (bits >>> 24)); digest.update((byte) (bits >>> 16));
                digest.update((byte) (bits >>> 8)); digest.update((byte) bits);
            }
        }
        StringBuilder text = new StringBuilder();
        for (byte b : digest.digest()) text.append(String.format("%02x", b & 255));
        return text.toString();
    }

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

    private static ByteProcessor translated(ImageProcessor p, int dx, int dy) {
        ByteProcessor moved = new ByteProcessor(p.getWidth(), p.getHeight());
        for (int y=0; y<p.getHeight(); y++) for (int x=0; x<p.getWidth(); x++) {
            int sx=x-dx, sy=y-dy;
            if (sx>=0 && sx<p.getWidth() && sy>=0 && sy<p.getHeight()) moved.set(x,y,p.get(sx,sy));
        }
        return moved;
    }

    private static ImagePlus pair(String title) {
        ByteProcessor p=pattern();
        ImageStack stack=new ImageStack(W,H);
        stack.addSlice(p); stack.addSlice(translated(p,DX,DY));
        return new ImagePlus(title,stack);
    }

    private static double stackMse(ImagePlus image) {
        WorkflowReport.check(image != null && image.getStackSize() >= 2, "Aligned output has fewer than two frames");
        ImageProcessor a=image.getStack().getProcessor(1), b=image.getStack().getProcessor(2);
        double error=0; int n=0;
        for(int y=24;y<H-24;y++) for(int x=24;x<W-24;x++) { double d=a.getf(x,y)-b.getf(x,y); error+=d*d; n++; }
        return error/n;
    }

    private static void requireAlignment(double before, double after) {
        WorkflowReport.check(before > 100, "Synthetic image is insufficiently displaced: MSE="+before);
        WorkflowReport.check(Double.isFinite(after) && after < before*0.15, "Alignment did not reduce MSE by at least 85%: before="+before+", after="+after);
    }

    private static ImagePlus newStack(int[] before, ImagePlus source) {
        int[] ids=WindowManager.getIDList();
        if(ids == null) return null;
        for(int id:ids) {
            boolean existed=false; if(before!=null) for(int previous:before) if(id==previous) existed=true;
            ImagePlus p=WindowManager.getImage(id);
            if(!existed && p!=null && p!=source && p.getWidth()==W && p.getHeight()==H && p.getStackSize()==source.getStackSize()) return p;
        }
        return null;
    }

    private static void save(ImagePlus image, Path path) {
        FileSaver saver=new FileSaver(image);
        boolean ok=image.getStackSize()>1 ? saver.saveAsTiffStack(path.toString()) : saver.saveAsTiff(path.toString());
        WorkflowReport.check(ok, "TIFF write failed: "+path);
    }

    private static void closeImages() {
        try {
            WindowManager.setTempCurrentImage(null);
            int[] ids=WindowManager.getIDList();
            if(ids!=null) for(int id:ids) { ImagePlus p=WindowManager.getImage(id); if(p!=null){ p.changes=false;p.close(); } }
            RoiManager rm=RoiManager.getInstance2(); if(rm!=null) rm.reset();
        } catch (Throwable ignored) { /* preserve test's original failure */ }
    }

    private static String describe(Throwable t) {
        while(t.getCause()!=null && t.getCause()!=t) t=t.getCause();
        return t.getClass().getName()+": "+String.valueOf(t.getMessage());
    }
}

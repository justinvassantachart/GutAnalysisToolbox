package Features.Tools;

import Features.Core.Params;
import ij.IJ;
import ij.ImagePlus;
import ij.ImageStack;
import ij.WindowManager;
import ij.measure.Calibration;
import ij.plugin.PlugIn;
import ij.process.ImageProcessor;
import ij.measure.ResultsTable;
import java.util.List;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;
import java.util.UUID;
import java.util.Map;
import java.util.WeakHashMap;
import java.util.Collections;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;

/**
 * AlignStack plugin
 * Aligns a multi-frame TIFF stack using Linear Stack Alignment with SIFT and/or Template Matching.
 * Converts macro logic to Java, using parameters from the Params object.
 */
public class AlignStack implements PlugIn {
    private static final Map<ImagePlus, TemplateMotion> TEMPLATE_MOTION = Collections.synchronizedMap(new WeakHashMap<>());
    private static final class TemplateMotion {
        final int reference;
        final double[][] shifts;
        TemplateMotion(int reference, double[][] shifts) { this.reference = reference; this.shifts = shifts; }
    }

    /** Container for alignment output: aligned stack and CSV file */
    public static class AlignResult {
        public final ImagePlus alignedStack;
        public final File resultCSV;

        public AlignResult(ImagePlus alignedStack, File resultCSV) {
            this.alignedStack = alignedStack;
            this.resultCSV = resultCSV;
        }
    }

    // URL for plugin installation guidance
    private static final String PLUGIN_INSTALLATION_URL =
            "https://sites.imagej.net/Template_Matching/";

    @Override
    public void run(String arg) {
        // Notify user about required plugins
        IJ.log("Please install template plugin if needed: " + PLUGIN_INSTALLATION_URL);
        IJ.showMessage("Info", "Please Ensure Linear Stack Alignment:Template Matching plugin is installed.\n" +
                "URL: " + PLUGIN_INSTALLATION_URL);
    }

    /**
     * Align the stack using parameters from the user interface (Params object)
     * @param p Params object containing alignment settings and paths
     * @return AlignResult containing the aligned ImagePlus and CSV of motion vectors
     * @throws Exception if input is invalid or stack is too short
     */
    public AlignResult run(Params p) throws Exception {
        // Reject unsupported native code before opening or modifying an image.
        if (p.useTemplateMatching) requireTemplateMatchingSupported();
        if (p.imagePath == null || p.imagePath.isEmpty()) {
            throw new IllegalArgumentException("No input image specified");
        }

        File file = new File(p.imagePath);
        if (!file.exists()) throw new IllegalArgumentException("File not found: " + p.imagePath);

        ImagePlus imp = IJ.openImage(p.imagePath);
        if (imp == null) throw new RuntimeException("Failed to open image: " + p.imagePath);

        int sizeC = imp.getNChannels();
        int sizeT = imp.getNFrames();

        // Require at least 10 frames for meaningful alignment
        if (sizeT < 10) {
            IJ.log("Stack has fewer than 10 frames. Skipping alignment: " + file.getName());
            throw new Exception("Stack has fewer than 10 frames. Skipping alignment.");
        }

        // Determine reference frame
        int refFrame = Math.min(Math.max(1, p.referenceFrame), sizeT);
        imp.setSlice(refFrame);
        IJ.showStatus("Starting alignment: " + file.getName());

        // The workflow intentionally aligns channel 1 only. Do not infer the
        // selected channel from global windows or close unrelated image windows.
        if (sizeC > 1) imp = firstAlignmentChannel(imp);

        // Perform SIFT alignment if requested
        if (p.useSIFT) {
            imp = alignedWithSIFT(imp, false);
        }

        // Perform Template Matching alignment if requested
        if (p.useTemplateMatching) {
            alignTemplateMatching(imp, refFrame);
        }

        // Save aligned stack if requested
        if (p.saveAlignedStack) {
            String outputPath = p.outputDir;
            if (!outputPath.endsWith(File.separator)) outputPath += File.separator;
            String outFile = outputPath + file.getName().replace(".tif", "_aligned.tif");
            IJ.saveAsTiff(imp, outFile);
            IJ.log("Saved aligned stack to: " + outFile);
        }

        // Never reinterpret unrelated global measurements or invent zero shifts.
        File resultCSV = writeVerifiedAlignmentResultsCSV(imp, p.outputDir);
        if (p.useSIFT && resultCSV != null) IJ.log("Motion CSV describes the Template Matching refinement stage only, not the preceding SIFT affine transform.");

        // Clean memory
        System.gc();
        IJ.showStatus("Alignment done: " + file.getName());

        return new AlignResult(imp, resultCSV);
    }

    /**
     * Compatibility entry point. The aligned image is displayed by the plugin;
     * callers that save or continue processing must use {@link #alignedWithSIFT}.
     * The supplied image is not modified.
     */
    public static void alignSIFT(ImagePlus imp, boolean defaultSettings) {
        alignedWithSIFT(imp, defaultSettings);
    }

    /**
     * Run the unchanged SIFT command on a private stack copy and return its
     * complete output. SIFT creates a new image; saving the input would silently
     * save unaligned pixels. Missing, partial or ambiguous results stop the run.
     * The caller's pixels, selection and metadata remain unchanged on failure.
     */
    public static ImagePlus alignedWithSIFT(ImagePlus imp, boolean defaultSettings) {
        if (imp == null || imp.getStackSize() < 2) {
            throw new IllegalArgumentException("SIFT alignment needs an image with at least two planes.");
        }
        if (imp.getNChannels() != 1) {
            throw new IllegalArgumentException("SIFT alignment expects one channel; choose the alignment channel first.");
        }
        int size = Math.min(imp.getWidth(), imp.getHeight());
        int maximalAlignmentError = (int) Math.ceil(0.1 * size);
        double inlierRatio = defaultSettings ? 0.05 : 0.7;
        int featureDescSize = defaultSettings ? 4 : (size < 500 ? 8 : 4);

        String args = String.format(Locale.ROOT,
                "initial_gaussian_blur=1.60 steps_per_scale_octave=%d minimum_image_size=64 " +
                "maximum_image_size=%d feature_descriptor_size=%d feature_descriptor_orientation_bins=8 " +
                "closest/next_closest_ratio=0.92 maximal_alignment_error=%d inlier_ratio=%f expected_transformation=Affine",
                defaultSettings ? 3 : 4, size, featureDescSize, maximalAlignmentError, inlierRatio
        );

        ImagePlus request = duplicateAlignmentInput(imp);
        request.setTitle("GAT_SIFT_" + UUID.randomUUID());
        try {
            // Keep the private request registered for ImageJ command lookup. Do
            // not use ImagePlus.duplicate(), which can crop an existing ROI.
            request.show();
            if (request.getWindow() != null) request.getWindow().setVisible(false);
            Set<Integer> before = imageIds();
            IJ.run(request, "Linear Stack Alignment with SIFT", args);
            IJ.wait(100);
            List<ImagePlus> created = new ArrayList<>();
            int[] after = WindowManager.getIDList();
            if (after != null) {
                for (int id : after) {
                    if (!before.contains(id)) created.add(WindowManager.getImage(id));
                }
            }
            ImagePlus result = selectSiftResult(imp, created);
            copyAlignmentMetadata(imp, result);
            result.setTitle(imp.getTitle());
            return result;
        } finally {
            request.changes = false;
            request.close();
        }
    }

    /** Copy exactly channel 1 across every Z/T plane without changing the source. */
    static ImagePlus firstAlignmentChannel(ImagePlus source) {
        ImageStack stack = new ImageStack(source.getWidth(), source.getHeight());
        for (int t = 1; t <= source.getNFrames(); t++) {
            for (int z = 1; z <= source.getNSlices(); z++) {
                int plane = source.getStackIndex(1, z, t);
                stack.addSlice(source.getStack().getSliceLabel(plane),
                        source.getStack().getProcessor(plane).duplicate());
            }
        }
        ImagePlus channel = new ImagePlus(source.getTitle(), stack);
        copyImageProperties(source, channel);
        channel.setDimensions(1, source.getNSlices(), source.getNFrames());
        channel.setOpenAsHyperStack(source.getOpenAsHyperStack());
        channel.setPositionWithoutUpdate(1, source.getZ(), source.getT());
        if (source instanceof ij.CompositeImage) {
            channel.setLut(((ij.CompositeImage) source).getChannelLut(1));
        }
        return channel;
    }

    /** Full-stack copy independent of the currently selected ROI or plane. */
    static ImagePlus duplicateAlignmentInput(ImagePlus source) {
        ImagePlus copy = new ImagePlus(source.getTitle(), source.getStack().duplicate());
        copyAlignmentMetadata(source, copy);
        return copy;
    }

    /** Validate before any caller can replace/save its input with a plugin result. */
    static ImagePlus selectSiftResult(ImagePlus source, List<ImagePlus> created) {
        ImagePlus selected = null;
        String completedTitle = "Aligned " + source.getStackSize() + " of " + source.getStackSize();
        for (ImagePlus candidate : created) {
            if (candidate == null || candidate == source || !completedTitle.equals(candidate.getTitle())) continue;
            if (candidate.getWidth() != source.getWidth() || candidate.getHeight() != source.getHeight()
                    || candidate.getStackSize() != source.getStackSize() || candidate.getBitDepth() != source.getBitDepth()) {
                throw new IllegalStateException("SIFT returned an incompatible aligned stack; the input was not changed.");
            }
            if (selected != null) {
                throw new IllegalStateException("SIFT returned multiple aligned stacks; the input was not changed.");
            }
            selected = candidate;
        }
        if (selected == null) {
            throw new IllegalStateException("SIFT did not return a complete aligned stack; the input was not changed. "
                    + "Check the Linear Stack Alignment with SIFT plugin and Fiji Log.");
        }
        return selected;
    }

    private static Set<Integer> imageIds() {
        Set<Integer> ids = new HashSet<>();
        int[] existing = WindowManager.getIDList();
        if (existing != null) for (int id : existing) ids.add(id);
        return ids;
    }

    private static void copyAlignmentMetadata(ImagePlus source, ImagePlus target) {
        copyImageProperties(source, target);
        target.setDimensions(source.getNChannels(), source.getNSlices(), source.getNFrames());
        target.setOpenAsHyperStack(source.getOpenAsHyperStack());
        target.setPositionWithoutUpdate(source.getC(), source.getZ(), source.getT());
    }

    private static void copyImageProperties(ImagePlus source, ImagePlus target) {
        Calibration calibration = source.getCalibration();
        target.setCalibration(calibration == null ? null : calibration.copy());
        target.setDisplayRange(source.getDisplayRangeMin(), source.getDisplayRangeMax());
        target.getStack().setColorModel(source.getStack().getColorModel());
        Object info = source.getProperty("Info");
        if (info != null) target.setProperty("Info", info);
    }

    /**
     * Perform Template Matching-based alignment
     * @param imp ImagePlus stack to align
     * @param refFrame Reference frame number
     */
    public static void alignTemplateMatching(ImagePlus imp, int refFrame) {
        requireTemplateMatchingSupported();
        TEMPLATE_MOTION.remove(imp);
        if (nativeTemplateMatchingSelected()) {
            try {
                double[][] shifts = Features.Inference.NativeAlignmentClient.predict(IJ.getDirectory("imagej"), imp, refFrame);
                ImagePlus result = Features.Inference.NativeAlignmentClient.translatedCopy(imp, shifts);
                imp.setStack(imp.getTitle(), result.getStack());
                copyAlignmentMetadata(result, imp);
                imp.updateAndDraw();
                recordTemplateMotion(imp, refFrame, shifts);
                IJ.log("Template Matching backend: isolated native OpenCV worker; original method5/integer shifts");
                return;
            } catch (InterruptedException error) {
                Thread.currentThread().interrupt();
                throw new IllegalStateException("Native Template Matching interrupted; input was not changed", error);
            } catch (IOException error) {
                throw new IllegalStateException(error.getMessage(), error);
            }
        }
        int xSize = (int) Math.floor(imp.getWidth() * 0.7);
        int ySize = (int) Math.floor(imp.getHeight() * 0.7);
        int x0 = (int) Math.floor(imp.getWidth() / 6.0);
        int y0 = (int) Math.floor(imp.getHeight() / 6.0);

        String args = String.format(
                "method=5 windowsizex=%d windowsizey=%d x0=%d y0=%d swindow=0 subpixel=false itpmethod=0 ref.slice=%d show=true",
                xSize, ySize, x0, y0, refFrame
        );

        ResultsTable before = ResultsTable.getResultsTable();
        IJ.run(imp, "Align slices in stack...", args);
        IJ.wait(10);
        ResultsTable after = ResultsTable.getResultsTable();
        if (after != before) {
            double[][] shifts = verifiedLegacyTemplateShifts(after, imp.getStackSize(), refFrame);
            if (shifts != null) recordTemplateMotion(imp, refFrame, shifts);
        }
    }

    static boolean nativeTemplateMatchingSelected() {
        String selection = System.getProperty("gat.alignment.backend", "auto").trim().toLowerCase(Locale.ROOT);
        boolean apple = Features.Inference.InferenceBackend.isAppleSiliconMac();
        if ("native".equals(selection)) return true;
        if ("auto".equals(selection)) return apple;
        if ("legacy".equals(selection) && !apple) return false;
        if ("legacy".equals(selection)) throw new IllegalStateException("Legacy Template Matching has no supplied Apple Silicon OpenCV library; use the isolated native worker.");
        throw new IllegalArgumentException("gat.alignment.backend must be auto, native or legacy");
    }

    /** Reject a missing isolated worker before opening or modifying an image. */
    public static void requireTemplateMatchingSupported() {
        if (nativeTemplateMatchingSelected()) Features.Inference.NativeAlignmentClient.checkInstallation(IJ.getDirectory("imagej"));
    }

    /**
     * Optional batch registration using StackReg plugin
     */
    public static void alignStackReg(ImagePlus imp, int referenceFrame) {
        if (imp == null) return;
        imp.setT(referenceFrame);
        IJ.run(imp, "StackReg", "transformation=[Rigid Body]");
    }

    /** Save only verified algorithm-owned data. Unavailable transforms produce no file. */
    public static void saveAlignmentResultsCSV(ImagePlus imp, String outputDir) {
        writeVerifiedAlignmentResultsCSV(imp, outputDir);
    }

    static File writeVerifiedAlignmentResultsCSV(ImagePlus imp, String outputDir) {
        if (imp == null || outputDir == null) return null;
        TemplateMotion motion = TEMPLATE_MOTION.get(imp);
        if (motion == null) {
            IJ.log("No verified per-slice translation data are available; no placeholder motion CSV was written. SIFT affine transforms are not exported by this plugin interface.");
            return null;
        }
        File file = new File(outputDir, imp.getTitle() + "_template_matching_alignment.csv");
        try (PrintWriter writer = new PrintWriter(new FileWriter(file))) {
            writer.println("Algorithm,ReferenceSlice,Slice,Dx,Dy");
            for (int slice = 0; slice < motion.shifts.length; slice++)
                writer.printf(Locale.ROOT, "TemplateMatching,%d,%d,%.6f,%.6f%n", motion.reference, slice + 1,
                        motion.shifts[slice][0], motion.shifts[slice][1]);
            if (writer.checkError()) throw new IOException("Error writing motion CSV");
            return file;
        } catch (IOException error) {
            throw new IllegalStateException("Failed to save verified alignment shifts: " + error.getMessage(), error);
        }
    }

    static void recordTemplateMotion(ImagePlus image, int reference, double[][] shifts) {
        if (shifts == null || shifts.length != image.getStackSize() || reference < 1 || reference > shifts.length)
            throw new IllegalArgumentException("Invalid Template Matching motion dimensions/reference");
        double[][] copy = new double[shifts.length][2];
        for (int frame = 0; frame < shifts.length; frame++) {
            if (shifts[frame] == null || shifts[frame].length != 2) throw new IllegalArgumentException("Invalid motion pair");
            for (int axis = 0; axis < 2; axis++) {
                double value = shifts[frame][axis];
                if (!Double.isFinite(value) || Math.abs(value) > (axis == 0 ? image.getWidth() : image.getHeight())
                        || frame == reference - 1 && value != 0) throw new IllegalArgumentException("Invalid motion value");
                copy[frame][axis] = value;
            }
        }
        TEMPLATE_MOTION.put(image, new TemplateMotion(reference, copy));
    }

    static double[][] verifiedLegacyTemplateShifts(ResultsTable table, int frames, int reference) {
        if (table == null || table.size() != frames - 1 || reference < 1 || reference > frames
                || !table.columnExists("Slice") || !table.columnExists("dX") || !table.columnExists("dY")) return null;
        double[][] shifts = new double[frames][2];
        boolean[] seen = new boolean[frames];seen[reference - 1] = true;
        for (int row = 0; row < table.size(); row++) {
            double slice = table.getValue("Slice", row), dx = table.getValue("dX", row), dy = table.getValue("dY", row);
            if (!Double.isFinite(slice) || slice != Math.rint(slice) || slice < 1 || slice > frames
                    || seen[(int) slice - 1] || !Double.isFinite(dx) || !Double.isFinite(dy)) return null;
            seen[(int) slice - 1] = true;
            shifts[(int) slice - 1][0] = dx;shifts[(int) slice - 1][1] = dy;
        }
        return shifts;
    }
}

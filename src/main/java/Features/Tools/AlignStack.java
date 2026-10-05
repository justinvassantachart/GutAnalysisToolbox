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

        // Export CSV with X/Y shifts per slice if available
        File resultCSV = new File(p.outputDir, imp.getTitle() + "_alignment.csv");
        ResultsTable rt = ResultsTable.getResultsTable();
        if (rt != null && rt.getCounter() > 0) {
            int lastCol = rt.getLastColumn();
            int secondLastCol = lastCol - 1;

            try (PrintWriter pw = new PrintWriter(new FileWriter(resultCSV))) {
                pw.println("Slice,Dx,Dy");
                for (int i = 0; i < rt.getCounter(); i++) {
                    double valDx = rt.getValueAsDouble(secondLastCol, i);
                    double valDy = rt.getValueAsDouble(lastCol, i);
                    pw.printf("%d,%.3f,%.3f%n", i + 1, valDx, valDy);
                }
            } catch (IOException ex) {
                IJ.log("Failed to save alignment CSV: " + ex.getMessage());
            }
        } else {
            IJ.log("Warning: ResultsTable is empty. No motion data found.");
        }

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
        int xSize = (int) Math.floor(imp.getWidth() * 0.7);
        int ySize = (int) Math.floor(imp.getHeight() * 0.7);
        int x0 = (int) Math.floor(imp.getWidth() / 6.0);
        int y0 = (int) Math.floor(imp.getHeight() / 6.0);

        String args = String.format(
                "method=5 windowsizex=%d windowsizey=%d x0=%d y0=%d swindow=0 subpixel=false itpmethod=0 ref.slice=%d show=true",
                xSize, ySize, x0, y0, refFrame
        );

        IJ.run(imp, "Align slices in stack...", args);
        IJ.wait(10);
    }

    /** The update site's Template Matching OpenCV binary is Intel-only on macOS. */
    public static void requireTemplateMatchingSupported() {
        if (Features.Inference.InferenceBackend.isAppleSiliconMac()) {
            throw new IllegalStateException("Template Matching alignment is unavailable in this Apple Silicon preview: "
                    + "the plugin's published macOS OpenCV binary is Intel-only. "
                    + "Turn off Template Matching and explicitly choose SIFT alignment if appropriate. "
                    + "GAT will not silently substitute a different alignment algorithm.");
        }
    }

    /**
     * Optional batch registration using StackReg plugin
     */
    public static void alignStackReg(ImagePlus imp, int referenceFrame) {
        if (imp == null) return;
        imp.setT(referenceFrame);
        IJ.run(imp, "StackReg", "transformation=[Rigid Body]");
    }

    /**
     * Save simple alignment shifts as CSV (placeholder if ResultsTable is empty)
     */
    public static void saveAlignmentResultsCSV(ImagePlus imp, String outputDir) {
        if (imp == null || outputDir == null) return;

        File csvFile = new File(outputDir, imp.getTitle() + "_alignment.csv");
        try (PrintWriter pw = new PrintWriter(csvFile)) {
            pw.println("Frame,X_shift,Y_shift");
            int nFrames = imp.getNFrames();
            for (int t = 1; t <= nFrames; t++) {
                double xShift = 0; // Placeholder
                double yShift = 0; // Placeholder
                pw.printf("%d,%.2f,%.2f%n", t, xShift, yShift);
            }
        } catch (Exception e) {
            IJ.log("Failed to save CSV: " + e.getMessage());
        }
    }
}

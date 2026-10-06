package Analysis;

import ij.IJ;
import ij.ImagePlus;
import ij.plugin.frame.RoiManager;
import ij.plugin.ZProjector;
import ij.plugin.ImageCalculator;
import java.io.File;
import java.awt.GridLayout;
import javax.swing.JLabel;
import javax.swing.JOptionPane;
import javax.swing.JPanel;
import javax.swing.JSpinner;
import javax.swing.SpinnerNumberModel;

import Features.Core.Params;

/**
 * This CalciumAnalysis class in provides methods for loading, processing, and analysing calcium
 * imaging data including image manipulation, ROI management, and measurement extraction.
 */
public class CalciumAnalysis {

    private final Params p;
    private ImagePlus rawStack;     // Original image stack
    public ImagePlus maxProj;       // Max intensity projection
    public ImagePlus normStack;     // Normalized F/F0 stack
    private RoiManager rm;          // ROI Manager for handling regions

    /**
     * Constructs a new {@code CalciumAnalysis} instance using the specified parameters.
     *
     * @param params the analysis parameters containing file paths and processing options
     */

    public CalciumAnalysis(Params params) {
        this.p = params;
    }

    /** Step 1: Load the image from file path */
    public void openImage() {
        // A failed reload must not leave the preceding movie/results usable.
        rawStack = null;
        maxProj = null;
        normStack = null;
        if (p.imagePath == null || p.imagePath.trim().isEmpty())
            throw new IllegalArgumentException("Select a calcium image file first.");
        File imgFile = new File(p.imagePath);
        if (!imgFile.isFile())
            throw new IllegalArgumentException("Image file not found: " + p.imagePath);
        ImagePlus loaded = IJ.openImage(p.imagePath);
        if (loaded == null)
            throw new IllegalArgumentException("Could not open calcium image: " + p.imagePath);
        requireSupportedMovie(loaded);
        rawStack = loaded;
        this.maxProj = rawStack;
        rawStack.show();
        IJ.selectWindow(rawStack.getTitle());
        IJ.log("Step 1: Image loaded successfully.");
    }

    /** Step 2: Generate max intensity projection for user-specified frame range */
    public void createMaxProjection() {
        requireSupportedMovie(rawStack);
        if (rawStack.getStackSize() <= 1) {
            IJ.showMessage("Error", "Image must have multiple slices for Max Projection.");
            return;
        }
        int[] frames = promptForFrames(rawStack.getStackSize());
        if (frames == null) return;

        int start = frames[0];
        int end = frames[1];
        maxProj = projectFrames(rawStack, start, end, ZProjector.MAX_METHOD);
        maxProj.setTitle("MAX_" + new File(p.imagePath).getName());
        maxProj.show();
        IJ.log("Step 2: Max intensity projection created.");
    }

    /** Step 3: Perform F/F0 normalization */
    public void normalizeStack() {
        requireSupportedMovie(rawStack);
        if (!p.useFF0) {
            normStack = rawStack;
            return;
        }

        int[] frames = promptForBaseline(rawStack.getStackSize());
        if (frames == null) return;

        int start = frames[0];
        int end = frames[1];
        ImagePlus f0 = projectFrames(rawStack, start, end, ZProjector.AVG_METHOD);
        normStack = divideByBaseline(rawStack, f0);
        normStack.setTitle("F_F0_" + new File(p.imagePath).getName());
        normStack.show();
        IJ.log("Step 3: F/F0 normalization completed.");
    }

    /**
     * This workflow treats one grayscale stack axis as time. Plain ImageJ stacks
     * store that axis as Z; time hyperstacks use T. Do not flatten channels or
     * simultaneous Z/T axes into frames.
     */
    static void requireSupportedMovie(ImagePlus source) {
        if (source == null || source.getProcessor() == null)
            throw new IllegalArgumentException("Open a calcium image first.");
        if (source.getNChannels() != 1 || source.getBitDepth() == 24
                || (source.getNSlices() > 1 && source.getNFrames() > 1))
            throw new IllegalArgumentException(
                    "Calcium analysis requires a single-channel grayscale movie: "
                    + "a plain stack or a time series with one Z plane. "
                    + "RGB, multiple channels, and combined Z/T stacks are not supported "
                    + "(C=" + source.getNChannels() + ", Z=" + source.getNSlices()
                    + ", T=" + source.getNFrames() + ", bit depth=" + source.getBitDepth() + ").");
    }

    /** Use the selected movie frames and ImageJ's unchanged projection algorithm. */
    static ImagePlus projectFrames(ImagePlus source, int first, int last, int method) {
        requireSupportedMovie(source);
        if (first < 1 || last < first || last > source.getStackSize())
            throw new IllegalArgumentException("Invalid calcium frame range.");
        ZProjector projector = new ZProjector(source);
        projector.setStartSlice(first);
        projector.setStopSlice(last);
        projector.setMethod(method);
        projector.doProjection();
        ImagePlus result = projector.getProjection();
        if (result == null || result == source || result.getStackSize() != 1)
            throw new IllegalStateException("ImageJ did not return a calcium projection.");
        result.setCalibration(source.getCalibration().copy());
        return result;
    }

    /** Keep ImageJ Divide/create/32-bit/stack semantics, including zero-baseline values. */
    static ImagePlus divideByBaseline(ImagePlus source, ImagePlus baseline) {
        requireSupportedMovie(source);
        requireSupportedMovie(baseline);
        if (baseline.getStackSize() != 1 || baseline.getWidth() != source.getWidth()
                || baseline.getHeight() != source.getHeight())
            throw new IllegalArgumentException("Calcium baseline must be a single plane matching the movie dimensions.");
        ImagePlus result = new ImageCalculator().run("Divide create 32-bit stack", source, baseline);
        if (result == null || result == source || result.getStackSize() != source.getStackSize())
            throw new IllegalStateException("ImageJ did not return a complete F/F0 stack.");
        result.setDimensions(source.getNChannels(), source.getNSlices(), source.getNFrames());
        result.setOpenAsHyperStack(source.isHyperStack());
        result.setCalibration(source.getCalibration().copy());
        return result;
    }

    /** Step 4: Initialize ROI Manager */
    public void setupROIManager() {
        rm = RoiManager.getInstance();
        if (rm == null) rm = new RoiManager();
        rm.reset();
        IJ.log("Step 4: ROI Manager initialized and cleared.");
    }

    /** Step 5: Import or generate ROIs for the specified cell type */
    public void handleCellType(int i) {
        String cellName = (p.cellNames != null && p.cellNames.size() > i)
                ? p.cellNames.get(i)
                : "CellType" + (i + 1);

        boolean imported = false;

        // Try importing ROI file if path is provided
        if (p.roiPath != null && !p.roiPath.isEmpty()) {
            File roiFile = new File(p.roiPath);
            if (roiFile.exists()) {
                try {
                    rm.runCommand("Open", roiFile.getAbsolutePath());
                    IJ.showMessage("ROIs Imported",
                            "Successfully imported ROIs from:\n" + roiFile.getName());
                    imported = true;
                } catch (Exception ex) {
                    IJ.showMessage("Error", "Failed to import ROIs:\n" + ex.getMessage());
                }
            } else {
                IJ.showMessage("ROI File Missing",
                        "The specified ROI file does not exist:\n" + roiFile.getAbsolutePath());
            }
        }

        // If no ROI imported, attempt automated segmentation with StarDist
        if (!imported && p.useStarDist) {
            try {
                runStarDist(maxProj, new File(p.imagePath).getParentFile());
                IJ.showMessage("StarDist Segmentation Completed",
                        "ROIs generated automatically for " + cellName + ".");
                imported = true;
            } catch (Exception ex) {
                IJ.showMessage("StarDist Error",
                        "StarDist segmentation failed: " + ex.getMessage());
            }
        }

        // If still no ROIs, prompt user to manually draw
        if (!imported) {
            IJ.selectWindow(maxProj.getTitle());
            IJ.setTool("oval");
            IJ.showMessage("Draw ROIs",
                    "No ROI file provided.\nPlease manually draw ROIs for " + cellName +
                    " using Oval or Freehand tools.");
        }
    }

    /** Step 6: Rename ROIs according to cell names */
    public void renameROIs() {
        int roiCount = rm.getCount();
        for (int r = 0; r < roiCount; r++) {
            String name = (p.cellNames != null && !p.cellNames.isEmpty())
                    ? p.cellNames.get(r % p.cellNames.size()) + "_" + (r + 1)
                    : "Cell_" + (r + 1);
            IJ.runMacro("roiManager(\"Select\", " + r + ");");
            IJ.runMacro("roiManager(\"Rename\", \"" + name + "\");");
        }
    }

    /** Step 7: Measure intensity for all ROIs in the normalized stack */
    public void measureROIs() {
        IJ.selectWindow(normStack.getTitle());
        IJ.run("Set Measurements...", "mean redirect=None decimal=2");
        rm.runCommand("Multi Measure");
        IJ.wait(50); // small delay to ensure measurements are recorded
    }

    /** Step 8: Save measurement results and ROIs to RESULTS folder */
    public File saveResults() {
        File imgFile = new File(p.imagePath);
        File resultsDir = new File(imgFile.getParentFile(),
                "RESULTS" + File.separator + imgFile.getName().replace(".tif", ""));
        if (!resultsDir.exists()) resultsDir.mkdirs();

        // Save measurements CSV
        File csvFile = new File(resultsDir, "RESULTS_" + imgFile.getName() + ".csv");
        IJ.saveAs("Results", csvFile.getAbsolutePath());

        // Save normalized stack if applicable
        if (p.useFF0) {
            IJ.selectWindow(normStack.getTitle());
            IJ.run("Select None");
            rm.deselect();
            IJ.saveAs("Tiff", new File(resultsDir, normStack.getTitle() + ".tif").getAbsolutePath());
            IJ.run("Close");
        }

        // Save all ROIs
        rm.deselect();
        rm.runCommand("Save", new File(resultsDir, "ROIS_" + imgFile.getName() + "_CELLS.zip").getAbsolutePath());
        IJ.log("Step 8: Results and ROIs saved at " + resultsDir.getAbsolutePath());

        return csvFile;
    }

    /** Run StarDist segmentation (currently disabled) */
    private void runStarDist(ImagePlus img, File resultsDir) {
        // A disabled implementation must not return as if it generated ROIs.
        // The caller keeps imported=false and offers the existing manual route.
        throw new UnsupportedOperationException(
                "Automatic calcium StarDist ROI generation is not implemented. "
                + "Import ROI ZIPs or draw ROIs manually.");
    }

    /** Prompt user to select start and end frames for max projection */
    private int[] promptForFrames(int stackSize) {
        JPanel panel = new JPanel(new GridLayout(2, 2, 4, 4));

        SpinnerNumberModel startModel = new SpinnerNumberModel(1, 1, stackSize, 1);
        SpinnerNumberModel endModel = new SpinnerNumberModel(stackSize, 1, stackSize, 1);

        JSpinner startSpinner = new JSpinner(startModel);
        JSpinner endSpinner = new JSpinner(endModel);

        panel.add(new JLabel("Start frame:"));
        panel.add(startSpinner);
        panel.add(new JLabel("End frame:"));
        panel.add(endSpinner);

        int option = JOptionPane.showConfirmDialog(
                null, panel, "Select Max Projection Frames", JOptionPane.OK_CANCEL_OPTION, JOptionPane.PLAIN_MESSAGE);

        if (option == JOptionPane.OK_OPTION) {
            int start = (Integer) startSpinner.getValue();
            int end = (Integer) endSpinner.getValue();
            if (start > end) {
                IJ.showMessage("Error", "Start frame must be ≤ end frame.");
                return null;
            }
            return new int[]{start, end};
        }
        return null;
    }

    /** Prompt user to select start and end frames for baseline calculation */
    private int[] promptForBaseline(int stackSize) {
        JPanel panel = new JPanel(new GridLayout(2, 2, 4, 4));

        SpinnerNumberModel startModel = new SpinnerNumberModel(1, 1, stackSize, 1);
        SpinnerNumberModel endModel = new SpinnerNumberModel(stackSize, 1, stackSize, 1);

        JSpinner startSpinner = new JSpinner(startModel);
        JSpinner endSpinner = new JSpinner(endModel);

        panel.add(new JLabel("Start frame:"));
        panel.add(startSpinner);
        panel.add(new JLabel("End frame:"));
        panel.add(endSpinner);

        int option = JOptionPane.showConfirmDialog(
                null, panel, "Select Baseline Frames", JOptionPane.OK_CANCEL_OPTION, JOptionPane.PLAIN_MESSAGE);

        if (option == JOptionPane.OK_OPTION) {
            int start = (Integer) startSpinner.getValue();
            int end = (Integer) endSpinner.getValue();
            if (start > end) {
                IJ.showMessage("Error", "Start frame must be ≤ end frame.");
                return null;
            }
            return new int[]{start, end};
        }
        return null;
    }
}

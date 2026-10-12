package Features.Macros;

import Features.Inference.InferenceBackend;
import Features.Inference.NativeAlignmentClient;
import ij.IJ;
import ij.ImagePlus;
import ij.Macro;
import ij.measure.ResultsTable;
import java.io.IOException;
import java.util.Locale;

/** Only the native-library boundary for the three original alignment calls. */
public final class LegacyTemplateMatching {
    private LegacyTemplateMatching() { }

    /** ImageJ macro call() accepts String arguments and a String return value. */
    public static String run(String options) {
        if (!useNativeWorker()) {
            IJ.run("Align slices in stack...", options);
            return "legacy";
        }
        ImagePlus image = IJ.getImage();
        int reference = validateOptions(image, options);
        try {
            double[][] shifts = NativeAlignmentClient.predict(IJ.getDirectory("imagej"), image, reference);
            ImagePlus result = NativeAlignmentClient.translatedCopy(image, shifts);
            // All computation/validation succeeds before touching the input.
            int channels = image.getNChannels(), slices = image.getNSlices(), frames = image.getNFrames();
            boolean hyperstack = image.getOpenAsHyperStack();
            image.setStack(image.getTitle(), result.getStack());
            image.setDimensions(channels, slices, frames);
            image.setOpenAsHyperStack(hyperstack);
            image.setDisplayRange(result.getDisplayRangeMin(), result.getDisplayRangeMax());
            // The original command leaves this reference slice and template ROI
            // selected; preserve this observable macro/UI state too.
            image.setSlice(reference);
            image.setRoi((int) Math.floor(image.getWidth() / 6.0), (int) Math.floor(image.getHeight() / 6.0),
                    (int) Math.floor(image.getWidth() * .7), (int) Math.floor(image.getHeight() * .7));
            image.updateAndDraw();
            ResultsTable table = resultsTable(shifts, reference);
            for (int row = 0; row < table.size(); row++)
                IJ.log("Slice:" + (int) table.getValue("Slice", row) + " X displacement:"
                        + table.getValue("dX", row) + " Y displacement:" + table.getValue("dY", row));
            if (Boolean.parseBoolean(Macro.getValue(options, "show", "true"))) table.show("Results");
            return "native";
        } catch (InterruptedException error) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Legacy macro Template Matching interrupted; input was not changed.", error);
        } catch (IOException error) {
            throw new IllegalStateException("Legacy macro Template Matching failed; input was not changed: " + error.getMessage(), error);
        }
    }

    static boolean useNativeWorker() {
        String mode = System.getProperty("gat.alignment.backend", "auto").trim().toLowerCase(Locale.ROOT);
        boolean apple = InferenceBackend.isAppleSiliconMac();
        if ("native".equals(mode)) return true;
        if ("auto".equals(mode)) return apple;
        if ("legacy".equals(mode) && !apple) return false;
        if ("legacy".equals(mode)) throw new IllegalStateException("Legacy Template Matching cannot run on Apple Silicon; use the native worker.");
        throw new IllegalArgumentException("gat.alignment.backend must be auto, native or legacy.");
    }

    static int validateOptions(ImagePlus image, String options) {
        if (image == null || options == null) throw new IllegalArgumentException("Missing alignment image/options.");
        int reference = integer(options, "ref.slice", 1);
        if (integer(options, "method", 5) != 5 || integer(options, "swindow", 0) != 0
                || Boolean.parseBoolean(Macro.getValue(options, "subpixel", "true"))
                || integer(options, "itpmethod", 0) != 0
                || integer(options, "windowsizex", 512) != (int) Math.floor(image.getWidth() * .7)
                || integer(options, "windowsizey", 512) != (int) Math.floor(image.getHeight() * .7)
                || integer(options, "x0", 0) != (int) Math.floor(image.getWidth() / 6.0)
                || integer(options, "y0", 0) != (int) Math.floor(image.getHeight() / 6.0))
            throw new IllegalArgumentException("Native MacroFork requires the original macro's method=5, 70% template at floor(size/6), full search and integer shifts. No different settings are substituted.");
        if (reference < 1 || reference > image.getStackSize()) throw new IllegalArgumentException("Invalid alignment reference slice.");
        return reference;
    }

    private static int integer(String options, String key, int fallback) {
        return Integer.parseInt(Macro.getValue(options, key, Integer.toString(fallback)));
    }

    static ResultsTable resultsTable(double[][] shifts, int reference) {
        ResultsTable table = new ResultsTable();
        // Original plugin exports before-reference slices in descending order,
        // then after-reference slices ascending. It omits the reference row.
        for (int slice = reference - 1; slice > 0; slice--) add(table, shifts, slice);
        for (int slice = reference + 1; slice <= shifts.length; slice++) add(table, shifts, slice);
        return table;
    }

    private static void add(ResultsTable table, double[][] shifts, int slice) {
        table.incrementCounter(); table.addValue("Slice", slice);
        table.addValue("dX", shifts[slice - 1][0]); table.addValue("dY", shifts[slice - 1][1]);
    }
}

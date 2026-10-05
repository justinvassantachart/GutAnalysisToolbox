package Features.Inference;

import Features.Core.PluginCalls;
import ij.IJ;
import ij.ImagePlus;
import ij.ImageStack;
import ij.WindowManager;
import ij.process.FloatProcessor;
import java.io.File;
import java.io.IOException;
import java.text.DecimalFormat;
import java.text.DecimalFormatSymbols;
import java.util.Locale;

/** Runs only neural inference externally, then uses the unchanged Fiji StarDist NMS command. */
public final class NativeStarDist {
    private NativeStarDist() { }

    public static ImagePlus run(ImagePlus input, String modelZip, double probability, double overlap) {
        if (input == null || input.getStackSize() != 1 || input.getNChannels() != 1 || input.getBitDepth() == 24)
            throw new IllegalArgumentException("Native GAT StarDist expects one 2D grayscale channel.");
        if (!Double.isFinite(probability) || !Double.isFinite(overlap)
                || probability < 0 || probability > 1 || overlap < 0 || overlap > 1)
            throw new IllegalArgumentException("StarDist probability and overlap thresholds must be within 0–1.");
        NativeInferenceClient.Prediction prediction;
        try {
            prediction = NativeInferenceClient.predict(IJ.getDirectory("imagej"), new File(modelZip),
                    input.getWidth(), input.getHeight(), (float[]) input.getProcessor().convertToFloatProcessor().getPixels(),
                    PluginCalls.suggestTiles(input.getWidth(), input.getHeight()));
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("GAT native inference was interrupted.", e);
        } catch (IOException e) {
            throw new IllegalStateException(e.getMessage(), e);
        }
        return postprocess(input, prediction, probability, overlap);
    }

    private static ImagePlus postprocess(ImagePlus input, NativeInferenceClient.Prediction p, double probability, double overlap) {
        String id = Long.toHexString(System.nanoTime());
        ImagePlus prob = new ImagePlus("GAT_prob_" + id, new FloatProcessor(p.width, p.height, p.planes[0]));
        ImageStack rays = new ImageStack(p.width, p.height);
        for (int c = 1; c < p.planes.length; c++) rays.addSlice(new FloatProcessor(p.width, p.height, p.planes[c]));
        ImagePlus dist = new ImagePlus("GAT_dist_" + id, rays);
        dist.setDimensions(p.planes.length - 1, 1, 1);
        dist.setOpenAsHyperStack(true);
        prob.setCalibration(input.getCalibration()); dist.setCalibration(input.getCalibration());
        try {
            // Command From Macro resolves ImagePlus inputs by their registered title.
            registerWithoutVisibleWindow(prob);
            registerWithoutVisibleWindow(dist);
            int[] before = WindowManager.getIDList();
            String args = nmsArguments(prob.getTitle(), dist.getTitle(), probability, overlap);
            IJ.run("Command From Macro", args);
            ImagePlus labels = PluginCalls.findNewImageSince(before);
            // Never use the input/current image as a fallback for failed NMS.
            if (labels == null || labels.getWidth() != p.width || labels.getHeight() != p.height || labels.getBitDepth() != 16)
                throw new IllegalStateException("StarDist NMS did not return the expected 16-bit label image. "
                        + "Check that StarDist 0.3.0 and its dependencies are installed.");
            labels.setCalibration(input.getCalibration()); labels.hide();
            return labels;
        } finally {
            prob.changes = false; prob.close();
            dist.changes = false; dist.close();
        }
    }

    static String nmsArguments(String probabilityTitle, String distanceTitle, double probability, double overlap) {
        // Match the legacy PluginCalls formatter, including six-digit rounding.
        DecimalFormat threshold = new DecimalFormat("0.######", DecimalFormatSymbols.getInstance(Locale.US));
        return "command=[de.csbdresden.stardist.StarDist2DNMS],args=['prob':'" + probabilityTitle
                + "','dist':'" + distanceTitle + "','probThresh':'" + threshold.format(probability)
                + "','nmsThresh':'" + threshold.format(overlap) + "','outputType':'Label Image',"
                + "'excludeBoundary':'2','roiPosition':'Stack','verbose':'false'], process=[false]";
    }

    static void registerWithoutVisibleWindow(ImagePlus image) {
        image.show();
        // ImagePlus.hide() unregisters the image and breaks title-based macro
        // lookup. Hide only its window, preserving WindowManager registration.
        if (image.getWindow() != null) image.getWindow().setVisible(false);
    }
}

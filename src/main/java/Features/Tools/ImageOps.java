package Features.Tools;

import ij.IJ;
import ij.ImagePlus;
import ij.measure.Calibration;
import ij.plugin.ZProjector;
import ij.plugin.HyperStackConverter;

import static Features.Core.PluginCalls.findNewImageSince;


/**
 * Low-level image manipulation helpers (projection, channel extraction, resizing)
 * with consistent calibration handling and minimal UI side-effects.
 *
 * Pipelines use these instead of calling ZProjector / Scale... / etc. directly.
 */
public final class ImageOps {
    private ImageOps() {}

    /**
     * Max Intensity Projection across Z.
     *
     * @param src Z-stack or hyperstack.
     * @return    New ImagePlus containing the max projection across all slices,
     *            with calibration copied and title "MAX_<srcTitle>".
     */
    public static ImagePlus mip(ImagePlus src) {
        if (src == null || src.getStackSize() < 1)
            throw new IllegalArgumentException("Select an image to project.");
        // ZProjector.doProjection treats a hyperstack as a flat stack. Split
        // by C/T explicitly so it cannot combine channels or time points.
        ij.ImageStack projected = new ij.ImageStack(src.getWidth(), src.getHeight());
        for (int t = 1; t <= src.getNFrames(); t++) {
            for (int c = 1; c <= src.getNChannels(); c++) {
                ij.ImageStack planes = new ij.ImageStack(src.getWidth(), src.getHeight());
                for (int z = 1; z <= src.getNSlices(); z++)
                    planes.addSlice(src.getStack().getProcessor(src.getStackIndex(c, z, t)));
                ImagePlus channel = new ImagePlus("projection channel", planes);
                ZProjector zp = new ZProjector(channel);
                zp.setMethod(ZProjector.MAX_METHOD);
                zp.setStartSlice(1);
                zp.setStopSlice(planes.size());
                if (src.getBitDepth() == 24) zp.doRGBProjection();
                else zp.doProjection();
                projected.addSlice(zp.getProjection().getProcessor());
            }
        }
        ImagePlus out = new ImagePlus("MAX_" + src.getTitle(), projected);
        out.setDimensions(src.getNChannels(), 1, src.getNFrames());
        out.setOpenAsHyperStack(src.getNChannels() > 1 || src.getNFrames() > 1);
        if (src instanceof ij.CompositeImage) {
            ij.CompositeImage composite = new ij.CompositeImage(out, ((ij.CompositeImage) src).getMode());
            composite.setLuts(((ij.CompositeImage) src).getLuts());
            out = composite;
        }
        out.setCalibration(src.getCalibration().copy());
        return out;
    }

    /**
     * Extract a single channel (1-based index from a possibly multi-channel stack)
     * as its own single-channel image.
     *
     * Behavior:
     *   - Duplicates only that channel across all Z/T.
     *   - Converts result to a 1-channel hyperstack if needed.
     *   - Copies calibration.
     *
     * If the source only has 1 channel, just returns a duplicate.
     *
     * @param imp The multi-channel source image.
     * @param c1  1-based channel index to extract.
     * @return    Single-channel ImagePlus with matching calibration.
     */
    public static ImagePlus extractChannel(ImagePlus imp, int c1) {
        if (imp.getNChannels()==1) return imp.duplicate();
        int ch = Math.max(1, Math.min(c1, imp.getNChannels()));
        ImagePlus dup = new ij.plugin.Duplicator().run(imp, ch, ch, 1, imp.getNSlices(), 1, imp.getNFrames());
        if (dup.getNChannels() > 1) {
            dup = ij.plugin.HyperStackConverter.toHyperStack(dup, 1, dup.getNSlices(), dup.getNFrames(), "default", "Color");
        }
        dup.setCalibration(imp.getCalibration());
        return dup;
    }

    /**
     * Resize an image to an exact width/height using "Scale..." with interpolation=None,
     * then fix the calibration so spatial units (microns per pixel) stay correct.
     *
     * This is mainly used for label maps (where we DON'T want interpolation to invent values).
     *
     * @param src   Source image.
     * @param newW  Target width in pixels.
     * @param newH  Target height in pixels.
     * @return      New hidden ImagePlus with updated calibration for the new pixel size.
     */
    public static ImagePlus resizeTo(ImagePlus src, int newW, int newH) {
        int[] before = ij.WindowManager.getIDList();
        SilentRun.on(src, "Scale...", "x=- y=- width="+newW+" height="+newH+" interpolation=None create");
        ImagePlus out = findNewImageSince(before); if (out == null) out = IJ.getImage();
        ij.measure.Calibration cal = src.getCalibration().copy();
        cal.pixelWidth  = cal.pixelWidth  * src.getWidth()  / (double) out.getWidth();
        cal.pixelHeight = cal.pixelHeight * src.getHeight() / (double) out.getHeight();
        out.setCalibration(cal);
        out.hide();
        return out;
    }

    /**
     * Resize an intensity image to an exact width/height using bilinear interpolation,
     * then:
     *   - Convert to grayscale,
     *   - Squash to a simple single-plane hyperstack,
     *   - Update calibration so microns-per-pixel scales properly.
     *
     * Used before StarDist so the pixel size matches the model's training scale.
     *
     * @param src   Source grayscale/fluorescence channel.
     * @param newW  Target width.
     * @param newH  Target height.
     * @return      New hidden ImagePlus (8-bit grayscale).
     */
    public static ImagePlus resizeToIntensity(ImagePlus src, int newW, int newH) {
        int[] before = ij.WindowManager.getIDList();
        SilentRun.on(src, "Scale...", "x=- y=- width="+newW+" height="+newH+" interpolation=Bilinear create");
        ImagePlus out = findNewImageSince(before); if (out == null) out = IJ.getImage();

        //hide our output
        out.hide();

        if (out.getType() == ImagePlus.COLOR_RGB) IJ.run(out, "8-bit", "");
        IJ.run(out, "Grays", "");
        out.setDimensions(1,1,1);
        out.setOpenAsHyperStack(false);

        ij.measure.Calibration cal = src.getCalibration().copy();
        cal.pixelWidth  = cal.pixelWidth  * src.getWidth()  / (double) out.getWidth();
        cal.pixelHeight = cal.pixelHeight * src.getHeight() / (double) out.getHeight();
        out.setCalibration(cal);
        out.hide();
        return out;
    }


}

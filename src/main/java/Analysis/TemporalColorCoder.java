package Analysis;

import Features.Core.Params;
import ij.IJ;
import ij.ImagePlus;
import ij.ImageStack;
import ij.process.ColorProcessor;
import ij.process.ImageProcessor;
import ij.plugin.ZProjector;
import ij.plugin.LutLoader;
import ij.process.LUT;
import java.awt.image.IndexColorModel;


/**
 * TemporalColorCoder
 * Converts a grayscale time-lapse stack into a temporally color-coded RGB stack.
 * Optionally applies Z-projection and creates a color scale.
 */
public class TemporalColorCoder {

    /** Output container for the RGB stack and optional color scale */
    public static class TemporalColorOutput {
        public final ImagePlus rgbStack;
        public final ImagePlus colorScale;

        public TemporalColorOutput(ImagePlus rgbStack, ImagePlus colorScale) {
            this.rgbStack = rgbStack;
            this.colorScale = colorScale;
        }
    }

    /**
     * Main workflow to convert a grayscale time-lapse stack to RGB with temporal color coding.
     *
     * @param imp Input single-channel ImagePlus stack
     * @param p Parameters including LUT, projection, and color scale options
     * @return TemporalColorOutput with the RGB stack and optional color scale
     * @throws Exception if input is null or multi-channel
     */
    public static TemporalColorOutput run(ImagePlus imp, Params p) throws Exception {
        if (imp == null) throw new IllegalArgumentException("Input stack cannot be null.");
        if (imp.getNChannels() > 1) throw new IllegalArgumentException("Multi-channel stacks are not supported.");
        if (imp.getBitDepth() == 24) throw new IllegalArgumentException("Select a grayscale movie, not an RGB image.");

        int width = imp.getWidth();
        int height = imp.getHeight();
        int slices = imp.getNSlices();
        int frames = imp.getNFrames();

        // Adjust dimensions if stack is interpreted differently
        boolean plainStack = slices > 1 && frames == 1;
        if (plainStack) {
            int tmp = slices;
            slices = frames;
            frames = tmp;
        }

        // Determine frame range for processing
        int startFrame = Math.max(1, p.referenceFrame);
        int endFrame = Math.min(frames, p.referenceFrameEnd > 0 ? p.referenceFrameEnd : frames);
        int totalFrames = endFrame - startFrame + 1;
        if (totalFrames < 1) throw new IllegalArgumentException("Selected temporal frame range is empty.");

        ImageStack rgbStack = new ImageStack(width, height);

        // Generate RGB lookup tables (LUTs) based on user selection
        int[][] rgbLUT = generateRGBLUT(p.lutName);
        int[] rLUT = rgbLUT[0];
        int[] gLUT = rgbLUT[1];
        int[] bLUT = rgbLUT[2];
        int lutSize = rLUT.length;

        // Loop through frames and slices to apply temporal color coding
        for (int t = startFrame; t <= endFrame; t++) {
            for (int z = 1; z <= slices; z++) {
                ImageProcessor ip = imp.getStack().getProcessor(plainStack ? t : imp.getStackIndex(1, z, t));
                // Preserve the established byte workflow. Wider grayscale data
                // must be display-scaled before RGB packing; float getPixel()
                // returns IEEE bits and raw 16-bit values can overflow channels.
                if (imp.getBitDepth() != 8) {
                    ip = ip.duplicate();
                    ip.setMinAndMax(imp.getDisplayRangeMin(), imp.getDisplayRangeMax());
                    ip = ip.convertToByte(true);
                }

                ColorProcessor cp = new ColorProcessor(width, height);

                // Map the current frame to a color index in the LUT
                int colorIndex = (int) Math.floor((lutSize / (double) totalFrames) * (t - startFrame));
                colorIndex = Math.min(colorIndex, lutSize - 1);

                // Apply LUT scaling to each pixel
                for (int y = 0; y < height; y++) {
                    for (int x = 0; x < width; x++) {
                        int gray = ip.getPixel(x, y);
                        double factor = gray / 255.0;
                        int r = (int) Math.round(rLUT[colorIndex] * factor);
                        int g = (int) Math.round(gLUT[colorIndex] * factor);
                        int b = (int) Math.round(bLUT[colorIndex] * factor);
                        cp.putPixel(x, y, (r << 16) | (g << 8) | b);
                    }
                }

                // Add the RGB slice to the output stack
                rgbStack.addSlice("Z" + z + "-T" + t, cp);
            }
        }

        ImagePlus rgbImp = new ImagePlus("TemporalColor_" + imp.getTitle(), rgbStack);
        rgbImp.setDimensions(1, slices, totalFrames);
        rgbImp.setOpenAsHyperStack(totalFrames > 1);
        rgbImp.setCalibration(imp.getCalibration().copy());

        // Apply optional Z-projection
        if (p.projectionMethod != null && !p.projectionMethod.isEmpty()) {
            int projection;
            switch (p.projectionMethod) {
                case "Average Intensity": projection = ZProjector.AVG_METHOD; break;
                case "Min Intensity": projection = ZProjector.MIN_METHOD; break;
                default: projection = ZProjector.MAX_METHOD; break;
            }
            // Like the legacy temporal macro, project TIME independently at
            // every Z. A flat stack projection mixes distinct optical planes.
            ImageStack projected = new ImageStack(width, height);
            for (int z = 1; z <= slices; z++) {
                ImageStack time = new ImageStack(width, height);
                for (int t = 0; t < totalFrames; t++)
                    time.addSlice(rgbStack.getProcessor(t * slices + z));
                ZProjector zp = new ZProjector(new ImagePlus("temporal plane", time));
                zp.setMethod(projection);
                zp.doProjection();
                projected.addSlice(zp.getProjection().getProcessor());
            }
            rgbImp = new ImagePlus("TemporalColor_" + imp.getTitle() + "_Proj", projected);
            rgbImp.setDimensions(1, slices, 1);
            rgbImp.setCalibration(imp.getCalibration().copy());
        }

        // Generate a color scale image if requested
        ImagePlus scaleImp = null;
        if (p.createColorScale) {
            scaleImp = createColorScale(rLUT, gLUT, bLUT, startFrame, endFrame);
        }

        // Display results unless running in batch mode
        // if (!p.batchMode) rgbImp.show();
        // if (!p.batchMode && scaleImp != null) scaleImp.show();

        return new TemporalColorOutput(rgbImp, scaleImp);
    }

    /** Generates RGB lookup tables based on a named LUT */
    private static int[][] generateRGBLUT(String lutName) {
        final int size = 256;
        int[] r = new int[size];
        int[] g = new int[size];
        int[] b = new int[size];

        try {
            // Use LutLoader to fetch the LUT by name
            IndexColorModel icm = LutLoader.getLut(lutName);
            if (icm == null) {
                IJ.log("LUT not found: " + lutName + ". Using default Fire LUT.");
                icm = LutLoader.getLut("Fire");
                if (icm == null) throw new IllegalStateException("Default LUT not found.");
            }

            // Pull RGB arrays from the IndexColorModel
            for (int i = 0; i < size; i++) {
                r[i] = icm.getRed(i);
                g[i] = icm.getGreen(i);
                b[i] = icm.getBlue(i);
            }

        } catch (Exception e) {
            IJ.log("Error loading LUT '" + lutName + "': " + e);
            // fallback to simple ramp
            for (int i = 0; i < size; i++) {
                float t = i / (float)(size - 1);
                r[i] = Math.min(255, (int)(255 * t));
                g[i] = Math.min(255, (int)(255 * t * 0.5));
                b[i] = 0;
            }
        }

        return new int[][] { r, g, b };
    }

    /** Creates a horizontal RGB color scale bar to show temporal mapping */
    private static ImagePlus createColorScale(int[] rLUT, int[] gLUT, int[] bLUT, int startFrame, int endFrame) {
        int width = 256;
        int height = 32;
        ImagePlus scale = IJ.createImage("TimeColorScale", "RGB", width, height, 1);
        ImageProcessor ip = scale.getProcessor();
        int totalFrames = endFrame - startFrame + 1;
        int lutSize = rLUT.length;

        // Map each horizontal pixel to the corresponding LUT color
        for (int x = 0; x < width; x++) {
            int lastColor = (int) Math.floor((lutSize / (double) totalFrames) * (totalFrames - 1));
            int frameIndex = (int) Math.floor(lastColor * x / (double) (width - 1));
            frameIndex = Math.min(frameIndex, lutSize - 1);
            int r = rLUT[frameIndex];
            int g = gLUT[frameIndex];
            int b = bLUT[frameIndex];
            int rgb = (r << 16) | (g << 8) | b;
            for (int y = 0; y < height; y++) ip.set(x, y, rgb);
        }

        return scale;
    }
}

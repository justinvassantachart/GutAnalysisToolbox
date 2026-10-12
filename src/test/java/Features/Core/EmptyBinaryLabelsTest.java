package Features.Core;

import ij.ImagePlus;
import ij.ImageStack;
import ij.Prefs;
import ij.process.ByteProcessor;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class EmptyBinaryLabelsTest {
    @Test void zeroMaskNeverBecomesOneFullFieldObjectWithEitherBackgroundPreference() {
        boolean old = Prefs.blackBackground;
        try {
            for (boolean black : new boolean[]{false, true}) {
                Prefs.blackBackground = black;
                for (boolean inverted : new boolean[]{false, true}) {
                    ByteProcessor pixels = new ByteProcessor(32, 24);
                    if (inverted) pixels.invertLut();
                    pixels.setThreshold(0, 0, 0);
                    ImagePlus source = new ImagePlus("empty", pixels);
                    source.getCalibration().pixelWidth = .31;
                    source.getCalibration().pixelHeight = .42;
                    source.getCalibration().setUnit("um");
                    ImagePlus labels = PluginCalls.binaryToLabels(source);
                    assertEquals(16, labels.getBitDepth());
                    assertEquals(32, labels.getWidth()); assertEquals(24, labels.getHeight());
                    for (int i = 0; i < 32 * 24; i++) {
                        assertEquals(0, labels.getProcessor().get(i));
                        assertEquals(0, source.getProcessor().get(i));
                    }
                    assertEquals(.31, labels.getCalibration().pixelWidth);
                    assertEquals(.42, labels.getCalibration().pixelHeight);
                    assertEquals(0, source.getProcessor().getMinThreshold());
                    assertEquals(inverted, source.getProcessor().isInvertedLut());
                    assertEquals(black, Prefs.blackBackground);
                }
            }
        } finally { Prefs.blackBackground = old; }
    }
    @Test void emptyHyperstackRetainsItsDeclaredDimensions() {
        ImageStack stack = new ImageStack(3, 2);
        for (int i = 0; i < 12; i++) stack.addSlice(new ByteProcessor(3, 2));
        ImagePlus source = new ImagePlus("empty-stack", stack);
        source.setDimensions(2, 3, 2); source.setOpenAsHyperStack(true);
        ImagePlus labels = PluginCalls.binaryToLabels(source);
        assertArrayEquals(source.getDimensions(), labels.getDimensions());
        assertEquals(16, labels.getBitDepth()); assertTrue(labels.getOpenAsHyperStack());
        for (int z = 1; z <= 12; z++) for (int i = 0; i < 6; i++)
            assertEquals(0, labels.getStack().getProcessor(z).get(i));
    }
}

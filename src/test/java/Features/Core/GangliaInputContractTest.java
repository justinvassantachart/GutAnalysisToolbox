package Features.Core;

import ij.ImagePlus;
import ij.ImageStack;
import ij.process.ByteProcessor;
import ij.process.FloatProcessor;
import ij.process.ImageProcessor;
import ij.process.ShortProcessor;
import org.junit.jupiter.api.Test;
import java.util.Arrays;
import java.util.Collections;
import static org.junit.jupiter.api.Assertions.*;

/** Real pixels and result objects; no mocked inference or ImageJ processing. */
class GangliaInputContractTest {
    private static ImagePlus source() {
        return source(
                new ByteProcessor(2, 2, new byte[]{(byte)255, 0, 64, (byte)128}, null),
                new ByteProcessor(2, 2, new byte[]{(byte)128, (byte)255, 0, 64}, null));
    }

    private static ImagePlus source(ImageProcessor... channels) {
        ImageStack stack = new ImageStack(channels[0].getWidth(), channels[0].getHeight());
        for (ImageProcessor channel : channels) stack.addSlice(channel);
        ImagePlus source = new ImagePlus("original", stack);
        source.setDimensions(channels.length, 1, 1);
        source.getCalibration().pixelWidth = .5;
        source.getCalibration().pixelHeight = .75;
        return source;
    }

    private static void assertInputChannels(PluginCalls.GangliaPrep prep, int[] hu, int[] ganglia) {
        ImagePlus input = prep.dijInput3C;
        int[][] expected = {hu, ganglia, hu};
        for (int channel = 1; channel <= 3; channel++) {
            float[] actual = (float[]) input.getStack().getProcessor(channel).getPixels();
            float[] normalized = new float[expected[channel - 1].length];
            for (int pixel = 0; pixel < normalized.length; pixel++) {
                // ImageJ FloatProcessor.multiply casts its multiplier to float first.
                normalized[pixel] = expected[channel - 1][pixel] * (float) (1.0 / 255.0);
            }
            // Exact equality catches missing, repeated or misplaced normalization.
            assertArrayEquals(normalized, actual, "channel " + channel);
        }
        for (int pixel = 0; pixel < hu.length; pixel++) {
            int rgb = (hu[pixel] << 16) | (ganglia[pixel] << 8) | hu[pixel];
            assertEquals(rgb, prep.rgbForOverlay.getProcessor().get(pixel) & 0xffffff);
        }
    }

    @Test void gangliaInputMatchesV2UnitRangeAndRgbChannelOrder() {
        ImagePlus source = source();
        PluginCalls.GangliaPrep prep = PluginCalls.prepareGangliaInputs(source, 2, 1);
        ImagePlus input = prep.dijInput3C;
        assertEquals(32, input.getBitDepth());
        assertEquals(3, input.getNChannels());
        assertEquals(1, input.getNSlices());
        assertEquals(1, input.getNFrames());
        assertInputChannels(prep, new int[]{255,0,64,128}, new int[]{128,255,0,64});
        assertEquals(.5, input.getCalibration().pixelWidth);
        assertEquals(.75, input.getCalibration().pixelHeight);
        assertEquals(.5, prep.rgbForOverlay.getCalibration().pixelWidth);
        assertEquals(.75, prep.rgbForOverlay.getCalibration().pixelHeight);
        assertEquals(24, prep.rgbForOverlay.getBitDepth());
        assertEquals("R", input.getStack().getSliceLabel(1));
        assertEquals("G", input.getStack().getSliceLabel(2));
        assertEquals("B", input.getStack().getSliceLabel(3));
        assertNull(input.getWindow());
        assertNull(prep.rgbForOverlay.getWindow());
        assertArrayEquals(new byte[]{(byte)255,0,64,(byte)128},
                (byte[]) source.getStack().getProcessor(1).getPixels());
        assertArrayEquals(new byte[]{(byte)128,(byte)255,0,64},
                (byte[]) source.getStack().getProcessor(2).getPixels());
        assertEquals("original", source.getTitle());
        assertEquals(8, source.getBitDepth());
        assertEquals(2, source.getNChannels());
    }

    @Test void everyByteValueIsNormalizedExactlyOnceWithoutChangingTheOverlay() {
        byte[] hu = new byte[256], ganglia = new byte[256];
        int[] expectedHu = new int[256], expectedGanglia = new int[256];
        for (int pixel = 0; pixel < 256; pixel++) {
            hu[pixel] = (byte) pixel;
            ganglia[pixel] = (byte) (255 - pixel);
            expectedHu[pixel] = pixel;
            expectedGanglia[pixel] = 255 - pixel;
        }
        ImagePlus source = source(new ByteProcessor(16,16,hu,null),
                new ByteProcessor(16,16,ganglia,null));
        assertInputChannels(PluginCalls.prepareGangliaInputs(source,2,1), expectedHu, expectedGanglia);
    }

    @Test void selectedChannelsStillMapHuToMagentaAndGangliaToGreen() {
        assertInputChannels(PluginCalls.prepareGangliaInputs(source(),1,2),
                new int[]{128,255,0,64}, new int[]{255,0,64,128});
    }

    @Test void sixteenBitChannelsKeepV2ByteConversionBeforeNormalization() {
        short[] hu = {1000,(short)65535,1000,(short)65535};
        short[] ganglia = {2000,2000,1000,1000};
        ImagePlus source = source(new ShortProcessor(2,2,hu.clone(),null),
                new ShortProcessor(2,2,ganglia.clone(),null));
        // V2 resets each extracted channel's display range before byte conversion.
        source.setDisplayRange(0,65535);
        assertInputChannels(PluginCalls.prepareGangliaInputs(source,2,1),
                new int[]{0,255,0,255}, new int[]{255,255,0,0});
        assertEquals(0, source.getDisplayRangeMin());
        assertEquals(65535, source.getDisplayRangeMax());
        assertArrayEquals(hu, (short[]) source.getStack().getProcessor(1).getPixels());
        assertArrayEquals(ganglia, (short[]) source.getStack().getProcessor(2).getPixels());
    }

    @Test void floatChannelsKeepV2RangeResetAndByteQuantizationBeforeNormalization() {
        float[] hu = {-2,1,-1,0}, ganglia = {30,10,20,40};
        ImagePlus source = source(new FloatProcessor(2,2,hu.clone()),
                new FloatProcessor(2,2,ganglia.clone()));
        source.setDisplayRange(-100,100);
        assertInputChannels(PluginCalls.prepareGangliaInputs(source,2,1),
                new int[]{0,255,85,170}, new int[]{170,0,85,255});
        assertEquals(-100, source.getDisplayRangeMin());
        assertEquals(100, source.getDisplayRangeMax());
        assertArrayEquals(hu, (float[]) source.getStack().getProcessor(1).getPixels());
        assertArrayEquals(ganglia, (float[]) source.getStack().getProcessor(2).getPixels());
    }

    @Test void oneSourceChannelIsRepeatedAcrossTheThreeV2InputChannels() {
        ImagePlus source = source(new ByteProcessor(2,2,new byte[]{0,1,127,(byte)255},null));
        assertInputChannels(PluginCalls.prepareGangliaInputs(source,1,1),
                new int[]{0,1,127,255}, new int[]{0,1,127,255});
    }

    private static ImagePlus result(String title, int w, int h) {
        return new ImagePlus(title, new FloatProcessor(w, h));
    }

    @Test void onlyTheCurrentRequestsNewOutputIsAccepted() {
        ImagePlus expected = result("GAT_ganglia_test_output0",2,2);
        ImagePlus previous = result("GAT_ganglia_old_output0",2,2);
        assertSame(expected, PluginCalls.selectGangliaOutput("GAT_ganglia_test",2,2,
                Arrays.asList(previous, result("unrelated",2,2), expected)));
    }

    @Test void missingOrAmbiguousResultsDoNotFallBackToAnOldImage() {
        assertThrows(IllegalStateException.class, () -> PluginCalls.selectGangliaOutput("request",2,2,
                Collections.singletonList(result("old_output0",2,2))));
        assertThrows(IllegalStateException.class, () -> PluginCalls.selectGangliaOutput("request",2,2,
                Arrays.asList(result("request_output0",2,2), result("request_output1",2,2))));
    }

    @Test void wrongShapeAndNonfiniteResultsAreRejected() {
        assertThrows(IllegalStateException.class, () -> PluginCalls.selectGangliaOutput("request",2,2,
                Collections.singletonList(result("request_output0",3,2))));
        ImagePlus nan = result("request_output0",2,2);
        nan.getProcessor().setf(0,Float.NaN);
        assertThrows(IllegalStateException.class, () -> PluginCalls.selectGangliaOutput("request",2,2,
                Collections.singletonList(nan)));
    }
}

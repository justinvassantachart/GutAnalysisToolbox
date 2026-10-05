package Features.Core;

import ij.ImagePlus;
import ij.ImageStack;
import ij.process.ByteProcessor;
import ij.process.FloatProcessor;
import org.junit.jupiter.api.Test;
import java.util.Arrays;
import java.util.Collections;
import static org.junit.jupiter.api.Assertions.*;

/** Real pixels and result objects; no mocked inference or ImageJ processing. */
class GangliaInputContractTest {
    private static ImagePlus source() {
        ImageStack stack = new ImageStack(2, 2);
        stack.addSlice(new ByteProcessor(2, 2, new byte[]{(byte)255, 0, 64, (byte)128}, null));
        stack.addSlice(new ByteProcessor(2, 2, new byte[]{(byte)128, (byte)255, 0, 64}, null));
        ImagePlus source = new ImagePlus("original", stack);
        source.setDimensions(2, 1, 1);
        source.getCalibration().pixelWidth = .5;
        source.getCalibration().pixelHeight = .75;
        return source;
    }

    @Test void gangliaInputPreservesByteRangeAndRgbChannelOrderForRdfNormalization() {
        ImagePlus source = source();
        PluginCalls.GangliaPrep prep = PluginCalls.prepareGangliaInputs(source, 2, 1);
        ImagePlus input = prep.dijInput3C;
        assertEquals(32, input.getBitDepth());
        assertEquals(3, input.getNChannels());
        assertEquals(1, input.getNSlices());
        assertEquals(1, input.getNFrames());
        assertArrayEquals(new float[]{255,0,64,128}, (float[])input.getStack().getProcessor(1).getPixels());
        assertArrayEquals(new float[]{128,255,0,64}, (float[])input.getStack().getProcessor(2).getPixels());
        assertArrayEquals(new float[]{255,0,64,128}, (float[])input.getStack().getProcessor(3).getPixels());
        assertEquals(.5, input.getCalibration().pixelWidth);
        assertEquals(.75, input.getCalibration().pixelHeight);
        assertEquals(255, source.getStack().getProcessor(1).get(0));
        assertEquals(128, source.getStack().getProcessor(2).get(0));
        assertEquals(0xff80ff, prep.rgbForOverlay.getProcessor().get(0) & 0xffffff);
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

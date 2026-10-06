package Features.Tools;

import ij.ImagePlus;
import ij.ImageStack;
import ij.gui.Roi;
import ij.process.ByteProcessor;
import ij.process.ShortProcessor;
import org.junit.jupiter.api.Test;
import java.util.Arrays;
import java.util.Collections;
import static org.junit.jupiter.api.Assertions.*;

/** Real ImageJ pixels/metadata; no mocked ImagePlus or plugin result objects. */
class SiftResultHandlingTest {
    private static ImagePlus stack(String title, int planes) {
        ImageStack stack = new ImageStack(3, 2);
        for (int i = 0; i < planes; i++) {
            short[] pixels = new short[6];
            Arrays.fill(pixels, (short) (i + 1));
            stack.addSlice("plane-" + (i + 1), new ShortProcessor(3, 2, pixels, null));
        }
        ImagePlus image = new ImagePlus(title, stack);
        image.setDimensions(1, 1, planes);
        image.setOpenAsHyperStack(true);
        image.getCalibration().pixelWidth = .35;
        image.getCalibration().pixelHeight = .45;
        image.getCalibration().frameInterval = 2.5;
        image.getCalibration().setUnit("um");
        return image;
    }

    @Test void fullStackCopyIgnoresRoiAndHasIndependentPixelsAndCalibration() {
        ImagePlus input = stack("original", 3);
        Roi roi = new Roi(1, 0, 1, 1);
        input.setRoi(roi);
        input.setPosition(1, 1, 2);
        ImagePlus copy = AlignStack.duplicateAlignmentInput(input);
        assertEquals(3, copy.getWidth());
        assertEquals(2, copy.getHeight());
        assertEquals(3, copy.getNFrames());
        assertEquals(2, copy.getT());
        assertEquals(.35, copy.getCalibration().pixelWidth);
        assertEquals(.45, copy.getCalibration().pixelHeight);
        assertEquals(2.5, copy.getCalibration().frameInterval);
        copy.getStack().getProcessor(2).set(0, 99);
        copy.getCalibration().pixelWidth = 9;
        assertEquals(2, input.getStack().getProcessor(2).get(0));
        assertEquals(.35, input.getCalibration().pixelWidth);
        assertSame(roi, input.getRoi());
        assertEquals(2, input.getT());
    }

    @Test void firstChannelExtractionIsDeterministicAcrossZAndTime() {
        ImageStack pixels = new ImageStack(3, 2);
        for (int t = 1; t <= 3; t++) for (int z = 1; z <= 2; z++) for (int c = 1; c <= 2; c++) {
            short[] plane = new short[6];
            Arrays.fill(plane, (short) (100 * c + 10 * t + z));
            pixels.addSlice("c" + c + "z" + z + "t" + t, new ShortProcessor(3, 2, plane, null));
        }
        ImagePlus input = new ImagePlus("channels", pixels);
        input.setDimensions(2, 2, 3);
        input.setOpenAsHyperStack(true);
        input.setPosition(2, 2, 3);
        input.setRoi(new Roi(1, 0, 1, 1));
        input.getCalibration().pixelWidth = .7;
        input.getCalibration().frameInterval = 4;
        ImagePlus first = AlignStack.firstAlignmentChannel(input);
        assertEquals(1, first.getNChannels());
        assertEquals(2, first.getNSlices());
        assertEquals(3, first.getNFrames());
        assertEquals(3, first.getWidth());
        assertEquals(2, first.getHeight());
        for (int t = 1; t <= 3; t++) for (int z = 1; z <= 2; z++) {
            assertEquals(100 + 10 * t + z, first.getStack().getProcessor(first.getStackIndex(1, z, t)).get(0));
        }
        first.getStack().getProcessor(1).set(0, 0);
        assertEquals(111, input.getStack().getProcessor(1).get(0));
        assertEquals(2, input.getC());
        assertEquals(2, input.getZ());
        assertEquals(3, input.getT());
        assertEquals(.7, first.getCalibration().pixelWidth);
        assertEquals(4, first.getCalibration().frameInterval);
    }

    @Test void selectsOnlyCompleteNewResult() {
        ImagePlus input = stack("original", 3);
        ImagePlus partial = stack("Aligned 2 of 3", 2);
        ImagePlus result = stack("Aligned 3 of 3", 3);
        ImagePlus unrelated = stack("other image", 3);
        assertSame(result, AlignStack.selectSiftResult(input, Arrays.asList(partial, unrelated, result)));
        assertEquals(1, input.getStack().getProcessor(1).get(0));
    }

    @Test void missingPartialOrAmbiguousOutputNeverFallsBackToInput() {
        ImagePlus input = stack("original", 3);
        assertThrows(IllegalStateException.class, () -> AlignStack.selectSiftResult(input, Collections.emptyList()));
        assertThrows(IllegalStateException.class, () -> AlignStack.selectSiftResult(input, Collections.singletonList(stack("Aligned 2 of 3", 2))));
        assertThrows(IllegalStateException.class, () -> AlignStack.selectSiftResult(input,
                Arrays.asList(stack("Aligned 3 of 3", 3), stack("Aligned 3 of 3", 3))));
        assertEquals(3, input.getNFrames());
        assertEquals("original", input.getTitle());
        assertEquals(.35, input.getCalibration().pixelWidth);
        assertEquals(1, input.getStack().getProcessor(1).get(0));
    }

    @Test void rejectsWrongPixelTypeOrDimensions() {
        ImagePlus input = stack("original", 3);
        ImageStack wrongType = new ImageStack(3, 2);
        for (int i = 0; i < 3; i++) wrongType.addSlice(new ByteProcessor(3, 2));
        assertThrows(IllegalStateException.class, () -> AlignStack.selectSiftResult(input,
                Collections.singletonList(new ImagePlus("Aligned 3 of 3", wrongType))));
        ImageStack wrongSize = new ImageStack(4, 2);
        for (int i = 0; i < 3; i++) wrongSize.addSlice(new ShortProcessor(4, 2));
        assertThrows(IllegalStateException.class, () -> AlignStack.selectSiftResult(input,
                Collections.singletonList(new ImagePlus("Aligned 3 of 3", wrongSize))));
        assertEquals(1, input.getStack().getProcessor(1).get(0));
    }
}

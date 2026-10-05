package services.multiplex.core;

import ij.IJ;
import ij.ImagePlus;
import ij.ImageStack;
import ij.WindowManager;
import ij.io.FileSaver;
import ij.macro.Interpreter;
import ij.process.ByteProcessor;
import ij.process.ShortProcessor;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class MultiplexResultHandlingTest {
    @TempDir Path temporary;

    private static ImagePlus image(String title) {
        ImagePlus image = new ImagePlus(title, new ShortProcessor(40, 30));
        image.getProcessor().set(20, 10, 1234);
        image.getCalibration().pixelWidth = .5;
        image.getCalibration().pixelHeight = .75;
        image.getCalibration().pixelDepth = 2;
        image.getCalibration().frameInterval = 1.25;
        image.getCalibration().xOrigin = 4;
        image.getCalibration().yOrigin = 5;
        image.getCalibration().setUnit("um");
        return image;
    }

    @Test void selectsNewPluginOutputEvenWhenCurrentImageIsStillTheSource() {
        boolean previousBatch = Interpreter.batchMode;
        ImagePlus previousCurrent = WindowManager.getTempCurrentImage();
        ImagePlus reference = image("reference");
        ImagePlus source = image("source");
        ImagePlus stale = image("Transformedsource");
        ImagePlus result = image("Transformedsource");
        try {
            Interpreter.batchMode = true;
            reference.show();
            source.show();
            stale.show();
            List<ImagePlus> before = MultiplexRegistrationService.openImages();
            assertTrue(before.contains(reference));
            assertTrue(before.contains(source));
            assertTrue(before.contains(stale));
            result.show();
            IJ.selectWindow(source.getID());
            assertSame(source, WindowManager.getCurrentImage());
            assertSame(result, MultiplexRegistrationService.selectWarpedResult(
                    source, reference, before, MultiplexRegistrationService.openImages()));
            assertEquals(1234, source.getProcessor().get(20, 10));
            assertEquals(.5, source.getCalibration().pixelWidth);
            assertEquals("source", source.getTitle());
        } finally {
            reference.close();
            source.close();
            stale.close();
            result.close();
            Interpreter.batchMode = previousBatch;
            WindowManager.setTempCurrentImage(previousCurrent);
        }
    }

    @Test void missingStaleUnrelatedAndAmbiguousOutputsFailInsteadOfUsingTheSource() {
        ImagePlus reference = image("reference");
        ImagePlus source = image("source");
        ImagePlus stale = image("Transformedsource");
        List<ImagePlus> before = Arrays.asList(source, reference, stale);
        assertThrows(IllegalStateException.class, () -> MultiplexRegistrationService.selectWarpedResult(
                source, reference, before, before));
        assertThrows(IllegalStateException.class, () -> MultiplexRegistrationService.selectWarpedResult(
                source, reference, before, Collections.emptyList()));
        assertThrows(IllegalStateException.class, () -> MultiplexRegistrationService.selectWarpedResult(
                source, reference, before, Arrays.asList(source, image("unrelated"))));
        assertThrows(IllegalStateException.class, () -> MultiplexRegistrationService.selectWarpedResult(
                source, reference, before, Arrays.asList(image("Transformedsource"), image("Transformedsource"))));
        assertEquals(1234, source.getProcessor().get(20, 10));
    }

    @Test void rejectsWrongSizePixelTypeAndPlaneCount() {
        ImagePlus reference = image("reference");
        ImagePlus source = image("source");
        ImageStack multiple = new ImageStack(40, 30);
        multiple.addSlice(new ShortProcessor(40, 30));
        multiple.addSlice(new ShortProcessor(40, 30));
        for (ImagePlus wrong : Arrays.asList(
                new ImagePlus("Transformedsource", new ByteProcessor(40, 30)),
                new ImagePlus("Transformedsource", new ShortProcessor(41, 30)),
                new ImagePlus("Transformedsource", new ShortProcessor(40, 31)),
                new ImagePlus("Transformedsource", multiple))) {
            assertThrows(IllegalStateException.class, () -> MultiplexRegistrationService.selectWarpedResult(
                    source, reference, Arrays.asList(source, reference), Collections.singletonList(wrong)));
        }
    }

    @Test void bothExportStacksPreserveReferenceCalibrationAfterTiffRoundTrip() throws Exception {
        ImagePlus reference = image("reference");
        Path sourcePath = temporary.resolve("source.tif");
        assertTrue(new FileSaver(reference).saveAsTiff(sourcePath.toString()));
        byte[] originalFile = Files.readAllBytes(sourcePath);
        ImagePlus reopenedReference = IJ.openImage(sourcePath.toString());
        for (String title : Arrays.asList("hu_stack", "STACK")) {
            ImagePlus output = MultiplexRegistrationService.createOutputStack(title, reopenedReference);
            assertEquals(reopenedReference.getWidth(), output.getWidth());
            assertEquals(reopenedReference.getHeight(), output.getHeight());
            assertEquals(reopenedReference.getBitDepth(), output.getBitDepth());
            assertNotSame(reopenedReference.getCalibration(), output.getCalibration());
            ImageStack planes = output.getStack();
            planes.setSliceLabel("reference", 1);
            planes.addSlice("channel-2", reopenedReference.getProcessor().duplicate());
            output.setStack(planes);
            Path outputPath = temporary.resolve(title + ".tif");
            assertTrue(new FileSaver(output).saveAsTiffStack(outputPath.toString()));
            ImagePlus reopened = IJ.openImage(outputPath.toString());
            assertEquals(2, reopened.getStackSize());
            assertEquals("reference", reopened.getStack().getSliceLabel(1));
            assertEquals("channel-2", reopened.getStack().getSliceLabel(2));
            assertEquals(reopenedReference.getCalibration().pixelWidth, reopened.getCalibration().pixelWidth);
            assertEquals(reopenedReference.getCalibration().pixelHeight, reopened.getCalibration().pixelHeight);
            assertEquals(reopenedReference.getCalibration().pixelDepth, reopened.getCalibration().pixelDepth);
            assertEquals(1.25, reopened.getCalibration().frameInterval);
            assertEquals(4, reopened.getCalibration().xOrigin);
            assertEquals(5, reopened.getCalibration().yOrigin);
            assertEquals(reopenedReference.getCalibration().getUnit(), reopened.getCalibration().getUnit());
            output.getCalibration().pixelWidth = 99;
            output.getStack().getProcessor(2).set(20, 10, 0);
            assertEquals(.5, reopenedReference.getCalibration().pixelWidth);
            assertEquals(1234, reopenedReference.getProcessor().get(20, 10));
        }
        assertArrayEquals(originalFile, Files.readAllBytes(sourcePath));
    }
}

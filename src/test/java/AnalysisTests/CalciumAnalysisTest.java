package AnalysisTests;

import Analysis.CalciumAnalysis;
import Features.Core.Params;
import ij.IJ;
import ij.ImagePlus;
import ij.ImageStack;
import ij.io.FileSaver;
import ij.process.FloatProcessor;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.mockito.MockedStatic;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class CalciumAnalysisTest {
    @TempDir Path directory;

    @Test void supportedImageIsValidatedBeforeDisplay() throws Exception {
        Params params = new Params();
        params.imagePath = directory.resolve("movie.tif").toString();
        ImagePlus source = new ImagePlus("movie", new FloatProcessor(2, 1));
        assertTrue(new FileSaver(source).saveAsTiff(params.imagePath));
        ImagePlus opened = spy(IJ.openImage(params.imagePath));
        doNothing().when(opened).show();
        try (MockedStatic<IJ> ij = mockStatic(IJ.class)) {
            ij.when(() -> IJ.openImage(params.imagePath)).thenReturn(opened);
            CalciumAnalysis analysis = new CalciumAnalysis(params);
            analysis.openImage();
            assertSame(opened, analysis.maxProj);
            assertNull(analysis.normStack);
            verify(opened).show();
            ij.verify(() -> IJ.selectWindow(opened.getTitle()));
            ij.verify(() -> IJ.log("Step 1: Image loaded successfully."));
        }
    }

    @Test void missingOrUnspecifiedFileClearsPreviousImageAndResults() throws Exception {
        Params params = new Params();
        for (String path : new String[]{null, "", directory.resolve("missing.tif").toString(), directory.toString()}) {
            params.imagePath = path;
            CalciumAnalysis analysis = analysisWithPreviousResults(params);
            assertThrows(IllegalArgumentException.class, analysis::openImage);
            assertCleared(analysis);
        }
    }

    @Test void unreadableFileClearsPreviousImageAndResults() throws Exception {
        Params params = new Params();
        params.imagePath = Files.createFile(directory.resolve("invalid.tif")).toString();
        CalciumAnalysis analysis = analysisWithPreviousResults(params);
        try (MockedStatic<IJ> ij = mockStatic(IJ.class)) {
            ij.when(() -> IJ.openImage(params.imagePath)).thenReturn(null);
            IllegalArgumentException error = assertThrows(IllegalArgumentException.class, analysis::openImage);
            assertTrue(error.getMessage().contains("Could not open"));
            ij.verify(() -> IJ.openImage(params.imagePath));
            ij.verify(() -> IJ.log(anyString()), never());
        }
        assertCleared(analysis);
    }

    @Test void unsupportedTiffFailsBeforeOpeningWindowAndClearsPreviousResults() throws Exception {
        ImageStack stack = new ImageStack(1, 1);
        for (float value : new float[]{10, 100, 20, 200, 30, 300})
            stack.addSlice(new FloatProcessor(1, 1, new float[]{value}));
        ImagePlus source = new ImagePlus("two channels", stack);
        source.setDimensions(2, 1, 3);
        source.setOpenAsHyperStack(true);
        Params params = new Params();
        params.imagePath = directory.resolve("two-channels.tif").toString();
        assertTrue(new FileSaver(source).saveAsTiffStack(params.imagePath));
        CalciumAnalysis analysis = analysisWithPreviousResults(params);
        // Real TIFF loading and dimensions, with no mocked ImageJ operations.
        IllegalArgumentException error = assertThrows(IllegalArgumentException.class, analysis::openImage);
        assertTrue(error.getMessage().contains("C=2, Z=1, T=3"));
        assertCleared(analysis);
    }

    private CalciumAnalysis analysisWithPreviousResults(Params params) throws Exception {
        CalciumAnalysis analysis = new CalciumAnalysis(params);
        ImagePlus old = new ImagePlus("previous movie", new FloatProcessor(2, 1));
        java.lang.reflect.Field raw = CalciumAnalysis.class.getDeclaredField("rawStack");
        raw.setAccessible(true);
        raw.set(analysis, old);
        analysis.maxProj = old;
        analysis.normStack = old;
        return analysis;
    }

    private void assertCleared(CalciumAnalysis analysis) {
        assertNull(analysis.maxProj);
        assertNull(analysis.normStack);
        assertThrows(IllegalArgumentException.class, analysis::createMaxProjection);
        assertThrows(IllegalArgumentException.class, analysis::normalizeStack);
    }
}

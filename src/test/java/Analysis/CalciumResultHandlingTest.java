package Analysis;
import ij.ImagePlus;
import ij.ImageStack;
import ij.WindowManager;
import ij.plugin.ZProjector;
import ij.process.FloatProcessor;
import ij.process.ColorProcessor;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/** Real ImageJ numerical operations, independent of global/current windows. */
class CalciumResultHandlingTest {
    private ImagePlus movie() {
        ImageStack stack = new ImageStack(2, 1);
        for (float v : new float[]{100, 100, 200}) stack.addSlice(new FloatProcessor(2, 1, new float[]{v, 0}));
        ImagePlus source = new ImagePlus("movie", stack);
        source.setDimensions(1,1,3);
        source.setOpenAsHyperStack(true);
        source.getCalibration().pixelWidth=.5;
        source.getCalibration().frameInterval=1.25;
        return source;
    }
    @Test void selectedMaxUsesReturnedProjectionAndDoesNotModifySource() {
        ImagePlus source=movie();
        WindowManager.setTempCurrentImage(source);
        try {
            ImagePlus max=CalciumAnalysis.projectFrames(source,2,3,ZProjector.MAX_METHOD);
            assertNotSame(source,max); assertEquals(1,max.getStackSize());
            assertEquals(200,max.getProcessor().getf(0));
            assertEquals(100,source.getStack().getProcessor(1).getf(0));
            assertEquals(3,source.getStackSize()); assertEquals(.5,max.getCalibration().pixelWidth);
            ImagePlus first=CalciumAnalysis.projectFrames(source,1,2,ZProjector.MAX_METHOD);
            assertEquals(100,first.getProcessor().getf(0));
        } finally {WindowManager.setTempCurrentImage(null);}
    }
    @Test void averageBaselineAndDivisionPreserveTimeDimensionsAndSource() {
        ImagePlus source=movie();
        ImagePlus baseline=CalciumAnalysis.projectFrames(source,1,2,ZProjector.AVG_METHOD);
        assertEquals(100,baseline.getProcessor().getf(0));
        ImagePlus result=CalciumAnalysis.divideByBaseline(source,baseline);
        assertEquals(32,result.getBitDepth()); assertEquals(3,result.getNFrames()); assertEquals(1,result.getNSlices());
        for(int i=1;i<=3;i++) assertEquals(i==3?2:1,result.getStack().getProcessor(i).getf(0));
        assertEquals(1.25,result.getCalibration().frameInterval);
        assertEquals(200,source.getStack().getProcessor(3).getf(0));
        assertTrue(Float.isNaN(result.getStack().getProcessor(1).getf(1)), "Preserve ImageJ's existing 0/0 semantics");
    }
    @Test void plainStacksKeepFrameSelectionAndZMetadata() {
        ImagePlus source = movie();
        source.setDimensions(1, 3, 1);
        source.setOpenAsHyperStack(false);
        ImagePlus baseline = CalciumAnalysis.projectFrames(source, 1, 2, ZProjector.AVG_METHOD);
        ImagePlus result = CalciumAnalysis.divideByBaseline(source, baseline);
        assertEquals(100, baseline.getProcessor().getf(0));
        assertEquals(200, CalciumAnalysis.projectFrames(source, 2, 3, ZProjector.MAX_METHOD)
                .getProcessor().getf(0));
        assertEquals(1, result.getNChannels());
        assertEquals(3, result.getNSlices());
        assertEquals(1, result.getNFrames());
        assertFalse(result.isHyperStack());
        assertEquals(.5, result.getCalibration().pixelWidth);
        assertEquals(1.25, result.getCalibration().frameInterval);
        for (int i = 1; i <= 3; i++) {
            assertEquals(i == 3 ? 2 : 1, result.getStack().getProcessor(i).getf(0));
            assertEquals(i == 3 ? 200 : 100, source.getStack().getProcessor(i).getf(0));
            assertTrue(Float.isNaN(result.getStack().getProcessor(i).getf(1)));
        }
    }

    @Test void multichannelTimeSeriesCannotMixChannelsIntoBaseline() {
        ImagePlus source = interleavedMovie();
        IllegalArgumentException error = assertThrows(IllegalArgumentException.class,
                () -> CalciumAnalysis.projectFrames(source, 1, 2, ZProjector.AVG_METHOD));
        assertTrue(error.getMessage().contains("C=2, Z=1, T=3"));
        assertUnsupportedNumericalInput(source);
        assertEquals(2, source.getNChannels());
        assertEquals(3, source.getNFrames());
        assertArrayEquals(new float[]{10, 100, 20, 200, 30, 300}, pixels(source));

        // The corresponding supported single-channel movie averages 10 and 20,
        // never the old flattened inter-channel pair 10 and 100 (55).
        ImagePlus singleChannel = scalarMovie(10, 20, 30);
        singleChannel.setDimensions(1, 1, 3);
        singleChannel.setOpenAsHyperStack(true);
        ImagePlus baseline = CalciumAnalysis.projectFrames(singleChannel, 1, 2, ZProjector.AVG_METHOD);
        assertEquals(15, baseline.getProcessor().getf(0));
        ImagePlus result = CalciumAnalysis.divideByBaseline(singleChannel, baseline);
        assertEquals(10f / 15f, result.getStack().getProcessor(1).getf(0), 1e-6);
        assertEquals(2, result.getStack().getProcessor(3).getf(0));
    }

    @Test void combinedZAndTimeAndRgbCannotBeTreatedAsScalarFrames() {
        ImagePlus volumeMovie = scalarMovie(10, 20, 30, 40, 50, 60);
        volumeMovie.setDimensions(1, 2, 3);
        volumeMovie.setOpenAsHyperStack(true);
        assertUnsupportedNumericalInput(volumeMovie);
        assertArrayEquals(new float[]{10, 20, 30, 40, 50, 60}, pixels(volumeMovie));
        assertUnsupportedNumericalInput(rgbMovie());
    }

    @Test void workflowRejectsUnsupportedInputsBeforePromptsIncludingNoNormalization() throws Exception {
        ImagePlus volumeMovie = scalarMovie(10, 20, 30, 40);
        volumeMovie.setDimensions(1, 2, 2);
        for (ImagePlus source : new ImagePlus[]{interleavedMovie(), volumeMovie, rgbMovie()}) {
            Features.Core.Params params = new Features.Core.Params();
            CalciumAnalysis analysis = new CalciumAnalysis(params);
            setRawStack(analysis, source);
            assertThrows(IllegalArgumentException.class, analysis::createMaxProjection);
            assertThrows(IllegalArgumentException.class, analysis::normalizeStack);
            params.useFF0 = false;
            assertThrows(IllegalArgumentException.class, analysis::normalizeStack);
            assertNull(analysis.normStack);
            assertNull(analysis.maxProj);
        }
    }

    @Test void noNormalizationStillAcceptsBothSupportedMovieLayouts() throws Exception {
        Features.Core.Params params = new Features.Core.Params();
        params.useFF0 = false;
        for (ImagePlus source : new ImagePlus[]{movie(), scalarMovie(10, 20, 30)}) {
            CalciumAnalysis analysis = new CalciumAnalysis(params);
            setRawStack(analysis, source);
            analysis.normalizeStack();
            assertSame(source, analysis.normStack);
        }
    }

    @Test void missingInputAndInvalidBaselineFailBeforeImageJProcessing() {
        CalciumAnalysis analysis = new CalciumAnalysis(new Features.Core.Params());
        assertThrows(IllegalArgumentException.class, analysis::createMaxProjection);
        assertThrows(IllegalArgumentException.class, analysis::normalizeStack);
        assertThrows(IllegalArgumentException.class,
                () -> CalciumAnalysis.projectFrames(null, 1, 1, ZProjector.AVG_METHOD));
        assertThrows(IllegalArgumentException.class,
                () -> CalciumAnalysis.projectFrames(new ImagePlus(), 1, 1, ZProjector.AVG_METHOD));
        ImagePlus source = movie();
        assertThrows(IllegalArgumentException.class, () -> CalciumAnalysis.divideByBaseline(source, null));
        assertThrows(IllegalArgumentException.class, () -> CalciumAnalysis.divideByBaseline(source, source));
        assertThrows(IllegalArgumentException.class,
                () -> CalciumAnalysis.divideByBaseline(source, scalarMovie(1)));
        assertThrows(IllegalArgumentException.class,
                () -> CalciumAnalysis.divideByBaseline(source, rgbMovie()));
    }

    private void assertUnsupportedNumericalInput(ImagePlus source) {
        assertThrows(IllegalArgumentException.class,
                () -> CalciumAnalysis.projectFrames(source, 1, 2, ZProjector.MAX_METHOD));
        assertThrows(IllegalArgumentException.class,
                () -> CalciumAnalysis.projectFrames(source, 1, 2, ZProjector.AVG_METHOD));
        assertThrows(IllegalArgumentException.class,
                () -> CalciumAnalysis.divideByBaseline(source, scalarMovie(1)));
    }

    private ImagePlus interleavedMovie() {
        ImagePlus source = scalarMovie(10, 100, 20, 200, 30, 300);
        source.setDimensions(2, 1, 3);
        source.setOpenAsHyperStack(true);
        return source;
    }

    private ImagePlus scalarMovie(float... values) {
        ImageStack stack = new ImageStack(1, 1);
        for (float value : values) stack.addSlice(new FloatProcessor(1, 1, new float[]{value}));
        return new ImagePlus("scalar movie", stack);
    }

    private ImagePlus rgbMovie() {
        ImageStack stack = new ImageStack(1, 1);
        stack.addSlice(new ColorProcessor(1, 1, new int[]{0x102030}));
        stack.addSlice(new ColorProcessor(1, 1, new int[]{0x405060}));
        return new ImagePlus("RGB movie", stack);
    }

    private float[] pixels(ImagePlus source) {
        float[] values = new float[source.getStackSize()];
        for (int i = 0; i < values.length; i++) values[i] = source.getStack().getProcessor(i + 1).getf(0);
        return values;
    }

    private void setRawStack(CalciumAnalysis analysis, ImagePlus source) throws Exception {
        java.lang.reflect.Field field = CalciumAnalysis.class.getDeclaredField("rawStack");
        field.setAccessible(true);
        field.set(analysis, source);
    }

    @Test void disabledAutomaticSegmentationCannotReturnFalseSuccess() throws Exception {
        CalciumAnalysis analysis=new CalciumAnalysis(new Features.Core.Params());
        java.lang.reflect.Method method=CalciumAnalysis.class.getDeclaredMethod("runStarDist",ImagePlus.class,java.io.File.class);
        method.setAccessible(true);
        java.lang.reflect.InvocationTargetException error=assertThrows(java.lang.reflect.InvocationTargetException.class,
                ()->method.invoke(analysis,movie(),null));
        assertInstanceOf(UnsupportedOperationException.class,error.getCause());
        assertTrue(error.getCause().getMessage().contains("not implemented"));
    }
    @Test void unavailableAutomaticOptionIsClearlyDisabledInSettings() throws Exception {
        javax.swing.SwingUtilities.invokeAndWait(()->{
            UI.panes.SettingPanes.calciumImagingAnalysisPane pane=new UI.panes.SettingPanes.calciumImagingAnalysisPane(null,null);
            try {
                java.lang.reflect.Field field=pane.getClass().getDeclaredField("useStarDistBox");field.setAccessible(true);
                javax.swing.JCheckBox option=(javax.swing.JCheckBox)field.get(pane);
                assertFalse(option.isEnabled());assertFalse(option.isSelected());
                assertTrue(option.getText().contains("not implemented"));
            } catch(ReflectiveOperationException error) {throw new AssertionError(error);}
        });
    }
    @Test void badRangesFailBeforeProcessing() {
        ImagePlus source=movie();
        assertThrows(IllegalArgumentException.class,()->CalciumAnalysis.projectFrames(source,3,2,ZProjector.MAX_METHOD));
        assertThrows(IllegalArgumentException.class,()->CalciumAnalysis.projectFrames(source,0,2,ZProjector.MAX_METHOD));
        assertThrows(IllegalArgumentException.class,()->CalciumAnalysis.projectFrames(source,1,4,ZProjector.MAX_METHOD));
    }
}

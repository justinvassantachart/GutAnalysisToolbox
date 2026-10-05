package Analysis;
import ij.ImagePlus;
import ij.ImageStack;
import ij.WindowManager;
import ij.plugin.ZProjector;
import ij.process.FloatProcessor;
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

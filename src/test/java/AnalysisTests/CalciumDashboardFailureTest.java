package AnalysisTests;

import Analysis.CalciumAnalysis;
import Features.Core.Params;
import UI.panes.WorkflowDashboards.CalciumImagingAnalysisDashboard;
import ij.IJ;
import ij.ImagePlus;
import ij.process.FloatProcessor;
import org.junit.jupiter.api.Test;
import org.mockito.MockedStatic;

import javax.swing.JButton;
import javax.swing.JTabbedPane;
import javax.swing.SwingUtilities;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class CalciumDashboardFailureTest {
    @Test void imageStepFailuresAreReportedAndDoNotPublishResults() throws Exception {
        SwingUtilities.invokeAndWait(() -> {
            try (MockedStatic<IJ> ij = mockStatic(IJ.class)) {
                CalciumImagingAnalysisDashboard dashboard = new CalciumImagingAnalysisDashboard(new Params());
                CalciumAnalysis analysis = mock(CalciumAnalysis.class);
                analysis.maxProj = new ImagePlus("loaded", new FloatProcessor(1, 1));
                setField(dashboard, "analysis", analysis);
                doThrow(new IllegalArgumentException("load failed")).when(analysis).openImage();
                doThrow(new IllegalArgumentException("projection failed")).when(analysis).createMaxProjection();
                doThrow(new IllegalArgumentException("normalization failed")).when(analysis).normalizeStack();
                button(dashboard, "btnOpenImage").doClick();
                button(dashboard, "btnMaxProj").doClick();
                button(dashboard, "btnNormalize").doClick();
                ij.verify(() -> IJ.showMessage("Calcium analysis", "load failed"));
                ij.verify(() -> IJ.showMessage("Calcium analysis", "projection failed"));
                ij.verify(() -> IJ.showMessage("Calcium analysis", "normalization failed"));
                assertEquals(0, ((JTabbedPane) getField(dashboard, "tabs")).getTabCount());
            }
        });
    }

    @Test void cancelledNormalizationDoesNotAddAnOldOrEmptyResultTab() throws Exception {
        SwingUtilities.invokeAndWait(() -> {
            CalciumImagingAnalysisDashboard dashboard = new CalciumImagingAnalysisDashboard(new Params());
            CalciumAnalysis analysis = mock(CalciumAnalysis.class);
            analysis.maxProj = new ImagePlus("loaded", new FloatProcessor(1, 1));
            setField(dashboard, "analysis", analysis);
            button(dashboard, "btnNormalize").doClick();
            analysis.normStack = new ImagePlus("previous result", new FloatProcessor(1, 1));
            button(dashboard, "btnNormalize").doClick();
            assertEquals(0, ((JTabbedPane) getField(dashboard, "tabs")).getTabCount());
            verify(analysis, times(2)).normalizeStack();
        });
    }

    private static JButton button(Object target, String name) {
        return (JButton) getField(target, name);
    }

    private static Object getField(Object target, String name) {
        try {
            java.lang.reflect.Field field = target.getClass().getDeclaredField(name);
            field.setAccessible(true);
            return field.get(target);
        } catch (ReflectiveOperationException error) {
            throw new AssertionError(error);
        }
    }

    private static void setField(Object target, String name, Object value) {
        try {
            java.lang.reflect.Field field = target.getClass().getDeclaredField(name);
            field.setAccessible(true);
            field.set(target, value);
        } catch (ReflectiveOperationException error) {
            throw new AssertionError(error);
        }
    }
}

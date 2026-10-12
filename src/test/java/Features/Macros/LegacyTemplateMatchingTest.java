package Features.Macros;

import ij.ImagePlus;
import ij.ImageStack;
import ij.measure.ResultsTable;
import ij.process.ByteProcessor;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class LegacyTemplateMatchingTest {
    static ImagePlus stack() {
        ImageStack stack = new ImageStack(101, 73);
        for (int i = 0; i < 5; i++) stack.addSlice(new ByteProcessor(101, 73));
        return new ImagePlus("odd stack", stack);
    }
    static String options() {
        return "method=5 windowsizex=70 windowsizey=51 x0=16 y0=12 swindow=0 subpixel=false itpmethod=0 ref.slice=3 show=true";
    }
    @Test void preservesOriginalReferenceAndFloorGeometry() {
        assertEquals(3, LegacyTemplateMatching.validateOptions(stack(), options()));
        assertEquals(4, LegacyTemplateMatching.validateOptions(stack(), options().replace("ref.slice=3", "ref.slice=4")));
    }
    @Test void rejectsDifferentNativeAlgorithmSettings() {
        for (String[] change : new String[][] {{"method=5", "method=3"}, {"windowsizex=70", "windowsizex=71"},
                {"x0=16", "x0=17"}, {"subpixel=false", "subpixel=true"}, {"swindow=0", "swindow=10"},
                {"itpmethod=0", "itpmethod=1"}, {"ref.slice=3", "ref.slice=6"}})
            assertThrows(IllegalArgumentException.class, () -> LegacyTemplateMatching.validateOptions(stack(),
                    options().replace(change[0], change[1])));
    }
    @Test void retainsOriginalResultsHeadersAndTraversalOrder() {
        double[][] shifts = {{1, -1}, {2, -2}, {0, 0}, {4, -4}, {5, -5}};
        ResultsTable table = LegacyTemplateMatching.resultsTable(shifts, 3);
        assertEquals(4, table.size());
        assertArrayEquals(new String[] {"Slice", "dX", "dY"}, table.getHeadings());
        assertArrayEquals(new double[] {2, 1, 4, 5}, table.getColumn("Slice"));
        assertArrayEquals(new double[] {2, 1, 4, 5}, table.getColumn("dX"));
        assertArrayEquals(new double[] {-2, -1, -4, -5}, table.getColumn("dY"));
    }
}

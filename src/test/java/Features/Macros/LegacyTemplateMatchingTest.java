package Features.Macros;

import ij.ImagePlus;
import ij.ImageStack;
import ij.WindowManager;
import java.nio.file.Path;
import org.junit.jupiter.api.io.TempDir;
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
    @Test void failedBoundaryReturnsExplicitNonSuccessInsteadOfThrowing() {
        String previous = System.getProperty("gat.alignment.backend");
        try {
            System.setProperty("gat.alignment.backend", "invalid-test-mode");
            String result = assertDoesNotThrow(() -> LegacyTemplateMatching.run(options()));
            assertEquals("GAT_ALIGNMENT_OK", LegacyTemplateMatching.SUCCESS_TOKEN);
            assertTrue(result.startsWith(LegacyTemplateMatching.ERROR_PREFIX));
            assertTrue(result.contains("gat.alignment.backend must be"));
            assertNotEquals(LegacyTemplateMatching.SUCCESS_TOKEN, result);
        } finally { restore("gat.alignment.backend", previous); }
    }

    @Test void missingWorkerReturnsFailureAndPreservesInput(@TempDir Path emptyWorker) {
        String backend = System.getProperty("gat.alignment.backend");
        String worker = System.getProperty("gat.alignment.directory");
        ImagePlus previousImage = WindowManager.getTempCurrentImage();
        ImagePlus input = stack();
        input.getStack().getProcessor(2).set(17, 93);
        ImageStack original = input.getStack();
        try {
            WindowManager.setTempCurrentImage(input);
            System.setProperty("gat.alignment.backend", "native");
            System.setProperty("gat.alignment.directory", emptyWorker.toString());
            String result = assertDoesNotThrow(() -> LegacyTemplateMatching.run(options()));
            assertTrue(result.startsWith(LegacyTemplateMatching.ERROR_PREFIX));
            assertNotEquals(LegacyTemplateMatching.SUCCESS_TOKEN, result);
            assertSame(original, input.getStack());
            assertEquals(93, input.getStack().getProcessor(2).get(17));
            assertNull(input.getRoi());
        } finally {
            WindowManager.setTempCurrentImage(previousImage);
            restore("gat.alignment.backend", backend); restore("gat.alignment.directory", worker);
        }
    }

    private static void restore(String name, String value) {
        if (value == null) System.clearProperty(name); else System.setProperty(name, value);
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

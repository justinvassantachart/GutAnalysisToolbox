package Features.Macros;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import net.imagej.Dataset;
import net.imagej.DatasetService;
import net.imagej.axis.Axes;
import net.imagej.axis.AxisType;
import net.imagej.axis.DefaultLinearAxis;
import net.imglib2.RandomAccess;
import net.imglib2.type.numeric.RealType;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.scijava.Context;
import static org.junit.jupiter.api.Assertions.*;

class LegacyMacroStarDistTest {
    static Context context;
    static DatasetService datasets;
    @BeforeAll static void init() {
        context = new Context(DatasetService.class);
        datasets = context.service(DatasetService.class);
    }
    @AfterAll static void dispose() { context.dispose(); }

    static Dataset image(long[] shape, AxisType[] axes) {
        return datasets.create(shape, "synthetic", axes, 32, true, true);
    }
    static Dataset image() { return image(new long[] {3, 2}, new AxisType[] {Axes.X, Axes.Y}); }

    @Test void inputPreservesRawValuesAndXYOrderingWithoutDisplayStretch() {
        Dataset source = image();
        RandomAccess<? extends RealType<?>> cursor = source.getImgPlus().randomAccess();
        float[] expected = {-2, 0, 1, 123.25f, 4095, 65535};
        for (int y = 0, i = 0; y < 2; y++) for (int x = 0; x < 3; x++, i++) {
            cursor.setPosition(new long[] {x, y}); cursor.get().setReal(expected[i]);
        }
        source.setChannelMinimum(0, 150); source.setChannelMaximum(0, 450);
        assertArrayEquals(expected, LegacyMacroStarDist.inputPixels(source));
        assertEquals(150, source.getChannelMinimum(0));
        assertEquals(450, source.getChannelMaximum(0));
    }

    @Test void rejectsUnselectedChannelsAndTimePlanes() {
        assertThrows(IllegalArgumentException.class, () -> LegacyMacroStarDist.inputPixels(
                image(new long[] {3, 2, 2}, new AxisType[] {Axes.X, Axes.Y, Axes.CHANNEL})));
        assertThrows(IllegalArgumentException.class, () -> LegacyMacroStarDist.inputPixels(
                image(new long[] {3, 2, 2}, new AxisType[] {Axes.X, Axes.Y, Axes.TIME})));
    }

    @Test void rejectsNonfiniteAndWrongAxes() {
        Dataset source = image(); source.getImgPlus().firstElement().setReal(Double.NaN);
        assertThrows(IllegalArgumentException.class, () -> LegacyMacroStarDist.inputPixels(source));
        assertThrows(IllegalArgumentException.class, () -> LegacyMacroStarDist.inputPixels(
                image(new long[] {3, 2}, new AxisType[] {Axes.Y, Axes.X})));
    }

    @Test void singletonAxesAreKeptInRoiPlacementDecision() {
        LegacyMacroStarDist adapter = new LegacyMacroStarDist();
        adapter.input = image(new long[] {3, 2, 1, 1}, new AxisType[] {Axes.X, Axes.Y, Axes.CHANNEL, Axes.TIME});
        assertEquals(6, LegacyMacroStarDist.inputPixels(adapter.input).length);
        assertEquals("Hyperstack", adapter.nmsArguments(null, null).get("roiPosition"));
        adapter.input = image();
        assertEquals("Stack", adapter.nmsArguments(null, null).get("roiPosition"));
    }

    @Test void everyRequestedNmsSettingSurvivesWithoutV2Rounding() {
        LegacyMacroStarDist adapter = new LegacyMacroStarDist(); adapter.input = image();
        for (String output : new String[] {"Both", "Label Image", "ROI Manager"})
            for (String position : new String[] {"Stack", "Hyperstack"})
                for (double threshold : new double[] {0, 0.123456789, 0.5, 1}) {
                    adapter.probThresh = threshold; adapter.nmsThresh = 1 - threshold;
                    adapter.outputType = output; adapter.roiPosition = position;
                    adapter.excludeBoundary = 7; adapter.verbose = true;
                    Map<String, Object> args = adapter.nmsArguments(null, null);
                    assertEquals(threshold, args.get("probThresh"));
                    assertEquals(1 - threshold, args.get("nmsThresh"));
                    assertEquals(output, args.get("outputType"));
                    assertEquals(position, args.get("roiPosition"));
                    assertEquals(7, args.get("excludeBoundary"));
                    assertEquals(true, args.get("verbose"));
                }
    }

    @Test void legacyBackendReceivesEveryOriginalParameter() {
        LegacyMacroStarDist adapter = new LegacyMacroStarDist(); adapter.input = image();
        adapter.nTiles = 13; adapter.probThresh = .718923456; adapter.outputType = "Both";
        Map<String, Object> args = adapter.legacyArguments();
        assertEquals(15, args.size());
        assertSame(adapter.input, args.get("input")); assertEquals(13, args.get("nTiles"));
        assertEquals(.718923456, args.get("probThresh")); assertEquals("Both", args.get("outputType"));
        assertEquals("Automatic", args.get("roiPosition"));
        assertEquals(1., args.get("percentileBottom")); assertEquals(99.8, args.get("percentileTop"));
    }

    @Test void nativeContractRejectsUnsupportedInternalNormalizationInsteadOfChangingIt() throws Exception {
        LegacyMacroStarDist adapter = new LegacyMacroStarDist();
        Path model = Files.createTempFile("gat-macro-contract-", ".zip");
        try {
            adapter.modelFile = model.toFile(); adapter.validateNativeParameters();
            adapter.percentileBottom = 2;
            assertThrows(IllegalArgumentException.class, adapter::validateNativeParameters);
            adapter.percentileBottom = 1; adapter.normalizeInput = false;
            assertThrows(IllegalArgumentException.class, adapter::validateNativeParameters);
            adapter.normalizeInput = true; adapter.showCsbdeepProgress = true;
            assertThrows(IllegalArgumentException.class, adapter::validateNativeParameters);
        } finally { Files.delete(model); }
    }

    @Test void thresholdAndTileBoundariesAreValidated() throws Exception {
        LegacyMacroStarDist adapter = new LegacyMacroStarDist();
        Path model = Files.createTempFile("gat-macro-contract-", ".zip");
        try {
            adapter.modelFile = model.toFile();
            for (double value : new double[] {0, .123456789, 1}) {
                adapter.probThresh = value; adapter.nmsThresh = value; adapter.validateNativeParameters();
            }
            for (double value : new double[] {-1, 1.01, Double.NaN, Double.POSITIVE_INFINITY}) {
                adapter.probThresh = value;
                assertThrows(IllegalArgumentException.class, adapter::validateNativeParameters);
            }
            adapter.probThresh = .5; adapter.nTiles = 0;
            assertThrows(IllegalArgumentException.class, adapter::validateNativeParameters);
        } finally { Files.delete(model); }
    }

    @Test void predictionPlanesAreZeroCopyAndKeepOriginalUncalibratedMetadata() {
        LegacyMacroStarDist adapter = new LegacyMacroStarDist();
        adapter.input = image(); adapter.datasets = datasets;
        adapter.input.setAxis(new DefaultLinearAxis(Axes.X, "micron", .3125848633), 0);
        float[][] planes = new float[5][6];
        Dataset[] prediction = adapter.predictionDatasets(3, 2, planes);
        assertEquals("Probability/Score Image", prediction[0].getName());
        assertEquals("Distance Image", prediction[1].getName());
        assertEquals(1, prediction[0].axis(0).calibratedValue(1));
        assertNotEquals("micron", prediction[0].axis(0).unit());
        planes[0][5] = .75f; planes[4][5] = 7.5f;
        RandomAccess<? extends RealType<?>> p = prediction[0].getImgPlus().randomAccess();
        p.setPosition(new long[] {2, 1}); assertEquals(.75f, p.get().getRealFloat());
        RandomAccess<? extends RealType<?>> d = prediction[1].getImgPlus().randomAccess();
        d.setPosition(new long[] {2, 1, 3}); assertEquals(7.5f, d.get().getRealFloat());
        d.get().setReal(9); assertEquals(9, planes[4][5]);
    }

    @Test void singletonTimeSurvivesPredictionToKeepRoiFramePosition() {
        LegacyMacroStarDist adapter = new LegacyMacroStarDist(); adapter.datasets = datasets;
        adapter.input = image(new long[] {3, 2, 1, 1}, new AxisType[] {Axes.X, Axes.Y, Axes.CHANNEL, Axes.TIME});
        Dataset[] prediction = adapter.predictionDatasets(3, 2, new float[5][6]);
        assertEquals(Axes.TIME, prediction[0].axis(2).type());
        assertEquals(Axes.CHANNEL, prediction[1].axis(2).type());
        assertEquals(Axes.TIME, prediction[1].axis(3).type());
    }

    @Test void rejectsEvenSingletonZAsOriginalStarDistDoes() {
        assertThrows(IllegalArgumentException.class, () -> LegacyMacroStarDist.inputPixels(
                image(new long[] {3, 2, 1}, new AxisType[] {Axes.X, Axes.Y, Axes.Z})));
        assertThrows(IllegalArgumentException.class, () -> LegacyMacroStarDist.inputPixels(
                image(new long[] {3, 2, 1, 1}, new AxisType[] {Axes.X, Axes.Y, Axes.CHANNEL, Axes.Z})));
    }
}

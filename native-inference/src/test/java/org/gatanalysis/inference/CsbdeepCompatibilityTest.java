package org.gatanalysis.inference;

import static org.junit.jupiter.api.Assertions.*;
import net.imglib2.FinalInterval;
import net.imglib2.RandomAccess;
import net.imglib2.RandomAccessibleInterval;
import net.imglib2.img.array.ArrayImgs;
import net.imglib2.type.numeric.real.FloatType;
import net.imglib2.view.Views;
import org.junit.jupiter.api.Test;

class CsbdeepCompatibilityTest {
    @Test void fullResolution96RayShapeFitsWithoutAllocatingItsPixels() {
        assertEquals(406847488, ImageTensor.elements(2048, 2048, 97));
        assertThrows(IllegalArgumentException.class, () -> ImageTensor.elements(Integer.MAX_VALUE, Integer.MAX_VALUE, 1024));
    }

    @Test void percentileUsesNearestSampleRatherThanLinearInterpolation() {
        assertEquals(10, CsbdeepNormalizer.percentile(new float[] {0, 2, 10, 20}, 50));
    }

    @Test void normalizationClampsLowButDoesNotClipHigh() {
        float[] input = new float[1001];
        for (int i = 0; i < input.length; i++) input[i] = i;
        float[] normalized = CsbdeepNormalizer.normalize(input);
        assertEquals(0.0f, normalized[0]);
        assertEquals(0.0f, normalized[10]);
        assertEquals(1.0f, normalized[998]);
        assertTrue(normalized[1000] > 1.0f);
        assertEquals(10.0f, input[10]);
    }

    @Test void constantImagesBecomeZeroAndNonFiniteFails() {
        assertArrayEquals(new float[4], CsbdeepNormalizer.normalize(new float[] {7, 7, 7, 7}));
        assertThrows(IllegalArgumentException.class, () -> CsbdeepNormalizer.normalize(new float[] {Float.NaN}));
    }

    @Test void preservesTileChoiceAndLegacyRounding() {
        CsbdeepTiling square = new CsbdeepTiling(512, 512, 2);
        assertEquals(2, square.tilesX);
        assertEquals(1, square.tilesY);
        CsbdeepTiling odd = new CsbdeepTiling(129, 64, 2);
        assertEquals(128, odd.expandedWidth); // Legacy integer truncation, intentionally preserved.
        assertEquals(64, odd.tileWidth);
        CsbdeepTiling small = new CsbdeepTiling(9, 3, 100);
        assertEquals(1, small.tilesX);
        assertEquals(1, small.tilesY);
    }

    @Test void tilesMatchActualImgLib2NestedMirrorViews() {
        for (int[] example : new int[][] {{129, 65, 4}, {231, 201, 7}, {7, 5, 1}, {130, 129, 4}, {64, 193, 2}}) {
            int width = example[0], height = example[1];
            CsbdeepTiling tiling = new CsbdeepTiling(width, height, example[2]);
            float[] pixels = new float[width * height];
            for (int i = 0; i < pixels.length; i++) pixels[i] = i;
            RandomAccessibleInterval<FloatType> source = ArrayImgs.floats(pixels, width, height, 1, 1);
            // Exact view composition in CSBDeep DefaultTiling: batch expansion,
            // X block expansion, then Y block expansion. Nonspatial singleton dims
            // do not change the X/Y coordinate mapping.
            source = Views.interval(Views.extendMirrorDouble(source), new FinalInterval(width, height, 1, 1));
            source = Views.interval(Views.extendMirrorDouble(source), new FinalInterval(tiling.expandedWidth, height, 1, 1));
            source = Views.interval(Views.extendMirrorDouble(source), new FinalInterval(tiling.expandedWidth, tiling.expandedHeight, 1, 1));
            for (int ty = 0; ty < tiling.tilesY; ty++) {
                for (int tx = 0; tx < tiling.tilesX; tx++) {
                    ImageTensor tile = tiling.tile(pixels, tx, ty);
                    long[] min = {(long) tx * tiling.tileWidth - tiling.overlapX,
                                  (long) ty * tiling.tileHeight - tiling.overlapY, 0, 0};
                    long[] max = {min[0] + tile.width - 1, min[1] + tile.height - 1, 0, 0};
                    // TiledView requests this actual extended interval; using the
                    // source's randomAccess() outside its bounds is undefined.
                    RandomAccess<FloatType> reference = Views.interval(source, min, max).randomAccess();
                    for (int y = 0; y < tile.height; y++) {
                        for (int x = 0; x < tile.width; x++) {
                            reference.setPosition((long) tx * tiling.tileWidth + x - tiling.overlapX, 0);
                            reference.setPosition((long) ty * tiling.tileHeight + y - tiling.overlapY, 1);
                            assertEquals(reference.get().get(), tile.values[y * tile.width + x],
                                    "Mismatch " + width + "x" + height + " at tile " + tx + "," + ty + " pixel " + x + "," + y);
                        }
                    }
                }
            }
        }
    }

    @Test void stitchingPreservesChannelsAndLegacyFinalReflection() throws Exception {
        int width = 129, height = 65;
        float[] pixels = new float[width * height];
        for (int i = 0; i < pixels.length; i++) pixels[i] = i;
        CsbdeepTiling tiling = new CsbdeepTiling(width, height, 4);
        TilePredictor echo = new TilePredictor() {
            public ImageTensor predict(ImageTensor tile) {
                float[] output = new float[tile.width * tile.height * 4];
                for (int i = 0; i < tile.values.length; i++)
                    for (int c = 0; c < 4; c++) output[i * 4 + c] = tile.values[i] + c;
                return new ImageTensor(tile.width, tile.height, 4, output);
            }
            public void close() {}
        };
        ImageTensor output = tiling.infer(pixels, echo);
        assertEquals(width, output.width);
        assertEquals(height, output.height);
        for (int y = 0; y < height; y++)
            for (int x = 0; x < width; x++)
                for (int c = 0; c < 4; c++)
                    assertEquals(pixels[y * width + Math.min(x, 127)] + c,
                            output.values[(y * width + x) * 4 + c]);
    }
    @Test void directStitchingMatchesPaddedCropAndMirrorReferenceAcrossShapes() throws Exception {
        // The final two cases require Y-only and simultaneous X/Y reflection.
        int[][] shapes = {{7, 5, 1}, {128, 128, 4}, {129, 65, 4},
                {231, 201, 7}, {64, 193, 2}, {65, 129, 4}, {129, 129, 4}};
        for (int[] shape : shapes) {
            int width = shape[0], height = shape[1];
            for (int channels : new int[] {4, 97}) {
                float[] image = new float[width * height];
                for (int i = 0; i < image.length; i++) image[i] = i;
                CsbdeepTiling tiling = new CsbdeepTiling(width, height, shape[2]);
                ImageTensor expected = paddedCropReference(tiling, image, tileLocalPredictor(channels));
                ImageTensor actual = tiling.infer(image, tileLocalPredictor(channels));
                assertEquals(width, actual.width);
                assertEquals(height, actual.height);
                assertEquals(channels, actual.channels);
                assertArrayEquals(expected.values, actual.values,
                        "Direct stitching differs at " + width + "x" + height
                                + ", " + channels + " channels, " + shape[2] + " requested tiles");
            }
        }
    }

    /** An echo predictor can hide seam offsets because overlapping input pixels agree. */
    private static TilePredictor tileLocalPredictor(final int channels) {
        return new TilePredictor() {
            private int tileOrdinal;
            public ImageTensor predict(ImageTensor tile) {
                float[] values = new float[ImageTensor.elements(tile.width, tile.height, channels)];
                int ordinal = tileOrdinal++;
                for (int y = 0; y < tile.height; y++)
                    for (int x = 0; x < tile.width; x++)
                        for (int c = 0; c < channels; c++)
                            values[(y * tile.width + x) * channels + c] =
                                    ordinal * 100000.0f + y * 257 + x + c * 0.25f;
                return new ImageTensor(tile.width, tile.height, channels, values);
            }
            public void close() {}
        };
    }

    /** The pre-optimization algorithm: stitch expanded pixels, then crop/reflect. */
    private static ImageTensor paddedCropReference(CsbdeepTiling tiling, float[] image,
                                                   TilePredictor predictor) throws Exception {
        float[] expanded = null;
        int channels = 0;
        for (int ty = 0; ty < tiling.tilesY; ty++) {
            for (int tx = 0; tx < tiling.tilesX; tx++) {
                ImageTensor tile = predictor.predict(tiling.tile(image, tx, ty));
                if (expanded == null) {
                    channels = tile.channels;
                    expanded = new float[ImageTensor.elements(
                            tiling.expandedWidth, tiling.expandedHeight, channels)];
                }
                for (int y = 0; y < tiling.tileHeight; y++) {
                    int from = ((y + tiling.overlapY) * tile.width + tiling.overlapX) * channels;
                    int to = ((ty * tiling.tileHeight + y) * tiling.expandedWidth
                            + tx * tiling.tileWidth) * channels;
                    System.arraycopy(tile.values, from, expanded, to, tiling.tileWidth * channels);
                }
            }
        }
        float[] result = new float[ImageTensor.elements(tiling.width, tiling.height, channels)];
        for (int y = 0; y < tiling.height; y++) {
            int sy = CsbdeepTiling.mirrorDouble(y, tiling.expandedHeight);
            for (int x = 0; x < tiling.width; x++) {
                int sx = CsbdeepTiling.mirrorDouble(x, tiling.expandedWidth);
                System.arraycopy(expanded, (sy * tiling.expandedWidth + sx) * channels,
                        result, (y * tiling.width + x) * channels, channels);
            }
        }
        return new ImageTensor(tiling.width, tiling.height, channels, result);
    }

}

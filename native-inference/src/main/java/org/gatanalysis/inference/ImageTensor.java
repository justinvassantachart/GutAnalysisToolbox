package org.gatanalysis.inference;

/** Dense row-major, channel-interleaved float image. */
final class ImageTensor {
    // Bound by Java array indexing, not an arbitrary 1 GiB payload ceiling.
    // A normal 2048x2048 image with 96 rays needs 406,847,488 floats.
    // Available heap still limits allocation; tiling reduces model working memory.
    static final int MAX_ELEMENTS = Integer.MAX_VALUE - 8;
    final int width;
    final int height;
    final int channels;
    final float[] values;

    ImageTensor(int width, int height, int channels, float[] values) {
        if (values.length != elements(width, height, channels))
            throw new IllegalArgumentException("Pixel count does not match image shape");
        this.width = width;
        this.height = height;
        this.channels = channels;
        this.values = values;
    }

    static int elements(int width, int height, int channels) {
        if (width < 1 || height < 1 || channels < 1)
            throw new IllegalArgumentException("Image dimensions must be positive");
        long count;
        try { count = Math.multiplyExact(Math.multiplyExact((long) width, height), channels); }
        catch (ArithmeticException e) { throw new IllegalArgumentException("Image dimensions overflow", e); }
        if (count > MAX_ELEMENTS)
            throw new IllegalArgumentException("Image/tensor exceeds supported limit of " + MAX_ELEMENTS + " float values");
        return (int) count;
    }
}

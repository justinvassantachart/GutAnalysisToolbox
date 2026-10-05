package org.gatanalysis.inference;

/** Dense row-major, channel-interleaved float image. */
final class ImageTensor {
    // Keep Java array indexing and protocol lengths bounded; actual available RAM may be lower.
    static final int MAX_ELEMENTS = 268_435_456;
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

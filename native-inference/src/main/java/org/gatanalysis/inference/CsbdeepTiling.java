/*
 * Adapted from CSBDeep Fiji preprocessing.
 * Copyright (C) 2017 - 2020 Deborah Schmidt, Florian Jug, Benjamin Wilhelm
 * 
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 * 
 * 1. Redistributions of source code must retain the above copyright notice,
 *    this list of conditions and the following disclaimer.
 * 2. Redistributions in binary form must reproduce the above copyright notice,
 *    this list of conditions and the following disclaimer in the documentation
 *    and/or other materials provided with the distribution.
 * 
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDERS OR CONTRIBUTORS BE
 * LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
 * CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 * SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 * INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 * CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 * POSSIBILITY OF SUCH DAMAGE.
 * 
 */
package org.gatanalysis.inference;

/** CSBDeep Fiji's 2D single-channel, batch-size-one, file-model tiling contract. */
final class CsbdeepTiling {
    static final int BLOCK = 64;
    static final int OVERLAP = 64;
    final int width;
    final int height;
    final int tilesX;
    final int tilesY;
    final int tileWidth;
    final int tileHeight;
    final int expandedWidth;
    final int expandedHeight;
    final int overlapX;
    final int overlapY;

    CsbdeepTiling(int width, int height, int requestedTiles) {
        ImageTensor.elements(width, height, 1);
        if (requestedTiles < 1 || requestedTiles > 1_000_000)
            throw new IllegalArgumentException("nTiles must be between 1 and 1000000");
        this.width = width;
        this.height = height;
        int nx = 1, ny = 1;
        while ((long) nx * ny < requestedTiles) {
            int sx = blockSize(width, nx), sy = blockSize(height, ny);
            if (sx > BLOCK && sx >= sy) nx++;
            else if (sy > BLOCK) ny++;
            else break;
        }
        tilesX = nx;
        tilesY = ny;
        tileWidth = blockSize(width, nx);
        tileHeight = blockSize(height, ny);
        expandedWidth = Math.multiplyExact(tileWidth, nx);
        expandedHeight = Math.multiplyExact(tileHeight, ny);
        ImageTensor.elements(expandedWidth, expandedHeight, 1);
        overlapX = nx > 1 ? OVERLAP : 0;
        overlapY = ny > 1 ? OVERLAP : 0;
    }

    static int blockSize(int size, int tiles) {
        // The integer division BEFORE ceil is intentional: preserve DefaultTiling#getTileSize.
        return Math.toIntExact((long) Math.ceil((size / tiles) / (double) BLOCK) * BLOCK);
    }

    static int mirrorDouble(long position, int size) {
        long period = 2L * size;
        long at = Math.floorMod(position, period);
        return (int) (at < size ? at : period - 1 - at);
    }

    ImageTensor tile(float[] image, int tx, int ty) {
        int tw = tileWidth + 2 * overlapX;
        int th = tileHeight + 2 * overlapY;
        float[] pixels = new float[ImageTensor.elements(tw, th, 1)];
        for (int y = 0; y < th; y++) {
            int sy = mirrorDouble((long) ty * tileHeight + y - overlapY, height);
            for (int x = 0; x < tw; x++) {
                long globalX = (long) tx * tileWidth + x - overlapX;
                // expandToFitBlockSize creates nested MirrorDouble views: X then Y.
                // The Y view first reflects X against expandedWidth; the X view then
                // reflects that coordinate against the original image width.
                int sx = mirrorDouble(mirrorDouble(globalX, expandedWidth), width);
                pixels[y * tw + x] = image[sy * width + sx];
            }
        }
        return new ImageTensor(tw, th, 1, pixels);
    }

    ImageTensor infer(float[] normalized, TilePredictor predictor) throws Exception {
        if (normalized.length != ImageTensor.elements(width, height, 1))
            throw new IllegalArgumentException("Normalized image size mismatch");
        float[] merged = null;
        int channels = 0;
        for (int ty = 0; ty < tilesY; ty++) {
            for (int tx = 0; tx < tilesX; tx++) {
                ImageTensor input = tile(normalized, tx, ty);
                ImageTensor result = predictor.predict(input);
                if (result.width != input.width || result.height != input.height || result.channels < 4)
                    throw new IllegalArgumentException("Unsupported model output: expected full-resolution probability + distance channels");
                if (merged == null) {
                    channels = result.channels;
                    merged = new float[ImageTensor.elements(expandedWidth, expandedHeight, channels)];
                } else if (channels != result.channels) {
                    throw new IllegalArgumentException("Model changed its output channel count between tiles");
                }
                for (int y = 0; y < tileHeight; y++) {
                    int from = ((y + overlapY) * result.width + overlapX) * channels;
                    int to = ((ty * tileHeight + y) * expandedWidth + tx * tileWidth) * channels;
                    System.arraycopy(result.values, from, merged, to, tileWidth * channels);
                }
            }
        }
        float[] output = new float[ImageTensor.elements(width, height, channels)];
        // Usually a crop; upstream can shrink by a pixel due to integer division,
        // so match its final MirrorDouble expansion in that case too.
        for (int y = 0; y < height; y++) {
            int sy = mirrorDouble(y, expandedHeight);
            for (int x = 0; x < width; x++) {
                int sx = mirrorDouble(x, expandedWidth);
                System.arraycopy(merged, (sy * expandedWidth + sx) * channels,
                        output, (y * width + x) * channels, channels);
            }
        }
        return new ImageTensor(width, height, channels, output);
    }
}

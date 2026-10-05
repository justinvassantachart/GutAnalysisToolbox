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

import java.util.Arrays;

/** Matches CSBDeep Fiji PercentileNormalizer, rather than NumPy's interpolated percentile. */
final class CsbdeepNormalizer {
    private CsbdeepNormalizer() {}

    static float[] normalize(float[] pixels) {
        if (pixels.length == 0) throw new IllegalArgumentException("Empty image");
        float[] sorted = pixels.clone();
        for (float value : sorted)
            if (!Float.isFinite(value)) throw new IllegalArgumentException("Non-finite input pixel");
        Arrays.sort(sorted);
        float low = percentile(sorted, 1.0f);
        float high = percentile(sorted, 99.8f);
        float factor = high - low < 0.0000001 ? 1 : 1.0f / (high - low);
        float[] normalized = new float[pixels.length];
        // clip=false still clamps below zero in the upstream Fiji implementation.
        for (int i = 0; i < pixels.length; i++)
            normalized[i] = Math.max(0, (pixels[i] - low) * factor);
        return normalized;
    }

    static float percentile(float[] sorted, float percentile) {
        return sorted[Math.min(sorted.length - 1,
                Math.max(0, Math.round((sorted.length - 1) * percentile / 100.0f)))];
    }
}

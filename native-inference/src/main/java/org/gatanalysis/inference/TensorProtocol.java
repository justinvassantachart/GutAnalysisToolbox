package org.gatanalysis.inference;

import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;

/** Version 1 protocol: big-endian ints and IEEE754 floats. No TIFF or Fiji dependency. */
final class TensorProtocol {
    static final int INPUT_MAGIC = 0x47415449; // GATI
    static final int OUTPUT_MAGIC = 0x4741544f; // GATO
    static final int VERSION = 1;

    private TensorProtocol() {}

    static ImageTensor readInput(Path path) throws IOException {
        try (DataInputStream in = new DataInputStream(new BufferedInputStream(Files.newInputStream(path)))) {
            if (in.readInt() != INPUT_MAGIC || in.readInt() != VERSION)
                throw new IOException("Unsupported GATI input protocol or version");
            int width = in.readInt();
            int height = in.readInt();
            final int count;
            try { count = ImageTensor.elements(width, height, 1); }
            catch (IllegalArgumentException e) { throw new IOException(e.getMessage(), e); }
            if (Files.size(path) != 16L + 4L * count)
                throw new IOException("Input length does not match GATI dimensions");
            float[] data = new float[count];
            for (int i = 0; i < count; i++) {
                data[i] = in.readFloat();
                if (!Float.isFinite(data[i]))
                    throw new IOException("Input contains a non-finite pixel at index " + i);
            }
            if (in.read() != -1) throw new IOException("Unexpected trailing input bytes");
            return new ImageTensor(width, height, 1, data);
        }
    }

    static void writeOutput(Path path, ImageTensor tensor) throws IOException {
        if (tensor.channels < 4) throw new IOException("StarDist output needs probability and at least three distances");
        Path destination = path.toAbsolutePath().normalize();
        if (Files.exists(destination)) throw new IOException("Output already exists: " + destination);
        Path temporary = Files.createTempFile(destination.getParent(), ".gat-result-", ".tmp");
        try {
            try (DataOutputStream out = new DataOutputStream(new BufferedOutputStream(Files.newOutputStream(temporary)))) {
                out.writeInt(OUTPUT_MAGIC);
                out.writeInt(VERSION);
                out.writeInt(tensor.width);
                out.writeInt(tensor.height);
                out.writeInt(tensor.channels);
                for (float value : tensor.values) {
                    if (!Float.isFinite(value)) throw new IOException("Model produced a non-finite prediction");
                    out.writeFloat(value);
                }
            }
            try { Files.move(temporary, destination, StandardCopyOption.ATOMIC_MOVE); }
            catch (AtomicMoveNotSupportedException e) { Files.move(temporary, destination); }
        } finally {
            Files.deleteIfExists(temporary);
        }
    }
}

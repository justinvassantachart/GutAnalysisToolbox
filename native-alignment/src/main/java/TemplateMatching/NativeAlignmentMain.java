package TemplateMatching;

import ij.ImagePlus;
import ij.ImageStack;
import ij.process.ByteProcessor;
import ij.process.ImageProcessor;
import ij.process.ShortProcessor;
import java.awt.Rectangle;
import java.awt.image.DataBuffer;
import java.awt.image.IndexColorModel;
import java.io.*;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

/** GPL-3.0 standalone protocol adapter for the original, separately licensed plugin. */
public final class NativeAlignmentMain {
    static final int INPUT_MAGIC = 0x47415441, OUTPUT_MAGIC = 0x47415453, VERSION = 1;
    static final long MAX_PIXELS = 67_108_864L;
    static final class Input {
        final ImagePlus image;
        final int reference;
        Input(ImagePlus image, int reference) { this.image = image; this.reference = reference; }
    }
    static Input readInput(Path path) throws IOException {
        try (DataInputStream in = new DataInputStream(new BufferedInputStream(Files.newInputStream(path)))) {
            if (in.readInt() != INPUT_MAGIC || in.readInt() != VERSION) throw new IOException("Unsupported alignment input protocol");
            int width = in.readInt(), height = in.readInt(), frames = in.readInt(), bits = in.readInt(), reference = in.readInt();
            long plane = (long) width * height;
            if (width < 2 || height < 2 || frames < 2 || frames > 10000 || (bits != 8 && bits != 16)
                    || reference < 1 || reference > frames || plane > MAX_PIXELS || plane * frames > MAX_PIXELS)
                throw new IOException("Unsupported stack dimensions, bit depth or reference slice");
            long expected = 28L + frames * (1024L + plane * (bits / 8));
            if (Files.size(path) != expected) throw new IOException("Incomplete or extra alignment input bytes");
            ImageStack stack = new ImageStack(width, height);
            for (int z = 0; z < frames; z++) {
                int[] argb = new int[256];
                for (int i = 0; i < argb.length; i++) argb[i] = in.readInt();
                IndexColorModel palette = new IndexColorModel(8, 256, argb, 0, true, -1, DataBuffer.TYPE_BYTE);
                ImageProcessor pixels;
                if (bits == 8) {
                    byte[] values = new byte[(int) plane];
                    in.readFully(values);
                    pixels = new ByteProcessor(width, height, values, palette);
                } else {
                    short[] values = new short[(int) plane];
                    for (int i = 0; i < values.length; i++) values[i] = in.readShort();
                    pixels = new ShortProcessor(width, height, values, palette);
                }
                stack.addSlice(pixels);
            }
            if (in.read() != -1) throw new IOException("Unexpected trailing input bytes");
            return new Input(new ImagePlus("GAT isolated alignment input", stack), reference);
        }
    }
    static double[][] align(Input input) throws Exception {
        ImagePlus image = input.image;
        Align_slices original = new Align_slices();
        original.imp = image;
        original.stack = image.getStack();
        original.width = image.getWidth();
        original.height = image.getHeight();
        original.method = 5;
        original.subPixel = false;
        original.sArea = 0;
        original.itpMethod = 0;
        original.refSlice = input.reference;
        original.rect = new Rectangle((int) Math.floor(original.width / 6.0), (int) Math.floor(original.height / 6.0),
                (int) Math.floor(original.width * 0.7), (int) Math.floor(original.height * 0.7));
        ImageProcessor reference = original.stack.getProcessor(input.reference);
        reference.setRoi(original.rect);
        original.ref = reference.crop();
        reference.resetRoi();
        Method alignSlice = Align_slices.class.getDeclaredMethod("alignSlices", int.class);
        alignSlice.setAccessible(true);
        double[][] shifts = new double[image.getStackSize()][2];
        // Preserve the author's exact before/after-reference traversal.
        for (int slice = input.reference - 1; slice > 0; slice--) runSlice(original, alignSlice, shifts, slice);
        for (int slice = input.reference + 1; slice <= shifts.length; slice++) runSlice(original, alignSlice, shifts, slice);
        return shifts;
    }
    private static void runSlice(Align_slices original, Method method, double[][] shifts, int slice) throws Exception {
        try { method.invoke(original, slice); }
        catch (InvocationTargetException failure) {
            Throwable cause = failure.getCause();
            if (cause instanceof Exception) throw (Exception) cause;
            if (cause instanceof Error) throw (Error) cause;
            throw failure;
        }
        shifts[slice - 1][0] = original.disX;
        shifts[slice - 1][1] = original.disY;
    }
    static void writeOutput(Path path, double[][] shifts, int width, int height) throws IOException {
        try (DataOutputStream out = new DataOutputStream(new BufferedOutputStream(Files.newOutputStream(path)))) {
            out.writeInt(OUTPUT_MAGIC); out.writeInt(VERSION); out.writeInt(shifts.length);
            for (double[] shift : shifts) {
                if (shift == null || shift.length != 2) throw new IOException("Invalid shift pair");
                for (int axis = 0; axis < 2; axis++) {
                    double value = shift[axis];
                    if (!Double.isFinite(value) || value != Math.rint(value) || Math.abs(value) > (axis == 0 ? width : height))
                        throw new IOException("Invalid integer alignment shift");
                    out.writeDouble(value);
                }
            }
        }
    }
    public static void main(String[] args) throws Exception {
        if (args.length != 2) throw new IllegalArgumentException("Usage: NativeAlignmentMain input.gata output.gats");
        Input input = readInput(Paths.get(args[0]));
        System.err.println("GAT isolated Template Matching: native OpenCV4.11.0, original method5/integer alignment; "
                + System.getProperty("os.name") + "/" + System.getProperty("os.arch"));
        long start = System.nanoTime();
        double[][] shifts = align(input);
        writeOutput(Paths.get(args[1]), shifts, input.image.getWidth(), input.image.getHeight());
        System.err.println("Aligned " + shifts.length + " slices in " + (System.nanoTime() - start) / 1_000_000 + " ms");
    }
}

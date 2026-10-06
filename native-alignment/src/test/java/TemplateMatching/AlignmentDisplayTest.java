package TemplateMatching;

import ij.ImagePlus;
import ij.ImageStack;
import ij.process.ByteProcessor;
import ij.process.ImageProcessor;
import ij.process.ShortProcessor;
import java.awt.image.BufferedImage;
import java.awt.image.IndexColorModel;
import java.io.DataOutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Random;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;

/** Preserve the pixels seen by the original matching algorithm across the protocol. */
class AlignmentDisplayTest {
    @TempDir Path temporary;

    @Test void adjustedByteContrastPreservesRenderedPixelsAndNativeShifts() throws Exception {
        checkRoundTrip(movie(8, null), 100, 120);
    }

    @Test void invertedByteLutPreservesRenderedPixelsAndNativeShifts() throws Exception {
        byte[] inverted = new byte[256];
        for (int i = 0; i < 256; i++) inverted[i] = (byte) (255 - i);
        checkRoundTrip(movie(8, new IndexColorModel(8, 256, inverted, inverted, inverted)), 80, 150);
    }

    @Test void coloredByteLutPreservesRenderedPixelsAndNativeShifts() throws Exception {
        byte[] red = new byte[256], green = new byte[256], blue = new byte[256];
        for (int i = 0; i < 256; i++) {
            red[i] = (byte) i;
            green[i] = (byte) (255 - i);
            blue[i] = (byte) (i / 2);
        }
        checkRoundTrip(movie(8, new IndexColorModel(8, 256, red, green, blue)), 100, 120);
    }

    @Test void shortPixelsAndNativeShiftsRemainUnchangedByDisplayRange() throws Exception {
        checkRoundTrip(movie(16, null), 10000, 30000);
    }

    private ImagePlus movie(int bits, IndexColorModel palette) {
        Random random = new Random(0);
        ImageStack stack = new ImageStack(64, 64);
        for (int z = 0; z < 2; z++) {
            ImageProcessor processor;
            if (bits == 8) {
                byte[] pixels = new byte[64 * 64];
                for (int i = 0; i < pixels.length; i++) pixels[i] = (byte) random.nextInt(256);
                processor = new ByteProcessor(64, 64, pixels, palette);
            } else {
                short[] pixels = new short[64 * 64];
                for (int i = 0; i < pixels.length; i++) pixels[i] = (short) random.nextInt(65536);
                processor = new ShortProcessor(64, 64, pixels, palette);
            }
            stack.addSlice(processor);
        }
        return new ImagePlus("display control", stack);
    }

    private void checkRoundTrip(ImagePlus source, double minimum, double maximum) throws Exception {
        source.setDisplayRange(minimum, maximum);
        NativeAlignmentMain.Input restored = NativeAlignmentMain.readInput(encode(source));
        for (int z = 1; z <= source.getStackSize(); z++) {
            ImageProcessor expected = source.getStack().getProcessor(z);
            ImageProcessor actual = restored.image.getStack().getProcessor(z);
            assertEquals(expected.getMin(), actual.getMin());
            assertEquals(expected.getMax(), actual.getMax());
            for (int i = 0; i < expected.getPixelCount(); i++) assertEquals(expected.get(i), actual.get(i));
            BufferedImage before = expected.getBufferedImage(), after = actual.getBufferedImage();
            assertArrayEquals(before.getRGB(0, 0, 64, 64, null, 0, 64),
                    after.getRGB(0, 0, 64, 64, null, 0, 64));
        }
        double[][] expected = NativeAlignmentMain.align(new NativeAlignmentMain.Input(source, 1));
        double[][] actual = NativeAlignmentMain.align(restored);
        for (int z = 0; z < expected.length; z++) assertArrayEquals(expected[z], actual[z]);
    }

    private Path encode(ImagePlus image) throws Exception {
        Path path = temporary.resolve("display.gata");
        try (DataOutputStream out = new DataOutputStream(Files.newOutputStream(path))) {
            out.writeInt(NativeAlignmentMain.INPUT_MAGIC);
            out.writeInt(NativeAlignmentMain.VERSION);
            out.writeInt(image.getWidth());
            out.writeInt(image.getHeight());
            out.writeInt(image.getStackSize());
            out.writeInt(image.getBitDepth());
            out.writeInt(1);
            for (int z = 1; z <= image.getStackSize(); z++) {
                ImageProcessor processor = image.getStack().getProcessor(z);
                out.writeDouble(processor.getMin());
                out.writeDouble(processor.getMax());
                IndexColorModel palette = (IndexColorModel) processor.getColorModel();
                for (int i = 0; i < 256; i++) out.writeInt(palette.getRGB(i));
                for (int i = 0; i < processor.getPixelCount(); i++) {
                    if (image.getBitDepth() == 8) out.writeByte(processor.get(i));
                    else out.writeShort(processor.get(i));
                }
            }
        }
        return path;
    }
}

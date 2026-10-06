package Features.Inference;

import ij.ImagePlus;
import ij.ImageStack;
import ij.gui.Roi;
import ij.process.ByteProcessor;
import java.io.*;
import java.nio.file.*;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;

class NativeAlignmentClientTest {
    @TempDir Path temporary;
    ImagePlus image() {
        ImageStack stack = new ImageStack(8, 8);
        for (int z = 0; z < 3; z++) {
            ByteProcessor plane = new ByteProcessor(8, 8);plane.set(3, 3, 100 + z);stack.addSlice("frame" + z, plane);
        }
        ImagePlus image = new ImagePlus("alignment", stack);image.setDimensions(1, 1, 3);image.setT(2);
        image.getCalibration().pixelWidth = 0.5;image.getCalibration().frameInterval = 1.25;
        image.setRoi(new Roi(1, 1, 2, 2));return image;
    }
    Path output(double[][] shifts) throws Exception {
        Path file=temporary.resolve("output.bin");
        try(DataOutputStream out=new DataOutputStream(Files.newOutputStream(file))) {
            out.writeInt(NativeAlignmentClient.OUTPUT_MAGIC);out.writeInt(NativeAlignmentClient.VERSION);out.writeInt(shifts.length);
            for(double[] row:shifts)for(double value:row)out.writeDouble(value);
        }
        return file;
    }
    @Test void inputKeepsPixelsSelectionPositionAndPalette() throws Exception {
        ImagePlus source=image();Roi roi=source.getRoi();Path file=temporary.resolve("input.bin");
        NativeAlignmentClient.writeInput(file,source,2);
        assertEquals(28+3*(16+1024+64),Files.size(file));assertSame(roi,source.getRoi());assertEquals(2,source.getT());
        assertEquals(101,source.getStack().getProcessor(2).get(3,3));
        try(DataInputStream in=new DataInputStream(Files.newInputStream(file))) {
            assertEquals(NativeAlignmentClient.INPUT_MAGIC,in.readInt());assertEquals(NativeAlignmentClient.VERSION,in.readInt());
            assertEquals(8,in.readInt());assertEquals(8,in.readInt());assertEquals(3,in.readInt());assertEquals(8,in.readInt());assertEquals(2,in.readInt());
            assertEquals(0,in.readDouble());assertEquals(255,in.readDouble());
            assertEquals(0xff000000,in.readInt());
        }
    }
    @Test void inputPreservesAdjustedDisplayRangeWithoutChangingSource() throws Exception {
        ImagePlus source = image();
        source.setDisplayRange(100, 120);
        Path file = temporary.resolve("contrast.bin");
        NativeAlignmentClient.writeInput(file, source, 2);
        try (DataInputStream in = new DataInputStream(Files.newInputStream(file))) {
            in.skipBytes(28);
            for (int z = 0; z < 3; z++) {
                assertEquals(100, in.readDouble());
                assertEquals(120, in.readDouble());
                for (int i = 0; i < 256; i++)
                    assertEquals(source.getStack().getProcessor(z + 1).getColorModel().getRGB(i), in.readInt());
                in.skipBytes(64);
            }
            assertEquals(-1, in.read());
        }
        assertEquals(100, source.getDisplayRangeMin());
        assertEquals(120, source.getDisplayRangeMax());
        assertEquals(2, source.getT());
    }
    @Test void outputPreservesReferenceAndOrdering() throws Exception {
        double[][] expected={{2,-1},{0,0},{-3,4}};
        double[][] actual=NativeAlignmentClient.readOutput(output(expected),3,8,8,2);
        for(int i=0;i<3;i++)assertArrayEquals(expected[i],actual[i]);
    }
    @Test void outputRejectsBadLengthReferenceAndValues() throws Exception {
        for(double value:new double[]{Double.NaN,Double.POSITIVE_INFINITY,0.5,9})
            assertThrows(IOException.class,()->NativeAlignmentClient.readOutput(output(new double[][]{{value,0},{0,0},{0,0}}),3,8,8,2));
        assertThrows(IOException.class,()->NativeAlignmentClient.readOutput(output(new double[][]{{0,0},{1,0},{0,0}}),3,8,8,2));
        assertThrows(IOException.class,()->NativeAlignmentClient.readOutput(output(new double[][]{{0,0}}),3,8,8,2));
    }
    @Test void oldWorkerResponseFailsClosed() throws Exception {
        Path file = output(new double[][]{{0, 0}, {0, 0}, {0, 0}});
        try (RandomAccessFile bytes = new RandomAccessFile(file.toFile(), "rw")) {
            bytes.seek(4); bytes.writeInt(1);
        }
        assertThrows(IOException.class, () -> NativeAlignmentClient.readOutput(file, 3, 8, 8, 2));
    }
    @Test void translatedCopyPreservesMetadataAndDoesNotMutateSource() {
        ImagePlus source=image();ImagePlus result=NativeAlignmentClient.translatedCopy(source,new double[][]{{1,-1},{0,0},{-1,1}});
        assertEquals(100,result.getStack().getProcessor(1).get(4,2));assertEquals(100,source.getStack().getProcessor(1).get(3,3));
        assertEquals(0,source.getStack().getProcessor(1).get(4,2));assertNotNull(source.getRoi());
        assertEquals(3,result.getNFrames());assertEquals(2,result.getT());assertEquals(0.5,result.getCalibration().pixelWidth);
        assertEquals(1.25,result.getCalibration().frameInterval);assertEquals("frame0",result.getStack().getSliceLabel(1));
    }
    @Test void invalidInputOrShiftsFailWithoutChangingPixels() {
        ImagePlus source=image();
        assertThrows(IllegalArgumentException.class,()->NativeAlignmentClient.writeInput(temporary.resolve("in"),source,4));
        assertThrows(IllegalArgumentException.class,()->NativeAlignmentClient.translatedCopy(source,new double[][]{{Double.NaN,0},{0,0},{0,0}}));
        assertEquals(100,source.getStack().getProcessor(1).get(3,3));
    }
}

package TemplateMatching;

import java.io.*;
import java.nio.file.*;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;

class AlignmentProtocolTest {
    @TempDir Path temporary;
    Path input(int width, int height, int frames, int bits, int reference, boolean body) throws Exception {
        Path file = temporary.resolve("input.bin");
        try (DataOutputStream out = new DataOutputStream(Files.newOutputStream(file))) {
            out.writeInt(NativeAlignmentMain.INPUT_MAGIC);out.writeInt(NativeAlignmentMain.VERSION);out.writeInt(width);out.writeInt(height);
            out.writeInt(frames);out.writeInt(bits);out.writeInt(reference);
            if (body) for(int z=0;z<frames;z++) {
                out.writeDouble(0);out.writeDouble(bits == 8 ? 255 : 65535);
                for(int i=0;i<256;i++)out.writeInt(0xff000000 | i<<16 | i<<8 | i);
                for(int i=0;i<width*height;i++) {if(bits==8)out.writeByte(i+z);else out.writeShort(i*1000+z);}
            }
        }
        return file;
    }
    @Test void bytePixelsAndNonFirstReferenceRoundTrip() throws Exception {
        NativeAlignmentMain.Input result=NativeAlignmentMain.readInput(input(3,2,3,8,2,true));
        assertEquals(2,result.reference);assertEquals(3,result.image.getStackSize());
        assertEquals(7,result.image.getStack().getProcessor(3).get(5));
    }
    @Test void unsignedShortPixelsRoundTrip() throws Exception {
        NativeAlignmentMain.Input result=NativeAlignmentMain.readInput(input(9,8,2,16,1,true));
        assertEquals(65001,result.image.getStack().getProcessor(2).get(65));
    }
    @Test void badShapesReferenceAndTypeRejectBeforeAllocation() throws Exception {
        assertThrows(IOException.class,()->NativeAlignmentMain.readInput(input(3,2,2,32,1,false)));
        assertThrows(IOException.class,()->NativeAlignmentMain.readInput(input(3,2,2,8,3,false)));
        assertThrows(IOException.class,()->NativeAlignmentMain.readInput(input(Integer.MAX_VALUE,Integer.MAX_VALUE,2,16,1,false)));
    }
    @Test void truncatedAndTrailingBytesReject() throws Exception {
        assertThrows(IOException.class,()->NativeAlignmentMain.readInput(input(3,2,2,8,1,false)));
        Path file=input(3,2,2,8,1,true);Files.write(file,new byte[]{1},StandardOpenOption.APPEND);
        assertThrows(IOException.class,()->NativeAlignmentMain.readInput(file));
    }
    @Test void oldVersionAndInvalidDisplayRangeFailClosed() throws Exception {
        Path file = input(3, 2, 2, 8, 1, true);
        try (RandomAccessFile bytes = new RandomAccessFile(file.toFile(), "rw")) {
            bytes.seek(4); bytes.writeInt(1);
        }
        Path oldVersion = file;
        assertThrows(IOException.class, () -> NativeAlignmentMain.readInput(oldVersion));
        for (double minimum : new double[]{Double.NaN, Double.NEGATIVE_INFINITY, 256}) {
            file = input(3, 2, 2, 8, 1, true);
            try (RandomAccessFile bytes = new RandomAccessFile(file.toFile(), "rw")) {
                bytes.seek(28); bytes.writeDouble(minimum);
            }
            Path invalid = file;
            assertThrows(IOException.class, () -> NativeAlignmentMain.readInput(invalid));
        }
    }
    @Test void differingStackDisplayRangesFailClosed() throws Exception {
        Path file = input(3, 2, 2, 8, 1, true);
        try (RandomAccessFile bytes = new RandomAccessFile(file.toFile(), "rw")) {
            bytes.seek(28 + 16 + 1024 + 6); bytes.writeDouble(1);
        }
        assertThrows(IOException.class, () -> NativeAlignmentMain.readInput(file));
    }
    @Test void differingStackPalettesFailClosed() throws Exception {
        Path file = input(3, 2, 2, 8, 1, true);
        try (RandomAccessFile bytes = new RandomAccessFile(file.toFile(), "rw")) {
            bytes.seek(28 + 16 + 1024 + 6 + 16); bytes.writeInt(0xffffffff);
        }
        assertThrows(IOException.class, () -> NativeAlignmentMain.readInput(file));
    }
    @Test void outputRejectsNonfiniteFractionalAndOutOfRange() {
        for(double value:new double[]{Double.NaN,Double.POSITIVE_INFINITY,0.5,11})
            assertThrows(IOException.class,()->NativeAlignmentMain.writeOutput(temporary.resolve("out"),new double[][]{{value,0}},10,10));
    }
}

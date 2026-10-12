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
    @Test void newMovieAndRawBudgetBoundariesAreAdmittedWithoutAllocation() throws Exception {
        assertEquals(67_371_008L, NativeAlignmentMain.rawBytesForShape(512, 512, 257, 8, 3));
        assertEquals(536_870_912L, NativeAlignmentMain.rawBytesForShape(512, 512, 2048, 8, 3));
        assertEquals(536_870_912L, NativeAlignmentMain.rawBytesForShape(512, 512, 1024, 16, 3));
        assertThrows(IOException.class, () -> NativeAlignmentMain.rawBytesForShape(512, 512, 2049, 8, 3));
        assertThrows(IOException.class, () -> NativeAlignmentMain.rawBytesForShape(512, 512, 1025, 16, 3));
    }
    @Test void combinedWorkingSetBoundaryIsIndependentOfRawByteLimit() throws Exception {
        // 192 MiB raw + 512 MiB plane reserve + 64 MiB runtime = 768 MiB.
        assertEquals(201_326_592L, NativeAlignmentMain.rawBytesForShape(8192, 8192, 3, 8, 3));
        assertThrows(IOException.class, () -> NativeAlignmentMain.rawBytesForShape(8192, 8192, 4, 8, 3));
        // 448 MiB raw + 256 MiB plane reserve + 64 MiB runtime = 768 MiB.
        assertEquals(469_762_048L, NativeAlignmentMain.rawBytesForShape(4096, 8192, 7, 16, 3));
        assertThrows(IOException.class, () -> NativeAlignmentMain.rawBytesForShape(4096, 8192, 8, 16, 3));
    }
    @Test void everyOldFrameBoundaryRetainsBothSupportedDepths() throws Exception {
        // Old total<=64M pixels, frames>=2: raw<=128MiB and plane reserve<=256MiB.
        // Therefore the old worst managed estimate<=448MiB, below the new768MiB.
        for (int frames = 2; frames <= 10000; frames++) {
            int height = (int) (67_108_864L / (2L * frames));
            for (int bits : new int[]{8, 16})
                assertEquals(2L * height * frames * (bits / 8), NativeAlignmentMain.rawBytesForShape(2, height, frames, bits, 1));
        }
    }
    @Test void retainedShapeGuardsRejectExtremeIntegersBeforeProducts() {
        for (int[] shape : new int[][] {{Integer.MAX_VALUE, Integer.MAX_VALUE, Integer.MAX_VALUE, 16, 1},
                {Integer.MIN_VALUE, 512, 3, 8, 1}, {1, 512, 3, 8, 1}, {512, 512, 10001, 8, 1},
                {8193, 8192, 2, 8, 1}, {512, 512, 3, 32, 1}, {512, 512, 3, 8, 4}})
            assertThrows(IOException.class, () -> NativeAlignmentMain.rawBytesForShape(shape[0], shape[1], shape[2], shape[3], shape[4]));
    }
    @Test void excessiveBudgetRejectsHeaderBeforeBodyReadOrAllocation() throws Exception {
        Path file = input(8192,8192,4,8,3,false);
        byte[] before = Files.readAllBytes(file);
        IOException error = assertThrows(IOException.class, () -> NativeAlignmentMain.readInput(file));
        assertArrayEquals(before, Files.readAllBytes(file));
        assertTrue(error.getMessage().contains("bounded stack-memory budget"));
        assertFalse(error.getMessage().contains("input bytes"));
    }

}

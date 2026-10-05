package Features.Tools;

import ij.ImagePlus;
import ij.ImageStack;
import ij.measure.ResultsTable;
import ij.plugin.filter.Analyzer;
import ij.process.ByteProcessor;
import java.io.File;
import java.nio.file.*;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;

class AlignmentMotionCsvTest {
    @TempDir Path temporary;
    ImagePlus image() {
        ImageStack stack=new ImageStack(64,64);for(int i=0;i<5;i++)stack.addSlice(new ByteProcessor(64,64));
        ImagePlus image=new ImagePlus("sample",stack);image.setDimensions(1,1,5);return image;
    }
    ResultsTable table() {
        ResultsTable table=new ResultsTable();for(int slice:new int[]{2,1,4,5}) {
            table.incrementCounter();table.addValue("Slice",slice);table.addValue("dX",slice*2);table.addValue("dY",-slice);
        }
        return table;
    }
    @Test void nonFirstReferenceRestoresActualFrameIds() {
        double[][] shifts=AlignStack.verifiedLegacyTemplateShifts(table(),5,3);
        assertNotNull(shifts);assertArrayEquals(new double[]{2,-1},shifts[0]);assertArrayEquals(new double[]{4,-2},shifts[1]);
        assertArrayEquals(new double[]{0,0},shifts[2]);assertArrayEquals(new double[]{10,-5},shifts[4]);
    }
    @Test void staleGlobalMeasurementsNeverProduceMotionCsv() throws Exception {
        ResultsTable previous=Analyzer.getResultsTable();ResultsTable stale=new ResultsTable();stale.incrementCounter();stale.addValue("Area",800);stale.addValue("Mean",255);
        try { Analyzer.setResultsTable(stale);assertNull(AlignStack.writeVerifiedAlignmentResultsCSV(image(),temporary.toString()));
            try(java.util.stream.Stream<Path> files=Files.list(temporary)){assertEquals(0,files.count());}
            assertSame(stale,Analyzer.getResultsTable());
        } finally {Analyzer.setResultsTable(previous);}
    }
    @Test void onlyAlgorithmOwnedCopiedDataAreExported() throws Exception {
        ImagePlus image=image();double[][] shifts=AlignStack.verifiedLegacyTemplateShifts(table(),5,3);
        AlignStack.recordTemplateMotion(image,3,shifts);shifts[0][0]=999;
        File csv=AlignStack.writeVerifiedAlignmentResultsCSV(image,temporary.toString());List<String> lines=Files.readAllLines(csv.toPath());
        assertEquals(6,lines.size());assertEquals("Algorithm,ReferenceSlice,Slice,Dx,Dy",lines.get(0));
        assertEquals("TemplateMatching,3,1,2.000000,-1.000000",lines.get(1));assertEquals("TemplateMatching,3,3,0.000000,0.000000",lines.get(3));
    }
    @Test void incompleteDuplicateOrUnrelatedTablesAreRejected() {
        ResultsTable duplicate=table();duplicate.setValue("Slice",1,2);assertNull(AlignStack.verifiedLegacyTemplateShifts(duplicate,5,3));
        ResultsTable invalid=table();invalid.setValue("dX",0,Double.NaN);assertNull(AlignStack.verifiedLegacyTemplateShifts(invalid,5,3));
        assertNull(AlignStack.verifiedLegacyTemplateShifts(new ResultsTable(),5,3));
    }
}

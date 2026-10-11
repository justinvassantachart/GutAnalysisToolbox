package services.merge;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;
class CsvMergerRegressionTest {
 @TempDir Path root;
 private Path csv(String directory,String text)throws Exception {
  Path d=Files.createDirectories(root.resolve(directory));return Files.writeString(d.resolve("results.csv"),text);
 }
 @Test void outputIsNeverPassedBackToInputAppender()throws Exception {
  csv("one","Count,Area\n1,2\n");
  CsvMerger merger=new CsvMerger(new DefaultLabelStrategy()) {
   @Override protected void appendCsvFile(Path root,Path input,String[] header,java.io.BufferedWriter writer)throws java.io.IOException,MergeException {
    assertFalse(input.getFileName().toString().startsWith("Merged_"),"Merger attempted to read its own output");
    super.appendCsvFile(root,input,header,writer);
   }
  };
  assertEquals(2,Files.readAllLines(merger.mergeSinglePattern(root,"results")).size());
 }
 @Test void largeMergeNeverReadsItsOwnOutputAndPreservesEveryRow()throws Exception {
  StringBuilder input=new StringBuilder("Count,Text\n");
  for(int i=0;i<3000;i++)input.append(i).append(",a long row to exceed the output writer buffer\n");
  csv("one",input.toString());csv("two",input.toString());
  Path out=new CsvMerger(new DefaultLabelStrategy()).mergeSinglePattern(root,"results");
  assertEquals(6001,Files.readAllLines(out).size());
  assertThrows(MergeException.class,()->new CsvMerger(new DefaultLabelStrategy()).mergeSinglePattern(root,"results"));
 }
 @Test void multilineQuotedRecordsReceiveOnlyOneExperimentLabel()throws Exception {
  csv("exp, ü","Count,Text\n1,\"first line\nsecond \"\"quoted\"\" line\"\n2,plain\n");
  Path out=new CsvMerger(new DefaultLabelStrategy()).mergeSinglePattern(root,"results");
  assertEquals("Experiment,Count,Text\n\"exp, ü\",1,\"first line\nsecond \"\"quoted\"\" line\"\n\"exp, ü\",2,plain\n",Files.readString(out));
 }
 @Test void headerMismatchAndUnclosedQuoteRemovePartialOutput()throws Exception {
  csv("one","Count,Area\n1,2\n");csv("two","Different,Schema\n3,4\n");
  CsvMerger merger=new CsvMerger(new DefaultLabelStrategy(),StandardCharsets.UTF_8,true,true);
  assertThrows(MergeException.class,()->merger.mergeSinglePattern(root,"results"));
  try(java.util.stream.Stream<Path> entries=Files.list(root)){assertEquals(2,entries.count());}
  Files.writeString(root.resolve("two/results.csv"),"Count,Area\n3,\"unclosed\n");
  assertThrows(MergeException.class,()->merger.mergeSinglePattern(root,"results"));
  try(java.util.stream.Stream<Path> entries=Files.list(root)){assertEquals(2,entries.count());}
 }
 @Test void emptyRootsProduceHelpfulFailureWithoutOutput()throws Exception {
  CsvMerger merger=new CsvMerger(new DefaultLabelStrategy());
  assertThrows(MergeException.class,()->merger.mergeFromFirstSubfolderPatterns(root));
  assertThrows(MergeException.class,()->merger.mergeSinglePattern(root,"results"));
  try(java.util.stream.Stream<Path> entries=Files.list(root)){assertEquals(0,entries.count());}
 }
}

package Features.Tools;
import java.nio.file.*;
import java.util.*;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;
class MultimarkerCsvRegressionTest {
 @TempDir Path temporary;
 private LinkedHashMap<String,Integer> totals(){LinkedHashMap<String,Integer> m=new LinkedHashMap<>();m.put("A",7);return m;}
 private LinkedHashMap<String,int[]> per(){LinkedHashMap<String,int[]> m=new LinkedHashMap<>();m.put("A",new int[]{0,2,5});return m;}
 @Test void gatedCsvUsesGanglionIdsOneThroughNWithoutBackgroundOrDroppedLastRow()throws Exception{
  Path path=temporary.resolve("hu.csv");OutputIO.writeMultiCsv(path.toFile(),"image",9,2,totals(),per(),new double[]{0,10,20});
  List<String> lines=Files.readAllLines(path);assertEquals(3,lines.size());
  assertEquals("image,9,2,7,2,10.000000",lines.get(1));assertEquals(",,,,5,20.000000",lines.get(2));
 }
 @Test void noHuCsvCountsRealGangliaAndExportsEveryActualId()throws Exception{
  Path path=temporary.resolve("nohu.csv");OutputIO.writeMultiCsvNoHu(path.toFile(),"image",totals(),per(),new double[]{0,10,20});
  List<String> lines=Files.readAllLines(path);assertEquals(3,lines.size());
  assertEquals("image,2,7,2,10.000000",lines.get(1));assertEquals(",,,5,20.000000",lines.get(2));
 }
 @Test void noGangliaCaseRetainsExistingSummaryShape()throws Exception{
  Path path=temporary.resolve("none.csv");OutputIO.writeMultiCsvNoHu(path.toFile(),"image",totals(),new LinkedHashMap<>(),null);
  assertEquals(Arrays.asList("File name,A","image,7"),Files.readAllLines(path));
 }
}

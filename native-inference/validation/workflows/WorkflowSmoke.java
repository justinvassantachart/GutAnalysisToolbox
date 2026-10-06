import Analysis.TemporalColorCoder;
import Features.Core.Params;
import Features.Tools.LabelOps;
import Features.Tools.OutputIO;
import Features.AnalyseWorkflows.GangliaOps;
import services.merge.*;
import services.multiplex.util.NamingUtils;
import ij.ImagePlus;
import ij.ImageStack;
import ij.process.ByteProcessor;
import ij.process.ShortProcessor;
import ij.io.Opener;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

/** Runs real GAT Java helpers on known pixels/files, never mocked ImageJ calls. */
public final class WorkflowSmoke {
 public static void main(String[] args)throws Exception {
  Path out=Paths.get(args[0]);WorkflowReport r=new WorkflowReport("gat-java-workflows",out,"workflow-smoke.json");
  ImagePlus hu=new ImagePlus("hu",new ShortProcessor(4,2,new short[]{1,1,2,2,0,0,0,0},null));
  ImagePlus marker=new ImagePlus("marker",new ShortProcessor(4,2,new short[]{1,0,2,2,0,0,0,0},null));
  r.test("hu_marker_overlap","GAT helper","LabelOps.neuronsPositiveByOverlap",()->{
   WorkflowReport.check(Arrays.equals(LabelOps.neuronsPositiveByOverlap(hu,marker,.6),new boolean[]{false,false,true}),"0.6 overlap mismatch");
   WorkflowReport.check(Arrays.equals(LabelOps.neuronsPositiveByOverlap(hu,marker,.5),new boolean[]{false,true,true}),"0.5 boundary mismatch");
   return WorkflowReport.values("thresholds",new double[]{.5,.6},"expected_kept_labels",Arrays.asList("1,2","2"));});
  r.test("ganglia_count_area","GAT helper","GangliaOps.countPerGanglion",()->{
   ImagePlus gl=new ImagePlus("ganglia",new ShortProcessor(4,2,new short[]{1,1,2,2,1,1,2,2},null));gl.getCalibration().pixelWidth=2;gl.getCalibration().pixelHeight=2;
   GangliaOps.Result g=GangliaOps.countPerGanglion(hu,gl);
   WorkflowReport.check(g.maxGanglionId==2&&g.countsPerGanglion[1]==1&&g.countsPerGanglion[2]==1&&g.areaUm2[1]==16&&g.areaUm2[2]==16,"Counts or calibrated area mismatch");
   ImagePlus kept=GangliaOps.keepGangliaWithAtLeast(gl,new int[]{0,2,1},2);byte[] actual=(byte[])kept.getProcessor().getPixels();
   WorkflowReport.check(Arrays.equals(actual,new byte[]{-1,-1,0,0,-1,-1,0,0}),"Minimum count filtering mismatch");
   return WorkflowReport.values("counts",g.countsPerGanglion,"area_um2",g.areaUm2,"pixel_width_um",2,"minimum_count_filter",2);});
  r.test("temporal_color_8bit","GAT helper","TemporalColorCoder.run",()->{
   ImageStack st=new ImageStack(2,2);st.addSlice(new ByteProcessor(2,2,new byte[]{0,-1,0,-1},null));st.addSlice(new ByteProcessor(2,2,new byte[]{0,-1,0,-1},null));
   ImagePlus seq=new ImagePlus("time",st);seq.setDimensions(1,1,2);Params p=new Params();p.referenceFrame=1;p.referenceFrameEnd=2;p.lutName="Fire";p.projectionMethod="";p.createColorScale=true;
   TemporalColorCoder.TemporalColorOutput t=TemporalColorCoder.run(seq,p);WorkflowReport.check(t.rgbStack.getStackSize()==2&&t.rgbStack.getBitDepth()==24&&t.colorScale.getWidth()==256,"Temporal dimensions/type mismatch");
   WorkflowReport.check(t.rgbStack.getStack().getProcessor(1).get(0)==0&&t.rgbStack.getStack().getProcessor(2).get(0)==0,"Black pixel should remain black");
   WorkflowReport.check(t.rgbStack.getStack().getProcessor(1).get(1)!=t.rgbStack.getStack().getProcessor(2).get(1),"Two timepoints should have different LUT colors");
   new ij.io.FileSaver(t.rgbStack).saveAsTiffStack(out.resolve("temporal-color.tif").toString());
   return WorkflowReport.values("frames",2,"bit_depth",24,"lut","Fire","evidence","temporal-color.tif","scope_note","8-bit/no projection only");});
  r.test("csv_merge_and_overwrite","GAT helper","CsvMerger.mergeSinglePattern",()->{
   Path root=Files.createDirectories(out.resolve("merge input ü"));Path a=Files.createDirectories(root.resolve("sample A")),b=Files.createDirectories(root.resolve("sample B"));
   Files.write(a.resolve("results.csv"),Arrays.asList("Count,Area","3,12"),StandardCharsets.UTF_8);Files.write(b.resolve("results.csv"),Arrays.asList("Count,Area","4,16"),StandardCharsets.UTF_8);
   Path merged=new CsvMerger(new DefaultLabelStrategy()).mergeSinglePattern(root,"results");List<String> lines=Files.readAllLines(merged,StandardCharsets.UTF_8);
   WorkflowReport.check(lines.size()==3&&lines.get(0).equals("Experiment,Count,Area")&&lines.contains("sample A,3,12")&&lines.contains("sample B,4,16"),"Merged rows/labels mismatch");
   boolean refused=false;try{new CsvMerger(new DefaultLabelStrategy()).mergeSinglePattern(root,"results");}catch(MergeException e){refused=true;}WorkflowReport.check(refused,"Existing output was not refused");
   return WorkflowReport.values("input_files",2,"output_rows",2,"overwrite_refused",true,"evidence",out.relativize(merged).toString());});
  r.test("counts_csv","GAT helper","OutputIO.writeCountsCsv",()->{
   Path f=out.resolve("counts.csv");OutputIO.writeCountsCsv(f.toFile(),"image","Hu",2);WorkflowReport.check(Files.readString(f).contains("image,2"),"Wrong count CSV");return WorkflowReport.values("count",2,"evidence","counts.csv");});
  r.test("label_tiff_roundtrip","GAT helper","OutputIO.saveTiff + ImageJ Opener",()->{
   Path f=out.resolve("labels.tif");hu.getCalibration().pixelWidth=.5;hu.getCalibration().pixelHeight=.5;hu.getCalibration().setUnit("um");OutputIO.saveTiff(hu,f.toFile());ImagePlus a=new Opener().openImage(f.toString());
   WorkflowReport.check(a!=null&&a.getBitDepth()==16&&Arrays.equals((short[])a.getProcessor().getPixels(),(short[])hu.getProcessor().getPixels()),"Label TIFF pixels changed");WorkflowReport.check(Math.abs(a.getCalibration().pixelWidth-.5)<1e-10,"Calibration changed");
   return WorkflowReport.values("differing_pixels",0,"pixel_width_um",a.getCalibration().pixelWidth,"evidence","labels.tif");});
  r.test("multiplex_naming","GAT helper only","NamingUtils",()->{
   WorkflowReport.check("layer1_hu".equals(NamingUtils.normalize(" Layer 1_Hu ")),"Normalization mismatch");WorkflowReport.check(NamingUtils.hasTifExt(new java.io.File("Layer 1_Hu.TIFF")),"TIFF extension mismatch");
   return WorkflowReport.values("scope_note","Filename handling only; registration is in a separate command harness");});
  r.notRun("neuron_subtype_full_gui","Full GAT Fiji workflow","Covered separately by inference fixtures; this helper run does not automate complete segmentation/review GUI");
  r.notRun("calcium_auto_stardist","Full GAT Fiji workflow","Existing production method is a disabled stub; not counted as a compatibility pass");
  r.write();if(r.failures()>0)System.exit(1);
 }
}

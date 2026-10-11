package Analysis;
import Features.Core.Params;
import ij.ImagePlus;
import ij.ImageStack;
import ij.process.*;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
class TemporalColorRegressionTest {
 private Params params(){Params p=new Params();p.referenceFrame=1;p.referenceFrameEnd=3;p.lutName="Fire";p.projectionMethod="";p.createColorScale=true;return p;}
 private ImagePlus movie(int bits){
  ImageStack stack=new ImageStack(2,1);
  for(int t=0;t<3;t++){
   ImageProcessor ip=bits==8?new ByteProcessor(2,1):bits==16?new ShortProcessor(2,1):new FloatProcessor(2,1);
   ip.setf(0,0);ip.setf(1,bits==8?255:bits==16?65535:1);
   stack.addSlice(ip);
  }
  ImagePlus source=new ImagePlus("time",stack);source.setDisplayRange(0,bits==8?255:bits==16?65535:1);
  source.getCalibration().pixelWidth=.5;source.getCalibration().frameInterval=2;source.setSlice(2);return source;
 }
 @Test void widerGrayscaleUsesDisplayRangeAndMatchesByteEndpoints()throws Exception{
  ImagePlus reference=TemporalColorCoder.run(movie(8),params()).rgbStack;
  for(int bits:new int[]{16,32}){
   ImagePlus source=movie(bits);ImagePlus result=TemporalColorCoder.run(source,params()).rgbStack;
   for(int frame=1;frame<=3;frame++)assertArrayEquals((int[])reference.getStack().getProcessor(frame).getPixels(),(int[])result.getStack().getProcessor(frame).getPixels());
   assertEquals(3,source.getNSlices());assertEquals(1,source.getNFrames());assertEquals(2,source.getCurrentSlice());
   assertEquals(1,result.getNSlices());assertEquals(3,result.getNFrames());assertEquals(.5,result.getCalibration().pixelWidth);assertEquals(2,result.getCalibration().frameInterval);
  }
 }
 @Test void scaleEndpointsMatchFirstAndLastSelectedColors()throws Exception {
  Params p=params();p.referenceFrame=2;p.referenceFrameEnd=3;
  TemporalColorCoder.TemporalColorOutput result=TemporalColorCoder.run(movie(8),p);
  assertEquals(2,result.rgbStack.getStackSize());
  assertEquals(result.rgbStack.getStack().getProcessor(1).get(1),result.colorScale.getProcessor().get(0,0));
  assertEquals(result.rgbStack.getStack().getProcessor(2).get(1),result.colorScale.getProcessor().get(255,0));
 }
 @Test void invalidRangesAndRgbFailBeforeChangingInput()throws Exception {
  ImagePlus source=movie(8);Params p=params();p.referenceFrame=9;
  assertThrows(IllegalArgumentException.class,()->TemporalColorCoder.run(source,p));
  assertEquals(2,source.getCurrentSlice());assertEquals(3,source.getNSlices());
  assertThrows(IllegalArgumentException.class,()->TemporalColorCoder.run(new ImagePlus("rgb",new ColorProcessor(2,1)),params()));
 }
 @Test void projectionKeepsCalibration()throws Exception {
  Params p=params();p.projectionMethod="Max Intensity";
  ImagePlus out=TemporalColorCoder.run(movie(16),p).rgbStack;
  assertEquals(1,out.getStackSize());assertEquals(24,out.getBitDepth());assertEquals(.5,out.getCalibration().pixelWidth);
 }
 @Test void temporalProjectionKeepsDistinctZPlanesForEveryMethod()throws Exception {
  ImageStack stack=new ImageStack(2,1);
  for(int t=0;t<3;t++)for(int z=0;z<2;z++)stack.addSlice(new ByteProcessor(2,1,z==0?new byte[]{-1,0}:new byte[]{0,-1},null));
  ImagePlus source=new ImagePlus("z-time",stack);source.setDimensions(1,2,3);source.setOpenAsHyperStack(true);
  source.setPosition(1,2,2);
  for(String method:new String[]{"Max Intensity","Average Intensity","Min Intensity"}){
   Params p=params();p.referenceFrame=2;p.referenceFrameEnd=3;p.projectionMethod=method;
   ImagePlus result=TemporalColorCoder.run(source,p).rgbStack;
   assertEquals(2,result.getNSlices());assertEquals(1,result.getNFrames());
   assertEquals(0,result.getStack().getProcessor(1).get(1)&0xffffff);assertEquals(0,result.getStack().getProcessor(2).get(0)&0xffffff);
   ImageStack single=new ImageStack(1,1);for(int t=0;t<3;t++)single.addSlice(new ByteProcessor(1,1,new byte[]{-1},null));
   int expected=TemporalColorCoder.run(new ImagePlus("single-z",single),p).rgbStack.getProcessor().get(0);
   assertEquals(expected,result.getStack().getProcessor(1).get(0));assertEquals(expected,result.getStack().getProcessor(2).get(1));
   assertEquals(2,source.getZ());assertEquals(2,source.getT());
  }
 }
 @Test void dashboardAcceptsDisabledColorScale()throws Exception {
  javax.swing.SwingUtilities.invokeAndWait(()->{
   try {
    UI.panes.SettingPanes.TemporalColorPane pane=new UI.panes.SettingPanes.TemporalColorPane(null,null);
    java.lang.reflect.Field source=pane.getClass().getDeclaredField("selectedImage");source.setAccessible(true);source.set(pane,movie(8));
    java.lang.reflect.Field end=pane.getClass().getDeclaredField("tfEndFrame");end.setAccessible(true);((javax.swing.JTextField)end.get(pane)).setText("3");
    java.lang.reflect.Field scale=pane.getClass().getDeclaredField("cbColorScale");scale.setAccessible(true);((javax.swing.JCheckBox)scale.get(pane)).setSelected(false);
    java.lang.reflect.Method run=pane.getClass().getDeclaredMethod("runWorkflow");run.setAccessible(true);run.invoke(pane);
    java.lang.reflect.Field tabs=pane.getClass().getDeclaredField("dashboardTabs");tabs.setAccessible(true);assertEquals(1,((javax.swing.JTabbedPane)tabs.get(pane)).getTabCount());
   } catch(ReflectiveOperationException error){throw new AssertionError(error);}
  });
 }

}

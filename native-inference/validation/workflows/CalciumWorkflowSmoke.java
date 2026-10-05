import Analysis.CalciumAnalysis;
import Features.Core.Params;
import ij.*;
import ij.gui.Roi;
import ij.io.FileSaver;
import ij.measure.ResultsTable;
import ij.plugin.frame.RoiManager;
import ij.process.FloatProcessor;
import java.awt.*;
import java.awt.event.*;
import javax.swing.*;
import java.nio.file.*;
import java.util.*;

/** Actual GAT calcium methods with synthetic movie and narrowly scoped in-process dialog controls. */
public final class CalciumWorkflowSmoke {
 static void visit(Component c, java.util.List<Component> all){all.add(c);if(c instanceof Container)for(Component child:((Container)c).getComponents())visit(child,all);}
 static final Map<Window,Integer> activeTicks=new IdentityHashMap<>();
 static final Set<Window> answered=Collections.newSetFromMap(new IdentityHashMap<Window,Boolean>());
 static final Map<String,Object> acceptedValues=new LinkedHashMap<>();
 static void respondToTestDialogs(){
  if(!SwingUtilities.isEventDispatchThread())throw new IllegalStateException("Dialog controller must run on EDT");
  for(Window w:Window.getWindows()) {
   if(!(w instanceof Dialog)||answered.contains(w))continue;
   Dialog dialog=(Dialog)w;String title=dialog.getTitle();
   if(!("Select Baseline Frames".equals(title)||"Select Max Projection Frames".equals(title)||"Multi Measure".equals(title)))continue;
   if(!w.isShowing()||!w.isDisplayable()||!w.isActive()||!dialog.isModal()) {activeTicks.remove(w);continue;}
   int ticks=activeTicks.getOrDefault(w,0)+1;activeTicks.put(w,ticks);
   if(ticks<2)continue; // Never answer during JOptionPane's opening/initialization race.
   java.util.List<Component> all=new ArrayList<>();visit(w,all);
   if("Select Baseline Frames".equals(title)||"Select Max Projection Frames".equals(title)) {
    java.util.List<JSpinner> spins=new ArrayList<>();JOptionPane pane=null;JButton ok=null;
    for(Component c:all) {
     if(c instanceof JSpinner)spins.add((JSpinner)c);
     if(c instanceof JOptionPane)pane=(JOptionPane)c;
     if(c instanceof JButton&&c.isShowing()&&c.isEnabled()&&"OK".equals(((JButton)c).getText().trim()))ok=(JButton)c;
    }
    if(spins.size()!=2||pane==null||ok==null)continue;
    spins.get(0).setValue(1);spins.get(1).setValue("Select Baseline Frames".equals(title)?2:3);
    final JOptionPane selected=pane;
    selected.addPropertyChangeListener(JOptionPane.VALUE_PROPERTY,event->{
     Object value=event.getNewValue();acceptedValues.put(title,value);
     System.out.println("DIALOG_VALUE "+title+" value="+value+" thread="+Thread.currentThread().getName());
    });
    answered.add(w);
    System.out.println("DIALOG_CLICK "+title+" start="+spins.get(0).getValue()+" end="+spins.get(1).getValue()+" active_ticks="+ticks+" button="+ok.getText());
    ok.doClick(); // Actual enabled Swing button; no direct JOptionPane.setValue shortcut.
    acceptedValues.put(title,selected.getValue());
    System.out.println("DIALOG_ACCEPTED "+title+" value="+selected.getValue()+" showing="+w.isShowing());
   } else {
    Button ok=null;for(Component c:all)if(c instanceof Button&&c.isShowing()&&c.isEnabled()&&"OK".equals(((Button)c).getLabel().trim()))ok=(Button)c;
    if(ok==null)continue;
    for(Component c:all)if(c instanceof Checkbox){Checkbox b=(Checkbox)c;String label=b.getLabel().toLowerCase(Locale.ROOT);if(label.contains("all")||label.contains("one row"))b.setState(true);if(label.contains("append"))b.setState(false);}
    answered.add(w);System.out.println("DIALOG_CLICK Multi Measure label="+ok.getLabel()+" active_ticks="+ticks);
    ok.dispatchEvent(new ActionEvent(ok,ActionEvent.ACTION_PERFORMED,ok.getActionCommand()));
   }
  }
 }
 static void requireAccepted(String title)throws Exception {
  SwingUtilities.invokeAndWait(()->{});
  Object value=acceptedValues.get(title);
  WorkflowReport.check(value instanceof Integer&&((Integer)value)==JOptionPane.OK_OPTION,
    "HARNESS_DIALOG_NOT_ACCEPTED: "+title+" value="+value+"; no production calculation failure is inferred");
 }
 static void logProductionClass()throws Exception {
  Class<?> c=CalciumAnalysis.class;java.security.MessageDigest hash=java.security.MessageDigest.getInstance("SHA-256");
  try(java.io.InputStream in=c.getResourceAsStream("/Analysis/CalciumAnalysis.class")) {byte[]b=new byte[8192];int n;while((n=in.read(b))>=0)hash.update(b,0,n);}
  StringBuilder hex=new StringBuilder();for(byte b:hash.digest())hex.append(String.format("%02x",b&255));
  boolean direct=false;for(java.lang.reflect.Method m:c.getDeclaredMethods())if(m.getName().equals("projectFrames"))direct=true;
  System.out.println("PRODUCTION_CLASS source="+c.getProtectionDomain().getCodeSource().getLocation()+" sha256="+hex+" direct_projection_helper="+direct);
 }
 public static void main(String[]args)throws Exception {
  Path out=Paths.get(args[0]);WorkflowReport r=new WorkflowReport("gat-calcium-commands",out,"calcium-report.json");
  if(GraphicsEnvironment.isHeadless()) {r.blocked("calcium_ff0_measure_export","Actual GAT methods and dialogs","AWT reports headless; baseline selection/ROI Manager require an accessible desktop");r.write();return;}
  javax.swing.Timer responder=new javax.swing.Timer(150,e->respondToTestDialogs());responder.start();
  try {
   new ImageJ(ImageJ.NO_SHOW);logProductionClass();
   r.test("calcium_ff0_measure_export","Actual GAT command workflow; no dashboard clicks","CalciumAnalysis open/projection/normalize/ROI/measure/save",()->{
    ImageStack st=new ImageStack(8,8);for(int z=0;z<3;z++){float[]p=new float[64];Arrays.fill(p,100);if(z==2)for(int y=0;y<2;y++)for(int x=0;x<2;x++)p[y*8+x]=200;st.addSlice(new FloatProcessor(8,8,p));}
    ImagePlus fixture=new ImagePlus("calcium-fixture",st);Path input=out.resolve("calcium-fixture.tif");WorkflowReport.check(new FileSaver(fixture).saveAsTiffStack(input.toString()),"Cannot write synthetic movie");
    Params params=new Params();params.imagePath=input.toAbsolutePath().toString();params.useFF0=true;params.useStarDist=false;params.cellNames=Arrays.asList("SyntheticCell");
    CalciumAnalysis a=new CalciumAnalysis(params);a.openImage();WorkflowReport.check(a.maxProj!=null&&a.maxProj.getStackSize()==3,"GAT did not open full stack");
    ImagePlus rawBeforeProjection=a.maxProj;
    ij.plugin.ZProjector control=new ij.plugin.ZProjector(rawBeforeProjection);control.setStartSlice(1);control.setStopSlice(3);control.setMethod(ij.plugin.ZProjector.MAX_METHOD);control.doProjection();
    float controlPixel=control.getProjection().getProcessor().getf(0,0);WorkflowReport.check(controlPixel==200,"Direct ImageJ projection control failed: "+controlPixel);
    a.createMaxProjection();requireAccepted("Select Max Projection Frames");
    System.out.println("PROJECTION_OBSERVED value="+a.maxProj.getProcessor().getf(0,0)+" stack="+a.maxProj.getStackSize()+" source_alias="+(a.maxProj==rawBeforeProjection)+" title="+a.maxProj.getTitle()+" control="+controlPixel);
    FileSaver observed=new FileSaver(a.maxProj);if(a.maxProj.getStackSize()>1)observed.saveAsTiffStack(out.resolve("projection-observed.tif").toString());else observed.saveAsTiff(out.resolve("projection-observed.tif").toString());
    WorkflowReport.check(a.maxProj!=rawBeforeProjection&&a.maxProj.getStackSize()==1&&a.maxProj.getProcessor().getf(0,0)==200,"Projection selected wrong result: value="+a.maxProj.getProcessor().getf(0,0)+" planes="+a.maxProj.getStackSize()+" source_alias="+(a.maxProj==rawBeforeProjection));
    a.normalizeStack();requireAccepted("Select Baseline Frames");WorkflowReport.check(a.normStack!=null&&a.normStack.getStackSize()==3,"No F/F0 stack");
    double[] expect={1,1,2};for(int z=1;z<=3;z++)WorkflowReport.check(Math.abs(a.normStack.getStack().getProcessor(z).getf(0,0)-expect[z-1])<1e-6,"Wrong normalized ROI pixel at frame "+z);
    a.setupROIManager();RoiManager rm=RoiManager.getInstance();rm.addRoi(new Roi(0,0,2,2));a.renameROIs();WorkflowReport.check(rm.getRoi(0).getName().equals("SyntheticCell_1"),"ROI rename mismatch");
    a.measureROIs();ResultsTable table=ResultsTable.getResultsTable();WorkflowReport.check(table!=null&&table.size()==3,"Expected three measurement rows");
    String[] heads=table.getHeadings();String mean=null;for(String h:heads)if(h.startsWith("Mean")){mean=h;break;}WorkflowReport.check(mean!=null,"No mean measurement column: "+Arrays.toString(heads));
    double[] measured=new double[3];for(int i=0;i<3;i++){measured[i]=table.getValue(mean,i);WorkflowReport.check(Math.abs(measured[i]-expect[i])<1e-6,"Wrong measured F/F0 at frame "+i);}
    java.io.File csv=a.saveResults();WorkflowReport.check(csv.exists()&&csv.length()>0,"Missing CSV");Path resultDir=csv.toPath().getParent();
    Path roi=resultDir.resolve("ROIS_calcium-fixture.tif_CELLS.zip");WorkflowReport.check(Files.isRegularFile(roi),"Missing ROI ZIP");rm.reset();rm.runCommand("Open",roi.toString());WorkflowReport.check(rm.getCount()==1&&rm.getRoi(0).getBounds().equals(new Rectangle(0,0,2,2)),"ROI ZIP did not round trip");
    return WorkflowReport.values("dialog_accepted_values",acceptedValues,"baseline_frames",new int[]{1,2},"max_projection_frames",new int[]{1,3},"expected_ff0",expect,"measured_ff0",measured,"roi_count",1,"csv",out.relativize(csv.toPath()).toString(),"roi_zip",out.relativize(roi).toString(),"scope_note","Invoked production methods and controlled only their own known dialogs; not a manual dashboard/navigation test");
   });
  } catch(Throwable t) {r.blocked("calcium_awt_initialization","Actual GAT commands",t.toString());}
  finally {responder.stop();r.notRun("calcium_zero_baseline","Numerical edge case","First smoke covers nonzero known baseline only");r.notRun("calcium_auto_stardist","Unsupported production path","Automatic StarDist method remains disabled; no generated-ROI claim");r.write();System.exit(r.failures()>0?1:0);}
 }
}

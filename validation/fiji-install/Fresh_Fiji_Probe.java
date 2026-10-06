import ij.IJ;
import ij.ImagePlus;
import ij.ImageStack;
import ij.Menus;
import ij.WindowManager;
import ij.plugin.PlugIn;
import ij.process.ByteProcessor;
import ij.process.ImageProcessor;
import java.awt.*;
import java.io.*;
import java.lang.reflect.InvocationTargetException;
import java.nio.*;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import java.util.List;
import javax.swing.*;

/** Diagnostic IJ1 plugin invoked by the real Fiji launcher and its normal macro/command bridge.
 * No new ImageJ context, legacy preinitialization, menu injection, or class-loader replacement. */
public final class Fresh_Fiji_Probe implements PlugIn {
    private final Map<String,Object> report = new LinkedHashMap<>();
    private final List<String> errors = Collections.synchronizedList(new ArrayList<>());
    private Path output;
    private String mode;
    private volatile boolean blocked;
    private final List<Map<String,Object>> dialogs = Collections.synchronizedList(new ArrayList<>());

    public void run(String arg) {
        mode=System.getProperty("gat.validation.mode", "startup");
        output=Paths.get(System.getProperty("gat.validation.report"));
        report.put("schema_version",1); report.put("mode",mode); report.put("status","RUNNING");
        report.put("scope", "Real installed Fiji launcher/classloader; named stage only, not all workflows");
        Thread.setDefaultUncaughtExceptionHandler((thread,error)->record(error));
        IJ.setExceptionHandler(this::record);
        try {
            runtime(); snapshot();
            if(mode.equals("dashboard")) dashboard();
            else if(mode.equals("neuron")) neuron();
            else if(mode.equals("alignment")) alignment();
            else if(mode.equals("engine_install")) engineInstall();
            else if(mode.equals("engine_inference") || mode.equals("ganglia")) {
                report.put("action", mode.equals("engine_inference") ? "Actual full-model JDLL inference in installed Fiji" : "Actual GAT DeepImageJ ganglia command in installed Fiji");snapshot();
                Object metrics=Class.forName("Fresh_Ganglia_Probe",true,IJ.getClassLoader()).getMethod("run",String.class,Path.class).invoke(null,mode,output);
                report.put("metrics",metrics);
            }
            else if(!mode.equals("startup")) throw new IllegalArgumentException("Unknown mode "+mode);
            captureWindows();
            report.put("status", blocked ? "BLOCKED" : errors.isEmpty() ? "PASS" : "FAIL");
        } catch(Throwable error) {
            record(error); report.put("status","FAIL");
        } finally {
            captureWindows(); report.put("dialogs",new ArrayList<>(dialogs));
            report.put("imagej_log",IJ.getLog()); report.put("errors",new ArrayList<>(errors));
            if(!errors.isEmpty() && "PASS".equals(report.get("status"))) report.put("status","FAIL");
            snapshot(); System.out.println("FRESH_FIJI_PROBE_DONE "+mode+" "+report.get("status"));
        }
        System.exit("PASS".equals(report.get("status"))?0:"BLOCKED".equals(report.get("status"))?3:2);
    }
    private void runtime() throws Exception {
        require(IJ.getInstance()!=null,"Native Fiji did not initialize its ImageJ UI");
        require(!GraphicsEnvironment.isHeadless(),"A GUI-capable native Mac is required");
        String arch=System.getProperty("os.arch");
        require(System.getProperty("os.name").startsWith("Mac") && (arch.equals("aarch64")||arch.equals("arm64")),"Not native macOS arm64");
        Path root=Paths.get(IJ.getDirectory("imagej")).toRealPath();
        require(root.equals(Paths.get(System.getProperty("gat.validation.root")).toRealPath()),"ImageJ root escaped the fresh fixture");
        Path javaHome=Paths.get(System.getProperty("java.home")).toRealPath();
        require(javaHome.startsWith(root.resolve("java").toRealPath()),"Fiji did not use its own bundled Java");
        report.put("imagej_root",root.toString()); report.put("java_home",javaHome.toString());
        for(String property:new String[]{"java.version","java.vendor","os.name","os.version","os.arch","java.class.path","sun.java.command","fiji.executable","ij.executable"})report.put(property,System.getProperty(property));
        report.put("system_classloader",ClassLoader.getSystemClassLoader().getClass().getName());
        report.put("plugin_classloader",IJ.getClassLoader().getClass().getName());
        report.put("probe_classloader",getClass().getClassLoader().getClass().getName());
        Map<String,Object> commands=new TreeMap<>();
        for(Object k:Menus.getCommands().keySet())commands.put(String.valueOf(k),String.valueOf(Menus.getCommands().get(k)));
        report.put("registered_commands",commands);
        Map<String,Object> sources=new LinkedHashMap<>();
        for(String name:new String[]{"UI.GatPluginUI","UI.Preflight","Features.Core.PluginCalls","Features.Tools.AlignStack","ij.IJ","net.imagej.Main","de.csbdresden.CommandFromMacro","de.csbdresden.stardist.StarDist2D","net.imagej.tensorflow.DefaultTensorFlowService","org.tensorflow.TensorFlow","TemplateMatching.Align_slices","DeepImageJ_Run"}){
            try{Class<?> type=Class.forName(name,false,IJ.getClassLoader());java.security.CodeSource s=type.getProtectionDomain().getCodeSource();sources.put(name,map("loader",String.valueOf(type.getClassLoader()),"source",s==null?String.valueOf(type.getResource("/"+name.replace('.','/')+".class")):s.getLocation().toString()));}
            catch(Throwable t){sources.put(name,map("unavailable",t.toString()));}
        }
        report.put("class_sources",sources);
        require(IJ.getClassLoader().getResource("org/tensorflow/types/TFloat32.class")==null,"Modern TensorFlow leaked onto Fiji classpath");
        if(!mode.equals("startup") && !mode.startsWith("engine_"))require(commands.containsKey("GATV2"),"GATV2 menu command was not registered by installed Fiji");
    }
    private void engineInstall() throws Exception {
        ClassLoader loader=IJ.getClassLoader();
        String resolved=(String)Class.forName("io.bioimage.modelrunner.versionmanagement.SupportedVersions",true,loader)
                .getMethod("getJavaVersionForPythonVersion",String.class,String.class).invoke(null,"pytorch","2.4.1+cpu");
        require("2.0.0".equals(resolved),"Installed JDLL resolver disagrees with pinned engine: "+resolved);
        Path engines=Paths.get(IJ.getDirectory("imagej"),"engines");
        report.put("action","Shipped JDLL EngineInstall.installEngineWithArgsInDir(pytorch,2.0.0,true,false,engines)");
        report.put("model_declared_version","2.4.1+cpu");report.put("catalog_resolved_version",resolved);snapshot();
        Class.forName("io.bioimage.modelrunner.engine.installation.EngineInstall",true,loader)
                .getMethod("installEngineWithArgsInDir",String.class,String.class,boolean.class,boolean.class,String.class)
                .invoke(null,"pytorch","2.0.0",true,false,engines.toString());
        require(Files.isDirectory(engines.resolve("pytorch-2.0.0-2.0.0-macosx-arm64-cpu")),"Supported installer did not create the requested real engine");
        report.put("note","Installer return alone is not proof: Python verifies all hashes, adds the pinned official native CPU jar, then a separate launcher process must load/run the full model before copying installations");
    }
    private void dashboard() throws Exception {
        report.put("action","IJ.run(\"GATV2\") using the real installed menu mapping"); snapshot();
        Thread launch=new Thread(()->{try{IJ.run("GATV2");}catch(Throwable t){record(t);}},"fresh-fiji-gat-command");
        launch.start(); long deadline=System.nanoTime()+60_000_000_000L;
        Set<Window> seen=Collections.newSetFromMap(new IdentityHashMap<Window,Boolean>());
        while(System.nanoTime()<deadline){
            final boolean[] visible={false};
            SwingUtilities.invokeAndWait(()->{
                for(Window w:Window.getWindows()){
                    if(!w.isShowing())continue;
                    String title=w instanceof Dialog?((Dialog)w).getTitle():w instanceof Frame?((Frame)w).getTitle():w.getClass().getName();
                    if("GAT Plugin".equals(title) && w instanceof JDialog && !((JDialog)w).isModal())visible[0]=true;
                    if(w instanceof Dialog && ((Dialog)w).isModal() && seen.add(w)){
                        String text=componentText(w);dialogs.add(map("title",title,"text",text));
                        if("GAT – First time".equals(title)){
                            dialogs.get(dialogs.size()-1).put("action","Dismissed informational first-run notice; GAT itself creates its sentinel");
                            w.dispose();
                        }else{
                            blocked=true;report.put("blocking_dialog",map("title",title,"text",text));
                            // Do not accept a warning, change options, download engines, or fabricate prerequisites.
                        }
                    }
                }
            });
            snapshot();
            if(visible[0]){report.put("dashboard_visible",true); return;}
            if(blocked){report.put("dashboard_visible",false); return;}
            if(!errors.isEmpty())throw new IllegalStateException("GAT launch raised an exception");
            Thread.sleep(250);
        }
        blocked=true;report.put("reason","GAT dashboard did not become visible within 60 seconds; inspect window and ImageJ logs");
        report.put("dashboard_visible",false);
    }
    private void neuron() throws Exception {
        Path model=Paths.get(IJ.getDirectory("imagej"),"models","2D_enteric_neuron_v4_1.zip");
        require(Files.isRegularFile(model),"Official updater did not install the neuron model");
        ImagePlus input=IJ.openImage(System.getProperty("gat.validation.fixture"));
        require(input!=null && input.getWidth()==175 && input.getHeight()==175 && input.getBitDepth()==8,"Public Hu fixture changed");
        input.setTitle("fresh_fiji_public_Hu");
        String before=pixels(input);
        report.put("action","Features.Core.PluginCalls.runStarDist2DLabel, invoked inside installed Fiji");snapshot();
        Class<?> type=Class.forName("Features.Core.PluginCalls",true,IJ.getClassLoader());
        int tiles=((Number)type.getMethod("suggestTiles",int.class,int.class).invoke(null,175,175)).intValue();
        report.put("requested_tiles",tiles);require(tiles==4,"The fixed API reference requires GAT's four-tile setting");
        report.put("probability_threshold",.5);report.put("nms_threshold",.3);
        ImagePlus labels=(ImagePlus)type.getMethod("runStarDist2DLabel",ImagePlus.class,String.class,double.class,double.class).invoke(null,input,model.toString(),.5,.3);
        captureWindows();
        require(labels!=null && labels!=input,"Null/unchanged-input fallback is not a segmentation result");
        require(labels.getBitDepth()==16 && labels.getWidth()==175 && labels.getHeight()==175 && labels.getStackSize()==1,"Unexpected label geometry/type");
        require(before.equals(pixels(input)),"Source image was modified");
        MessageDigest digest=MessageDigest.getInstance("SHA-256");Set<Integer> ids=new TreeSet<>();
        for(short v:(short[])labels.getProcessor().getPixels()){int n=v&65535;if(n>0)ids.add(n);digest.update((byte)(n>>>8));digest.update((byte)n);}
        String hash=hex(digest.digest());report.put("label_sha256",hash);report.put("object_count",ids.size());
        require(!ids.isEmpty(),"Public fixture produced no objects");
        require(hash.equals(System.getProperty("gat.validation.expectedLabels")),"Label raster differs from the pinned public fixture reference");
        report.put("source_unchanged",true);
    }
    private void alignment() throws Exception {
        int width=128,height=96;ByteProcessor base=new ByteProcessor(width,height);Random random=new Random(8291);
        for(int y=10;y<height-10;y++)for(int x=10;x<width-10;x++)base.set(x,y,random.nextInt(200)+1);
        ImageStack stack=new ImageStack(width,height);
        for(int[] shift:new int[][]{{0,0},{3,-2},{-4,5},{0,0}}){ImageProcessor p=base.duplicate();p.translate(shift[0],shift[1]);stack.addSlice(p);}
        ImagePlus input=new ImagePlus("fresh_fiji_synthetic_alignment",stack);input.show();input.setSlice(1);String before=pixels(input);
        report.put("action","Features.Tools.AlignStack.alignTemplateMatching, invoked inside installed Fiji");snapshot();
        Class.forName("Features.Tools.AlignStack",true,IJ.getClassLoader()).getMethod("alignTemplateMatching",ImagePlus.class,int.class).invoke(null,input,1);
        captureWindows();String after=pixels(input);report.put("input_sha256",before);report.put("aligned_sha256",after);
        require(!before.equals(after),"Alignment left shifted input unchanged");
        require(after.equals("8be9c6ad7c4c28d68b07f0b45c562deb9d29e4febf030b0ad24dcb198ea7fa9c"),"Alignment pixels differ from original Linux same-fixture reference");
    }
    private void captureWindows(){
        List<Map<String,Object>> windows=new ArrayList<>();
        for(Frame f:WindowManager.getNonImageWindows())if(f instanceof ij.text.TextWindow){String text=((ij.text.TextWindow)f).getTextPanel().getText();windows.add(map("title",f.getTitle(),"text",text));if("Exception".equals(f.getTitle()) && !errors.contains(text))errors.add(text);}
        report.put("text_windows",windows);
    }
    private static String componentText(Component c){StringBuilder s=new StringBuilder();if(c instanceof JLabel)s.append(((JLabel)c).getText()).append('\n');if(c instanceof javax.swing.text.JTextComponent)s.append(((javax.swing.text.JTextComponent)c).getText()).append('\n');if(c instanceof java.awt.TextComponent)s.append(((java.awt.TextComponent)c).getText()).append('\n');if(c instanceof Container)for(Component child:((Container)c).getComponents())s.append(componentText(child));return s.toString();}
    private static String pixels(ImagePlus image)throws Exception{MessageDigest d=MessageDigest.getInstance("SHA-256");ByteBuffer b=ByteBuffer.allocate(4).order(ByteOrder.BIG_ENDIAN);for(int z=1;z<=image.getStackSize();z++)for(int i=0;i<image.getWidth()*image.getHeight();i++){b.clear();b.putFloat(image.getStack().getProcessor(z).getf(i));d.update(b.array());}return hex(d.digest());}
    private static String hex(byte[] bytes){StringBuilder s=new StringBuilder();for(byte b:bytes)s.append(String.format("%02x",b&255));return s.toString();}
    private void record(Throwable t){if(t instanceof InvocationTargetException && t.getCause()!=null)t=t.getCause();StringWriter s=new StringWriter();t.printStackTrace(new PrintWriter(s));errors.add(s.toString());System.err.print(s);}
    private void snapshot(){try{report.put("errors",new ArrayList<>(errors));Files.writeString(output,json(report)+"\n");}catch(Exception e){throw new RuntimeException(e);}}
    private static void require(boolean ok,String text){if(!ok)throw new AssertionError(text);}
    private static Map<String,Object> map(Object... pairs){Map<String,Object> m=new LinkedHashMap<>();for(int i=0;i<pairs.length;i+=2)m.put(String.valueOf(pairs[i]),pairs[i+1]);return m;}
    private static String json(Object x){if(x==null)return "null";if(x instanceof Boolean || x instanceof Number)return x.toString();if(x instanceof Map){List<String>a=new ArrayList<>();for(Map.Entry<?,?>e:((Map<?,?>)x).entrySet())a.add(json(e.getKey())+":"+json(e.getValue()));return "{"+String.join(",",a)+"}";}if(x instanceof Iterable){List<String>a=new ArrayList<>();for(Object e:(Iterable<?>)x)a.add(json(e));return "["+String.join(",",a)+"]";}StringBuilder s=new StringBuilder("\"");for(char c:String.valueOf(x).toCharArray()){switch(c){case '\\':s.append("\\\\");break;case '"':s.append("\\\"");break;case '\n':s.append("\\n");break;case '\r':s.append("\\r");break;case '\t':s.append("\\t");break;default:if(c<32)s.append(String.format("\\u%04x",(int)c));else s.append(c);}}return s.append('"').toString();}
}

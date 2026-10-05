import com.google.gson.GsonBuilder;
import ij.ImagePlus;
import ij.ImageStack;
import ij.Macro;
import ij.plugin.filter.PlugInFilter;
import ij.process.ByteProcessor;
import ij.process.ImageProcessor;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.nio.ByteBuffer;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Random;

/** Direct published-plugin control, separate from original GAT's IJ.run dispatch. */
public final class LegacyPluginProbe {
    private static ImagePlus fixture() {
        ByteProcessor base = new ByteProcessor(128, 96); Random random = new Random(8291);
        for (int y=10;y<86;y++) for(int x=10;x<118;x++) base.set(x,y,random.nextInt(200)+1);
        ImageStack stack = new ImageStack(128,96);
        for(int[] shift:new int[][]{{0,0},{3,-2},{-4,5},{0,0}}) {
            ImageProcessor frame=base.duplicate();frame.translate(shift[0],shift[1]);stack.addSlice(frame);
        }
        return new ImagePlus("direct-published-template-plugin",stack);
    }
    private static String pixels(ImagePlus image) throws Exception {
        MessageDigest digest=MessageDigest.getInstance("SHA-256");ByteBuffer word=ByteBuffer.allocate(4);
        for(int z=1;z<=image.getStackSize();z++) for(int p=0;p<128*96;p++) {
            word.clear();word.putFloat(image.getStack().getProcessor(z).getf(p));digest.update(word.array());
        }
        StringBuilder out=new StringBuilder();for(byte b:digest.digest())out.append(String.format("%02x",b&255));return out.toString();
    }
    public static void main(String[] args) throws Exception {
        if(args.length!=1)throw new IllegalArgumentException("report.json");
        Map<String,Object> result=new LinkedHashMap<>();
        result.put("probe","template-plugin-direct");result.put("scope","published original plugin setup/run component control; not original GAT IJ.run dispatch");
        result.put("actual_gat_method_invoked",false);result.put("plugin_run_invoked",false);
        result.put("java_arch",System.getProperty("os.arch"));result.put("java_version",System.getProperty("java.version"));
        String oldName=Thread.currentThread().getName();
        try {
            if (java.awt.GraphicsEnvironment.isHeadless()) ij.IJ.runPlugIn("ij.IJ.init", "");
            ImagePlus input=fixture();result.put("input_pixel_sha256",pixels(input));
            Class<?> type=Class.forName("TemplateMatching.Align_slices");
            result.put("code_source",type.getProtectionDomain().getCodeSource().getLocation().toString());
            PlugInFilter plugin=(PlugInFilter)type.getDeclaredConstructor().newInstance();
            result.put("setup_flags",plugin.setup("",input));
            // Exact GAT alignment parameters, including show=true. The official
            // legacy headless patcher handles the result window on Linux.
            Thread.currentThread().setName("Run$_LegacyPluginControl");
            Macro.setOptions("method=5 windowsizex=89 windowsizey=67 x0=21 y0=16 swindow=0 subpixel=false itpmethod=0 ref.slice=1 show=true");
            result.put("macro_options",Macro.getOptions());result.put("plugin_run_invoked",true);
            plugin.run(input.getProcessor());
            String after=pixels(input);result.put("aligned_pixel_sha256",after);
            if(!after.equals("8be9c6ad7c4c28d68b07f0b45c562deb9d29e4febf030b0ad24dcb198ea7fa9c"))
                throw new AssertionError("Published plugin did not produce expected aligned fixture");
            result.put("status","success");
        } catch(Throwable error) {
            StringWriter text=new StringWriter();error.printStackTrace(new PrintWriter(text));
            result.put("exception",text.toString());System.err.println(text);
            result.put("status",Boolean.TRUE.equals(result.get("plugin_run_invoked"))?"plugin_component_failure":"setup_failure");
        } finally {Macro.setOptions((String)null);Thread.currentThread().setName(oldName);}
        Path report=Path.of(args[0]);Files.createDirectories(report.toAbsolutePath().getParent());
        String json=new GsonBuilder().serializeNulls().setPrettyPrinting().create().toJson(result);
        Files.writeString(report,json+"\n");System.out.println(json);System.exit("success".equals(result.get("status"))?0:2);
    }
}

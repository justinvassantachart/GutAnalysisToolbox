import Features.Core.PluginCalls;
import Features.Core.Params;
import ij.*;
import ij.io.FileSaver;
import ij.process.ByteProcessor;
import io.bioimage.modelrunner.numpy.DecodeNumpy;
import net.imglib2.RandomAccessibleInterval;
import net.imglib2.type.numeric.integer.UnsignedByteType;
import java.awt.GraphicsEnvironment;
import java.nio.file.*;
import java.util.*;

/** Actual GAT ganglia command chain in an isolated, validation-only Fiji directory. */
public final class GangliaCommandSmoke {
    public static void main(String[] args) throws Exception {
        Path out=Paths.get(args[0]), model=Paths.get(args[1]), engines=Paths.get(args[2]);
        WorkflowReport report=new WorkflowReport("ganglia-gat-command",out,"ganglia-command-report.json");
        if(GraphicsEnvironment.isHeadless() || (System.getProperty("os.name").startsWith("Linux") && System.getenv("DISPLAY")==null)) {report.blocked("gat_ganglia_command", "GAT/DeepImageJ command and MorphoLibJ cleanup", "AWT display required");report.write();return;}
        report.test("gat_ganglia_command", "Actual production GAT call through DeepImageJ Run and morphological cleanup", "PluginCalls.runDeepImageJForGanglia", () -> {
            Path root=model.getParent().getParent().toRealPath();
            System.setProperty("plugins.dir", root.resolve("plugins").toString());
            new ImageJ(ImageJ.NO_SHOW);
            Path actualRoot=Paths.get(IJ.getDirectory("imagej")).toRealPath();
            WorkflowReport.check(actualRoot.equals(root),"ImageJ directory escaped validation fixture: "+actualRoot);
            WorkflowReport.check(Paths.get(deepimagej.Constants.FIJI_FOLDER).toRealPath().equals(root),"DeepImageJ engine directory escaped validation fixture");
            Menus.getCommands().put("DeepImageJ Run", "DeepImageJ_Run");
            Menus.getCommands().put("Size Opening 2D/3D", "inra.ijpb.plugins.SizeOpeningPlugin");
            RandomAccessibleInterval<UnsignedByteType> raw=DecodeNumpy.loadNpy(model.resolve("test-input.npy").toString());
            int h=(int)raw.dimension(2),w=(int)raw.dimension(3);
            byte[] hu=new byte[w*h],ganglia=new byte[w*h];
            net.imglib2.RandomAccess<UnsignedByteType> a=raw.randomAccess();
            for(int y=0;y<h;y++)for(int x=0;x<w;x++) {
                a.setPosition(new long[]{0,0,y,x});hu[y*w+x]=(byte)a.get().get();
                a.setPosition(1,1);ganglia[y*w+x]=(byte)a.get().get();
            }
            ImageStack stack=new ImageStack(w,h);stack.addSlice(new ByteProcessor(w,h,hu,null));stack.addSlice(new ByteProcessor(w,h,ganglia,null));
            ImagePlus source=new ImagePlus("public-ganglia-two-channel",stack);source.setDimensions(2,1,1);source.setOpenAsHyperStack(true);
            source.getCalibration().pixelWidth=.378;source.getCalibration().pixelHeight=.378;source.getCalibration().setUnit("um");
            byte[] originalHu=hu.clone(),originalGanglia=ganglia.clone();
            ImagePlus unrelated=new ImagePlus("unrelated-existing-image",new ByteProcessor(w,h));unrelated.show();
            Params p=new Params();p.gangliaInteractiveReview=false;p.gangliaProbThresh01=.6;p.gangliaOpenIterations=1;p.gangliaMinAreaUm2=1.0;
            long start=System.nanoTime();
            ImagePlus mask=PluginCalls.runDeepImageJForGanglia(source,2,1,model.getFileName().toString(),1.0,p,null);
            double elapsed=(System.nanoTime()-start)/1e9;
            WorkflowReport.check(mask!=null&&mask!=source&&mask!=unrelated,"GAT selected an old/input image");
            WorkflowReport.check(mask.getWidth()==w&&mask.getHeight()==h&&mask.getStackSize()==1&&mask.getBitDepth()==8,"Wrong ganglia mask geometry/type");
            long foreground=0;for(int i=0;i<w*h;i++){int value=mask.getProcessor().get(i);WorkflowReport.check(value==0||value==255,"Non-binary mask");if(value==255)foreground++;}
            WorkflowReport.check(foreground>0&&foreground<(long)w*h,"Public fixture produced an empty/full mask");
            WorkflowReport.check(Arrays.equals(originalHu,hu)&&Arrays.equals(originalGanglia,ganglia),"Source pixels changed");
            WorkflowReport.check(mask.getCalibration().pixelWidth==.378&&mask.getCalibration().pixelHeight==.378,"Calibration lost");
            WorkflowReport.check(new FileSaver(mask).saveAsTiff(out.resolve("gat-ganglia-mask.tif").toString()),"Cannot save mask");
            return WorkflowReport.values("input","Public supplied test-input.npy channels 0=Hu and 1=ganglia; GAT builds R=Hu,G=ganglia,B=Hu", "width",w,"height",h,
                "foreground_pixels",foreground,"command_seconds_including_model_load",elapsed,"rdf_threshold",.6,"gat_threshold",.6,"open_iterations",1,"minimum_area_um2",1.0,
                "source_unchanged",true,"evidence","gat-ganglia-mask.tif","scope_note","Actual command, model inference and cleanup; interactive painting/dashboard navigation excluded. Scientific correction, not legacy-mask parity.");
        });
        report.notRun("ganglia_manual_paint_review","Optional interactive edit","Requires a person choosing biologically correct edits");
        report.write();System.exit(report.failures()==0?0:1);
    }
}

import ij.IJ;
import ij.ImagePlus;
import ij.ImageStack;
import ij.process.ByteProcessor;
import io.bioimage.modelrunner.model.java.BioimageIoModelJava;
import io.bioimage.modelrunner.numpy.DecodeNumpy;
import io.bioimage.modelrunner.tensor.Tensor;
import io.bioimage.modelrunner.versionmanagement.SupportedVersions;
import net.imglib2.RandomAccessibleInterval;
import net.imglib2.type.numeric.integer.UnsignedByteType;
import net.imglib2.type.numeric.real.FloatType;
import net.imglib2.view.Views;
import java.lang.reflect.Method;
import java.nio.file.*;
import java.util.*;

/** Compiled only against the updater-installed Fiji libraries. No replacement context or menus. */
public final class Fresh_Ganglia_Probe {
    public static Map<String,Object> run(String mode, Path evidence) throws Exception {
        Path root=Paths.get(IJ.getDirectory("imagej")).toRealPath();
        Path model=root.resolve("models/2D_Ganglia_RGB_v3.bioimage.io.model");
        Path engines=root.resolve("engines");
        if(mode.equals("engine_inference"))return infer(model,engines);
        if(mode.equals("ganglia"))return command(model,root,evidence);
        throw new IllegalArgumentException(mode);
    }
    private static Map<String,Object> infer(Path model,Path engines)throws Exception{
        String resolved=SupportedVersions.getJavaVersionForPythonVersion("pytorch","2.4.1+cpu");
        check("2.0.0".equals(resolved),"Shipped resolver differs from the pinned engine choice: "+resolved);
        long start=System.nanoTime();
        BioimageIoModelJava runner=BioimageIoModelJava.createBioimageioModel(model.toString(),engines.toString());
        try{
            runner.loadModel();
            check("pytorch".equals(runner.getEngineInfo().getFramework()),"Wrong framework");
            check("2.0.0".equals(runner.getEngineInfo().getVersion()),"Wrong Python engine version");
            check("2.0.0".equals(runner.getEngineInfo().getJavaVersion()),"Wrong Java engine version");
            check(runner.getEngineInfo().isCPU(),"CPU engine required");
            RandomAccessibleInterval<UnsignedByteType> raw=DecodeNumpy.loadNpy(model.resolve("test-input.npy").toString());
            Tensor<UnsignedByteType> input=Tensor.build("input","bcyx",raw);
            List<Tensor<FloatType>> outputs=runner.run(new ArrayList<>(Collections.singletonList(input)));
            check(outputs.size()==1,"Expected one model output");
            Tensor<FloatType> output=outputs.get(0);long finite=0;double min=Double.POSITIVE_INFINITY,max=Double.NEGATIVE_INFINITY;
            for(FloatType value:Views.iterable(output.getData())){double v=value.getRealDouble();check(Double.isFinite(v),"Non-finite model output");min=Math.min(min,v);max=Math.max(max,v);finite++;}
            check(finite>0 && max>min,"Empty or constant public-fixture model output");
            return map("engine_framework",runner.getEngineInfo().getFramework(),"engine_version",runner.getEngineInfo().getVersion(),
                    "engine_java_version",runner.getEngineInfo().getJavaVersion(),"engine_cpu",runner.getEngineInfo().isCPU(),
                    "model_declared_version","2.4.1+cpu","catalog_resolved_version",resolved,
                    "input_shape",raw.dimensionsAsLongArray(),"output_shape",output.getData().dimensionsAsLongArray(),
                    "output_axes",output.getAxesOrderString(),"finite_values",finite,"minimum",min,"maximum",max,
                    "seconds",(System.nanoTime()-start)/1e9,
                    "scope","Actual shipped JDLL model loading, RDF preprocessing, tiling, inference and postprocessing inside installed Fiji; not a scientific reference-parity claim");
        }finally{runner.close();}
    }
    private static Map<String,Object> command(Path model,Path root,Path evidence)throws Exception{
        check(IJ.getInstance()!=null,"Real Fiji UI not running");
        check(ij.Menus.getCommands().containsKey("DeepImageJ Run"),"Real DeepImageJ command absent");
        check(ij.Menus.getCommands().containsKey("Size Opening 2D/3D"),"Real MorphoLibJ command absent");
        ClassLoader loader=IJ.getClassLoader();
        Class<?> constants=Class.forName("deepimagej.Constants",true,loader);
        check(Paths.get(String.valueOf(constants.getField("FIJI_FOLDER").get(null))).toRealPath().equals(root),"DeepImageJ escaped the fresh Fiji root");
        RandomAccessibleInterval<UnsignedByteType> raw=DecodeNumpy.loadNpy(model.resolve("test-input.npy").toString());
        int h=(int)raw.dimension(2),w=(int)raw.dimension(3);byte[] hu=new byte[w*h],ganglia=new byte[w*h];
        net.imglib2.RandomAccess<UnsignedByteType> a=raw.randomAccess();
        for(int y=0;y<h;y++)for(int x=0;x<w;x++){a.setPosition(new long[]{0,0,y,x});hu[y*w+x]=(byte)a.get().get();a.setPosition(1,1);ganglia[y*w+x]=(byte)a.get().get();}
        ImageStack stack=new ImageStack(w,h);stack.addSlice(new ByteProcessor(w,h,hu,null));stack.addSlice(new ByteProcessor(w,h,ganglia,null));
        ImagePlus source=new ImagePlus("fresh_ganglia_public_two_channel",stack);source.setDimensions(2,1,1);source.setOpenAsHyperStack(true);
        source.getCalibration().pixelWidth=.378;source.getCalibration().pixelHeight=.378;source.getCalibration().setUnit("um");
        byte[] originalHu=hu.clone(),originalGanglia=ganglia.clone();
        ImagePlus unrelated=new ImagePlus("unrelated-existing-image",new ByteProcessor(w,h));unrelated.show();
        Class<?> paramsType=Class.forName("Features.Core.Params",true,loader);Object params=paramsType.getDeclaredConstructor().newInstance();
        Fresh_Ganglia_Params.configure(params);
        Class<?> calls=Class.forName("Features.Core.PluginCalls",true,loader);
        Method method=Arrays.stream(calls.getMethods()).filter(m->m.getName().equals("runDeepImageJForGanglia") && m.getParameterCount()==7).findFirst().orElseThrow(()->new NoSuchMethodException("GAT ganglia call"));
        long start=System.nanoTime();
        ImagePlus mask=(ImagePlus)method.invoke(null,source,2,1,model.getFileName().toString(),1.0,params,null);
        check(mask!=null && mask!=source && mask!=unrelated,"GAT returned old/input image instead of mask");
        check(mask.getWidth()==w && mask.getHeight()==h && mask.getStackSize()==1 && mask.getBitDepth()==8,"Wrong mask geometry/type");
        long foreground=0;for(int i=0;i<w*h;i++){int value=mask.getProcessor().get(i);check(value==0||value==255,"Nonbinary mask");if(value==255)foreground++;}
        check(foreground>0 && foreground<(long)w*h,"Empty/full public-fixture mask");
        check(Arrays.equals((byte[])source.getStack().getProcessor(1).getPixels(),originalHu)
                &&Arrays.equals((byte[])source.getStack().getProcessor(2).getPixels(),originalGanglia),"Source pixels changed");
        check(mask.getCalibration().pixelWidth==.378 && mask.getCalibration().pixelHeight==.378,"Calibration lost");
        Path saved=evidence.resolveSibling(evidence.getFileName().toString().replace(".json","-mask.tif"));
        check(new ij.io.FileSaver(mask).saveAsTiff(saved.toString()),"Cannot persist mask");
        return map("width",w,"height",h,"foreground_pixels",foreground,"seconds",(System.nanoTime()-start)/1e9,
                "source_unchanged",true,"calibration_preserved",true,"mask_file",saved.getFileName().toString(),
                "mask_pixels_uint8_row_major_sha256",Fresh_Ganglia_Evidence.sha256((byte[])mask.getProcessor().getPixels()),
                "mask_tiff_sha256",Fresh_Ganglia_Evidence.sha256(Files.readAllBytes(saved)),
                "input_contract","Supplied test-input.npy channel 0=Hu/channel 1=ganglia; actual GAT builds R=Hu,G=ganglia,B=Hu",
                "rdf_threshold",.6,"gat_threshold",.6,"open_iterations",1,"minimum_area_um2",1.0,
                "scope","Actual GAT->registered DeepImageJ Run->model->MorphoLibJ cleanup; biological and manual-paint review excluded");
    }
    private static void check(boolean ok,String text){if(!ok)throw new AssertionError(text);}
    private static Map<String,Object> map(Object... pairs){Map<String,Object> m=new LinkedHashMap<>();for(int i=0;i<pairs.length;i+=2){Object value=pairs[i+1];if(value instanceof long[]){List<Long> numbers=new ArrayList<>();for(long n:(long[])value)numbers.add(n);value=numbers;}m.put(String.valueOf(pairs[i]),value);}return m;}
}

import io.bioimage.modelrunner.model.java.BioimageIoModelJava;
import io.bioimage.modelrunner.tensor.Tensor;
import io.bioimage.modelrunner.numpy.DecodeNumpy;
import io.bioimage.modelrunner.versionmanagement.SupportedVersions;
import net.imglib2.RandomAccessibleInterval;
import net.imglib2.type.numeric.integer.UnsignedByteType;
import net.imglib2.type.numeric.real.FloatType;
import net.imglib2.view.Views;
import java.nio.file.*;
import java.util.*;

/** Uses shipped JDLL model descriptor parsing, preprocessing, tiling and postprocessing, in isolation. */
public final class GangliaJdllSmoke {
 public static void main(String[] args)throws Exception {
  Path out=Paths.get(args[0]),model=Paths.get(args[1]),engines=Paths.get(args[2]);WorkflowReport r=new WorkflowReport("ganglia-jdll",out,"ganglia-jdll-report.json");
  r.test("jdll_engine_resolution","Shipped JDLL resolver","SupportedVersions 0.6.2-SNAPSHOT",()->{
   String resolved=SupportedVersions.getJavaVersionForPythonVersion("pytorch","2.4.1+cpu");WorkflowReport.check("2.0.0".equals(resolved),"Unexpected resolver result");return WorkflowReport.values("model_version","2.4.1+cpu","resolved_version",resolved);});
  r.test("jdll_descriptor_preprocess_tile_infer","JDLL model execution; no ImageJ macro or GUI","BioimageIoModelJava.createBioimageioModel/loadModel/run",()->{
   long start=System.nanoTime();BioimageIoModelJava m=BioimageIoModelJava.createBioimageioModel(model.toString(),engines.toString());double setup=(System.nanoTime()-start)/1e9;
   try {
    start=System.nanoTime();m.loadModel();double load=(System.nanoTime()-start)/1e9;
    RandomAccessibleInterval<UnsignedByteType> raw=DecodeNumpy.loadNpy(model.resolve("test-input.npy").toString());
    Tensor<UnsignedByteType> in=Tensor.build("input","bcyx",raw);start=System.nanoTime();
    List<Tensor<FloatType>> outputs=m.run(new ArrayList<>(Collections.singletonList(in)));double infer=(System.nanoTime()-start)/1e9;
    WorkflowReport.check(outputs.size()==1,"Expected one JDLL output");Tensor<FloatType> output=outputs.get(0);long[] shape=output.getData().dimensionsAsLongArray();double min=Double.POSITIVE_INFINITY,max=Double.NEGATIVE_INFINITY;long finite=0;
    for(FloatType f:Views.iterable(output.getData())){double v=f.getRealDouble();WorkflowReport.check(Double.isFinite(v),"Nonfinite JDLL output");min=Math.min(min,v);max=Math.max(max,v);finite++;}
    DecodeNumpy.saveNpy(out.resolve("jdll-output.npy").toString(),output.getData());
    return WorkflowReport.values("engine_framework",m.getEngineInfo().getFramework(),"engine_version",m.getEngineInfo().getVersion(),"engine_java_version",m.getEngineInfo().getJavaVersion(),"engine_cpu",m.getEngineInfo().isCPU(),
     "model_setup_seconds",setup,"model_load_seconds",load,"run_seconds_including_preprocess_tiling_postprocess",infer,"output_axes",output.getAxesOrderString(),"output_shape",shape,"finite_values",finite,"min",min,"max",max,"evidence","jdll-output.npy","note","Unchanged RDF preprocessing and postprocessing; excludes DeepImageJ external ImageJ macros and full GAT GUI");
   } finally {m.close();}
  });
  r.blocked("jdll_reference_scientific_parity","Full model reference agreement","No validated complete expected-output transformation yet; compare exported dimensions/data with supplied reference separately, without changing metadata or tolerances.");
  r.write();if(r.failures()>0)System.exit(1);
 }
}

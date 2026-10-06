import ai.djl.Device;
import ai.djl.Model;
import ai.djl.engine.Engine;
import ai.djl.inference.Predictor;
import ai.djl.ndarray.*;
import ai.djl.ndarray.types.*;
import ai.djl.translate.NoopTranslator;
import java.nio.*;
import java.nio.file.*;
import java.util.*;

/** Separate JVM test of the exact DJL/PyTorch engine named by the shipped JDLL catalog. */
public final class GangliaDjlSmoke {
 public static void main(String[] args)throws Exception {
  Path out=Paths.get(args[0]),modelDir=Paths.get(args[1]);WorkflowReport r=new WorkflowReport("ganglia-direct-djl",out,"ganglia-djl-report.json");
  r.test("pytorch_ganglia_load_infer","Direct DJL component; not full JDLL or Fiji","PyTorch 2.0.0 CPU / DJL 0.22.1",()->{
   long start=System.nanoTime();String version=Engine.getEngine("PyTorch").getVersion();double engineSeconds=(System.nanoTime()-start)/1e9;
   WorkflowReport.check("2.0.0".equals(version),"Unexpected actual PyTorch version: "+version);
   try(Model model=Model.newInstance("best_model_torchscript",Device.cpu(),"PyTorch")) {
    start=System.nanoTime();model.load(modelDir,"best_model_torchscript");double loadSeconds=(System.nanoTime()-start)/1e9;
    byte[] npy=Files.readAllBytes(modelDir.resolve("test-input.npy"));WorkflowReport.check(npy[0]==(byte)0x93&&npy[6]==1,"Expected NPY v1 input");
    int headerLength=(npy[8]&255)|((npy[9]&255)<<8);String header=new String(npy,10,headerLength,java.nio.charset.StandardCharsets.US_ASCII);
    WorkflowReport.check(header.contains("'|u1'")&&(header.contains("True")||header.contains("False"))&&header.contains("(1, 3, 1024, 1024)"),"Unexpected NPY input contract: "+header);
    int n=3*1024*1024;WorkflowReport.check(npy.length==10+headerLength+n,"Wrong input length");float[] input=new float[n];float[] mean={.485f,.456f,.406f},std={.229f,.224f,.225f};
    boolean fortran=header.contains("'fortran_order': True");
    for(int c=0;c<3;c++)for(int y=0;y<1024;y++)for(int x=0;x<1024;x++){
     int target=c*1024*1024+y*1024+x,source=fortran?c+3*y+3*1024*x:target;
     input[target]=((npy[10+headerLength+source]&255)*.00392156862f-mean[c])/(std[c]+1e-6f);
    }
    ByteBuffer prepared=ByteBuffer.allocate(n*4).order(ByteOrder.LITTLE_ENDIAN);prepared.asFloatBuffer().put(input);
    StringBuilder inputHash=new StringBuilder();for(byte v:java.security.MessageDigest.getInstance("SHA-256").digest(prepared.array()))inputHash.append(String.format("%02x",v&255));
    WorkflowReport.check("0197f4136b2a3fdfe65d9924ab2deb4c8ae814a551149a81ece3174a048367ba".equals(inputHash.toString()),"Preprocessed pixels differ from independently prepared NumPy fixture");
    try(NDManager nm=NDManager.newBaseManager(Device.cpu(),"PyTorch");Predictor<NDList,NDList> predict=model.newPredictor(new NoopTranslator())){
     NDArray tensor=nm.create(input,new Shape(1,3,1024,1024));start=System.nanoTime();NDList outputs=predict.predict(new NDList(tensor));double inferenceSeconds=(System.nanoTime()-start)/1e9;
     WorkflowReport.check(outputs.size()==1,"Expected one output");NDArray a=outputs.get(0);float[] values=a.toFloatArray();float min=Float.POSITIVE_INFINITY,max=Float.NEGATIVE_INFINITY;
     for(float v:values){WorkflowReport.check(Float.isFinite(v),"Nonfinite prediction");min=Math.min(min,v);max=Math.max(max,v);}
     WorkflowReport.check(Arrays.equals(a.getShape().getShape(),new long[]{1,1,1024,1024}),"Unexpected direct output shape");
     ByteBuffer bytes=ByteBuffer.allocate(values.length*4).order(ByteOrder.LITTLE_ENDIAN);bytes.asFloatBuffer().put(values);Files.write(out.resolve("direct-probabilities.f32le"),bytes.array());
     return WorkflowReport.values("runtime",version,"device","cpu","engine_initialization_seconds",engineSeconds,"model_load_seconds",loadSeconds,"inference_seconds",inferenceSeconds,
      "input_shape",new int[]{1,3,1024,1024},"npy_storage_order",fortran?"Fortran":"C","preprocessed_input_sha256",inputHash.toString(),"output_shape",a.getShape().getShape(),"min",min,"max",max,"finite",true,"preprocessing","RDF gain then channel mean/(std+epsilon), unchanged NCHW; no ImageJ macro", "evidence","direct-probabilities.f32le");
    }
   }
  });
  r.blocked("ganglia_supplied_reference_parity","Scientific-reference comparison","Direct output is 1024x1024; supplied reference is 768x768; declared 64-pixel halo alone does not reconcile them. No arbitrary crop, model metadata change, or attribution to a TorchScript-version bug.");
  r.notRun("ganglia_full_fiji_gui","Full GAT/DeepImageJ workflow","Direct engine execution does not cover RGB construction, ImageJ macro preprocessing, JDLL tiling or downstream review/measurement");
  r.write();if(r.failures()>0)System.exit(1);
 }
}

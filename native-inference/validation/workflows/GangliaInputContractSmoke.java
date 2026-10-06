import Features.Core.PluginCalls;
import ij.ImagePlus;
import ij.ImageStack;
import ij.process.ByteProcessor;
import deepimagej.gui.ImageJGui;
import io.bioimage.modelrunner.bioimageio.description.ModelDescriptor;
import io.bioimage.modelrunner.bioimageio.description.ModelDescriptorFactory;
import io.bioimage.modelrunner.model.processing.Processing;
import io.bioimage.modelrunner.tensor.Tensor;
import net.imglib2.type.numeric.real.FloatType;
import java.nio.file.*;
import java.util.*;

/** Actual GAT -> DeepImageJ conversion -> supplied RDF preprocessing, no engine/model substitution. */
public final class GangliaInputContractSmoke {
    static List<Tensor<FloatType>> convert(ImagePlus input, ModelDescriptor descriptor) {
        Map<String,Object> images = new HashMap<>(); images.put("input", input);
        return new ImageJGui().convertToInputTensors(images, descriptor);
    }
    static double value(List<Tensor<FloatType>> tensors, int channel) {
        Tensor<FloatType> t=tensors.get(0);
        net.imglib2.RandomAccess<FloatType> a=t.getData().randomAccess();
        long[] position=new long[t.getShape().length];
        position[t.getAxesOrderString().indexOf('c')]=channel;
        a.setPosition(position); return a.get().getRealDouble();
    }
    public static void main(String[] args) throws Exception {
        Path out=Paths.get(args[0]);
        WorkflowReport report=new WorkflowReport("ganglia-input-contract",out,"ganglia-contract-report.json");
        report.test("actual_gat_deepimagej_rdf_input", "Reached preprocessing contract; no model execution", "GAT RGB construction, DeepImageJ ImageJGui conversion, JDLL Processing.preprocess", () -> {
            byte[] hu=new byte[64], ganglia=new byte[64];
            for(int i=0;i<64;i++){hu[i]=(byte)(i*4);ganglia[i]=(byte)(i*3);}
            hu[0]=(byte)255;ganglia[0]=(byte)128;ganglia[1]=(byte)255;
            ImageStack stack=new ImageStack(8,8);
            stack.addSlice(new ByteProcessor(8,8,hu,null));stack.addSlice(new ByteProcessor(8,8,ganglia,null));
            ImagePlus source=new ImagePlus("synthetic-contract",stack);source.setDimensions(2,1,1);
            source.getCalibration().pixelWidth=.5;source.getCalibration().pixelHeight=.75;
            PluginCalls.GangliaPrep prep=PluginCalls.prepareGangliaInputs(source,2,1);
            ModelDescriptor descriptor=ModelDescriptorFactory.readFromLocalFile(Paths.get(args[1],"rdf.yaml").toString());
            List<Tensor<FloatType>> corrected=convert(prep.dijInput3C,descriptor);
            double[] raw=new double[3], actual=new double[3], old=new double[3], expected=new double[3];
            double[] means={.485,.456,.406}, std={.229,.224,.225};
            for(int c=0;c<3;c++){raw[c]=value(corrected,c);WorkflowReport.check(raw[c]==(c==1?128:255),"GAT/DeepImageJ changed raw intensity channel "+c+": "+raw[c]);}
            ImagePlus oldInput=prep.dijInput3C.duplicate();
            for(int c=1;c<=3;c++)oldInput.getStack().getProcessor(c).multiply(1.0/255.0);
            List<Tensor<FloatType>> previous=convert(oldInput,descriptor);
            Processing.init(descriptor).preprocess(corrected,true);
            Processing.init(descriptor).preprocess(previous,true);
            for(int c=0;c<3;c++) {
                actual[c]=value(corrected,c);old[c]=value(previous,c);
                expected[c]=(raw[c]*.00392156862-means[c])/(std[c]+1e-6);
                WorkflowReport.check(Math.abs(actual[c]-expected[c])<2e-6,"RDF normalization mismatch channel "+c);
                WorkflowReport.check(Math.abs(actual[c]-old[c])>2,"Former double-scaled control unexpectedly matches corrected contract");
            }
            WorkflowReport.check(source.getStack().getProcessor(1).get(0)==255,"Source modified");
            return WorkflowReport.values("source", "Synthetic 8x8 two-channel uint8", "tensor_axes",corrected.get(0).getAxesOrderString(),
                "tensor_shape",corrected.get(0).getShape(),"raw_rgb_pixel",raw,"corrected_model_input_pixel",actual,
                "former_double_scaled_control_pixel",old,"expected_rdf_only_normalization",expected,
                "scientific_change", "Correcting a reached double 1/255 scaling bug changes predictions; legacy output parity is not expected",
                "unchanged", "Weights, RDF mean/std/epsilon/scale, RDF threshold, GAT RGB order and display-range conversion");
        });
        report.notRun("full_gat_ganglia_command", "DeepImageJ command and morphological cleanup", "This suite proves the reached input contract only; use a separate native AWT command test");
        report.write();System.exit(report.failures()==0?0:1);
    }
}

import ij.IJ;
import ij.ImagePlus;
import ij.ImageStack;
import ij.WindowManager;
import ij.gui.Roi;
import ij.io.FileSaver;
import ij.io.RoiDecoder;
import ij.process.ByteProcessor;
import ij.process.ShortProcessor;
import io.bioimage.modelrunner.numpy.DecodeNumpy;
import net.imglib2.RandomAccessibleInterval;
import net.imglib2.type.numeric.integer.UnsignedByteType;
import java.io.*;
import java.lang.reflect.*;
import java.nio.*;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import java.util.zip.*;

/** Test-only, real-command comparison. No replacement inference, menu or runtime. */
public final class Fresh_Ganglia_Parity {
    public static Map<String,Object> run(Path model, Path root, Path evidence) throws Exception {
        Path samples=Paths.get(System.getProperty("gat.validation.paritySamples")).toRealPath();
        List<Map<String,Object>> rows=new ArrayList<>();
        rows.add(sample("model_public", publicFixture(model), 2, 1, model, evidence, null));
        rows.add(sample("distal_hu_gfap", image(samples.resolve("distal-hu-gfap.tif"),3), 2, 3,
                model,evidence,samples.resolve("distal-neuron-rois.zip")));
        rows.add(sample("proximal_hu_chat", image(samples.resolve("proximal-hu-chat.tif"),4), 1, 4,
                model,evidence,null));
        return map("samples",rows,"scope","Behavioral parity on three real public samples, not expert-annotation accuracy or all-workflow validation",
                "original_v2_commit","1870d9e16e16fd6daeac0bd05122e851029ddedc",
                "control_commit","ab1865cc745a8cb589f8a0034968d85b99843cf2");
    }
    private static ImagePlus image(Path path,int channels) {
        ImagePlus image=IJ.openImage(path.toString());
        check(image!=null,"Cannot open public sample: "+path);
        check(image.getStackSize()==channels,"Unexpected sample channel/plane count");
        image.setDimensions(channels,1,1);image.setOpenAsHyperStack(true);
        check(image.getCalibration().pixelWidth>0 && image.getCalibration().pixelHeight>0,"Missing calibration");
        return image;
    }
    private static ImagePlus publicFixture(Path model)throws Exception {
        RandomAccessibleInterval<UnsignedByteType> raw=DecodeNumpy.loadNpy(model.resolve("test-input.npy").toString());
        int h=(int)raw.dimension(2),w=(int)raw.dimension(3);byte[] hu=new byte[w*h],ganglia=new byte[w*h];
        net.imglib2.RandomAccess<UnsignedByteType> a=raw.randomAccess();
        for(int y=0;y<h;y++)for(int x=0;x<w;x++){a.setPosition(new long[]{0,0,y,x});hu[y*w+x]=(byte)a.get().get();a.setPosition(1,1);ganglia[y*w+x]=(byte)a.get().get();}
        ImageStack st=new ImageStack(w,h);st.addSlice(new ByteProcessor(w,h,hu,null));st.addSlice(new ByteProcessor(w,h,ganglia,null));
        ImagePlus image=new ImagePlus("public_model_two_channel",st);image.setDimensions(2,1,1);image.setOpenAsHyperStack(true);
        image.getCalibration().pixelWidth=.378;image.getCalibration().pixelHeight=.378;image.getCalibration().setUnit("um");return image;
    }
    private static Map<String,Object> sample(String id,ImagePlus source,int gangliaChannel,int huChannel,
                                             Path model,Path evidence,Path neuronRois)throws Exception {
        // No image from a previous invocation may be mistaken for this sample's output.
        int[] old=WindowManager.getIDList();if(old!=null)for(int key:old){ImagePlus im=WindowManager.getImage(key);if(im!=null){im.changes=false;im.close();}}
        source.setTitle("parity_"+id);int w=source.getWidth(),h=source.getHeight();
        int sourceDepth=source.getBitDepth(),channels=source.getNChannels();
        String sourceHash=floatHash(source,null);double pw=source.getCalibration().pixelWidth,ph=source.getCalibration().pixelHeight;
        ClassLoader loader=IJ.getClassLoader();Class<?> calls=Class.forName("Features.Core.PluginCalls",true,loader);
        Object prep=calls.getMethod("prepareGangliaInputs",ImagePlus.class,int.class,int.class).invoke(null,source,gangliaChannel,huChannel);
        ImagePlus input=(ImagePlus)prep.getClass().getField("dijInput3C").get(prep);
        ImagePlus rgb=(ImagePlus)prep.getClass().getField("rgbForOverlay").get(prep);
        String prefix=evidence.getFileName().toString().replace(".json","")+"-"+id;
        Path inputFile=evidence.resolveSibling(prefix+"-input.f32be.gz");
        String inputHash=floatHash(input,inputFile);double min=Double.POSITIVE_INFINITY,max=Double.NEGATIVE_INFINITY;
        for(int c=1;c<=input.getStackSize();c++)for(float value:(float[])input.getStack().getProcessor(c).getPixels()){check(Float.isFinite(value),"Non-finite prepared input");min=Math.min(min,value);max=Math.max(max,value);}
        check(input.getBitDepth()==32 && input.getNChannels()==3 && input.getStackSize()==3,"Prepared input contract changed");
        Path rgbFile=evidence.resolveSibling(prefix+"-rgb.png");check(new FileSaver(rgb).saveAsPng(rgbFile.toString()),"Cannot save RGB preview");
        input.changes=false;input.close();rgb.changes=false;rgb.close();
        Object params=Class.forName("Features.Core.Params",true,loader).getDeclaredConstructor().newInstance();Fresh_Ganglia_Params.configure(params);
        Method command=Arrays.stream(calls.getMethods()).filter(m->m.getName().equals("runDeepImageJForGanglia")&&m.getParameterCount()==7).findFirst().orElseThrow(()->new NoSuchMethodException("GAT ganglia command"));
        long start=System.nanoTime();ImagePlus mask=(ImagePlus)command.invoke(null,source,gangliaChannel,huChannel,model.getFileName().toString(),1.0,params,null);
        check(mask!=null && mask!=source && mask.getWidth()==w && mask.getHeight()==h && mask.getBitDepth()==8 && mask.getStackSize()==1,"Wrong mask object/geometry");
        long foreground=0;for(byte value:(byte[])mask.getProcessor().getPixels()){int v=value&255;check(v==0||v==255,"Non-binary mask");if(v==255)foreground++;}
        check(sourceHash.equals(floatHash(source,null)),"Source pixels changed");
        check(mask.getCalibration().pixelWidth==pw && mask.getCalibration().pixelHeight==ph,"Mask calibration changed");
        String maskHash=Fresh_Ganglia_Evidence.sha256((byte[])mask.getProcessor().getPixels());
        Path maskFile=evidence.resolveSibling(prefix+"-mask.tif");check(new FileSaver(mask).saveAsTiff(maskFile.toString()),"Cannot persist mask");
        ImagePlus labels=(ImagePlus)calls.getMethod("binaryToLabels",ImagePlus.class).invoke(null,mask);
        labels.setCalibration(source.getCalibration());
        check(labels.getBitDepth()==16 && labels.getWidth()==w && labels.getHeight()==h,"Wrong ganglia labels");
        Path labelsFile=evidence.resolveSibling(prefix+"-labels.tif");check(new FileSaver(labels).saveAsTiff(labelsFile.toString()),"Cannot persist ganglia labels");
        short[] lp=(short[])labels.getProcessor().getPixels();Set<Integer> objects=new TreeSet<>();ByteBuffer labelBytes=ByteBuffer.allocate(2*w*h).order(ByteOrder.BIG_ENDIAN);
        for(short v:lp){labelBytes.putShort(v);if((v&65535)>0)objects.add(v&65535);}
        Class<?> ops=Class.forName("Features.AnalyseWorkflows.GangliaOps",true,loader);
        double[] areas=(double[])ops.getMethod("areaPerGanglionUm2",ImagePlus.class).invoke(null,labels);
        Map<String,Object> result=map("id",id,"width",w,"height",h,"source_channels",channels,"source_bit_depth",sourceDepth,
            "ganglia_channel",gangliaChannel,"cell_channel",huChannel,"pixel_width_um",pw,"pixel_height_um",ph,
            "source_sha256",sourceHash,"source_unchanged",true,"calibration_preserved",true,
            "calibration",map("pixel_width_um",pw,"pixel_height_um",ph),
            "input_contract",map("channels",3,"axes","cyx","mapping","R=cell,G=ganglia,B=cell","encoding","float32-big-endian"),
            "params",map("rdf_threshold",.6,"gat_threshold",.6,"open_iterations",1,"minimum_area_um2",1.0,"minimum_area_px",(int)Math.ceil(1.0/(pw*pw))),
            "input_float_sha256",inputHash,"input_float_file",inputFile.getFileName().toString(),"input_axes","cyx",
            "input_min",min,"input_max",max,"rgb_file",rgbFile.getFileName().toString(),
            "mask_file",maskFile.getFileName().toString(),"mask_pixels_uint8_row_major_sha256",maskHash,
            "foreground_pixels",foreground,"ganglion_count",objects.size(),"labels_file",labelsFile.getFileName().toString(),
            "labels_pixels_uint16_be_sha256",Fresh_Ganglia_Evidence.sha256(labelBytes.array()),"areas_um2",numbers(areas),
            "rdf_threshold",.6,"gat_threshold",.6,"open_iterations",1,"minimum_area_um2",1.0,"minimum_area_px",(int)Math.ceil(1.0/(pw*pw)),
            "seconds",(System.nanoTime()-start)/1e9);
        if(neuronRois!=null){
            ImagePlus neurons=fixedNeurons(neuronRois,w,h);
            Object counts=ops.getMethod("countPerGanglion",ImagePlus.class,ImagePlus.class).invoke(null,neurons,labels);
            int[] perGanglion=(int[])counts.getClass().getField("countsPerGanglion").get(counts);
            result.put("assignment_neuron_source","83 fixed historical workflow ROIs matched only to distal_hu_gfap; not rerun neuron inference or expert ground truth");
            result.put("assignment_neuron_roi_sha256",Fresh_Ganglia_Evidence.sha256(Files.readAllBytes(neuronRois)));
            result.put("neurons_per_ganglion",numbers(perGanglion));result.put("assignments",assignments(neurons,lp,perGanglion));
            neurons.close();
        }
        mask.changes=false;mask.close();labels.changes=false;labels.close();source.changes=false;source.close();return result;
    }
    private static ImagePlus fixedNeurons(Path file,int w,int h)throws Exception{
        ShortProcessor ip=new ShortProcessor(w,h);int count=0;
        try(ZipFile zip=new ZipFile(file.toFile())){
            List<? extends ZipEntry> entries=Collections.list(zip.entries());entries.sort(Comparator.comparing(ZipEntry::getName));
            for(ZipEntry entry:entries){if(!entry.getName().endsWith(".roi"))continue;byte[] bytes;
                try(InputStream in=zip.getInputStream(entry)){bytes=in.readAllBytes();}
                Roi roi=new RoiDecoder(bytes,entry.getName()).getRoi();check(roi!=null,"Invalid historical ROI");
                check(roi.getBounds().x>=0&&roi.getBounds().y>=0&&roi.getBounds().getMaxX()<=w&&roi.getBounds().getMaxY()<=h,"Historical ROI outside matched image");
                ip.setValue(++count);ip.fill(roi);
            }
        }
        check(count==83,"Historical neuron ROI set changed");return new ImagePlus("fixed_historical_neurons",ip);
    }
    private static List<Map<String,Object>> assignments(ImagePlus neurons,short[] ganglia,int[] counts){
        int w=neurons.getWidth(),h=neurons.getHeight();short[] np=(short[])neurons.getProcessor().getPixels();
        double[] sx=new double[84],sy=new double[84];int[] n=new int[84];
        for(int y=0;y<h;y++)for(int x=0;x<w;x++){int id=np[y*w+x]&65535;if(id>0){sx[id]+=x;sy[id]+=y;n[id]++;}}
        List<Map<String,Object>> rows=new ArrayList<>();int[] verified=new int[counts.length];
        for(int id=1;id<84;id++){check(n[id]>0,"Historical neuron label absent");int x=(int)Math.round(sx[id]/n[id]),y=(int)Math.round(sy[id]/n[id]);int gid=ganglia[y*w+x]&65535;
            rows.add(map("neuron_id",id,"ganglion_id",gid));if(gid>0){check(gid<verified.length,"Invalid ganglion assignment");verified[gid]++;}}
        check(Arrays.equals(counts,verified),"Actual GangliaOps counts differ from per-neuron assignments");return rows;
    }
    private static String floatHash(ImagePlus image,Path output)throws Exception{
        MessageDigest digest=MessageDigest.getInstance("SHA-256");ByteBuffer buffer=ByteBuffer.allocate(4).order(ByteOrder.BIG_ENDIAN);
        OutputStream stream=output==null?OutputStream.nullOutputStream():new GZIPOutputStream(Files.newOutputStream(output));
        try(OutputStream out=stream){for(int c=1;c<=image.getStackSize();c++)for(int i=0;i<image.getWidth()*image.getHeight();i++){buffer.clear();buffer.putFloat(image.getStack().getProcessor(c).getf(i));byte[] bytes=buffer.array();digest.update(bytes);out.write(bytes);}}
        StringBuilder result=new StringBuilder();for(byte v:digest.digest())result.append(String.format("%02x",v&255));return result.toString();
    }
    private static List<Number> numbers(Object array){List<Number> out=new ArrayList<>();for(int i=0;i<Array.getLength(array);i++)out.add((Number)Array.get(array,i));return out;}
    private static void check(boolean ok,String text){if(!ok)throw new AssertionError(text);}
    private static Map<String,Object> map(Object... pairs){Map<String,Object> m=new LinkedHashMap<>();for(int i=0;i<pairs.length;i+=2)m.put(String.valueOf(pairs[i]),pairs[i+1]);return m;}
}

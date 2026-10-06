package Features.Tools;

import ij.ImagePlus;
import java.io.File;
import ij.ImageStack;
import ij.process.*;
import java.nio.*;
import java.security.*;
import java.nio.file.*;
import java.util.*;

/** Calls the actual GAT adapter/process boundary; compares pixels and owned motion CSV. */
public final class AdapterProbe {
 static String digest(ImagePlus image) throws Exception {
  MessageDigest hash=MessageDigest.getInstance("SHA-256");
  ByteBuffer word=ByteBuffer.allocate(4).order(ByteOrder.BIG_ENDIAN);
  for(int z=1;z<=image.getStackSize();z++) for(int i=0;i<image.getWidth()*image.getHeight();i++) {word.clear();word.putFloat(image.getStack().getProcessor(z).getf(i));hash.update(word.array());}
  StringBuilder s=new StringBuilder();for(byte b:hash.digest())s.append(String.format("%02x",b&255));return s.toString();
 }
 static ImagePlus synthetic(int bits) {
  int w=128,h=96;ImageProcessor base=bits==8?new ByteProcessor(w,h):new ShortProcessor(w,h);
  Random rng=new Random(8291);for(int y=10;y<h-10;y++)for(int x=10;x<w-10;x++)base.set(x,y,rng.nextInt(bits==8?200:50000)+1);
  ImageStack stack=new ImageStack(w,h);for(int[] shift:new int[][]{{0,0},{3,-2},{-4,5},{0,0}}){ImageProcessor copy=base.duplicate();copy.translate(shift[0],shift[1]);stack.addSlice(copy);}
  return new ImagePlus("synthetic-"+bits,stack);
 }

    public static void main(String[] args) throws Exception {
        Path directory=Paths.get(args[0]);Files.createDirectories(directory);
        System.setProperty("gat.alignment.backend","native");
        System.setProperty("gat.alignment.directory",Paths.get(args[1]).toAbsolutePath().toString());
        List<String> cases=new ArrayList<>();
        String[] names={"synthetic8","synthetic16","synthetic8-ref3","synthetic16-ref2","public-calcium","public-calcium-ref71"};
        int[] references={1,1,3,2,1,71};
        for(int i=0;i<names.length;i++) {
            ImagePlus input=i<4?synthetic(i%2==0?8:16):ij.IJ.openImage(args[2]);
            if(input==null)throw new AssertionError("Missing public fixture");
            input.setTitle(names[i]);input.setDimensions(1,1,input.getStackSize());
            input.getCalibration().pixelWidth=0.5;input.getCalibration().frameInterval=1.25;
            long start=System.nanoTime();
            AlignStack.alignTemplateMatching(input,references[i]);
            double elapsed=(System.nanoTime()-start)/1e9;
            File csv=AlignStack.writeVerifiedAlignmentResultsCSV(input,directory.toString());
            if(csv==null)throw new AssertionError("No verified motion CSV");
            List<String> rows=Files.readAllLines(csv.toPath());
            if(rows.size()!=input.getStackSize()+1||!rows.get(0).equals("Algorithm,ReferenceSlice,Slice,Dx,Dy"))throw new AssertionError("Wrong motion CSV shape");
            double[][] shifts=new double[input.getStackSize()][2];
            for(int row=1;row<rows.size();row++) {
                String[] cells=rows.get(row).split(",");
                if(!cells[0].equals("TemplateMatching")||Integer.parseInt(cells[1])!=references[i]||Integer.parseInt(cells[2])!=row)
                    throw new AssertionError("Motion CSV stage/reference/frame mismatch");
                shifts[row-1][0]=Double.parseDouble(cells[3]);shifts[row-1][1]=Double.parseDouble(cells[4]);
            }
            if(input.getNFrames()!=shifts.length||input.getCalibration().pixelWidth!=0.5||input.getCalibration().frameInterval!=1.25)
                throw new AssertionError("Alignment metadata lost");
            cases.add("{\"case\":\""+names[i]+"\",\"width\":"+input.getWidth()+",\"height\":"+input.getHeight()
                    +",\"frames\":"+input.getStackSize()+",\"bits\":"+input.getBitDepth()+",\"shifts\":"+Arrays.deepToString(shifts)
                    +",\"aligned_pixel_sha256\":\""+digest(input)+"\",\"adapter_seconds\":"+elapsed+"}");
        }
        Files.writeString(directory.resolve("adapter.json"),"{\"cases\":["+String.join(",",cases)+"]}\n");
    }
}

package TemplateMatching;
import ij.*;
import ij.process.*;
import java.awt.Rectangle;
import java.lang.reflect.Method;
import java.nio.*;
import java.nio.file.*;
import java.security.*;
import java.util.*;
public class TemplateMatchProbe {
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
 static String run(ImagePlus image,String name,int referenceSlice)throws Exception {
  long started=System.nanoTime();Align_slices a=new Align_slices();a.imp=image;a.stack=image.getStack();a.width=image.getWidth();a.height=image.getHeight();a.method=5;a.subPixel=false;a.sArea=0;a.itpMethod=0;
  a.refSlice=referenceSlice;a.rect=new Rectangle((int)Math.floor(a.width/6.0),(int)Math.floor(a.height/6.0),(int)Math.floor(a.width*0.7),(int)Math.floor(a.height*0.7));
  String macro=String.format(java.util.Locale.ROOT,"method=5 windowsizex=%d windowsizey=%d x0=%d y0=%d swindow=0 subpixel=false itpmethod=0 ref.slice=%d show=true",a.rect.width,a.rect.height,a.rect.x,a.rect.y,referenceSlice);
  Method parse=Align_slices.class.getDeclaredMethod("getMacroParameters",String.class);parse.setAccessible(true);parse.invoke(a,macro);
  if(a.method!=5||a.subPixel||a.sArea!=0||a.itpMethod!=0||a.refSlice!=referenceSlice||a.windowSizeX!=a.rect.width||a.iniX!=a.rect.x)throw new AssertionError("GAT macro options parsed differently from worker parameters");
  ImageProcessor reference=a.stack.getProcessor(referenceSlice);reference.setRoi(a.rect);a.ref=reference.crop();reference.resetRoi();
  Method method=Align_slices.class.getDeclaredMethod("alignSlices",int.class);method.setAccessible(true);
  double[][] values=new double[image.getStackSize()][2];for(int z=referenceSlice-1;z>0;z--){method.invoke(a,z);values[z-1][0]=a.disX;values[z-1][1]=a.disY;}for(int z=referenceSlice+1;z<=image.getStackSize();z++){method.invoke(a,z);values[z-1][0]=a.disX;values[z-1][1]=a.disY;}String shifts=Arrays.deepToString(values);
  return "{\"case\":\""+name+"\",\"width\":"+a.width+",\"height\":"+a.height+",\"frames\":"+image.getStackSize()+",\"bits\":"+image.getBitDepth()+",\"shifts\":"+shifts+",\"aligned_pixel_sha256\":\""+digest(image)+"\",\"milliseconds\":"+(System.nanoTime()-started)/1000000+"}";
 }
 public static void main(String[]args)throws Exception {
  List<String>results=new ArrayList<>();results.add(run(synthetic(8),"synthetic8",1));results.add(run(synthetic(16),"synthetic16",1));
  results.add(run(synthetic(8),"synthetic8-ref3",3));results.add(run(synthetic(16),"synthetic16-ref2",2));
  if(args.length>1){ImagePlus real=IJ.openImage(args[1]);if(real==null)throw new IllegalArgumentException("Cannot read public TIFF");results.add(run(real,"public-calcium",1));ImagePlus second=IJ.openImage(args[1]);results.add(run(second,"public-calcium-ref71",71));}
  Files.writeString(Paths.get(args[0]),"{\"java\":\""+System.getProperty("java.version")+"\",\"arch\":\""+System.getProperty("os.arch")+"\",\"cases\":["+String.join(",",results)+"]}\n");
 }
}

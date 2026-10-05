import java.io.*;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import de.csbdresden.stardist.Candidates;
import ij.process.ShortProcessor;
import net.imglib2.img.array.ArrayImgs;

public class NmsComparison {
 static class Prediction {
  int w,h,c; float[] values,prob,dist;
  Prediction(String file) throws Exception {
   try(DataInputStream in=new DataInputStream(new BufferedInputStream(Files.newInputStream(Path.of(file))))) {
    if(in.readInt()!=0x4741544f || in.readInt()!=1)throw new AssertionError("protocol");
    w=in.readInt();h=in.readInt();c=in.readInt();int pixels=w*h;
    values=new float[pixels*c];prob=new float[pixels];dist=new float[pixels*(c-1)];
    for(int p=0;p<pixels;p++)for(int ch=0;ch<c;ch++) {
     float value=in.readFloat();values[p*c+ch]=value;
     if(ch==0)prob[p]=value; else dist[(ch-1)*pixels+p]=value;
    }
    if(in.read()!=-1)throw new AssertionError("trailing bytes");
   }
  }
 }
 static class Segmentation {
  int candidates,count;short[] labels;String hash;List<String> origins=new ArrayList<>();
  Segmentation(Prediction p,double probability,double overlap)throws Exception {
   Candidates result=new Candidates(ArrayImgs.floats(p.prob,p.w,p.h),ArrayImgs.floats(p.dist,p.w,p.h,p.c-1),probability,2,null);
   candidates=result.getSorted().size();result.nms(overlap);List<Integer> winners=result.getWinner();count=winners.size();
   ShortProcessor output=new ShortProcessor(p.w,p.h);
   for(int i=count-1;i>=0;i--) {output.setColor(1+i%65535);output.fill(result.getPolygonRoi(winners.get(i)));}
   for(int winner:winners){ij.process.FloatPolygon points=result.getOriginRoi(winner).getFloatPolygon();origins.add(points.xpoints[0]+","+points.ypoints[0]);}
   labels=(short[])output.getPixels();MessageDigest digest=MessageDigest.getInstance("SHA-256");
   for(short value:labels) {digest.update((byte)(value>>>8));digest.update((byte)value);}
   StringBuilder b=new StringBuilder();for(byte v:digest.digest())b.append(String.format("%02x",v&255));hash=b.toString();
  }
 }
 public static void main(String[] args)throws Exception {
  Prediction modern=new Prediction(args[0]),legacy=new Prediction(args[1]);
  if(modern.w!=legacy.w||modern.h!=legacy.h||modern.c!=legacy.c)throw new AssertionError("shape mismatch");
  double maxProb=0,maxDist=0,sumProb=0,sumDist=0;int mismatchedFloats=0;
  for(int i=0;i<modern.values.length;i++) {
   double d=Math.abs((double)modern.values[i]-legacy.values[i]);if(d!=0)mismatchedFloats++;
   if(i%modern.c==0){maxProb=Math.max(maxProb,d);sumProb+=d;}else{maxDist=Math.max(maxDist,d);sumDist+=d;}
  }
  double probability=Double.parseDouble(args[2]),overlap=Double.parseDouble(args[3]);
  Segmentation m=new Segmentation(modern,probability,overlap),l=new Segmentation(legacy,probability,overlap);
  int labelDiff=0,foregroundDiff=0;for(int i=0;i<m.labels.length;i++){if(m.labels[i]!=l.labels[i])labelDiff++;if((m.labels[i]!=0)!=(l.labels[i]!=0))foregroundDiff++;}
  System.out.printf(Locale.ROOT,"shape=%dx%dx%d; thresholds=%.6f/%.6f; boundary=2%n",modern.w,modern.h,modern.c,probability,overlap);
  System.out.printf(Locale.ROOT,"raw float differences=%d/%d; probability max/mean abs error=%.9g/%.9g; distance max/mean abs error=%.9g/%.9g%n",mismatchedFloats,modern.values.length,maxProb,sumProb/(modern.w*modern.h),maxDist,sumDist/(modern.w*modern.h*(modern.c-1)));
  System.out.println("modern candidates/count="+m.candidates+"/"+m.count+"; legacy candidates/count="+l.candidates+"/"+l.count);
  System.out.println("differing labeled pixels="+labelDiff+"/"+m.labels.length+"; differing foreground pixels="+foregroundDiff+"; winner centers same="+m.origins.equals(l.origins));
  System.out.println("modern label SHA256="+m.hash+"; legacy label SHA256="+l.hash);
 }
}

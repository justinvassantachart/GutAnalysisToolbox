import java.io.*;
import java.nio.file.*;
import java.security.*;
import java.util.*;
import java.util.zip.GZIPOutputStream;
import de.csbdresden.stardist.Candidates;
import ij.process.ShortProcessor;
import net.imglib2.img.array.ArrayImgs;

/** Independent pixel-level regression checker. Never loads a TensorFlow runtime. */
public class CorpusNmsComparison {
 static class Prediction {
  final int w,h,c; final float[] prob,dist;
  Prediction(int w,int h,int c){this.w=w;this.h=h;this.c=c;prob=new float[w*h];dist=new float[Math.multiplyExact(w*h,c-1)];}
  void set(int p,int c,float v){if(c==0)prob[p]=v;else dist[(c-1)*w*h+p]=v;}
 }
 static class Pair {
  Prediction modern,legacy;String modernHash,legacyHash;
  long differentValues,thresholdFlips,outsideTolerance;
  double maxProbability,maxDistance,sumProbability,sumDistance;
  Pair(String modernPath,String legacyPath,double threshold)throws Exception {
   MessageDigest md=MessageDigest.getInstance("SHA-256"),ld=MessageDigest.getInstance("SHA-256");
   try(DataInputStream m=reader(modernPath,md);DataInputStream l=reader(legacyPath,ld)) {
    int[] mh=header(m),lh=header(l);if(!Arrays.equals(mh,lh))throw new IOException("Prediction header mismatch");
    int w=mh[2],h=mh[3],c=mh[4];modern=new Prediction(w,h,c);legacy=new Prediction(w,h,c);
    for(int p=0;p<w*h;p++)for(int ch=0;ch<c;ch++) {
     float mv=m.readFloat(),lv=l.readFloat();if(!Float.isFinite(mv)||!Float.isFinite(lv))throw new IOException("Nonfinite prediction");
     modern.set(p,ch,mv);legacy.set(p,ch,lv);double d=Math.abs((double)mv-lv);
     if(Float.floatToIntBits(mv)!=Float.floatToIntBits(lv))differentValues++;
     if(d>1e-4+1e-4*Math.abs(lv))outsideTolerance++;
     if(ch==0){maxProbability=Math.max(maxProbability,d);sumProbability+=d;if((mv>threshold)!=(lv>threshold))thresholdFlips++;}
     else{maxDistance=Math.max(maxDistance,d);sumDistance+=d;}
    }
    if(m.read()!=-1||l.read()!=-1)throw new IOException("Trailing prediction bytes");
   }
   modernHash=hex(md.digest());legacyHash=hex(ld.digest());
  }
 }
 static DataInputStream reader(String path,MessageDigest digest)throws IOException {
  return new DataInputStream(new BufferedInputStream(new DigestInputStream(Files.newInputStream(Path.of(path)),digest),65536));
 }
 static int[] header(DataInputStream in)throws IOException {
  int[] h=new int[5];for(int i=0;i<5;i++)h[i]=in.readInt();
  if(h[0]!=0x4741544f||h[1]!=1||h[2]<1||h[3]<1||h[4]<4||h[4]>1024||(long)h[2]*h[3]*h[4]>268435456L)throw new IOException("Invalid GATO header");
  return h;
 }
 static String hex(byte[] bytes){StringBuilder b=new StringBuilder();for(byte v:bytes)b.append(String.format("%02x",v&255));return b.toString();}
 static String hash(short[] labels)throws Exception {MessageDigest d=MessageDigest.getInstance("SHA-256");for(short v:labels){d.update((byte)(v>>>8));d.update((byte)v);}return hex(d.digest());}
 static class Outline {
  final float cx,cy; final float[] x,y; final double perimeter,area;
  Outline(ij.process.FloatPolygon center,ij.process.FloatPolygon polygon) {
   cx=center.xpoints[0];cy=center.ypoints[0];x=Arrays.copyOf(polygon.xpoints,polygon.npoints);y=Arrays.copyOf(polygon.ypoints,polygon.npoints);
   double length=0,twiceArea=0;
   for(int i=0;i<x.length;i++){int j=(i+1)%x.length;length+=Math.hypot((double)x[j]-x[i],(double)y[j]-y[i]);twiceArea+=(double)x[i]*y[j]-(double)x[j]*y[i];}
   perimeter=length;area=Math.abs(twiceArea)/2;
  }
 }
 static class OutlineComparison {
  int matched,unmatchedModern,unmatchedLegacy,changedObjects,changedVertices,rayMismatches;
  double maxCoordinate,maxVertexDistance,maxPerimeter,maxArea;
  OutlineComparison(Segmentation modern,Segmentation legacy) {
   for(Map.Entry<String,Outline> entry:modern.outlines.entrySet()) {
    Outline a=entry.getValue(),b=legacy.outlines.get(entry.getKey());
    if(b==null){unmatchedModern++;continue;}matched++;
    if(a.x.length!=b.x.length){rayMismatches++;continue;}
    boolean changed=false;
    for(int i=0;i<a.x.length;i++) {
     double dx=Math.abs((double)a.x[i]-b.x[i]),dy=Math.abs((double)a.y[i]-b.y[i]);
     maxCoordinate=Math.max(maxCoordinate,Math.max(dx,dy));maxVertexDistance=Math.max(maxVertexDistance,Math.hypot(dx,dy));
     if(dx!=0||dy!=0){changed=true;changedVertices++;}
    }
    if(changed)changedObjects++;
    maxPerimeter=Math.max(maxPerimeter,Math.abs(a.perimeter-b.perimeter));maxArea=Math.max(maxArea,Math.abs(a.area-b.area));
   }
   for(String center:legacy.outlines.keySet())if(!modern.outlines.containsKey(center))unmatchedLegacy++;
  }
  boolean equal(){return unmatchedModern==0&&unmatchedLegacy==0&&rayMismatches==0&&changedVertices==0;}
 }
 static class Segmentation {
  int candidates,count,visibleLabels;short[] labels,canonical;String hash,canonicalHash,measurementHash;List<String> centers=new ArrayList<>();List<String> measurements=new ArrayList<>();Map<String,Outline> outlines=new TreeMap<>();Map<String,Integer> labelsByCenter=new TreeMap<>();StringBuilder details=new StringBuilder("[");
  Segmentation(Prediction p,double probability,double overlap)throws Exception {
   Candidates result=new Candidates(ArrayImgs.floats(p.prob,p.w,p.h),ArrayImgs.floats(p.dist,p.w,p.h,p.c-1),probability,2,null);
   candidates=result.getSorted().size();result.nms(overlap);List<Integer>winners=result.getWinner();count=winners.size();
   ShortProcessor output=new ShortProcessor(p.w,p.h);
   for(int i=count-1;i>=0;i--){output.setColor(1+i%65535);output.fill(result.getPolygonRoi(winners.get(i)));}
   for(int wi=0;wi<winners.size();wi++){int winner=winners.get(wi);ij.process.FloatPolygon points=result.getOriginRoi(winner).getFloatPolygon();String center=points.xpoints[0]+","+points.ypoints[0];centers.add(center);labelsByCenter.put(center,1+wi%65535);outlines.put(center,new Outline(points,result.getPolygonRoi(winner).getFloatPolygon()));}
   Collections.sort(centers);labels=(short[])output.getPixels();canonical=new short[labels.length];
   int[] mapping=new int[65536];int next=1;
   for(int i=0;i<labels.length;i++){int old=labels[i]&65535;if(old==0)continue;if(mapping[old]==0)mapping[old]=next++;canonical[i]=(short)mapping[old];}
   visibleLabels=next-1;long[][]stats=new long[next][8];for(int i=1;i<next;i++){stats[i][4]=p.w;stats[i][5]=p.h;}
   for(int y=0;y<p.h;y++)for(int x=0;x<p.w;x++) {
    int at=y*p.w+x,id=canonical[at]&65535;if(id==0)continue;long[]s=stats[id];s[0]++;s[1]+=x;s[2]+=y;
    if(x==0||canonical[at-1]!=canonical[at])s[3]++;if(x==p.w-1||canonical[at+1]!=canonical[at])s[3]++;
    if(y==0||canonical[at-p.w]!=canonical[at])s[3]++;if(y==p.h-1||canonical[at+p.w]!=canonical[at])s[3]++;
    s[4]=Math.min(s[4],x);s[5]=Math.min(s[5],y);s[6]=Math.max(s[6],x);s[7]=Math.max(s[7],y);
   }
   // Canonical object order is first raster occurrence; sums preserve exact pixel centroids without floating rounding.
   MessageDigest measurementDigest=MessageDigest.getInstance("SHA-256");
   for(int id=1;id<next;id++){String row=Arrays.toString(stats[id]);measurements.add(row);measurementDigest.update((row+"\n").getBytes(java.nio.charset.StandardCharsets.UTF_8));}
   int detailIndex=0;
   for(Map.Entry<String,Outline> entry:outlines.entrySet()) {
    Outline polygon=entry.getValue();int originalLabel=labelsByCenter.get(entry.getKey());int canonicalId=mapping[originalLabel];long[] s=stats[canonicalId];
    if(detailIndex++>0)details.append(',');
    details.append(object("winning_center_x_px",polygon.cx,"winning_center_y_px",polygon.cy,
     "label_id",originalLabel,"canonical_label_id",canonicalId,"area_pixels",s[0],
     "centroid_x_px",s[0]>0?(double)s[1]/s[0]+0.5:null,"centroid_y_px",s[0]>0?(double)s[2]/s[0]+0.5:null,
     "four_neighbor_perimeter_px",s[3],"bbox_x_min",s[0]>0?s[4]:null,"bbox_y_min",s[0]>0?s[5]:null,
     "bbox_x_max_inclusive",s[0]>0?s[6]:null,"bbox_y_max_inclusive",s[0]>0?s[7]:null,
     "quantized_polygon_perimeter_px",polygon.perimeter,"quantized_polygon_area_px2",polygon.area));
   }
   details.append(']');
   measurementHash=hex(measurementDigest.digest());hash=hash(labels);canonicalHash=hash(canonical);
  }
 }
 static void saveOutlines(String filename,Segmentation segmentation,int width,int height)throws Exception {
  Path path=Path.of(filename),tmp=Path.of(filename+".tmp");Files.createDirectories(path.getParent());
  try(DataOutputStream out=new DataOutputStream(new BufferedOutputStream(new GZIPOutputStream(Files.newOutputStream(tmp))))) {
   out.writeInt(0x47415450);out.writeInt(1);out.writeInt(width);out.writeInt(height);out.writeInt(segmentation.outlines.size());
   for(Outline polygon:segmentation.outlines.values()){out.writeFloat(polygon.cx);out.writeFloat(polygon.cy);out.writeInt(polygon.x.length);for(int i=0;i<polygon.x.length;i++){out.writeFloat(polygon.x[i]);out.writeFloat(polygon.y[i]);}}
  }
  try(java.nio.channels.FileChannel file=java.nio.channels.FileChannel.open(tmp,StandardOpenOption.WRITE)){file.force(true);}
  Files.move(tmp,path,StandardCopyOption.REPLACE_EXISTING,StandardCopyOption.ATOMIC_MOVE);
 }
 static String jsonString(String s){return "\""+s.replace("\\","\\\\").replace("\"","\\\"")+"\"";}
 static String object(Object...pairs){StringBuilder b=new StringBuilder("{");for(int i=0;i<pairs.length;i+=2){if(i>0)b.append(',');b.append(jsonString((String)pairs[i])).append(':');Object v=pairs[i+1];if(v instanceof String)b.append(jsonString((String)v));else b.append(v);}return b.append('}').toString();}
 public static void main(String[]args)throws Exception {
  if(args.length!=4&&args.length!=5)throw new IllegalArgumentException("modern.bin legacy.bin probability overlap [outline-artifact-prefix]");
  double probability=Double.parseDouble(args[2]),overlap=Double.parseDouble(args[3]);Pair pair=new Pair(args[0],args[1],probability);Prediction p=pair.modern;
  Segmentation m=new Segmentation(pair.modern,probability,overlap),l=new Segmentation(pair.legacy,probability,overlap);
  int labelDiff=0,canonicalDiff=0,foregroundDiff=0,foregroundUnion=0,foregroundIntersection=0;
  for(int i=0;i<m.labels.length;i++){if(m.labels[i]!=l.labels[i])labelDiff++;if(m.canonical[i]!=l.canonical[i])canonicalDiff++;boolean mf=m.labels[i]!=0,lf=l.labels[i]!=0;if(mf!=lf)foregroundDiff++;if(mf||lf)foregroundUnion++;if(mf&&lf)foregroundIntersection++;}
  StringBuilder changedPixelSamples=new StringBuilder("[");int sampleCount=0;
  for(int i=0;i<m.labels.length&&sampleCount<20;i++)if(m.labels[i]!=l.labels[i]){if(sampleCount++>0)changedPixelSamples.append(',');changedPixelSamples.append(object("x",i%p.w,"y",i/p.w,"modern_label",m.labels[i]&65535,"legacy_label",l.labels[i]&65535));}
  changedPixelSamples.append(']');
  OutlineComparison outlines=new OutlineComparison(m,l);
  if(args.length==5){saveOutlines(args[4]+"-modern.polygons.gz",m,p.w,p.h);saveOutlines(args[4]+"-legacy.polygons.gz",l,p.w,p.h);}
  long pixelCount=(long)p.w*p.h;
  System.out.println(object(
   "comparison_schema_version",2,"width",p.w,"height",p.h,"channels",p.c,"probability_threshold",probability,"nms_threshold",overlap,"excluded_boundary",2,
   "modern_tensor_sha256",pair.modernHash,"legacy_tensor_sha256",pair.legacyHash,
   "different_float_values",pair.differentValues,"total_float_values",pixelCount*p.c,
   "max_abs_probability",pair.maxProbability,"mean_abs_probability",pair.sumProbability/pixelCount,
   "max_abs_distance",pair.maxDistance,"mean_abs_distance",pair.sumDistance/(pixelCount*(p.c-1)),
   "outside_atol_1e4_rtol_1e4",pair.outsideTolerance,"probability_threshold_flips",pair.thresholdFlips,
   "modern_candidates",m.candidates,"legacy_candidates",l.candidates,"modern_count",m.count,"legacy_count",l.count,
   "modern_visible_labels",m.visibleLabels,"legacy_visible_labels",l.visibleLabels,
   "different_label_pixels",labelDiff,"changed_label_pixel_samples",changedPixelSamples,
   "measurement_detail_version",1,
   "modern_object_measurements",labelDiff>0?m.details:new StringBuilder("[]"),
   "legacy_object_measurements",labelDiff>0?l.details:new StringBuilder("[]"),"different_canonical_label_pixels",canonicalDiff,"different_foreground_pixels",foregroundDiff,
   "foreground_iou",foregroundUnion==0?1.0:(double)foregroundIntersection/foregroundUnion,
   "winner_centers_equal",m.centers.equals(l.centers),"pixel_measurements_equal",m.measurements.equals(l.measurements),
   "strict_quantized_outlines_equal",outlines.equal(),"matched_outline_objects",outlines.matched,
   "unmatched_modern_outline_centers",outlines.unmatchedModern,"unmatched_legacy_outline_centers",outlines.unmatchedLegacy,
   "outline_ray_count_mismatches",outlines.rayMismatches,"outlines_with_changed_vertices",outlines.changedObjects,"changed_outline_vertices",outlines.changedVertices,
   "max_abs_vertex_coordinate_delta_px",outlines.maxCoordinate,"max_euclidean_vertex_delta_px",outlines.maxVertexDistance,
   "max_abs_polygon_perimeter_delta_px",outlines.maxPerimeter,"max_abs_polygon_area_delta_px2",outlines.maxArea,
   "measurement_fields","area,sum_x,sum_y,4_neighbor_perimeter,x_min,y_min,x_max,y_max; canonical raster-order objects; pixel units",
   "modern_label_sha256",m.hash,"legacy_label_sha256",l.hash,"modern_canonical_sha256",m.canonicalHash,"legacy_canonical_sha256",l.canonicalHash,
   "modern_measurements_sha256",m.measurementHash,"legacy_measurements_sha256",l.measurementHash));
 }
}

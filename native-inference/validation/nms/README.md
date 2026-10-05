# Independent Fiji StarDist NMS comparison

`NmsComparison.java` reads two GATO predictions, reports per-channel numerical differences, applies upstream Fiji StarDist NMS, and compares final 16-bit label images and winner centers. Boundary exclusion is fixed at 2, matching GAT. Modern and legacy label SHA-256 hashes are printed. This is a small validation tool, not a user-input parser or replacement segmentation implementation.

The tested upstream revision is `aff59dbd3cdf88dfa567d4dd562eab943bf4f99b` of https://github.com/stardist/stardist-imagej . Keep its source unchanged for a meaningful comparison. The compiler classpath needs its `lib/Clipper-6.4.2.jar` plus these Maven artifacts (or the matching Fiji-installed JARs):

- net.imagej:ij:1.54p
- net.imglib2:imglib2:7.1.5
- net.imagej:imagej-common:2.1.1
- org.scijava:scijava-common:2.100.1

From this directory, with `STARDIST` set to that checkout and `DEPENDENCY_CP` set to the four JAR paths separated by your OS classpath separator:

```sh
CP="$STARDIST/lib/Clipper-6.4.2.jar:$DEPENDENCY_CP"
mkdir -p classes
javac -cp "$CP" -d classes \
  "$STARDIST/src/main/java/de/csbdresden/stardist/"{Candidates,Point2D,Box2D,Utils}.java \
  NmsComparison.java
java -Djava.awt.headless=true -cp "classes:$CP" NmsComparison \
  modern-output.bin legacy-output.bin 0.5 0.3
```

The comparator reproduces `StarDist2DBase`'s reverse winner traversal, label numbering, and ImageJ `ShortProcessor.fill` rasterization. It reports differences rather than silently treating approximate neural-network values as label equivalence. See `../RESULTS.md` for the checked datasets and results. To keep numerical and biological claims distinct, inspect probability/distance errors separately from labeled-pixel mismatches and test multiple representative images and thresholds.

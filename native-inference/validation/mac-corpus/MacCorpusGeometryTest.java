import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.zip.GZIPInputStream;
import ij.gui.PolygonRoi;
import ij.gui.Roi;
import ij.process.ShortProcessor;

/** Standalone validation-only controls; run with the same pinned geometry classpath. */
public final class MacCorpusGeometryTest {
    static int checks;
    static void check(boolean condition, String message) {
        checks++; if (!condition) throw new AssertionError(message);
    }
    interface Throwing { void run() throws Exception; }
    static void rejects(Throwing body, String message) throws Exception {
        boolean failed = false;
        try { body.run(); } catch (IOException | IllegalArgumentException expected) { failed = true; }
        check(failed, message);
    }
    static PolygonRoi square(float left, float top, float right, float bottom) {
        return new PolygonRoi(new float[]{left, right, right, left}, new float[]{top, top, bottom, bottom}, 4, Roi.POLYGON);
    }
    static MacCorpusGeometry.Outline outline(float cx, float cy, PolygonRoi roi, int label) throws Exception {
        return new MacCorpusGeometry.Outline(cx, cy, roi, label);
    }
    static long[] referenceStats(short[] image, int width, int height) {
        long[] stats = new long[]{0, 0, 0, 0, width, height, 0, 0};
        for (int y = 0; y < height; y++) for (int x = 0; x < width; x++) {
            int at = y * width + x; if (image[at] == 0) continue;
            stats[0]++; stats[1] += x; stats[2] += y;
            if (x == 0 || image[at - 1] == 0) stats[3]++;
            if (x == width - 1 || image[at + 1] == 0) stats[3]++;
            if (y == 0 || image[at - width] == 0) stats[3]++;
            if (y == height - 1 || image[at + width] == 0) stats[3]++;
            stats[4] = Math.min(stats[4], x); stats[5] = Math.min(stats[5], y);
            stats[6] = Math.max(stats[6], x); stats[7] = Math.max(stats[7], y);
        }
        return stats;
    }
    static void maskControls() throws Exception {
        int width = 19, height = 17;
        List<PolygonRoi> shapes = new ArrayList<>();
        shapes.add(square(-4.27f, -3.61f, 6.54f, 9.28f));
        shapes.add(square(14.42f, 12.69f, 21.99f, 23.91f));
        shapes.add(square(23, 25, 27, 29));
        shapes.add(square(2.5f, 2.5f, 3.5f, 3.5f));
        shapes.add(new PolygonRoi(new float[]{-0.7f, 15.33f, 9.23f, 3.98f}, new float[]{6.77f, -1.94f, 19.68f, 8.12f}, 4, Roi.POLYGON));
        Random random = new Random(71423);
        for (int i = 0; i < 70; i++) {
            int rays = 16; float[] x = new float[rays], y = new float[rays];
            float cx = random.nextFloat() * 28 - 4, cy = random.nextFloat() * 26 - 4;
            for (int r = 0; r < rays; r++) {
                double angle = 2 * Math.PI * r / rays, radius = 1 + 10 * random.nextDouble();
                x[r] = (float) (cx + Math.cos(angle) * radius); y[r] = (float) (cy + Math.sin(angle) * radius);
            }
            shapes.add(new PolygonRoi(x, y, rays, Roi.POLYGON));
        }
        for (PolygonRoi roi : shapes) {
            ShortProcessor reference = new ShortProcessor(width, height); reference.setColor(1); reference.fill(roi);
            short[] labels = (short[]) reference.getPixels();
            MacCorpusGeometry.Mask mask = new MacCorpusGeometry.Mask(roi, width, height);
            BitSet expected = new BitSet(width * height), actual = new BitSet(width * height);
            for (int p = 0; p < labels.length; p++) if (labels[p] != 0) expected.set(p);
            for (int p : mask.pixels) actual.set(p);
            check(expected.equals(actual), "ROI mask must match full-image ImageJ fill, including clipped boundaries");
            long[] stats = referenceStats(labels, width, height);
            check(stats[0] == 0 ? mask.stats[0] == 0 : Arrays.equals(stats, mask.stats), "Independent pixel measurements differ");
        }
    }
    static void orderControls(Path root) throws Exception {
        MacCorpusGeometry.Geometry geometry = new MacCorpusGeometry.Geometry(16, 16);
        geometry.add(outline(3.5f, 3.5f, square(1.5f, 1.5f, 7.5f, 7.5f), 1));
        geometry.add(outline(6.5f, 6.5f, square(4.5f, 4.5f, 10.5f, 10.5f), 2));
        geometry.measureMasks(); geometry.composite = new MacCorpusGeometry.Composite(geometry);
        check(geometry.composite.labels[5 * 16 + 5] == 1, "Reverse overpaint must favor lower original label");
        Path payload = root.resolve("polygons.gz"); MacCorpusGeometry.saveOutlines(payload, geometry);
        MacCorpusGeometry.Geometry legacy = MacCorpusGeometry.readOutlines(payload, 16, 16);
        check(legacy.composite == null, "An archive must not imply an original label order");
        check(legacy.maskMultisetHash.equals(geometry.maskMultisetHash), "Polygon roundtrip independent masks");
        Path order = root.resolve("order.tsv"); Files.writeString(order, "6.5\t6.5\t2\n3.5\t3.5\t1\n");
        MacCorpusGeometry.applyRetainedOrder(legacy, order);
        check(geometry.composite.labelHash.equals(legacy.composite.labelHash), "Supplied retained order restores raw labels");
        check(geometry.composite.canonicalHash.equals(legacy.composite.canonicalHash), "Supplied retained order restores canonical labels");
        check(geometry.composite.measurementHash.equals(legacy.composite.measurementHash), "Supplied retained order restores measurements");
        Files.writeString(order, "6.5\t6.5\t1\n3.5\t3.5\t2\n");
        MacCorpusGeometry.applyRetainedOrder(legacy, order);
        check(!geometry.composite.labelHash.equals(legacy.composite.labelHash), "Wrong order negative control alters raster");
        check(!geometry.composite.canonicalHash.equals(legacy.composite.canonicalHash), "Wrong order can alter canonical overlap geometry");
        check(legacy.maskMultisetHash.equals(geometry.maskMultisetHash), "Independent geometry ignores winner ordering");
        Files.writeString(order, "6.5\t6.5\t1\n"); rejects(() -> MacCorpusGeometry.applyRetainedOrder(legacy, order), "Incomplete order rejected");
        Files.writeString(order, "6.5\t6.5\t1\n3.5\t3.5\t1\n"); rejects(() -> MacCorpusGeometry.applyRetainedOrder(legacy, order), "Duplicate label rejected");
        Files.writeString(order, "6.5\t6.5\t1\n6.5\t6.5\t2\n"); rejects(() -> MacCorpusGeometry.applyRetainedOrder(legacy, order), "Duplicate center rejected");
        rejects(() -> MacCorpusGeometry.readOutlines(payload, 15, 16), "GATP dimension mismatch rejected");
        Path trailing = root.resolve("trailing.gz");
        try (OutputStream out = new java.util.zip.GZIPOutputStream(Files.newOutputStream(trailing)); InputStream in = new GZIPInputStream(Files.newInputStream(payload))) {
            in.transferTo(out); out.write(0);
        }
        rejects(() -> MacCorpusGeometry.readOutlines(trailing, 16, 16), "Trailing GATP bytes rejected");
    }
    @SuppressWarnings("unchecked")
    static void matchingControls() throws Exception {
        MacCorpusGeometry.Geometry modern = new MacCorpusGeometry.Geometry(20, 20), legacy = new MacCorpusGeometry.Geometry(20, 20);
        modern.add(outline(5.5f, 5.5f, square(2.5f, 2.5f, 8.5f, 8.5f), 1));
        legacy.add(outline(6.5f, 5.5f, square(3.5f, 2.5f, 9.5f, 8.5f), 0));
        modern.measureMasks(); legacy.measureMasks();
        List<Object> unmatched = MacCorpusGeometry.unmatchedDiagnostics(modern, legacy, true);
        check(unmatched.size() == 1, "Moved winner must not disappear from diagnostics");
        Map<String, Object> row = (Map<String, Object>) unmatched.get(0);
        Map<String, Object> cmp = (Map<String, Object>) row.get("comparison");
        check((Long) cmp.get("intersection_pixels") == 30 && (Long) cmp.get("union_pixels") == 42, "Moved polygon intersection/union exact control");
        check(Math.abs((Double) cmp.get("per_object_iou") - 5.0 / 7) < 1e-12, "Moved polygon IoU exact control");
        check(!(Boolean) cmp.get("exact_center_match"), "Moved center must not be reported exact");
        MacCorpusGeometry.Geometry distant = new MacCorpusGeometry.Geometry(20, 20);
        distant.add(outline(16.5f, 16.5f, square(14.5f, 14.5f, 18.5f, 18.5f), 0)); distant.measureMasks();
        Map<String, Object> noOverlap = (Map<String, Object>) MacCorpusGeometry.unmatchedDiagnostics(modern, distant, true).get(0);
        check(noOverlap.get("comparison") == null, "Disjoint centers must not receive a forced correspondence");
        check(noOverlap.get("nearest_opposite_center") != null, "Disjoint cases still show nearest-center diagnostic");
        MacCorpusGeometry.Geometry empty = new MacCorpusGeometry.Geometry(20, 20); empty.measureMasks();
        Map<String, Object> noTarget = (Map<String, Object>) MacCorpusGeometry.unmatchedDiagnostics(modern, empty, true).get(0);
        check(noTarget.get("nearest_opposite_center") == null && noTarget.get("comparison") == null, "Empty counterpart is explicit");
    }
    static void predictionControls(Path root) throws Exception {
        Path prediction = root.resolve("prediction.gato");
        try (DataOutputStream out = new DataOutputStream(Files.newOutputStream(prediction))) {
            out.writeInt(0x4741544f); out.writeInt(1); out.writeInt(12); out.writeInt(12); out.writeInt(9);
            for (int p = 0; p < 144; p++) for (int c = 0; c < 9; c++)
                out.writeFloat(c == 0 ? (p == 5 * 12 + 5 ? 0.9f : p == 1 * 12 + 1 ? 0.99f : 0f) : 2f);
        }
        MacCorpusGeometry.Prediction parsed = new MacCorpusGeometry.Prediction(prediction);
        MacCorpusGeometry.Geometry modern = MacCorpusGeometry.segment(parsed, 0.5);
        check(modern.candidates == 1 && modern.outlines.size() == 1, "NMS fixed boundary must exclude edge candidate");
        check(modern.outlines.containsKey("5.5,5.5"), "ImageJ half-pixel center offset preserved");
        Path legacy = root.resolve("prediction-polygons.gz"); MacCorpusGeometry.saveOutlines(legacy, modern);
        String prefix = root.resolve("result").toString();
        ByteArrayOutputStream stdout = new ByteArrayOutputStream(); PrintStream previous = System.out;
        try { System.setOut(new PrintStream(stdout)); MacCorpusGeometry.main(new String[]{prediction.toString(), legacy.toString(), "-", prefix, "0.5"}); }
        finally { System.setOut(previous); }
        String result = Files.readString(Path.of(prefix + ".geometry.json"));
        check(result.contains("\"legacy_label_sha256\":null"), "No synthetic legacy label hashes without order");
        check(result.contains("\"strict_quantized_outlines_equal\":true"), "Identical GATP comparison");
        check(result.contains("\"foreground_iou\":1.0"), "Identical union comparison");
        check(result.contains("\"modern_object_measurements\":[{"), "Full actual per-cell measures retained even on equality");
        check(!Files.exists(Path.of(prefix + ".legacy.labels.u16be.gz")), "No unrequested legacy composite artifact");
        check(!stdout.toString().contains("modern_object_measurements"), "Stdout remains compact");
        rejects(() -> MacCorpusGeometry.main(new String[]{prediction.toString(), legacy.toString(), "-", prefix, "0.3"}), "Changed probability default rejected");
        byte[] full = Files.readAllBytes(prediction); Files.write(prediction, Arrays.copyOf(full, full.length - 1));
        rejects(() -> new MacCorpusGeometry.Prediction(prediction), "Truncated GATO rejected");
        Files.write(prediction, Arrays.copyOf(full, full.length + 1));
        rejects(() -> new MacCorpusGeometry.Prediction(prediction), "Trailing GATO rejected");
        byte[] nan = full.clone(); nan[20] = 0x7f; nan[21] = (byte) 0xc0; nan[22] = nan[23] = 0; Files.write(prediction, nan);
        rejects(() -> new MacCorpusGeometry.Prediction(prediction), "Nonfinite GATO rejected");
        check(MacCorpusGeometry.json("a\n\"\\").equals("\"a\\u000a\\\"\\\\\""), "JSON escaping exact control");
    }
    public static void main(String[] args) throws Exception {
        Path root = Files.createTempDirectory("mac-corpus-geometry-test-");
        try {
            maskControls(); orderControls(root); matchingControls(); predictionControls(root);
            System.out.println("MacCorpusGeometryTest passed " + checks + " checks");
        } finally {
            try (java.util.stream.Stream<Path> paths = Files.walk(root)) {
                for (Path path : paths.sorted(Comparator.reverseOrder()).toArray(Path[]::new)) Files.delete(path);
            }
        }
    }
}

import java.awt.Rectangle;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.*;
import java.util.*;
import java.util.zip.GZIPInputStream;
import java.util.zip.GZIPOutputStream;

import de.csbdresden.stardist.Candidates;
import ij.gui.PolygonRoi;
import ij.gui.Roi;
import ij.process.FloatPolygon;
import ij.process.ImageProcessor;
import ij.process.ShortProcessor;
import net.imglib2.img.array.ArrayImgs;

/** Validation only. Uses pinned, unchanged StarDist NMS and ImageJ rasterization.
 * Does not load a TensorFlow runtime. Legacy GATP files contain geometry, not winner
 * order: no legacy composite is constructed unless a complete retained-order TSV
 * is supplied. Independent polygon masks never claim occlusion-aware legacy parity.
 */
public final class MacCorpusGeometry {
    static final int BOUNDARY = 2;
    static final double NMS_THRESHOLD = 0.3;
    static final long MAX_VALUES = 242500000L; // 2.5 MP x 97 production channels; <1 GiB of floats
    static final long MAX_PIXELS = 2500000L; // Above the largest retained corpus image
    static final int MAX_OBJECTS = 65535;

    static final class Prediction {
        final int width, height, channels;
        final float[] probabilities, distances;
        final String sha256;
        Prediction(Path path) throws Exception {
            MessageDigest digest = digest();
            try (DataInputStream in = new DataInputStream(new BufferedInputStream(
                    new DigestInputStream(Files.newInputStream(path), digest), 65536))) {
                if (in.readInt() != 0x4741544f || in.readInt() != 1)
                    throw new IOException("Invalid GATO magic/version");
                width = in.readInt(); height = in.readInt(); channels = in.readInt();
                checkDimensions(width, height);
                if (channels < 4 || channels > 1024 || (long) width * height * channels > MAX_VALUES)
                    throw new IOException("Invalid or oversized GATO shape");
                long expected = 20L + 4L * width * height * channels;
                if (Files.size(path) != expected) throw new IOException("GATO length does not match shape");
                int pixels = width * height;
                probabilities = new float[pixels];
                distances = new float[pixels * (channels - 1)];
                for (int p = 0; p < pixels; p++) for (int c = 0; c < channels; c++) {
                    float value = in.readFloat();
                    if (!Float.isFinite(value)) throw new IOException("Nonfinite GATO value");
                    if (c == 0) {
                        if (value < 0 || value > 1) throw new IOException("Probability outside [0,1]");
                        probabilities[p] = value;
                    } else distances[(c - 1) * pixels + p] = value;
                }
                if (in.read() != -1) throw new IOException("Trailing GATO data");
            }
            sha256 = hex(digest.digest());
        }
    }

    static final class Outline {
        final float cx, cy;
        final float[] x, y;
        final PolygonRoi roi;
        final String key;
        final double perimeter, area;
        Mask mask;
        int label;
        Outline(float cx, float cy, PolygonRoi roi, int label) throws IOException {
            this(cx, cy, roi, label, roi.getFloatPolygon());
        }
        Outline(float cx, float cy, PolygonRoi roi, int label, FloatPolygon points) throws IOException {
            if (!Float.isFinite(cx) || !Float.isFinite(cy)) throw new IOException("Nonfinite center");
            this.cx = cx; this.cy = cy; this.roi = roi; this.label = label;
            key = centerKey(cx, cy);
            x = Arrays.copyOf(points.xpoints, points.npoints);
            y = Arrays.copyOf(points.ypoints, points.npoints);
            double length = 0, twiceArea = 0;
            for (int i = 0; i < x.length; i++) {
                int j = (i + 1) % x.length;
                if (!Float.isFinite(x[i]) || !Float.isFinite(y[i])) throw new IOException("Nonfinite vertex");
                length += Math.hypot((double) x[j] - x[i], (double) y[j] - y[i]);
                twiceArea += (double) x[i] * y[j] - (double) x[j] * y[i];
            }
            perimeter = length; area = Math.abs(twiceArea) / 2;
        }
    }

    static final class Geometry {
        final int width, height;
        final TreeMap<String, Outline> outlines = new TreeMap<>();
        final BitSet union;
        int candidates = -1;
        Composite composite;
        String maskMultisetHash;
        Geometry(int width, int height) throws IOException {
            checkDimensions(width, height);
            this.width = width; this.height = height; union = new BitSet(width * height);
        }
        void add(Outline outline) throws IOException {
            if (outlines.putIfAbsent(outline.key, outline) != null) throw new IOException("Duplicate winner center");
            if (outlines.size() > MAX_OBJECTS) throw new IOException("Too many objects for unique u16 labels");
        }
        void measureMasks() throws Exception {
            List<String> hashes = new ArrayList<>();
            for (Outline outline : outlines.values()) {
                outline.mask = new Mask(outline.roi, width, height);
                for (int at : outline.mask.pixels) union.set(at);
                hashes.add(outline.mask.sha256);
            }
            Collections.sort(hashes);
            MessageDigest d = digest();
            for (String hash : hashes) d.update((hash + "\n").getBytes(StandardCharsets.UTF_8));
            maskMultisetHash = hex(d.digest());
        }
    }

    /** Exact ImageJ ROI mask, clipped to the image, stored as sorted linear pixels. */
    static final class Mask {
        final int[] pixels;
        final long[] stats;
        final String sha256;
        final Rectangle bounds;
        Mask(PolygonRoi roi, int width, int height) throws Exception {
            Rectangle raw = roi.getBounds();
            long maskArea = (long) raw.width * raw.height;
            if (raw.width < 0 || raw.height < 0 || maskArea > MAX_PIXELS * 4)
                throw new IOException("Polygon mask exceeds validation resource bound");
            bounds = raw.intersection(new Rectangle(0, 0, width, height));
            if (bounds.isEmpty()) {
                pixels = new int[0]; stats = new long[8]; sha256 = hashPixelIndices(pixels, width, height); return;
            }
            ImageProcessor mask = roi.getMask();
            if (mask == null || mask.getWidth() != raw.width || mask.getHeight() != raw.height)
                throw new IOException("Unexpected ImageJ polygon mask shape");
            int count = 0;
            for (int y = bounds.y; y < bounds.y + bounds.height; y++)
                for (int x = bounds.x; x < bounds.x + bounds.width; x++)
                    if (mask.get(x - raw.x, y - raw.y) != 0) count++;
            pixels = new int[count]; int next = 0;
            stats = new long[] {0, 0, 0, 0, width, height, 0, 0};
            for (int y = bounds.y; y < bounds.y + bounds.height; y++) {
                for (int x = bounds.x; x < bounds.x + bounds.width; x++) {
                    if (mask.get(x - raw.x, y - raw.y) == 0) continue;
                    pixels[next++] = y * width + x;
                    stats[0]++; stats[1] += x; stats[2] += y;
                    if (x == 0 || x <= raw.x || mask.get(x - raw.x - 1, y - raw.y) == 0) stats[3]++;
                    if (x == width - 1 || x + 1 >= raw.x + raw.width || mask.get(x - raw.x + 1, y - raw.y) == 0) stats[3]++;
                    if (y == 0 || y <= raw.y || mask.get(x - raw.x, y - raw.y - 1) == 0) stats[3]++;
                    if (y == height - 1 || y + 1 >= raw.y + raw.height || mask.get(x - raw.x, y - raw.y + 1) == 0) stats[3]++;
                    stats[4] = Math.min(stats[4], x); stats[5] = Math.min(stats[5], y);
                    stats[6] = Math.max(stats[6], x); stats[7] = Math.max(stats[7], y);
                }
            }
            sha256 = hashPixelIndices(pixels, width, height);
        }
    }

    /** Same reverse winner overpaint and canonical raster-order hashing as CorpusNmsComparison. */
    static final class Composite {
        final short[] labels, canonical;
        final int[] mapping = new int[65536];
        final long[][] stats;
        final String labelHash, canonicalHash, measurementHash;
        final int visible;
        Composite(Geometry geometry) throws Exception {
            int width = geometry.width, height = geometry.height, count = geometry.outlines.size();
            Outline[] byLabel = new Outline[count];
            for (Outline outline : geometry.outlines.values()) {
                if (outline.label < 1 || outline.label > count || byLabel[outline.label - 1] != null)
                    throw new IOException("Incomplete or duplicate original winner label order");
                byLabel[outline.label - 1] = outline;
            }
            ShortProcessor output = new ShortProcessor(width, height);
            for (int i = count - 1; i >= 0; i--) {
                if (byLabel[i] == null) throw new IOException("Missing winner label");
                output.setColor(i + 1); output.fill(byLabel[i].roi);
            }
            labels = (short[]) output.getPixels(); canonical = new short[labels.length];
            int next = 1;
            for (int i = 0; i < labels.length; i++) {
                int old = labels[i] & 65535;
                if (old == 0) continue;
                if (mapping[old] == 0) mapping[old] = next++;
                canonical[i] = (short) mapping[old];
            }
            visible = next - 1; stats = new long[next][8];
            for (int id = 1; id < next; id++) { stats[id][4] = width; stats[id][5] = height; }
            for (int y = 0; y < height; y++) for (int x = 0; x < width; x++) {
                int at = y * width + x, id = canonical[at] & 65535;
                if (id == 0) continue;
                long[] s = stats[id]; s[0]++; s[1] += x; s[2] += y;
                if (x == 0 || canonical[at - 1] != canonical[at]) s[3]++;
                if (x == width - 1 || canonical[at + 1] != canonical[at]) s[3]++;
                if (y == 0 || canonical[at - width] != canonical[at]) s[3]++;
                if (y == height - 1 || canonical[at + width] != canonical[at]) s[3]++;
                s[4] = Math.min(s[4], x); s[5] = Math.min(s[5], y);
                s[6] = Math.max(s[6], x); s[7] = Math.max(s[7], y);
            }
            MessageDigest d = digest();
            for (int id = 1; id < next; id++)
                d.update((Arrays.toString(stats[id]) + "\n").getBytes(StandardCharsets.UTF_8));
            measurementHash = hex(d.digest()); labelHash = hashLabels(labels); canonicalHash = hashLabels(canonical);
        }
    }

    static Geometry segment(Prediction prediction, double probability) throws Exception {
        Geometry geometry = new Geometry(prediction.width, prediction.height);
        Candidates candidates = new Candidates(ArrayImgs.floats(prediction.probabilities, prediction.width, prediction.height),
                ArrayImgs.floats(prediction.distances, prediction.width, prediction.height, prediction.channels - 1),
                probability, BOUNDARY, null);
        geometry.candidates = candidates.getSorted().size(); candidates.nms(NMS_THRESHOLD);
        List<Integer> winners = candidates.getWinner();
        if (winners.size() > MAX_OBJECTS) throw new IOException("Too many winners for unique u16 labels");
        for (int i = 0; i < winners.size(); i++) {
            int winner = winners.get(i);
            FloatPolygon center = candidates.getOriginRoi(winner).getFloatPolygon();
            geometry.add(new Outline(center.xpoints[0], center.ypoints[0], candidates.getPolygonRoi(winner), i + 1));
        }
        geometry.composite = new Composite(geometry);
        geometry.measureMasks();
        return geometry;
    }

    static Geometry readOutlines(Path path, int expectedWidth, int expectedHeight) throws Exception {
        try (DataInputStream in = new DataInputStream(new BufferedInputStream(new GZIPInputStream(Files.newInputStream(path))))) {
            if (in.readInt() != 0x47415450 || in.readInt() != 1) throw new IOException("Invalid GATP magic/version");
            int width = in.readInt(), height = in.readInt(), count = in.readInt();
            if (width != expectedWidth || height != expectedHeight) throw new IOException("Legacy polygon dimensions differ");
            if (count < 0 || count > MAX_OBJECTS) throw new IOException("Invalid GATP object count");
            Geometry geometry = new Geometry(width, height);
            long vertices = 0;
            for (int i = 0; i < count; i++) {
                float cx = in.readFloat(), cy = in.readFloat(); int rays = in.readInt();
                if (rays < 3 || rays > 1024 || (vertices += rays) > 8388608L) throw new IOException("Invalid GATP ray count");
                float[] x = new float[rays], y = new float[rays];
                for (int r = 0; r < rays; r++) {
                    x[r] = in.readFloat(); y[r] = in.readFloat();
                    if (!Float.isFinite(x[r]) || !Float.isFinite(y[r])) throw new IOException("Nonfinite GATP vertex");
                }
                // Preserve archived float vertices exactly; constructing an ROI is only for rasterization.
                geometry.add(new Outline(cx, cy, new PolygonRoi(x, y, rays, Roi.POLYGON), 0, new FloatPolygon(x, y, rays)));
            }
            if (in.read() != -1) throw new IOException("Trailing GATP data");
            geometry.measureMasks(); return geometry;
        }
    }

    static void applyRetainedOrder(Geometry legacy, Path path) throws Exception {
        Set<String> seen = new HashSet<>();
        for (String line : Files.readAllLines(path, StandardCharsets.UTF_8)) {
            if (line.isBlank()) continue;
            String[] fields = line.split("\t", -1);
            if (fields.length != 3) throw new IOException("Order TSV needs center_x, center_y, label_id, no header");
            float x = Float.parseFloat(fields[0]), y = Float.parseFloat(fields[1]);
            String key = centerKey(x, y);
            Outline outline = legacy.outlines.get(key);
            if (!Float.isFinite(x) || !Float.isFinite(y) || outline == null || !seen.add(key))
                throw new IOException("Unknown, nonfinite or duplicate order center");
            outline.label = Integer.parseInt(fields[2]);
        }
        if (seen.size() != legacy.outlines.size()) throw new IOException("Order TSV does not cover every legacy polygon");
        legacy.composite = new Composite(legacy);
    }

    static Map<String, Object> measurements(Outline outline, long[] stats) {
        Map<String, Object> row = object("winning_center_x_px", outline.cx, "winning_center_y_px", outline.cy,
                "area_pixels", stats[0], "sum_x", stats[1], "sum_y", stats[2],
                "centroid_x_px", centroid(stats, 1), "centroid_y_px", centroid(stats, 2),
                "four_neighbor_perimeter_px", stats[3],
                "bbox_x_min", stats[0] > 0 ? stats[4] : null, "bbox_y_min", stats[0] > 0 ? stats[5] : null,
                "bbox_x_max_inclusive", stats[0] > 0 ? stats[6] : null, "bbox_y_max_inclusive", stats[0] > 0 ? stats[7] : null,
                "quantized_polygon_perimeter_px", outline.perimeter, "quantized_polygon_area_px2", outline.area,
                "ray_count", outline.x.length);
        return row;
    }

    static List<Object> objectMeasurements(Geometry geometry, boolean independent) {
        List<Object> rows = new ArrayList<>();
        if (!independent && geometry.composite == null) return rows;
        for (Outline outline : geometry.outlines.values()) {
            int canonicalId = geometry.composite == null ? 0 : geometry.composite.mapping[outline.label];
            long[] stats = independent ? outline.mask.stats : geometry.composite.stats[canonicalId];
            Map<String, Object> row = measurements(outline, stats);
            row.put("measurement_scope", independent ? "independent_polygon_mask_clipped_to_image" : "occlusion_aware_winner_label_mask");
            row.put("label_id", outline.label == 0 ? null : outline.label);
            row.put("canonical_label_id", geometry.composite == null ? null : canonicalId);
            if (independent) row.put("pixel_indices_sha256", outline.mask.sha256);
            rows.add(row);
        }
        return rows;
    }

    static long intersection(Mask a, Mask b) {
        if (!a.bounds.intersects(b.bounds)) return 0;
        long total = 0; int i = 0, j = 0;
        while (i < a.pixels.length && j < b.pixels.length) {
            int x = a.pixels[i], y = b.pixels[j];
            if (x == y) { total++; i++; j++; } else if (x < y) i++; else j++;
        }
        return total;
    }

    static Map<String, Object> comparison(Outline modern, Outline legacy, long intersection) {
        long ma = modern.mask.stats[0], la = legacy.mask.stats[0], union = ma + la - intersection;
        boolean sameRays = modern.x.length == legacy.x.length;
        double maxCoordinate = 0, maxVertex = 0; int changed = 0;
        if (sameRays) for (int r = 0; r < modern.x.length; r++) {
            double dx = Math.abs((double) modern.x[r] - legacy.x[r]), dy = Math.abs((double) modern.y[r] - legacy.y[r]);
            maxCoordinate = Math.max(maxCoordinate, Math.max(dx, dy)); maxVertex = Math.max(maxVertex, Math.hypot(dx, dy));
            if (dx != 0 || dy != 0) changed++;
        }
        Double mx = centroid(modern.mask.stats, 1), my = centroid(modern.mask.stats, 2);
        Double lx = centroid(legacy.mask.stats, 1), ly = centroid(legacy.mask.stats, 2);
        return object("modern_center", Arrays.asList(modern.cx, modern.cy), "legacy_center", Arrays.asList(legacy.cx, legacy.cy),
                "exact_center_match", modern.key.equals(legacy.key),
                "winning_center_distance_px", Math.hypot((double) modern.cx - legacy.cx, (double) modern.cy - legacy.cy),
                "measurement_scope", "independent_polygon_masks_clipped_to_image",
                "modern_area_pixels", ma, "legacy_area_pixels", la, "area_delta_pixels", ma - la,
                "intersection_pixels", intersection, "union_pixels", union,
                "per_object_iou", union == 0 ? 1.0 : (double) intersection / union,
                "per_object_dice", ma + la == 0 ? 1.0 : 2.0 * intersection / (ma + la),
                "different_mask_pixels", union - intersection,
                "centroid_x_delta_px", mx == null || lx == null ? null : mx - lx,
                "centroid_y_delta_px", my == null || ly == null ? null : my - ly,
                "centroid_distance_px", mx == null || lx == null ? null : Math.hypot(mx - lx, my - ly),
                "four_neighbor_perimeter_delta_px", modern.mask.stats[3] - legacy.mask.stats[3],
                "bbox_x_min_delta_px", ma == 0 || la == 0 ? null : modern.mask.stats[4] - legacy.mask.stats[4],
                "bbox_y_min_delta_px", ma == 0 || la == 0 ? null : modern.mask.stats[5] - legacy.mask.stats[5],
                "bbox_x_max_inclusive_delta_px", ma == 0 || la == 0 ? null : modern.mask.stats[6] - legacy.mask.stats[6],
                "bbox_y_max_inclusive_delta_px", ma == 0 || la == 0 ? null : modern.mask.stats[7] - legacy.mask.stats[7],
                "quantized_polygon_perimeter_delta_px", modern.perimeter - legacy.perimeter,
                "quantized_polygon_area_delta_px2", modern.area - legacy.area,
                "ray_counts_match", sameRays, "changed_vertices", sameRays ? changed : null,
                "max_abs_vertex_coordinate_delta_px", sameRays ? maxCoordinate : null,
                "max_euclidean_vertex_delta_px", sameRays ? maxVertex : null,
                "vertex_delta_scope", "same_ray_index; center movement included");
    }

    static List<Object> unmatchedDiagnostics(Geometry modern, Geometry legacy, boolean modernSide) {
        Geometry source = modernSide ? modern : legacy, target = modernSide ? legacy : modern;
        List<Object> rows = new ArrayList<>();
        for (Outline outline : source.outlines.values()) {
            if (target.outlines.containsKey(outline.key)) continue;
            Outline best = null, nearest = null; long bestIntersection = 0, bestUnion = 1; int overlapCount = 0;
            double nearestDistance = Double.POSITIVE_INFINITY;
            for (Outline other : target.outlines.values()) {
                double distance = Math.hypot((double) outline.cx - other.cx, (double) outline.cy - other.cy);
                if (distance < nearestDistance) { nearestDistance = distance; nearest = other; }
                long overlap = intersection(outline.mask, other.mask);
                if (overlap == 0) continue;
                overlapCount++;
                long union = outline.mask.stats[0] + other.mask.stats[0] - overlap;
                // Exact rational comparison, deterministic center-string order resolves ties.
                if (best == null || overlap * bestUnion > bestIntersection * union) {
                    best = other; bestIntersection = overlap; bestUnion = union;
                }
            }
            Map<String, Object> row = object("source_center", Arrays.asList(outline.cx, outline.cy),
                    "overlapping_opposite_objects", overlapCount,
                    "best_overlap_center", best == null ? null : Arrays.asList(best.cx, best.cy),
                    "best_overlap_already_has_exact_center_match", best == null ? null : source.outlines.containsKey(best.key),
                    "nearest_opposite_center", nearest == null ? null : Arrays.asList(nearest.cx, nearest.cy),
                    "nearest_center_distance_px", nearest == null ? null : nearestDistance,
                    "comparison", best == null ? null : modernSide ? comparison(outline, best, bestIntersection) : comparison(best, outline, bestIntersection),
                    "interpretation", "best-overlap diagnostic, not a forced one-to-one biological correspondence");
            rows.add(row);
        }
        return rows;
    }

    static Map<String, Object> summarize(Prediction prediction, Geometry modern, Geometry legacy, double probability, String orderHash) throws Exception {
        BitSet common = (BitSet) modern.union.clone(); common.and(legacy.union);
        BitSet all = (BitSet) modern.union.clone(); all.or(legacy.union);
        int intersection = common.cardinality(), union = all.cardinality();
        List<Object> matches = new ArrayList<>();
        int changedObjects = 0, changedVertices = 0, rayMismatch = 0;
        double maxCoordinate = 0, maxVertex = 0, maxArea = 0, maxPerimeter = 0, minIou = 1;
        for (Outline outline : modern.outlines.values()) {
            Outline other = legacy.outlines.get(outline.key);
            if (other == null) continue;
            Map<String, Object> cmp = comparison(outline, other, intersection(outline.mask, other.mask));
            matches.add(cmp);
            if (!(Boolean) cmp.get("ray_counts_match")) rayMismatch++;
            else {
                int changed = (Integer) cmp.get("changed_vertices");
                changedVertices += changed; if (changed != 0) changedObjects++;
                maxCoordinate = Math.max(maxCoordinate, (Double) cmp.get("max_abs_vertex_coordinate_delta_px"));
                maxVertex = Math.max(maxVertex, (Double) cmp.get("max_euclidean_vertex_delta_px"));
            }
            maxArea = Math.max(maxArea, Math.abs(outline.area - other.area));
            maxPerimeter = Math.max(maxPerimeter, Math.abs(outline.perimeter - other.perimeter));
            minIou = Math.min(minIou, (Double) cmp.get("per_object_iou"));
        }
        List<Object> unmatchedModern = unmatchedDiagnostics(modern, legacy, true);
        List<Object> unmatchedLegacy = unmatchedDiagnostics(modern, legacy, false);
        boolean centersEqual = unmatchedModern.isEmpty() && unmatchedLegacy.isEmpty();
        Composite mc = modern.composite, lc = legacy.composite;
        Map<String, Object> summary = object("comparison_schema_version", 1, "comparison_kind", "modern_prediction_vs_retained_legacy_geometry",
                "width", prediction.width, "height", prediction.height, "channels", prediction.channels,
                "probability_threshold", probability, "nms_threshold", NMS_THRESHOLD, "excluded_boundary", BOUNDARY,
                "modern_tensor_sha256", prediction.sha256, "legacy_tensor_comparison_available", false,
                "modern_candidates", modern.candidates, "legacy_candidates", null,
                "modern_count", modern.outlines.size(), "legacy_count", legacy.outlines.size(),
                "modern_visible_labels", mc.visible, "legacy_visible_labels", lc == null ? null : lc.visible,
                "modern_label_sha256", mc.labelHash, "modern_canonical_sha256", mc.canonicalHash, "modern_measurements_sha256", mc.measurementHash,
                "legacy_label_sha256", lc == null ? null : lc.labelHash,
                "legacy_canonical_sha256", lc == null ? null : lc.canonicalHash,
                "legacy_measurements_sha256", lc == null ? null : lc.measurementHash,
                "legacy_composite_available", lc != null,
                "legacy_composite_provenance", lc == null ? "not_reconstructed; GATP archive omits winner order" : "replayed_from_supplied_retained_order_tsv; verify_against_archived_hashes",
                "legacy_order_sha256", orderHash,
                "winner_centers_equal", centersEqual,
                "strict_quantized_outlines_equal", centersEqual && rayMismatch == 0 && changedVertices == 0,
                "matched_outline_objects", matches.size(),
                "unmatched_modern_outline_centers", unmatchedModern.size(), "unmatched_legacy_outline_centers", unmatchedLegacy.size(),
                "outline_ray_count_mismatches", rayMismatch, "outlines_with_changed_vertices", changedObjects,
                "changed_outline_vertices", changedVertices, "max_abs_vertex_coordinate_delta_px", maxCoordinate,
                "max_euclidean_vertex_delta_px", maxVertex, "max_abs_polygon_area_delta_px2", maxArea,
                "max_abs_polygon_perimeter_delta_px", maxPerimeter,
                "matched_center_min_independent_polygon_iou", matches.isEmpty() ? null : minIou,
                "outline_delta_summary_scope", "exact winning-center matches only; inspect unmatched best-overlap diagnostics separately",
                "modern_foreground_pixels", modern.union.cardinality(), "legacy_foreground_pixels", legacy.union.cardinality(),
                "foreground_intersection_pixels", intersection, "foreground_union_pixels", union,
                "different_foreground_pixels", union - intersection, "foreground_iou", union == 0 ? 1.0 : (double) intersection / union,
                "modern_foreground_sha256", hashUnion(modern.union, prediction.width * prediction.height),
                "legacy_foreground_sha256", hashUnion(legacy.union, prediction.width * prediction.height),
                "modern_independent_mask_multiset_sha256", modern.maskMultisetHash,
                "legacy_independent_mask_multiset_sha256", legacy.maskMultisetHash,
                "independent_polygon_masks_equal_ignoring_ids_and_centers", modern.maskMultisetHash.equals(legacy.maskMultisetHash),
                "measurement_fields", "area,sum_x,sum_y,4_neighbor_perimeter,x_min,y_min,x_max,y_max; pixel centroids +0.5; no calibration",
                "mask_hash_encoding", "per polygon: big-endian int32 width,height,count,then sorted linear pixel indices; multiset: sorted hex hashes with newline; foreground: raster-order u8 0/1",
                "modern_object_measurements", objectMeasurements(modern, false),
                "legacy_object_measurements", objectMeasurements(legacy, false),
                "modern_independent_polygon_measurements", objectMeasurements(modern, true),
                "legacy_independent_polygon_measurements", objectMeasurements(legacy, true),
                "matched_center_comparisons", matches,
                "unmatched_modern_best_overlap", unmatchedModern, "unmatched_legacy_best_overlap", unmatchedLegacy);
        if (lc != null) {
            int labelDiff = 0, canonicalDiff = 0;
            for (int p = 0; p < mc.labels.length; p++) {
                if (mc.labels[p] != lc.labels[p]) labelDiff++;
                if (mc.canonical[p] != lc.canonical[p]) canonicalDiff++;
            }
            summary.put("different_label_pixels", labelDiff); summary.put("different_canonical_label_pixels", canonicalDiff);
            summary.put("pixel_measurements_equal", mc.measurementHash.equals(lc.measurementHash));
        } else {
            summary.put("different_label_pixels", null); summary.put("different_canonical_label_pixels", null); summary.put("pixel_measurements_equal", null);
        }
        return summary;
    }

    interface Writer { void write(OutputStream out) throws Exception; }
    static void save(Path target, Writer writer) throws Exception {
        Path absolute = target.toAbsolutePath(); Files.createDirectories(absolute.getParent());
        Path temp = Files.createTempFile(absolute.getParent(), absolute.getFileName().toString(), ".tmp");
        try {
            try (OutputStream out = new BufferedOutputStream(Files.newOutputStream(temp))) { writer.write(out); }
            try (java.nio.channels.FileChannel channel = java.nio.channels.FileChannel.open(temp, StandardOpenOption.WRITE)) { channel.force(true); }
            Files.move(temp, absolute, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
        } finally { Files.deleteIfExists(temp); }
    }
    static void saveOutlines(Path path, Geometry geometry) throws Exception {
        save(path, stream -> {
            try (DataOutputStream out = new DataOutputStream(new GZIPOutputStream(stream))) {
                out.writeInt(0x47415450); out.writeInt(1); out.writeInt(geometry.width); out.writeInt(geometry.height); out.writeInt(geometry.outlines.size());
                for (Outline outline : geometry.outlines.values()) {
                    out.writeFloat(outline.cx); out.writeFloat(outline.cy); out.writeInt(outline.x.length);
                    for (int r = 0; r < outline.x.length; r++) { out.writeFloat(outline.x[r]); out.writeFloat(outline.y[r]); }
                }
            }
        });
    }
    static void saveLabels(Path path, short[] labels) throws Exception {
        save(path, stream -> { try (DataOutputStream out = new DataOutputStream(new GZIPOutputStream(stream))) {
            for (short label : labels) out.writeShort(label);
        }});
    }
    static void saveUnion(Path path, BitSet union, int count) throws Exception {
        save(path, stream -> { try (GZIPOutputStream out = new GZIPOutputStream(stream)) {
            for (int p = 0; p < count; p++) out.write(union.get(p) ? 1 : 0);
        }});
    }
    static void checkDimensions(int width, int height) throws IOException {
        if (width < 1 || height < 1 || (long) width * height > MAX_PIXELS) throw new IOException("Invalid or oversized dimensions");
    }
    static String centerKey(float x, float y) { return Float.toString(x) + "," + Float.toString(y); }
    static Double centroid(long[] stats, int axis) { return stats[0] == 0 ? null : (double) stats[axis] / stats[0] + 0.5; }
    static MessageDigest digest() throws NoSuchAlgorithmException { return MessageDigest.getInstance("SHA-256"); }
    static String hex(byte[] bytes) { StringBuilder out = new StringBuilder(); for (byte b : bytes) out.append(String.format(Locale.ROOT, "%02x", b & 255)); return out.toString(); }
    static void hashInt(MessageDigest d, int v) { d.update((byte) (v >>> 24)); d.update((byte) (v >>> 16)); d.update((byte) (v >>> 8)); d.update((byte) v); }
    static String hashPixelIndices(int[] pixels, int width, int height) throws Exception {
        MessageDigest d = digest(); hashInt(d, width); hashInt(d, height); hashInt(d, pixels.length); for (int p : pixels) hashInt(d, p); return hex(d.digest());
    }
    static String hashLabels(short[] labels) throws Exception { MessageDigest d = digest(); for (short label : labels) { d.update((byte) (label >>> 8)); d.update((byte) label); } return hex(d.digest()); }
    static String hashUnion(BitSet union, int count) throws Exception { MessageDigest d = digest(); for (int p = 0; p < count; p++) d.update((byte) (union.get(p) ? 1 : 0)); return hex(d.digest()); }
    static String hashFile(Path path) throws Exception {
        MessageDigest d = digest(); try (InputStream in = Files.newInputStream(path)) { byte[] buffer = new byte[65536]; int n; while ((n = in.read(buffer)) != -1) d.update(buffer, 0, n); } return hex(d.digest());
    }
    static Map<String, Object> object(Object... pairs) {
        Map<String, Object> map = new LinkedHashMap<>(); for (int i = 0; i < pairs.length; i += 2) map.put((String) pairs[i], pairs[i + 1]); return map;
    }
    static String json(Object value) {
        if (value == null) return "null";
        if (value instanceof String) {
            StringBuilder out = new StringBuilder("\"");
            for (char c : ((String) value).toCharArray()) {
                if (c == '\\' || c == '"') out.append('\\').append(c);
                else if (c < 32) out.append(String.format(Locale.ROOT, "\\u%04x", (int) c));
                else out.append(c);
            }
            return out.append('"').toString();
        }
        if (value instanceof Map) {
            StringBuilder out = new StringBuilder("{"); boolean first = true;
            for (Object raw : ((Map<?, ?>) value).entrySet()) {
                Map.Entry<?, ?> entry = (Map.Entry<?, ?>) raw;
                if (!first) out.append(','); first = false;
                out.append(json(entry.getKey())).append(':').append(json(entry.getValue()));
            }
            return out.append('}').toString();
        }
        if (value instanceof Iterable) {
            StringBuilder out = new StringBuilder("["); boolean first = true;
            for (Object item : (Iterable<?>) value) { if (!first) out.append(','); first = false; out.append(json(item)); }
            return out.append(']').toString();
        }
        if (value instanceof Double && !Double.isFinite((Double) value) || value instanceof Float && !Float.isFinite((Float) value))
            throw new IllegalArgumentException("Nonfinite JSON number");
        if (value instanceof Number || value instanceof Boolean) return value.toString();
        throw new IllegalArgumentException("Unsupported JSON type: " + value.getClass());
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 5) throw new IllegalArgumentException("modern.gato legacy.polygons.gz legacy-order.tsv|- output-prefix probability");
        double probability = Double.parseDouble(args[4]);
        if (probability != 0.5 && probability != 0.4) throw new IllegalArgumentException("Only GAT defaults 0.5/0.4 are permitted");
        Prediction prediction = new Prediction(Path.of(args[0]));
        Geometry modern = segment(prediction, probability);
        Geometry legacy = readOutlines(Path.of(args[1]), prediction.width, prediction.height);
        String orderHash = null;
        if (!args[2].equals("-")) { applyRetainedOrder(legacy, Path.of(args[2])); orderHash = hashFile(Path.of(args[2])); }
        Map<String, Object> summary = summarize(prediction, modern, legacy, probability, orderHash);
        String prefix = args[3];
        Path polygons = Path.of(prefix + ".modern.polygons.gz"); saveOutlines(polygons, modern);
        saveLabels(Path.of(prefix + ".modern.labels.u16be.gz"), modern.composite.labels);
        saveLabels(Path.of(prefix + ".modern.canonical.u16be.gz"), modern.composite.canonical);
        saveUnion(Path.of(prefix + ".modern.foreground.u8.gz"), modern.union, prediction.width * prediction.height);
        saveUnion(Path.of(prefix + ".legacy.foreground.u8.gz"), legacy.union, prediction.width * prediction.height);
        if (legacy.composite != null) {
            saveLabels(Path.of(prefix + ".legacy.labels.u16be.gz"), legacy.composite.labels);
            saveLabels(Path.of(prefix + ".legacy.canonical.u16be.gz"), legacy.composite.canonical);
        }
        summary.put("modern_polygon_artifact_sha256", hashFile(polygons));
        summary.put("legacy_polygon_artifact_sha256", hashFile(Path.of(args[1])));
        Path geometry = Path.of(prefix + ".geometry.json");
        byte[] result = (json(summary) + "\n").getBytes(StandardCharsets.UTF_8);
        save(geometry, out -> out.write(result));
        Map<String, Object> compact = new LinkedHashMap<>(summary);
        for (String key : Arrays.asList("modern_object_measurements", "legacy_object_measurements", "modern_independent_polygon_measurements",
                "legacy_independent_polygon_measurements", "matched_center_comparisons", "unmatched_modern_best_overlap", "unmatched_legacy_best_overlap")) compact.remove(key);
        compact.put("geometry_file", geometry.getFileName().toString()); compact.put("geometry_file_sha256", hashFile(geometry));
        System.out.println(json(compact));
    }
}

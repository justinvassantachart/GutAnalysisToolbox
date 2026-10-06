import java.io.BufferedInputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.BufferedOutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.zip.GZIPOutputStream;

import de.csbdresden.stardist.Candidates;
import ij.process.FloatPolygon;
import ij.process.ShortProcessor;
import net.imglib2.img.array.ArrayImgs;

/** Validation only: extract the fixed public moved-center diagnostic with pinned Fiji NMS.
 * Shape and threshold are fixed intentionally; this never alters production inference. */
public final class MovedCenterNms {
    public static void main(String[] args) throws Exception {
        if (args.length != 3) throw new IllegalArgumentException("prediction.gato output-prefix probability-threshold");
        final int width, height, channels;
        final float[] probabilities, distances;
        try (DataInputStream input = new DataInputStream(new BufferedInputStream(Files.newInputStream(Path.of(args[0]))))) {
            if (input.readInt() != 0x4741544f || input.readInt() != 1) throw new AssertionError("Invalid GATO header");
            width = input.readInt(); height = input.readInt(); channels = input.readInt();
            if (width != 760 || height != 1024 || channels != 97) throw new AssertionError("Unexpected fixture shape");
            int pixels = width * height;
            probabilities = new float[pixels]; distances = new float[pixels * (channels - 1)];
            for (int p = 0; p < pixels; p++) {
                for (int c = 0; c < channels; c++) {
                    float value = input.readFloat();
                    if (!Float.isFinite(value)) throw new AssertionError("Non-finite prediction");
                    if (c == 0) {
                        if (value < 0 || value > 1) throw new AssertionError("Probability outside [0,1]");
                        probabilities[p] = value;
                    } else distances[(c - 1) * pixels + p] = value;
                }
            }
            if (input.read() != -1) throw new AssertionError("Trailing GATO data");
        }
        final double threshold = Double.parseDouble(args[2]);
        if (threshold != 0.5) throw new AssertionError("Unexpected fixture threshold");
        Candidates candidates = new Candidates(ArrayImgs.floats(probabilities, width, height),
                ArrayImgs.floats(distances, width, height, channels - 1), threshold, 2, null);
        int candidateCount = candidates.getSorted().size();
        candidates.nms(0.3);
        List<Integer> winners = candidates.getWinner();
        ShortProcessor output = new ShortProcessor(width, height);
        // Same reverse traversal, labels, and ImageJ rasterizer as StarDist2DBase.
        for (int i = winners.size() - 1; i >= 0; i--) {
            output.setColor(1 + i % 65535);
            output.fill(candidates.getPolygonRoi(winners.get(i)));
        }
        String prefix = args[1];
        try (DataOutputStream stream = new DataOutputStream(new BufferedOutputStream(Files.newOutputStream(Path.of(prefix + ".probability.f32be"))))) {
            for (float value : probabilities) stream.writeFloat(value);
        }
        try (DataOutputStream stream = new DataOutputStream(new BufferedOutputStream(Files.newOutputStream(Path.of(prefix + ".labels.u16be"))))) {
            for (short value : (short[]) output.getPixels()) stream.writeShort(value);
        }
        StringBuilder summary = new StringBuilder("{\"shape\":[" + width + "," + height + "," + channels
                + "],\"probability_threshold\":" + threshold + ",\"nms_threshold\":0.3,\"boundary\":2,\"candidates\":"
                + candidateCount + ",\"count\":" + winners.size() + ",\"winner_centers\":[");
        for (int i = 0; i < winners.size(); i++) {
            if (i != 0) summary.append(',');
            FloatPolygon point = candidates.getOriginRoi(winners.get(i)).getFloatPolygon();
            summary.append('[').append(point.xpoints[0]).append(',').append(point.ypoints[0]).append(']');
        }
        Files.writeString(Path.of(prefix + ".nms.json"), summary.append("]}\n").toString(), StandardCharsets.UTF_8);
        try (DataOutputStream stream = new DataOutputStream(new GZIPOutputStream(Files.newOutputStream(Path.of(prefix + ".polygons.gz"))))) {
            stream.writeInt(0x47415450); stream.writeInt(1);
            stream.writeInt(width); stream.writeInt(height); stream.writeInt(winners.size());
            for (int winner : winners) {
                FloatPolygon center = candidates.getOriginRoi(winner).getFloatPolygon();
                FloatPolygon polygon = candidates.getPolygonRoi(winner).getFloatPolygon();
                stream.writeFloat(center.xpoints[0]); stream.writeFloat(center.ypoints[0]);
                stream.writeInt(polygon.npoints);
                for (int i = 0; i < polygon.npoints; i++) {
                    stream.writeFloat(polygon.xpoints[i]); stream.writeFloat(polygon.ypoints[i]);
                }
            }
        }
    }
}

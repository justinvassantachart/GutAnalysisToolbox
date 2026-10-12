package Features.Macros;

import ij.gui.Roi;
import ij.plugin.frame.RoiManager;
import ij.process.FloatPolygon;
import java.awt.GraphicsEnvironment;
import java.io.DataOutputStream;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import net.imagej.Dataset;
import net.imagej.DatasetService;
import net.imagej.axis.Axes;
import net.imagej.axis.AxisType;
import net.imagej.axis.DefaultLinearAxis;
import net.imglib2.RandomAccess;
import net.imglib2.type.numeric.RealType;
import org.scijava.Context;
import org.scijava.command.CommandModule;
import org.scijava.command.CommandService;

/** Real original StarDist2DNMS vs candidate adapter; no model/inference or mocks.
 * Run only in a disposable AWT JVM. This does not invoke whole legacy macros.
 */
public final class LegacyMacroNmsProbe {
    private static final double[] PROBABILITIES = {0, .3, .5, .8, 1};
    private static final double[] OVERLAPS = {0, .3, .7, 1};
    private static final String[] OUTPUTS = {"Both", "Label Image", "ROI Manager"};
    private static final String[] POSITIONS = {"Automatic", "Stack", "Hyperstack"};
    private static final Map<String, Object> report = new LinkedHashMap<>();
    private static final List<Object> cases = new ArrayList<>();

    public static void main(String[] args) throws Exception {
        if (args.length != 1) throw new IllegalArgumentException("New empty output directory required");
        Path output = Path.of(args[0]);
        Files.createDirectory(output);
        report.put("schema_version", 1);
        report.put("scope", "original-nms-vs-adapter-postprocessing-only");
        report.put("model_execution", false);
        report.put("whole_macro_execution", false);
        report.put("source_revision", "f2098636d5f42f73c3e724286af0b212fe3ea5c0");
        report.put("java_version", System.getProperty("java.version"));
        report.put("os", System.getProperty("os.name"));
        report.put("arch", System.getProperty("os.arch"));
        report.put("cases", cases);
        report.put("status", "RUNNING");
        checkpoint(output);
        Context context = null;
        RoiManager manager = null;
        int exit = 2;
        try {
            if (GraphicsEnvironment.isHeadless()) throw new IllegalStateException("AWT required for actual ROI Manager");
            if (RoiManager.getInstance2() != null) throw new IllegalStateException("Disposable JVM must have no existing ROI Manager");
            manager = new RoiManager();
            if (RoiManager.getInstance2() != manager) throw new IllegalStateException("Probe does not own the actual global ROI Manager");
            context = new Context(CommandService.class, DatasetService.class, org.scijava.ui.UIService.class,
                    org.scijava.app.StatusService.class, net.imagej.lut.LUTService.class);
            CommandService commands = context.service(CommandService.class);
            DatasetService datasets = context.service(DatasetService.class);
            Class<?> original = Class.forName("de.csbdresden.stardist.StarDist2DNMS");
            report.put("original_class", provenance(original));
            report.put("adapter_class", provenance(LegacyMacroStarDist.class));
            for (int shape = 0; shape < 2; shape++) {
                int width = shape == 0 ? 33 : 32, height = shape == 0 ? 29 : 30;
                float[][] tensor = tensor(width, height);
                for (int dimensions : new int[] {2, 4})
                    for (double probability : PROBABILITIES)
                        for (double overlap : OVERLAPS)
                            for (String type : OUTPUTS)
                                for (String position : POSITIONS) {
                                    Map<String, Object> row = runCase(datasets, commands, manager, width, height,
                                            dimensions, tensor, probability, overlap, type, position);
                                    cases.add(row);
                                    if (!Boolean.TRUE.equals(row.get("pass"))) {
                                        report.put("status", "FAIL_POSTPROCESSING_SCOPE");
                                        checkpoint(output);
                                        throw new AssertionError("Paired mismatch: " + row.get("id"));
                                    }
                                }
                checkpoint(output);
            }
            report.put("status", "PASS_POSTPROCESSING_SCOPE");
            report.put("case_count", cases.size());
            exit = 0;
        } catch (Throwable failure) {
            if (!String.valueOf(report.get("status")).startsWith("FAIL"))
                report.put("status", cases.isEmpty() ? "BLOCKED_SETUP" : "ERROR_INCOMPLETE");
            report.put("error", failure.toString());
            failure.printStackTrace();
        } finally {
            checkpoint(output);
            if (manager != null) manager.close();
            if (context != null) context.dispose();
        }
        // AWT event threads must not keep this disposable validation JVM alive.
        System.exit(exit);
    }

    private static Map<String, Object> runCase(DatasetService datasets, CommandService commands,
            RoiManager manager, int width, int height, int dimensions, float[][] values,
            double probability, double overlap, String type, String position) throws Exception {
        Dataset input = datasets.create(dimensions == 2 ? new long[] {width, height}
                : new long[] {width, height, 1, 1}, "Input",
                dimensions == 2 ? new AxisType[] {Axes.X, Axes.Y}
                : new AxisType[] {Axes.X, Axes.Y, Axes.CHANNEL, Axes.TIME}, 16, false, false);
        input.setAxis(new DefaultLinearAxis(Axes.X, "um", .568, 1.2), 0);
        input.setAxis(new DefaultLinearAxis(Axes.Y, "um", .713, -2.1), 1);
        Dataset prob = planeDataset(datasets, input, width, height, values, true);
        Dataset dist = planeDataset(datasets, input, width, height, values, false);
        String probBefore = datasetDigest(prob), distBefore = datasetDigest(dist);
        Map<String, Object> parameters = new LinkedHashMap<>();
        parameters.put("prob", prob); parameters.put("dist", dist);
        parameters.put("probThresh", probability); parameters.put("nmsThresh", overlap);
        parameters.put("outputType", type); parameters.put("excludeBoundary", 2);
        parameters.put("roiPosition", position.equals("Automatic") ? (dimensions > 3 ? "Hyperstack" : "Stack") : position);
        parameters.put("verbose", false);
        seedManager(manager);
        CommandModule legacy = commands.run("de.csbdresden.stardist.StarDist2DNMS", false, parameters).get();
        if (legacy.isCanceled()) throw new IllegalStateException("Original NMS canceled: " + legacy.getCancelReason());
        Map<String, Object> expected = snapshot((Dataset) legacy.getOutput("label"), manager);
        boolean inputsUnchanged = probBefore.equals(datasetDigest(prob)) && distBefore.equals(datasetDigest(dist));

        seedManager(manager);
        LegacyMacroStarDist adapter = new LegacyMacroStarDist();
        adapter.commands = commands; adapter.datasets = datasets; adapter.input = input;
        adapter.probThresh = probability; adapter.nmsThresh = overlap;
        adapter.outputType = type; adapter.roiPosition = position;
        adapter.excludeBoundary = 2; adapter.showProbAndDist = true;
        adapter.runNativeNms(width, height, values);
        Map<String, Object> actual = snapshot(adapter.label, manager);
        boolean auxiliaryMatch = dimensions == 2 ? datasetDigest(adapter.prob).equals(probBefore)
                && datasetDigest(adapter.dist).equals(distBefore) : adapter.prob == null && adapter.dist == null;
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("id", width + "x" + height + "-d" + dimensions + "-p" + probability
                + "-n" + overlap + "-" + type + "-" + position);
        row.put("fixture", "deterministic-synthetic-8-ray-peaks-v1");
        row.put("shape", Arrays.asList(width, height, 9));
        row.put("input_dimensions", dimensions);
        row.put("probability", probability); row.put("overlap", overlap);
        row.put("output_type", type); row.put("roi_position", position);
        row.put("probability_sha256", probBefore); row.put("distance_sha256", distBefore);
        row.put("original", expected); row.put("adapter", actual);
        row.put("inputs_unchanged", inputsUnchanged);
        row.put("auxiliary_pixels_match", auxiliaryMatch);
        row.put("pass", expected.equals(actual) && inputsUnchanged && auxiliaryMatch);
        return row;
    }

    private static void seedManager(RoiManager manager) {
        if (RoiManager.getInstance2() != manager) throw new IllegalStateException("Original command replaced the global ROI Manager");
        manager.reset();
        Roi sentinel = new Roi(1, 2, 2, 3);
        sentinel.setName("existing-roi-sentinel"); sentinel.setPosition(7);
        manager.addRoi(sentinel);
    }

    private static float[][] tensor(int width, int height) {
        float[][] result = new float[9][width * height];
        for (int ray = 1; ray < result.length; ray++) Arrays.fill(result[ray], 3.25f + ray * .125f);
        // Exact threshold values, adjacent overlap, score ties, boundary exclusion,
        // and a distant object make a nonempty default and high-threshold empty control.
        int[][] points = {{1, 1}, {8, 9}, {10, 9}, {21, 19}, {25, 7}, {17, 23}};
        float[] scores = {1, .8f, .8f, .5f, .3f, .93f};
        for (int i = 0; i < points.length; i++) result[0][points[i][1] * width + points[i][0]] = scores[i];
        return result;
    }

    private static Dataset planeDataset(DatasetService service, Dataset input, int w, int h, float[][] values, boolean probability) {
        boolean time = input.dimensionIndex(Axes.TIME) >= 0;
        long[] shape = probability ? (time ? new long[] {w, h, 1} : new long[] {w, h})
                : (time ? new long[] {w, h, values.length - 1, 1} : new long[] {w, h, values.length - 1});
        AxisType[] axes = probability ? (time ? new AxisType[] {Axes.X, Axes.Y, Axes.TIME} : new AxisType[] {Axes.X, Axes.Y})
                : (time ? new AxisType[] {Axes.X, Axes.Y, Axes.CHANNEL, Axes.TIME} : new AxisType[] {Axes.X, Axes.Y, Axes.CHANNEL});
        Dataset data = service.create(shape, probability ? "Probability/Score Image" : "Distance Image", axes, 32, true, true);
        // Original StarDist splitPrediction creates fresh uncalibrated axes.
        // Deliberately do not transfer the calibrated input axes here.
        RandomAccess<? extends RealType<?>> pixels = data.getImgPlus().randomAccess();
        for (int c = probability ? 0 : 1; c < (probability ? 1 : values.length); c++) {
            if (!probability) pixels.setPosition(c - 1, 2);
            for (int y = 0, p = 0; y < h; y++) {
                pixels.setPosition(y, 1);
                for (int x = 0; x < w; x++, p++) {
                    pixels.setPosition(x, 0); pixels.get().setReal(values[c][p]);
                }
            }
        }
        return data;
    }

    private static Map<String, Object> snapshot(Dataset label, RoiManager manager) throws Exception {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("label_present", label != null);
        if (label != null) {
            List<Object> axes = new ArrayList<>(), shape = new ArrayList<>();
            for (int d = 0; d < label.numDimensions(); d++) {
                shape.add(label.dimension(d));
                axes.add(Arrays.asList(label.axis(d).type().getLabel(), label.axis(d).unit(),
                        label.axis(d).calibratedValue(0), label.axis(d).calibratedValue(1)));
            }
            result.put("label_shape", shape); result.put("label_axes", axes);
            result.put("label_dtype", label.getType().getClass().getName());
            result.put("label_name", label.getName());
            result.put("label_pixels_sha256", datasetDigest(label));
        }
        List<Object> rois = new ArrayList<>();
        for (Roi roi : manager.getRoisAsArray()) {
            FloatPolygon polygon = roi.getFloatPolygon();
            List<Object> points = new ArrayList<>();
            for (int p = 0; p < polygon.npoints; p++) points.add(Arrays.asList(polygon.xpoints[p], polygon.ypoints[p]));
            rois.add(Arrays.asList(roi.getName(), roi.getType(), roi.getPosition(), roi.getCPosition(),
                    roi.getZPosition(), roi.getTPosition(), points));
        }
        result.put("rois_in_manager_order", rois);
        result.put("roi_count_including_existing_sentinel", rois.size());
        return result;
    }

    private static String datasetDigest(Dataset dataset) throws Exception {
        if (dataset == null) return "null";
        ByteArrayOutputStream raw = new ByteArrayOutputStream();
        DataOutputStream out = new DataOutputStream(raw);
        for (RealType<?> value : dataset.getImgPlus()) out.writeFloat(value.getRealFloat());
        return digest(raw.toByteArray());
    }

    private static Map<String, Object> provenance(Class<?> type) throws Exception {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("name", type.getName());
        result.put("code_source", type.getProtectionDomain().getCodeSource().getLocation().toString());
        try (java.io.InputStream in = type.getResourceAsStream("/" + type.getName().replace('.', '/') + ".class")) {
            result.put("class_sha256", digest(in.readAllBytes()));
        }
        return result;
    }

    private static String digest(byte[] data) throws Exception {
        StringBuilder result = new StringBuilder();
        for (byte b : MessageDigest.getInstance("SHA-256").digest(data)) result.append(String.format("%02x", b & 255));
        return result.toString();
    }

    private static void checkpoint(Path directory) throws Exception {
        Files.writeString(directory.resolve("report.json"), json(report) + "\n", StandardCharsets.UTF_8);
    }

    private static String json(Object object) {
        if (object == null) return "null";
        if (object instanceof Number || object instanceof Boolean) return object.toString();
        if (object instanceof Map) {
            List<String> members = new ArrayList<>();
            for (Map.Entry<?, ?> entry : ((Map<?, ?>) object).entrySet()) members.add(json(entry.getKey()) + ":" + json(entry.getValue()));
            return "{" + String.join(",", members) + "}";
        }
        if (object instanceof Iterable) {
            List<String> values = new ArrayList<>();
            for (Object value : (Iterable<?>) object) values.add(json(value));
            return "[" + String.join(",", values) + "]";
        }
        return "\"" + object.toString().replace("\\", "\\\\").replace("\"", "\\\"")
                .replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t") + "\"";
    }
}

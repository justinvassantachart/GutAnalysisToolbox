package Features.Macros;

import Features.Inference.InferenceBackend;
import Features.Inference.NativeInferenceClient;
import ij.IJ;
import java.io.File;
import java.io.IOException;
import java.util.LinkedHashMap;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ExecutionException;
import net.imagej.Dataset;
import net.imagej.DatasetService;
import net.imagej.ImgPlus;
import net.imagej.axis.Axes;
import net.imagej.axis.AxisType;
import net.imglib2.RandomAccess;
import net.imglib2.RandomAccessibleInterval;
import net.imglib2.img.ImgView;
import net.imglib2.img.array.ArrayImgs;
import net.imglib2.img.array.ArrayImgFactory;
import net.imglib2.type.numeric.real.FloatType;
import net.imglib2.view.Views;
import net.imglib2.type.numeric.RealType;
import org.scijava.ItemIO;
import org.scijava.command.Command;
import org.scijava.command.CommandModule;
import org.scijava.command.CommandService;
import org.scijava.plugin.Parameter;
import org.scijava.plugin.Plugin;

/**
 * Compatibility boundary for the preserved legacy macros, not a Java workflow.
 * The macros keep every preprocessing/postprocessing operation and UI option.
 * Only TF inference moves to an isolated native worker. The original StarDist
 * command still owns NMS, labels, ROI Manager export and the output display.
 */
@Plugin(type = Command.class, headless = true)
public final class LegacyMacroStarDist implements Command {
    @Parameter Dataset input;
    @Parameter String modelChoice = "Model (.zip) from File";
    @Parameter boolean normalizeInput = true;
    @Parameter double percentileBottom = 1.0;
    @Parameter double percentileTop = 99.8;
    @Parameter double probThresh = 0.5;
    @Parameter double nmsThresh = 0.3;
    @Parameter String outputType = "Both";
    @Parameter File modelFile;
    @Parameter int nTiles = 1;
    @Parameter int excludeBoundary = 2;
    @Parameter String roiPosition = "Automatic";
    @Parameter boolean verbose = false;
    @Parameter boolean showCsbdeepProgress = false;
    @Parameter boolean showProbAndDist = false;
    @Parameter CommandService commands;
    @Parameter DatasetService datasets;
    @Parameter(type = ItemIO.OUTPUT) Dataset label;
    @Parameter(type = ItemIO.OUTPUT, required = false) Dataset prob;
    @Parameter(type = ItemIO.OUTPUT, required = false) Dataset dist;

    @Override public void run() {
        label = null; prob = null; dist = null;
        try {
            if (!InferenceBackend.useNativeWorker()) {
                // Same original command, arguments and module outputs on legacy
                // hosts. This branch must never load TF1 on Apple Silicon.
                CommandModule legacy = commands.run("de.csbdresden.stardist.StarDist2D", false,
                        legacyArguments()).get();
                copyOutputs(legacy);
                return;
            }
            validateNativeParameters();
            float[] pixels = inputPixels(input);
            NativeInferenceClient.Prediction prediction = NativeInferenceClient.predict(
                    IJ.getDirectory("imagej"), modelFile, (int) input.dimension(0),
                    (int) input.dimension(1), pixels, nTiles);
            runNativeNms(prediction.width, prediction.height, prediction.planes);
        } catch (InterruptedException error) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Legacy macro StarDist was interrupted.", error);
        } catch (IOException | ExecutionException error) {
            throw new IllegalStateException("Legacy macro StarDist failed: " + error.getMessage(), error);
        }
    }

    void validateNativeParameters() {
        if (!"Model (.zip) from File".equals(modelChoice) || !normalizeInput
                || percentileBottom != 1.0 || percentileTop != 99.8)
            throw new IllegalArgumentException("MacroFork supports the legacy macros' file models and 1.0/99.8 percentile normalization. No alternative is substituted.");
        if (modelFile == null || !modelFile.isFile())
            throw new IllegalArgumentException("The selected StarDist model ZIP is missing: " + modelFile);
        if (!Double.isFinite(probThresh) || !Double.isFinite(nmsThresh)
                || probThresh < 0 || probThresh > 1 || nmsThresh < 0 || nmsThresh > 1
                || nTiles < 1 || excludeBoundary < 0)
            throw new IllegalArgumentException("Invalid StarDist threshold, tile count or boundary exclusion.");
        if (!"Both".equals(outputType) && !"Label Image".equals(outputType)
                && !"ROI Manager".equals(outputType))
            throw new IllegalArgumentException("Unsupported StarDist output type: " + outputType);
        if (!"Automatic".equals(roiPosition) && !"Stack".equals(roiPosition)
                && !"Hyperstack".equals(roiPosition))
            throw new IllegalArgumentException("Unsupported StarDist ROI position: " + roiPosition);
        if (showCsbdeepProgress)
            throw new IllegalArgumentException("The separate native worker cannot show the legacy CSBDeep progress dialog. The GAT macros pass false.");
    }

    static float[] inputPixels(Dataset source) {
        if (source == null || source.isRGBMerged() || source.numDimensions() < 2
                || source.axis(0).type() != Axes.X || source.axis(1).type() != Axes.Y)
            throw new IllegalArgumentException("MacroFork StarDist needs a single 2D grayscale channel with X/Y axes.");
        boolean channel = source.dimensionIndex(Axes.CHANNEL) >= 0;
        boolean time = source.dimensionIndex(Axes.TIME) >= 0;
        if (source.numDimensions() != 2 + (channel ? 1 : 0) + (time ? 1 : 0))
            throw new IllegalArgumentException("Original StarDist2D supports only X/Y and optional channel/time axes, not Z or duplicate axes.");
        for (int d = 2; d < source.numDimensions(); d++)
            if (source.dimension(d) != 1)
                throw new IllegalArgumentException("The legacy macro must select/project a single grayscale plane before StarDist.");
        long width = source.dimension(0), height = source.dimension(1);
        if (width < 1 || height < 1 || width > Integer.MAX_VALUE || height > Integer.MAX_VALUE
                || width * height > Integer.MAX_VALUE - 8L)
            throw new IllegalArgumentException("StarDist input dimensions exceed Java array limits.");
        float[] pixels = new float[(int) (width * height)];
        RandomAccess<? extends RealType<?>> access = source.getImgPlus().randomAccess();
        for (int y = 0, i = 0; y < height; y++) {
            access.setPosition(y, 1);
            for (int x = 0; x < width; x++, i++) {
                access.setPosition(x, 0);
                float value = access.get().getRealFloat();
                if (!Float.isFinite(value)) throw new IllegalArgumentException("StarDist input contains non-finite pixels.");
                pixels[i] = value;
            }
        }
        return pixels;
    }

    /** Also used by no-model tests of the actual legacy NMS/output contract. */
    void runNativeNms(int width, int height, float[][] planes) throws InterruptedException, ExecutionException {
        label = null; prob = null; dist = null;
        if (planes == null || planes.length < 4) throw new IllegalArgumentException("Missing probability/ray planes.");
        Dataset[] predictions = predictionDatasets(width, height, planes);
        Dataset probability = predictions[0], distances = predictions[1];
        CommandModule nms = commands.run("de.csbdresden.stardist.StarDist2DNMS", false,
                nmsArguments(probability, distances)).get();
        label = (Dataset) nms.getOutput("label");
        if (!"ROI Manager".equals(outputType) && (label == null
                || label.dimension(0) != width || label.dimension(1) != height))
            throw new IllegalStateException("Legacy StarDist NMS did not return the requested label image.");
        // Command From Macro displays these declared module outputs, just as it
        // does for original StarDist2D. Never guess from the current image.
        if (showProbAndDist && input.dimensionIndex(Axes.TIME) < 0) { prob = probability; dist = distances; }
    }

    Dataset[] predictionDatasets(int width, int height, float[][] planes) {
        if (width < 1 || height < 1 || planes == null || planes.length < 4)
            throw new IllegalArgumentException("Invalid StarDist prediction dimensions.");
        List<RandomAccessibleInterval<FloatType>> rays = new ArrayList<>();
        for (int c = 0; c < planes.length; c++) {
            if (planes[c] == null || planes[c].length != (long) width * height)
                throw new IllegalArgumentException("Invalid StarDist prediction plane dimensions.");
            for (float value : planes[c]) if (!Float.isFinite(value))
                throw new IllegalArgumentException("Non-finite StarDist prediction.");
            if (c > 0) rays.add(ArrayImgs.floats(planes[c], width, height));
        }
        // Wrap the worker's existing planes. A copied 2048^2 x 97 tensor would
        // otherwise add another ~1.5 GiB inside Fiji before NMS even starts.
        RandomAccessibleInterval<FloatType> probability = ArrayImgs.floats(planes[0], width, height);
        RandomAccessibleInterval<FloatType> distances = Views.stack(rays);
        boolean time = input.dimensionIndex(Axes.TIME) >= 0;
        if (time) {
            // Original StarDist exports frame=1 for a singleton TIME axis too.
            // Collapsing it would change ROI placement to frame=0.
            probability = Views.addDimension(probability, 0, 0);
            distances = Views.addDimension(distances, 0, 0);
        }
        AxisType[] probAxes = time ? new AxisType[] {Axes.X, Axes.Y, Axes.TIME}
                : new AxisType[] {Axes.X, Axes.Y};
        AxisType[] distAxes = time ? new AxisType[] {Axes.X, Axes.Y, Axes.CHANNEL, Axes.TIME}
                : new AxisType[] {Axes.X, Axes.Y, Axes.CHANNEL};
        // StarDist2D.splitPrediction -> Utils.raiToDataset preserves AxisType
        // only, creating default uncalibrated axes. Do not add input calibration.
        Dataset p = datasets.create(new ImgPlus<>(ImgView.wrap(probability,
                new ArrayImgFactory<>(new FloatType())), "Probability/Score Image", probAxes));
        Dataset d = datasets.create(new ImgPlus<>(ImgView.wrap(distances,
                new ArrayImgFactory<>(new FloatType())), "Distance Image", distAxes));
        return new Dataset[] {p, d};
    }

    Map<String, Object> nmsArguments(Dataset probability, Dataset distances) {
        Map<String, Object> args = new LinkedHashMap<>();
        args.put("prob", probability); args.put("dist", distances);
        // No six-decimal rounding: the legacy macro already supplied its value.
        args.put("probThresh", probThresh); args.put("nmsThresh", nmsThresh);
        args.put("outputType", outputType); args.put("excludeBoundary", excludeBoundary);
        args.put("roiPosition", "Automatic".equals(roiPosition)
                ? (input.numDimensions() > 3 && !input.isRGBMerged() ? "Hyperstack" : "Stack") : roiPosition);
        args.put("verbose", verbose);
        return args;
    }

    Map<String, Object> legacyArguments() {
        Map<String, Object> args = new LinkedHashMap<>();
        args.put("input", input); args.put("modelChoice", modelChoice);
        args.put("normalizeInput", normalizeInput); args.put("percentileBottom", percentileBottom);
        args.put("percentileTop", percentileTop); args.put("probThresh", probThresh);
        args.put("nmsThresh", nmsThresh); args.put("outputType", outputType);
        args.put("modelFile", modelFile); args.put("nTiles", nTiles);
        args.put("excludeBoundary", excludeBoundary); args.put("roiPosition", roiPosition);
        args.put("verbose", verbose); args.put("showCsbdeepProgress", showCsbdeepProgress);
        args.put("showProbAndDist", showProbAndDist);
        return args;
    }

    private void copyOutputs(CommandModule result) {
        label = (Dataset) result.getOutput("label");
        prob = (Dataset) result.getOutput("prob");
        dist = (Dataset) result.getOutput("dist");
    }
}

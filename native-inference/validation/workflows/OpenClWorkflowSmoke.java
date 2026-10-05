import Analysis.SpatialSingleCellType;
import Analysis.SpatialTwoCellType;
import ij.ImagePlus;
import ij.ImageStack;
import ij.WindowManager;
import ij.macro.Interpreter;
import ij.measure.ResultsTable;
import ij.process.ByteProcessor;
import ij.process.FloatProcessor;
import ij.process.ImageProcessor;
import ij.process.ShortProcessor;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import net.haesleinhuepf.clij.clearcl.ClearCLBuffer;
import net.haesleinhuepf.clij2.CLIJ2;
import org.jocl.CL;
import org.jocl.Pointer;
import org.jocl.cl_device_id;
import org.jocl.cl_platform_id;

/** Validation only: real OpenCL bindings, kernels and GAT spatial code, no mocks. */
public final class OpenClWorkflowSmoke {
    private static final List<String> checks = new ArrayList<>();
    private static boolean failed;
    private static CLIJ2 clij;
    private static Path output;
    private interface Check { String run() throws Exception; }
    private static String quote(String value) {
        StringBuilder result = new StringBuilder("\"");
        for (char ch : value.toCharArray()) {
            if (ch == '"' || ch == '\\') result.append('\\').append(ch);
            else if (ch < 32) result.append(String.format("\\u%04x", (int) ch));
            else result.append(ch);
        }
        return result.append('"').toString();
    }
    private static void record(String name, String status, String detail, long start) {
        checks.add("{\"name\":" + quote(name) + ",\"status\":" + quote(status)
                + ",\"detail\":" + quote(detail) + ",\"milliseconds\":"
                + ((System.nanoTime() - start) / 1_000_000) + "}");
        System.out.println(status + " " + name + ": " + detail);
        failed |= status.equals("FAIL");
    }
    private static void check(String name, Check test) {
        long start = System.nanoTime();
        try { record(name, "PASS", test.run(), start); }
        catch (Throwable error) {
            error.printStackTrace();
            record(name, "FAIL", error.toString(), start);
        } finally { if (clij != null) clij.clear(); }
    }
    private static void require(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }
    private static String deviceName(cl_device_id device) {
        long[] size = new long[1];
        int status = CL.clGetDeviceInfo(device, CL.CL_DEVICE_NAME, 0, null, size);
        require(status == 0 && size[0] > 0 && size[0] < 65536, "Invalid OpenCL device name");
        byte[] bytes = new byte[(int) size[0]];
        require(CL.clGetDeviceInfo(device, CL.CL_DEVICE_NAME, bytes.length, Pointer.to(bytes), null) == 0,
                "Cannot read OpenCL device name");
        return new String(bytes, 0, bytes.length - 1, StandardCharsets.UTF_8);
    }
    private static int enumerate() {
        CL.setExceptionsEnabled(false);
        int[] count = new int[1];
        int error = CL.clGetPlatformIDs(0, null, count);
        if (error == -1001 || error == 0 && count[0] == 0) return 0;
        require(error == 0 && count[0] <= 64, "clGetPlatformIDs error " + error);
        cl_platform_id[] platforms = new cl_platform_id[count[0]];
        require(CL.clGetPlatformIDs(platforms.length, platforms, null) == 0, "Platform enumeration failed");
        int total = 0;
        for (cl_platform_id platform : platforms) {
            int[] number = new int[1];
            error = CL.clGetDeviceIDs(platform, CL.CL_DEVICE_TYPE_ALL, 0, null, number);
            if (error == CL.CL_DEVICE_NOT_FOUND) continue;
            require(error == 0 && number[0] <= 128, "clGetDeviceIDs error " + error);
            cl_device_id[] devices = new cl_device_id[number[0]];
            require(CL.clGetDeviceIDs(platform, CL.CL_DEVICE_TYPE_ALL, devices.length, devices, null) == 0,
                    "Device enumeration failed");
            for (cl_device_id device : devices) System.out.println("OpenCL device: " + deviceName(device));
            total += devices.length;
        }
        return total;
    }
    private static void transfer(int bits) {
        ImageProcessor pixels = bits == 8 ? new ByteProcessor(16, 12)
                : bits == 16 ? new ShortProcessor(16, 12) : new FloatProcessor(16, 12);
        for (int i = 0; i < pixels.getPixelCount(); i++) pixels.setf(i, (i * 3) % 100);
        ImagePlus original = new ImagePlus("transfer-" + bits, pixels);
        try (ClearCLBuffer input = clij.push(original); ClearCLBuffer result = clij.create(input)) {
            require(clij.multiplyImageAndScalar(input, result, 2), "Kernel reported failure");
            ImagePlus actual = clij.pull(result);
            for (int i = 0; i < pixels.getPixelCount(); i++)
                require(actual.getProcessor().getf(i) == 2 * pixels.getf(i), "Transfer/kernel pixel mismatch " + i);
            actual.close();
        }
    }
    private static ImagePlus labels(String title, boolean markers) {
        ShortProcessor pixels = new ShortProcessor(32, 24);
        if (markers) {
            for (int y = 8; y < 14; y++) for (int x = 3; x < 9; x++) pixels.set(x, y, 1);
        } else {
            for (int y = 8; y < 14; y++) for (int x = 3; x < 9; x++) pixels.set(x, y, 1);
            for (int y = 8; y < 14; y++) for (int x = 9; x < 15; x++) pixels.set(x, y, 2);
            for (int y = 8; y < 14; y++) for (int x = 24; x < 28; x++) pixels.set(x, y, 3);
        }
        return new ImagePlus(title, pixels);
    }
    private static String singleSpatial() throws Exception {
        ImagePlus labels = labels("GAT-opencl-single", false);
        labels.show();
        require(WindowManager.getImage(labels.getTitle()) == labels, "Batch window registration failed");
        try {
            SpatialSingleCellType.execute("Hu", labels.getTitle(), "NA", output.resolve("single").toString(),
                    0, false, 1, "unused");
            ResultsTable result = ResultsTable.open(output.resolve("single/spatial_analysis/Neighbour_count_Hu.csv").toString());
            require(result.size() == 3, "Expected three spatial rows");
            int[] expected = {1, 1, 0};
            for (int i = 0; i < 3; i++) require(result.getValue("No of cells around Hu", i) == expected[i],
                    "Unexpected GAT neighbor count at row " + i + ": " + result.getValue("No of cells around Hu", i));
            return "Actual SpatialSingleCellType.execute; touching labels give [1,1,0], CSV verified";
        } finally { labels.changes = false; labels.close(); }
    }
    private static String twoSpatial() throws Exception {
        Method method = SpatialTwoCellType.class.getDeclaredMethod("countNeighboursAroundRef", CLIJ2.class,
                ImagePlus.class, ImagePlus.class, int.class, String.class, int.class, int.class);
        method.setAccessible(true);
        ImagePlus reference = labels("reference", false), marker = labels("marker", true);
        int[] actual = (int[]) method.invoke(null, clij, reference, marker, 0, "NA", 32, 24);
        require(Arrays.equals(actual, new int[]{0, 1, 0, 0}), "Unexpected overlap counts " + Arrays.toString(actual));
        ShortProcessor mask = new ShortProcessor(32, 24);
        ImagePlus ganglia = new ImagePlus("GAT-opencl-ganglia-zero", mask);
        ganglia.show();
        try {
            int[] restricted = (int[]) method.invoke(null, clij, reference, marker, 0, ganglia.getTitle(), 32, 24);
            require(Arrays.equals(restricted, new int[]{0, 0, 0, 0}), "Ganglia restriction did not clear overlaps");
        } finally { ganglia.changes = false; ganglia.close(); }
        return "Actual private GAT overlap helper, unrestricted and zero ganglia mask; ROI Manager/CSV UI path not tested";
    }
    private static String edfKernel() {
        ImageStack stack = new ImageStack(32, 24);
        FloatProcessor plane = new FloatProcessor(32, 24);
        for (int y = 0; y < 24; y++) for (int x = 0; x < 32; x++) plane.setf(x, y, (x * x + 3 * y) % 50 + 5);
        for (int z = 0; z < 3; z++) stack.addSlice(plane.duplicate());
        try (ClearCLBuffer source = clij.push(new ImagePlus("edf", stack));
             ClearCLBuffer destination = clij.create(new long[]{32, 24}, clij.Float)) {
            require(clij.extendedDepthOfFocusVarianceProjection(source, destination, 2, 2, 10), "EDF kernel failed");
            ImagePlus actual = clij.pull(destination);
            for (int i = 0; i < plane.getPixelCount(); i++)
                require(Float.isFinite(actual.getProcessor().getf(i))
                        && Math.abs(actual.getProcessor().getf(i) - plane.getf(i)) < 0.001,
                        "Identical-slice EDF invariant failed at " + i);
            actual.close();
        }
        return "Real CLIJ2 variance EDF kernel (2,2,10); identical three-slice invariant; GAT IJ.run menu routing not tested";
    }
    public static void main(String[] args) throws Exception {
        output = Paths.get(args[0]);
        Files.createDirectories(output);
        Interpreter.batchMode = true;
        long start = System.nanoTime();
        int devices = -1;
        try {
            devices = enumerate();
            record("jocl-enumeration", devices > 0 ? "PASS" : "BLOCKED_ENVIRONMENT",
                    devices + " devices; JOCL " + CL.class.getProtectionDomain().getCodeSource().getLocation(), start);
        } catch (Throwable error) { error.printStackTrace(); record("jocl-enumeration", "FAIL", error.toString(), start); }
        if (devices > 0) {
            try { clij = CLIJ2.getInstance(); record("clij-context", "PASS", clij.getGPUName(), System.nanoTime()); }
            catch (Throwable error) { error.printStackTrace(); record("clij-context", "FAIL", error.toString(), System.nanoTime()); }
        }
        if (clij != null) {
            for (int bits : new int[]{8,16,32}) check("push-kernel-pull-" + bits, () -> { transfer(bits); return "Exact pixels after multiply by 2"; });
            check("gat-spatial-single", OpenClWorkflowSmoke::singleSpatial);
            check("gat-spatial-two-helper", OpenClWorkflowSmoke::twoSpatial);
            check("variance-edf-kernel", OpenClWorkflowSmoke::edfKernel);
            clij.close();
        } else {
            for (String name : new String[]{"push-kernel-pull-8", "push-kernel-pull-16", "push-kernel-pull-32",
                    "gat-spatial-single", "gat-spatial-two-helper", "variance-edf-kernel"})
                record(name, "BLOCKED", "No usable CLIJ context; see native enumeration/context result", System.nanoTime());
        }
        String json = "{\"scope\":\"Headless native OpenCL and GAT component checks; not full GUI validation\",\"os\":"
                + quote(System.getProperty("os.name")) + ",\"arch\":" + quote(System.getProperty("os.arch"))
                + ",\"java\":" + quote(System.getProperty("java.version")) + ",\"checks\":[" + String.join(",", checks) + "]}\n";
        Files.write(output.resolve("opencl-report.json"), json.getBytes(StandardCharsets.UTF_8));
        if (failed) System.exit(1);
    }
}

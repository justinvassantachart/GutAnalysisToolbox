import com.google.gson.GsonBuilder;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;

/** Separate component evidence, never a claim that a GAT workflow reached JNI. */
public final class LegacyJniProbe {
    public static void main(String[] args) throws Exception {
        if (args.length != 2 || !(args[0].equals("tensorflow") || args[0].equals("opencv")))
            throw new IllegalArgumentException("tensorflow|opencv report.json");
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("probe", args[0] + "-jni"); result.put("scope", "direct original JNI component control; not actual GAT workflow evidence");
        result.put("actual_gat_method_invoked", false);
        result.put("java_version", System.getProperty("java.version")); result.put("java_arch", System.getProperty("os.arch"));
        result.put("os", System.getProperty("os.name"));
        result.put("system_classloader", ClassLoader.getSystemClassLoader().getClass().getName());
        result.put("native_operation_attempted", false);
        try {
            ClassLoader loader = LegacyJniProbe.class.getClassLoader();
            if (loader.getResource("org/tensorflow/types/TFloat32.class") != null)
                throw new IllegalStateException("Modern TensorFlow is forbidden in an original-runtime control");
            String name = args[0].equals("tensorflow") ? "org.tensorflow.TensorFlow" : "org.bytedeco.javacpp.opencv_core";
            Class<?> type = Class.forName(name, false, loader);
            result.put("code_source", type.getProtectionDomain().getCodeSource().getLocation().toString());
            result.put("native_operation_attempted", true);
            if (args[0].equals("tensorflow")) {
                // version() initializes the original JNI loader; Graph allocates a
                // genuine native object if that library load succeeds.
                result.put("runtime_version", org.tensorflow.TensorFlow.version());
                try (org.tensorflow.Graph graph = new org.tensorflow.Graph()) {
                    result.put("native_graph_created", true);
                }
            } else {
                result.put("javacpp_platform", org.bytedeco.javacpp.Loader.getPlatform());
                result.put("loaded_native_library", org.bytedeco.javacpp.Loader.load(org.bytedeco.javacpp.opencv_core.class));
                result.put("opencv_build_information", org.bytedeco.javacpp.opencv_core.getBuildInformation().getString());
            }
            result.put("status", "success");
        } catch (Throwable error) {
            StringWriter text = new StringWriter(); error.printStackTrace(new PrintWriter(text));
            result.put("status", Boolean.TRUE.equals(result.get("native_operation_attempted")) ? "native_component_failure" : "setup_failure");
            result.put("exception", text.toString()); System.err.println(text);
        }
        Path report = Path.of(args[1]); Files.createDirectories(report.toAbsolutePath().getParent());
        String json = new GsonBuilder().serializeNulls().setPrettyPrinting().disableHtmlEscaping().create().toJson(result);
        Files.writeString(report, json + "\n"); System.out.println(json);
        System.exit("success".equals(result.get("status")) ? 0 : 2);
    }
}

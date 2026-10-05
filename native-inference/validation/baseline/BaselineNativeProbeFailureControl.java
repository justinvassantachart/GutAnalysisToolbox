import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;
import javax.swing.JOptionPane;

/** Synthetic callback control only: does not invoke GAT or claim native evidence. */
public final class BaselineNativeProbeFailureControl {
    private static void set(Class<?> probe, String name, Object value) throws Exception {
        Field field = probe.getDeclaredField(name);
        field.setAccessible(true);
        field.set(null, value);
    }

    @SuppressWarnings("unchecked")
    public static void main(String[] args) throws Exception {
        Path report = Path.of(args[1]);
        Class<?> probe = Class.forName("BaselineNativeProbe");
        set(probe, "reportFile", report);
        set(probe, "startedAt", System.nanoTime());
        Field field = probe.getDeclaredField("result");
        field.setAccessible(true);
        Map<String, Object> result = (Map<String, Object>) field.get(null);
        result.put("synthetic_validation_control", true);
        result.put("probe", "stardist");
        result.put("status", "running");
        result.put("stage", CsbdeepTensorFlowDialogObserver.CALL_STAGE);
        set(probe, "invoked", true);
        Method save = probe.getDeclaredMethod("saveSnapshot");
        save.setAccessible(true);
        if (!Boolean.TRUE.equals(save.invoke(null))) throw new AssertionError("Initial control snapshot failed");
        if (args[0].equals("persistence-failure")) {
            // Block only the next atomic write, preserving the previous running snapshot.
            Files.createDirectory(report.resolveSibling(report.getFileName() + ".pending"));
        }
        Map<String, Object> evidence = new LinkedHashMap<>();
        evidence.put("synthetic_validation_control", true);
        evidence.put("title", CsbdeepTensorFlowDialogObserver.TITLE);
        evidence.put("message", CsbdeepTensorFlowDialogObserver.MESSAGE);
        evidence.put("message_type", JOptionPane.ERROR_MESSAGE);
        evidence.put("stage_at_observation", CsbdeepTensorFlowDialogObserver.CALL_STAGE);
        evidence.put("selected_value", "JOptionPane.UNINITIALIZED_VALUE");
        Method failure = probe.getDeclaredMethod("nativeFailureDialog", Map.class);
        failure.setAccessible(true);
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            try {
                Files.writeString(report.resolveSibling("shutdown-hook-ran"), "A GUI shutdown hook could dismiss the dialog\n");
            } catch (Exception error) {
                error.printStackTrace();
            }
        }));
        failure.invoke(null, evidence);
        throw new AssertionError("Callback must terminate its isolated control JVM");
    }
}

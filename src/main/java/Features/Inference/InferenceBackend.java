package Features.Inference;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.Locale;
import java.util.concurrent.TimeUnit;

/** Selects a backend without initializing any TensorFlow or OpenCL classes. */
public final class InferenceBackend {
    public static final String PROPERTY = "gat.stardist.backend";
    private InferenceBackend() { }

    public static boolean useNativeWorker() {
        String mode = System.getProperty(PROPERTY, "auto");
        return select(mode, isAppleSiliconMac());
    }

    /** Hardware check shared by guards for other native-library workflows. */
    public static boolean isAppleSiliconMac() {
        String os = System.getProperty("os.name", "");
        String arch = System.getProperty("os.arch", "");
        Boolean hardware = isArmMac(os, arch) ? Boolean.TRUE : (isMac(os) ? isAppleHardware() : Boolean.FALSE);
        if (hardware == null) throw new IllegalStateException("Could not determine this Mac's CPU architecture. "
                + "GAT will not load legacy TensorFlow until the architecture is known. "
                + "On Apple Silicon use native arm64 Fiji with its bundled Java.");
        return hardware;
    }

    static boolean select(String mode, boolean appleSilicon) {
        String normalized = mode.trim().toLowerCase(Locale.ROOT);
        if ("native".equals(normalized)) return true;
        if ("auto".equals(normalized)) return appleSilicon;
        if ("legacy".equals(normalized)) {
            if (appleSilicon) throw new IllegalStateException(
                    "The legacy TensorFlow 1.x backend cannot be selected on Apple Silicon. "
                    + "Use native arm64 Fiji and the GAT native-inference package.");
            return false;
        }
        throw new IllegalArgumentException("Unknown " + PROPERTY + ": " + mode
                + ". Expected auto, native, or legacy.");
    }

    public static void requireWorkerJava() {
        String os = System.getProperty("os.name", "");
        String arch = System.getProperty("os.arch", "");
        requireMacVersion(os, System.getProperty("os.version", "0"));
        if (isMac(os) && !isArm(arch) && Boolean.TRUE.equals(isAppleHardware())) {
            throw new IllegalStateException("Fiji is running through Rosetta on Apple Silicon. "
                    + "Install native macOS arm64 Fiji (with its bundled Java 21), then add "
                    + "the GAT Apple Silicon test package. Do not use Intel Fiji/Java 8.");
        }
        if (javaMajor(System.getProperty("java.specification.version", "0")) < 11) {
            throw new IllegalStateException("The isolated GAT inference worker requires Java 11 or newer. "
                    + "Use native arm64 Fiji with bundled Java 21 on an Apple Silicon Mac.");
        }
    }

    static void requireMacVersion(String os, String version) {
        if (isMac(os) && javaMajor(version) < 14) {
            throw new IllegalStateException("This native TensorFlow preview requires macOS 14 Sonoma or newer. "
                    + "Its bundled Apple Silicon JNI library has a minimum macOS deployment target of 14.0.");
        }
    }

    static int javaMajor(String version) {
        String v = version.startsWith("1.") ? version.substring(2) : version;
        int dot = v.indexOf('.');
        if (dot >= 0) v = v.substring(0, dot);
        try { return Integer.parseInt(v); }
        catch (NumberFormatException e) { return 0; }
    }

    static boolean isMac(String os) { return os.toLowerCase(Locale.ROOT).contains("mac"); }
    static boolean isArm(String arch) {
        return "aarch64".equalsIgnoreCase(arch) || "arm64".equalsIgnoreCase(arch);
    }
    static boolean isArmMac(String os, String arch) { return isMac(os) && isArm(arch); }

    // Native Java reports its architecture correctly. This read-only, bounded
    // OS probe also catches an Intel Java process translated by Rosetta.
    private static Boolean isAppleHardware() {
        Process process = null;
        try {
            process = new ProcessBuilder("/usr/sbin/sysctl", "-n", "hw.optional.arm64")
                    .redirectErrorStream(true).start();
            if (!process.waitFor(2, TimeUnit.SECONDS)) return null;
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream(), "UTF-8"))) {
                String value = reader.readLine();
                if (process.exitValue() != 0) return null;
                return "1".equals(value) ? Boolean.TRUE : ("0".equals(value) ? Boolean.FALSE : null);
            }
        } catch (Exception e) {
            if (e instanceof InterruptedException) Thread.currentThread().interrupt();
            return null;
        } finally {
            if (process != null && process.isAlive()) process.destroyForcibly();
        }
    }
}

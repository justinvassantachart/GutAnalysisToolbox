package Features.Inference;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.Locale;
import java.util.concurrent.TimeUnit;
import java.util.function.Supplier;

/** Selects a backend without initializing any TensorFlow or OpenCL classes. */
public final class InferenceBackend {
    public static final String PROPERTY = "gat.stardist.backend";
    private static final String ARM64_KEY = "hw.optional.arm64";
    private InferenceBackend() { }

    public static boolean useNativeWorker() {
        String mode = System.getProperty(PROPERTY, "auto");
        return select(mode, isAppleSiliconMac());
    }

    /** Hardware check shared by guards for other native-library workflows. */
    public static boolean isAppleSiliconMac() {
        return isAppleSiliconMac(System.getProperty("os.name", ""),
                System.getProperty("os.arch", ""), InferenceBackend::isAppleHardware);
    }

    // Keep OS-probe outcomes testable without changing JVM-global properties or
    // requiring a particular host architecture to exercise Intel and Rosetta.
    static boolean isAppleSiliconMac(String os, String arch, Supplier<Boolean> probe) {
        if (!isMac(os)) return false;
        if (isArm(arch)) return true;
        Boolean hardware = isIntel(arch) ? probe.get() : null;
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
        if (isMac(os) && !isArm(arch) && isAppleSiliconMac()) {
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
    private static boolean isIntel(String arch) {
        return "x86_64".equalsIgnoreCase(arch) || "amd64".equalsIgnoreCase(arch)
                || "x86".equalsIgnoreCase(arch) || "i386".equalsIgnoreCase(arch);
    }

    // Native Java reports its architecture correctly. This read-only, bounded
    // OS probe also catches an Intel Java process translated by Rosetta.
    private static Boolean isAppleHardware() {
        Process process = null;
        try {
            ProcessBuilder builder = new ProcessBuilder("/usr/sbin/sysctl", "-n", ARM64_KEY)
                    .redirectErrorStream(true);
            // The exact ENOENT diagnostic below must not depend on user locale.
            builder.environment().put("LC_ALL", "C");
            process = builder.start();
            if (!process.waitFor(2, TimeUnit.SECONDS)) return null;
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream(), "UTF-8"))) {
                String value = reader.readLine();
                // Reject extra output rather than accidentally accepting a partial response.
                if (reader.readLine() != null) return null;
                return parseArm64Probe(process.exitValue(), value);
            }
        } catch (Exception e) {
            if (e instanceof InterruptedException) Thread.currentThread().interrupt();
            return null;
        } finally {
            if (process != null && process.isAlive()) process.destroyForcibly();
        }
    }

    static Boolean parseArm64Probe(int exitCode, String output) {
        if (exitCode == 0) {
            return "1".equals(output) ? Boolean.TRUE : ("0".equals(output) ? Boolean.FALSE : null);
        }
        // XNU registers hw.optional.arm64 only in its ARM machine branch.
        // Intel macOS can therefore return ENOENT (exit 1), not a numeric 0.
        // Recognize only this exact missing-key outcome; timeouts, permission
        // errors and malformed responses must still fail closed.
        if (exitCode == 1 && ("sysctl: unknown oid '" + ARM64_KEY + "'").equals(output)) {
            return Boolean.FALSE;
        }
        return null;
    }
}

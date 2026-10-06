package Features.Inference;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class InferenceBackendTest {
    @Test void enforcesVerifiedNativeMacDeploymentTarget() {
        assertThrows(IllegalStateException.class, () -> InferenceBackend.requireMacVersion("Mac OS X", "13.6"));
        assertDoesNotThrow(() -> InferenceBackend.requireMacVersion("Mac OS X", "14.0"));
        assertDoesNotThrow(() -> InferenceBackend.requireMacVersion("Mac OS X", "15.1"));
        assertDoesNotThrow(() -> InferenceBackend.requireMacVersion("Linux", "6.1"));
    }
    @Test void autoKeepsIntelAndLinuxLegacy() {
        assertFalse(InferenceBackend.select("auto", false));
        assertTrue(InferenceBackend.select("auto", true));
    }
    @Test void explicitWorkerIsAvailableForCrossPlatformValidation() {
        assertTrue(InferenceBackend.select("native", false));
        assertTrue(InferenceBackend.select("native", true));
    }
    @Test void appleNeverFallsBackToUnsafeLegacy() {
        assertThrows(IllegalStateException.class, () -> InferenceBackend.select("legacy", true));
        assertFalse(InferenceBackend.select("legacy", false));
        assertThrows(IllegalArgumentException.class, () -> InferenceBackend.select("typo", false));
    }
    @Test void recognizesBothJavaArchitectureNames() {
        assertTrue(InferenceBackend.isArmMac("Mac OS X", "aarch64"));
        assertTrue(InferenceBackend.isArmMac("Mac OS X", "arm64"));
        assertFalse(InferenceBackend.isArmMac("Mac OS X", "x86_64"));
        assertFalse(InferenceBackend.isArmMac("Linux", "aarch64"));
    }
    @Test void intelMacAcceptsNumericZeroAndTheRealMissingOidDiagnostic() {
        for (Boolean probe : new Boolean[]{
                InferenceBackend.parseArm64Probe(0, "0"),
                InferenceBackend.parseArm64Probe(1, "sysctl: unknown oid 'hw.optional.arm64'")}) {
            assertEquals(Boolean.FALSE, probe);
            boolean apple = InferenceBackend.isAppleSiliconMac("Mac OS X", "x86_64", () -> probe);
            assertFalse(apple);
            assertFalse(InferenceBackend.select("auto", apple));
            assertFalse(InferenceBackend.select("legacy", apple));
            assertTrue(InferenceBackend.select("native", apple));
        }
    }
    @Test void rosettaIsStillAppleHardwareAndCannotSelectLegacy() {
        boolean apple = InferenceBackend.isAppleSiliconMac("Mac OS X", "x86_64",
                () -> InferenceBackend.parseArm64Probe(0, "1"));
        assertTrue(apple);
        assertTrue(InferenceBackend.select("auto", apple));
        assertThrows(IllegalStateException.class, () -> InferenceBackend.select("legacy", apple));
    }
    @Test void nativeArmAndOtherOperatingSystemsDoNotRunTheMacProbe() {
        java.util.function.Supplier<Boolean> unexpected = () -> { throw new AssertionError("Unexpected probe"); };
        assertTrue(InferenceBackend.isAppleSiliconMac("Mac OS X", "aarch64", unexpected));
        assertTrue(InferenceBackend.isAppleSiliconMac("Mac OS X", "arm64", unexpected));
        assertFalse(InferenceBackend.isAppleSiliconMac("Linux", "aarch64", unexpected));
        assertFalse(InferenceBackend.isAppleSiliconMac("Windows 11", "amd64", unexpected));
    }
    @Test void genuineProbeFailuresNeverEnableLegacyTensorFlow() {
        assertNull(InferenceBackend.parseArm64Probe(1, "sysctl: hw.optional.arm64: Operation not permitted"));
        assertNull(InferenceBackend.parseArm64Probe(1, "sysctl: unknown oid 'unrelated.key'"));
        assertNull(InferenceBackend.parseArm64Probe(2, "sysctl: unknown oid 'hw.optional.arm64'"));
        assertNull(InferenceBackend.parseArm64Probe(0, null));
        assertNull(InferenceBackend.parseArm64Probe(0, "unexpected"));
        assertNull(InferenceBackend.parseArm64Probe(1, "0"));
        assertThrows(IllegalStateException.class,
                () -> InferenceBackend.isAppleSiliconMac("Mac OS X", "x86_64", () -> null));
        assertThrows(IllegalStateException.class,
                () -> InferenceBackend.isAppleSiliconMac("Mac OS X", "unknown", () -> false));
    }
    @Test void realHostProbeMatchesTheCiRunnerArchitecture() {
        String expected = System.getProperty("gat.test.expectedAppleSilicon");
        org.junit.jupiter.api.Assumptions.assumeTrue(expected != null,
                "Host expectation is set explicitly by the CI runner matrix");
        assertEquals(Boolean.parseBoolean(expected), InferenceBackend.isAppleSiliconMac());
    }
    @Test void parsesLegacyAndModernJavaVersions() {
        assertEquals(8, InferenceBackend.javaMajor("1.8"));
        assertEquals(11, InferenceBackend.javaMajor("11"));
        assertEquals(21, InferenceBackend.javaMajor("21.0.1"));
        assertEquals(0, InferenceBackend.javaMajor("unknown"));
    }
}

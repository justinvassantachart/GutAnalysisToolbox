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
    @Test void parsesLegacyAndModernJavaVersions() {
        assertEquals(8, InferenceBackend.javaMajor("1.8"));
        assertEquals(11, InferenceBackend.javaMajor("11"));
        assertEquals(21, InferenceBackend.javaMajor("21.0.1"));
        assertEquals(0, InferenceBackend.javaMajor("unknown"));
    }
}

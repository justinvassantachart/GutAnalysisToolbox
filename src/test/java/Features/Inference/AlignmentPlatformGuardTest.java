package Features.Inference;

import Features.Core.Params;
import Features.Tools.AlignStack;
import Features.Tools.AlignStackBatch;
import ij.ImagePlus;
import org.junit.jupiter.api.Test;
import org.mockito.MockedStatic;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class AlignmentPlatformGuardTest {
    @Test void templateMatchingIsRejectedBeforeTouchingImageOnAppleSilicon() {
        try (MockedStatic<InferenceBackend> backend = mockStatic(InferenceBackend.class)) {
            backend.when(InferenceBackend::isAppleSiliconMac).thenReturn(true);
            ImagePlus image = mock(ImagePlus.class);
            assertThrows(IllegalStateException.class, () -> AlignStack.alignTemplateMatching(image, 1));
            verifyNoInteractions(image);
            Params p = new Params(); p.useTemplateMatching = true;
            assertThrows(IllegalStateException.class, () -> new AlignStack().run(p));
            assertThrows(IllegalStateException.class, () -> AlignStackBatch.runBatch(p));
        }
    }
    @Test void guardDoesNotRejectExistingIntelOrOtherPlatformPath() {
        try (MockedStatic<InferenceBackend> backend = mockStatic(InferenceBackend.class)) {
            backend.when(InferenceBackend::isAppleSiliconMac).thenReturn(false);
            assertDoesNotThrow(AlignStack::requireTemplateMatchingSupported);
        }
    }
}

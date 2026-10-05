package Features.Inference;

import ij.ImagePlus;
import ij.gui.ImageWindow;
import ij.WindowManager;
import ij.macro.Interpreter;
import ij.process.FloatProcessor;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.*;

class NativeStarDistTest {
    @Test void nmsUsesLegacyThresholdFormattingAndBoundaryPolicy() {
        String arguments = NativeStarDist.nmsArguments("prob", "dist", 0.123456789, 0.3);
        assertTrue(arguments.contains("'probThresh':'0.123457'"));
        assertTrue(arguments.contains("'nmsThresh':'0.3'"));
        assertTrue(arguments.contains("'excludeBoundary':'2'"));
        assertTrue(arguments.contains("'outputType':'Label Image'"));
    }
    @Test void realBatchImageRemainsResolvableByNmsTitle() {
        boolean oldBatchMode = Interpreter.batchMode;
        ImagePlus image = new ImagePlus("GAT_registration_regression", new FloatProcessor(3, 2));
        try {
            Interpreter.batchMode = true;
            NativeStarDist.registerWithoutVisibleWindow(image);
            assertSame(image, WindowManager.getImage(image.getTitle()));
        } finally {
            image.changes = false; image.close();
            Interpreter.batchMode = oldBatchMode;
        }
    }
    @Test void nmsInputStaysRegisteredWhenItsWindowIsHidden() {
        ImagePlus image = mock(ImagePlus.class);
        ImageWindow window = mock(ImageWindow.class);
        when(image.getWindow()).thenReturn(window);
        NativeStarDist.registerWithoutVisibleWindow(image);
        verify(image).show();
        verify(window).setVisible(false);
        verify(image, never()).hide();
        verify(image, never()).close();
    }
    @Test void batchModeInputWithoutWindowIsNotUnregistered() {
        ImagePlus image = mock(ImagePlus.class);
        NativeStarDist.registerWithoutVisibleWindow(image);
        verify(image).show();
        verify(image, never()).hide();
        verify(image, never()).close();
    }
}

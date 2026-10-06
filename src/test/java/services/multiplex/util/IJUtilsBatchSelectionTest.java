package services.multiplex.util;

import ij.ImagePlus;
import ij.WindowManager;
import ij.macro.Interpreter;
import ij.process.ByteProcessor;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class IJUtilsBatchSelectionTest {
    @Test void selectsTheIntendedImageWithoutAnImageWindow() {
        boolean previousBatch = Interpreter.batchMode;
        ImagePlus previousCurrent = WindowManager.getTempCurrentImage();
        ImagePlus reference = new ImagePlus("batch-reference", new ByteProcessor(8, 8));
        ImagePlus target = new ImagePlus("batch-target", new ByteProcessor(8, 8));
        try {
            Interpreter.batchMode = true;
            reference.show();
            target.show();
            assertNull(reference.getWindow());
            assertNull(target.getWindow());
            assertSame(target, WindowManager.getCurrentImage());

            IJUtils.selectWindow(reference.getTitle());
            assertSame(reference, WindowManager.getCurrentImage());
            IJUtils.selectWindow(target.getTitle());
            assertSame(target, WindowManager.getCurrentImage());

            IJUtils.selectWindow(null);
            IJUtils.selectWindow("no-such-multiplex-image");
            assertSame(target, WindowManager.getCurrentImage());
        } finally {
            reference.close();
            target.close();
            Interpreter.batchMode = previousBatch;
            WindowManager.setTempCurrentImage(previousCurrent);
        }
    }
}

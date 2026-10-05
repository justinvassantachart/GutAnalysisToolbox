import ij.ImagePlus;
import ij.WindowManager;
import ij.macro.Interpreter;
import ij.process.ByteProcessor;
import services.multiplex.util.IJUtils;

/** Isolated positive counterpart to the frozen old helper reproduction. */
public class ReviewCorrectedBatchSelection {
    public static void main(String[] args) {
        Interpreter.batchMode = true;
        ImagePlus ref = new ImagePlus("review_ref", new ByteProcessor(8, 8));
        ImagePlus target = new ImagePlus("review_target", new ByteProcessor(8, 8));
        ref.show(); target.show();
        System.out.println("ref_window=" + ref.getWindow() + " target_window=" + target.getWindow()
            + " before=" + WindowManager.getCurrentImage().getTitle());
        if (ref.getWindow() != null || target.getWindow() != null || WindowManager.getCurrentImage() != target)
            throw new AssertionError("Wrong batch selection precondition");
        IJUtils.selectWindow(ref.getTitle());
        System.out.println("after_helper=" + WindowManager.getCurrentImage().getTitle());
        if (WindowManager.getCurrentImage() != ref) throw new AssertionError("Corrected helper did not select reference");
        ref.close(); target.close(); Interpreter.batchMode = false;
        System.out.println("corrected_batch_selection_PASS");
    }
}

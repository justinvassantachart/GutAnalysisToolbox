import ij.IJ;
import ij.ImagePlus;
import ij.measure.Calibration;
import java.nio.file.Path;

/** Read-only audit of the archived TIFFs, independent of the service and harness. */
public class ReviewSavedCalibration {
    public static void main(String[] args) {
        for (String arg : args) {
            Path caseDir = Path.of(arg);
            String[] names = {"inputs/Layer1_Hu.tif", "output/Results/Aligned_Stack.tif", "output/Results/hu_stack.tif"};
            for (String name : names) {
                ImagePlus image = IJ.openImage(caseDir.resolve(name).toString());
                if (image == null) throw new AssertionError("Cannot open " + name);
                Calibration c = image.getCalibration();
                System.out.println(caseDir.getFileName() + " " + name + " pixel_width=" + c.pixelWidth
                    + " pixel_height=" + c.pixelHeight + " pixel_depth=" + c.pixelDepth
                    + " frame_interval=" + c.frameInterval + " unit=" + c.getUnit()
                    + " time_unit=" + c.getTimeUnit());
                image.close();
            }
        }
    }
}

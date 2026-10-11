package Features.Tools;

import ij.ImagePlus;
import ij.ImageStack;
import ij.CompositeImage;
import ij.process.FloatProcessor;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class ImageProjectionTest {
    @Test void projectsZSeparatelyForEveryChannelAndTimeWithoutChangingSource() {
        ImageStack stack = new ImageStack(2, 1);
        for (int t = 1; t <= 2; t++) for (int z = 1; z <= 2; z++) for (int c = 1; c <= 4; c++)
            stack.addSlice(new FloatProcessor(2, 1, new float[]{100*t + 10*z + c, 100*t - 10*z - c}));
        ImagePlus source = new ImagePlus("channel-time controls", stack);
        source.setDimensions(4, 2, 2);
        source = new CompositeImage(source, CompositeImage.COMPOSITE);
        source.setPosition(3, 2, 2);
        source.getCalibration().pixelWidth=.3;
        source.getCalibration().pixelHeight=.7;
        source.getCalibration().frameInterval=2.5;
        ImagePlus actual=ImageOps.mip(source);
        assertEquals(4, actual.getNChannels()); assertEquals(1,actual.getNSlices()); assertEquals(2,actual.getNFrames());
        assertInstanceOf(CompositeImage.class,actual);
        for(int t=1;t<=2;t++) for(int c=1;c<=4;c++) {
            assertEquals(100*t+20+c,actual.getStack().getProcessor(actual.getStackIndex(c,1,t)).getf(0));
            assertEquals(100*t-10-c,actual.getStack().getProcessor(actual.getStackIndex(c,1,t)).getf(1));
        }
        assertEquals(3,source.getC()); assertEquals(2,source.getZ()); assertEquals(2,source.getT());
        assertEquals(.3,actual.getCalibration().pixelWidth); assertEquals(.7,actual.getCalibration().pixelHeight);
        assertEquals(2.5,actual.getCalibration().frameInterval);
        actual.getCalibration().pixelWidth=9; assertEquals(.3,source.getCalibration().pixelWidth);
        actual.getStack().getProcessor(1).setf(0,999); assertEquals(111,source.getStack().getProcessor(1).getf(0));
    }
    @Test void singleZKeepsAllChannelsAndPlainStacksKeepTheExistingMaximum() {
        ImageStack stack=new ImageStack(1,1);
        for(float v:new float[]{1,2,3,4}) stack.addSlice(new FloatProcessor(1,1,new float[]{v}));
        ImagePlus source=new ImagePlus("single-Z",stack);source.setDimensions(4,1,1);
        ImagePlus actual=ImageOps.mip(source);assertEquals(4,actual.getNChannels());
        for(int c=1;c<=4;c++)assertEquals(c,actual.getStack().getProcessor(c).getf(0));
        source.setDimensions(1,4,1);assertEquals(4,ImageOps.mip(source).getProcessor().getf(0));
    }
}

package services.multiplex.core;

import ij.IJ;
import ij.ImagePlus;
import ij.gui.PointRoi;
import ij.gui.Roi;
import ij.plugin.frame.RoiManager;
import ij.process.ByteProcessor;
import org.junit.jupiter.api.Test;
import org.mockito.MockedStatic;

import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class FeatureMatchingLandmarksTest {
    static ImagePlus image(String title, float dx, float dy) {
        ImagePlus image = new ImagePlus(title, new ByteProcessor(40, 30));
        image.setRoi(new PointRoi(new float[]{2.25f + dx, 9.5f + dx, 20 + dx},
                new float[]{12 + dy, 21.75f + dy, 25 + dy}, 3));
        return image;
    }

    static void assertPoints(Roi roi, float dx, float dy) {
        assertInstanceOf(PointRoi.class, roi);
        assertEquals(3, roi.getFloatPolygon().npoints);
        assertArrayEquals(new float[]{2.25f + dx, 9.5f + dx, 20 + dx}, roi.getFloatPolygon().xpoints);
        assertArrayEquals(new float[]{12 + dy, 21.75f + dy, 25 + dy}, roi.getFloatPolygon().ypoints);
    }

    @Test void snapshotsKeepDistinctSubpixelCoordinatesAndDoNotAliasEitherImage() {
        ImagePlus reference = image("reference", 0, 0);
        ImagePlus target = image("target", 7, -5);
        Roi[] snapshots = FeatureMatching.snapshotLandmarks(reference, target);
        assertNotSame(reference.getRoi(), snapshots[0]);
        assertNotSame(target.getRoi(), snapshots[1]);
        assertNotSame(snapshots[0], snapshots[1]);
        reference.getRoi().setLocation(0, 0);
        target.getRoi().setLocation(1, 1);
        assertPoints(snapshots[0], 0, 0);
        assertPoints(snapshots[1], 7, -5);
        snapshots[0].setLocation(3, 3);
        assertPoints(snapshots[1], 7, -5);
    }

    @Test void storesBothSnapshotsBeforeAnyManagerSideEffect() {
        // Mock only command/manager UI plumbing, not ROI coordinates or cloning.
        // This is a result-handling test, not a feature-extraction accuracy test.
        ImagePlus reference = image("reference", 0, 0);
        ImagePlus target = image("target", 7, -5);
        RoiManager manager = mock(RoiManager.class);
        List<Roi> stored = new ArrayList<>();
        when(manager.getCount()).thenAnswer(invocation -> stored.size());
        doAnswer(invocation -> {
            stored.add(invocation.getArgument(0));
            target.setRoi((Roi) reference.getRoi().clone());
            return null;
        }).when(manager).addRoi(any(Roi.class));
        doAnswer(invocation -> {
            stored.get(invocation.getArgument(0, Integer.class)).setName(invocation.getArgument(1));
            return null;
        }).when(manager).rename(anyInt(), anyString());

        try (MockedStatic<IJ> commands = mockStatic(IJ.class);
             MockedStatic<RoiManager> managers = mockStatic(RoiManager.class)) {
            managers.when(RoiManager::getInstance2).thenReturn(manager);
            assertTrue(FeatureMatching.matchWithFallbacks(reference, target, "hu", 1, .5, 3));
            commands.verify(() -> IJ.run(eq("Extract SIFT Correspondences"), contains("expected_transformation=Affine")));
        }
        assertEquals(2, stored.size());
        assertPoints(stored.get(0), 0, 0);
        assertPoints(stored.get(1), 7, -5);
        assertEquals("hu_1_ref", stored.get(0).getName());
        assertEquals("hu_1_target", stored.get(1).getName());
        verify(manager, never()).select(anyInt());
    }

    @Test void restoresClonesToExplicitImagesWithoutModifyingStoredLandmarks() {
        ImagePlus reference = image("reference", 0, 0);
        ImagePlus target = image("target", 7, -5);
        Roi referencePoints = reference.getRoi();
        Roi targetPoints = target.getRoi();
        RoiManager manager = mock(RoiManager.class);
        when(manager.getRoi(2)).thenReturn(referencePoints);
        when(manager.getRoi(3)).thenReturn(targetPoints);
        reference.deleteRoi();
        target.deleteRoi();

        MultiplexRegistrationService.restoreLandmarks(reference, target, manager, 2);
        assertPoints(reference.getRoi(), 0, 0);
        assertPoints(target.getRoi(), 7, -5);
        assertNotSame(referencePoints, reference.getRoi());
        assertNotSame(targetPoints, target.getRoi());
        reference.getRoi().setLocation(1, 1);
        target.getRoi().setLocation(2, 2);
        assertPoints(referencePoints, 0, 0);
        assertPoints(targetPoints, 7, -5);
        verify(manager, never()).select(anyInt());
    }
}

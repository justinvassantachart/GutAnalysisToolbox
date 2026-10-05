# Multiplex result-handling correction

The actual multiplex service's SIFT and MOPS paths completed on a native Mac in
run `37375259755`, job `111995832061`, source `5a00f6d`, but saved incorrect
results: all seven final planes matched the unwarped inputs, exported reference
and target landmark pairs had identical coordinates, and both TIFF outputs lost
the reference calibration. These are pre-existing result/metadata defects;
they have not been established as ARM-only defects.

The correction is limited to ImageJ result handling:

- Use ImageJ's batch-aware image selection API instead of selecting a null
  `ImageWindow` while batch mode is active.
- Clone both correspondence ROIs before any ROI Manager mutation; store the
  reference/target pair without restoring a manager selection onto the other
  image. Restore cloned stored landmarks onto explicit images when warping.
- Require a newly created, unambiguous Landmark Correspondences result with
  the expected title, reference dimensions, source pixel type, and one plane.
  Missing or malformed results fail explicitly rather than falling back to an
  unwarped input or an unrelated active image.
- Copy reference calibration into both the QC and final output stacks.

The output contract was checked against the pinned `mpicbg_-1.6.6.jar` used by
the native validation (SHA-256
`a18fc250b1fd464f6b79855c425e1b23d765974e0b0d2e9fdb03ce2f137406bb`).
`Transform_Roi` creates a separate image with template dimensions and source
pixel type, names it exactly `"Transformed" + source.getTitle()` (no separator),
and shows it after mapping. The dependency provenance is in
[`dependencies.json`](../native-inference/validation/multiplex-full/dependencies.json).

## Validation scope

Eight focused JUnit tests pass on headless Linux with real ImageJ pixel/ROI
objects. They cover distinct subpixel ROI snapshots, explicit-image landmark
restoration, batch image selection, fresh-output discovery even when the source
is current, stale/missing/ambiguous/wrong-output rejection, TIFF calibration and
label round trips, independent output buffers, and source-file preservation.
The full root Maven suite also passes: 61 tests, zero failures/errors/skips.
The ROI Manager/command plumbing test uses mocks; it is not a feature-extraction
accuracy test. Calibration is compared to the reopened reference TIFF because
ImageJ's single-plane TIFF serialization itself can omit Z spacing.

The SIFT/MOPS thresholds, fallback order, affine/least-squares settings,
interpolation, channel order, filenames, and scientific algorithms are unchanged.
The native full-service harness was not changed to accommodate this fix. A new
native full-service run is still required to verify actual SIFT/MOPS registration,
saved aligned pixels, correspondence exports, and final-dialog controls together.
Focused tests alone do not establish scientific accuracy or complete M1 workflow
readiness.

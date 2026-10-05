# Optional Apple Silicon JPEG XR test overlay

This adds one arm64 JNI resource to the existing Java JPEG-XR stack. It contains
**zero Java classes** and does not replace Bio-Formats, change codec functions,
or alter GAT segmentation/registration. Use it only in a separate test Fiji.
This is experimental, not an upstream jxrlib release or a blanket CZI/LIF claim.

## Requirements and exact content

- Native macOS arm64 Fiji/Java; the successful validation platform is recorded
  in the accompanying report. The native build requests macOS deployment 11.0.
- Existing **jxrlib-all 0.2.4**, **native-lib-loader 2.5.0**, and **Bio-Formats
  8.5.0**. The package does not install/download any of these. Verify the actual
  loaded versions, including duplicate Java classes inside Bio-Formats bundles.
- `jars/gat-jxrlib-0.2.4-osx-arm64-test-overlay.jar`, containing only the native
  resource `META-INF/lib/osx_arm64/libjxrjava.dylib` and metadata/license files.
- Complete matching corresponding source in `source/`, with an offline developer
  build recipe, compatibility header, unchanged old vector typemap and generated
  JNI wrapper. Source and exact BSD/GPL-2.0-or-later/SWIG notices travel together.
- `BUILD_INFO.json`, `SHA256SUMS`, exact golden decode results and loader logs.

## Install without a toolchain or downloads at install time

1. Obtain this ZIP and checksum from the verified fork release. Verify SHA-256
   using macOS `shasum -a 256`. Inspect BUILD_INFO and the packaged manifest.
2. Quit the separate test Fiji. Find the actual Fiji directory containing `jars`
   and `plugins`; current native Fiji has this directory beside its inner
   `Fiji.app`. Do not assume `Fiji.app/Contents` is the plugin root.
3. Verify the three required dependency versions. If missing/different, stop and
   obtain a separately approved, pinned setup. Do not blindly replace Java JARs.
4. Copy **only** the overlay JAR into that copy's `jars` folder. Keep all existing
   required JARs. Do not copy the dylib into a system path, rename it `osx_64`,
   modify `java.library.path`, or add DYLD environment overrides. Do not install
   multiple arm64 overlays with the same resource path.
5. Keep the complete source/license package outside Fiji as the matching
   distribution record. No Python, Maven, Git, compiler, SWIG or installer is
   required to use the prebuilt JAR. Do not execute the rebuild script merely to
   install it. Handle any macOS security prompt through the user's normal
   approval process; never disable Gatekeeper or strip quarantine attributes.
6. Start native Fiji and record the Java/code-source/resource paths. Decode a
   known public JPEG-XR fixture through the actual Bio-Formats service/codec,
   then an appropriate public JPEG-XR-compressed microscopy container through
   the normal importer. Save logs, decoded pixel hashes, dimensions/type,
   channel order, series/metadata, calibration and screenshot. An ordinary TIFF
   or non-JPEG-XR CZI does not exercise this codec.
7. Compare against the same unmodified Java dependencies without the overlay in
   a separate process/copy. Keep expected original failure and corrected decode
   evidence separate from unrelated GAT workflows. Recheck the overlay hash
   after an updater run; the updater is not responsible for this optional JAR.

Rollback: quit Fiji and move only this named overlay JAR into an external backup
folder. Restart. Do not delete the original jxrlib/Bio-Formats dependencies.

## What was checked

Packaging requires a successful native checker result: 13 exact golden fixture
matches against the official Linux reference, 59 matching JNI declarations and
vector API controls. It reruns the final resource JAR with unchanged published
Java bindings and the Bio-Formats 8.5.0 service/codec, with the overlay **last**
on the classpath, no native-path overrides, and an empty native search directory.
The native resource must resolve from this exact final JAR. Every checked codec
pixel result must match; successful dynamic loading alone is insufficient.

The library is thin arm64 and depends only on system libc++ and libSystem.
Its own absolute `LC_ID_DYLIB` identity is preserved and distinguished from an
external dependency. It is not a request to open its build directory at runtime.
The distribution does not normalize that ID or change the validated native bytes.

This still requires full Fiji classloader/updater/GUI checks and representative
whole CZI/LIF/other files on the user's physical Mac. The golden fixtures are
standalone JPEG-XR tiles, not every reader's series/metadata/ROI path, every
codec format, encoder operation, malformed-input robustness or long concurrent
workload. Use public images first. Do not upload private research images or
credentials. Read THIRD_PARTY_NOTICES.md before redistributing.

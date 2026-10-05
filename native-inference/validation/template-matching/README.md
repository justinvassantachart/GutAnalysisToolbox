# Native Template Matching port validation

This is a validation-only prototype, not yet a replacement installed by GAT.
It tests a minimal API port of Qingzong Tseng’s original Template Matching plugin
from JavaCV 1.4.4 / OpenCV 4.0.1 to JavaCV 1.5.12 / OpenCV 4.11.0.
Only Java imports and the renamed native-buffer accessor change; the alignment,
reference ROI, matching method, search, peak selection and ImageJ translation code
remain unchanged. Sources are downloaded at a pinned author commit with hashes.

The author source is GPL-3.0. The generated validation module retains the full
author license and source; it is not shaded into GAT’s plugin. A production
backend would likewise need a separately packaged/licensed integration and
reviewed classpath isolation. This test does not remove the current arm64 guard.

Run with Python 3, JDK 17+ and Maven:

```sh
python3 native-inference/validation/template-matching/check.py --platform macosx-arm64 --output target/template-matching-mac
```

Use `--platform linux-x86_64` on Linux. `--maven` selects a Maven executable.
The script fetches the original public 448×448, 142-frame, 16-bit calcium TIFF
and both checksum-pinned source files. It compiles only the modern port against
official Maven artifacts for the selected platform, runs two known-shift synthetic
controls (8/16 bit) and all public frames, then requires exactly equal per-frame
shifts and aligned pixel SHA-256 against isolated old-runtime references.

Initial Linux comparison passed all 150 frames: synthetic shifts were corrected
by (-3,+2) and (+4,-5); all aligned pixels were identical between versions.
The public calcium movie has little measured drift, so synthetic controls are
important and this does not establish quality on arbitrary large motion.
Native macOS execution and the GAT process/UI integration remain separate gates.

The original plugin’s edge behavior, including FloatProcessor-based peak
selection, is deliberately preserved. No threshold, interpolation or algorithm
change is made to force agreement. New templates, unusual LUTs, search-window
settings and subpixel registration are outside this fixed GAT-parameter test.

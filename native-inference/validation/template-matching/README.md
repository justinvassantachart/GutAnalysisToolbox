# Native Template Matching port validation

These checks cover the API port and the separate production adapter/worker.
It tests a minimal API port of Qingzong Tseng’s original Template Matching plugin
from JavaCV 1.4.4 / OpenCV 4.0.1 to JavaCV 1.5.12 / OpenCV 4.11.0.
Only Java imports and the renamed native-buffer accessor change; the alignment,
reference ROI, matching method, search, peak selection and ImageJ translation code
remain unchanged. Sources are downloaded at a pinned author commit with hashes.

The author source is GPL-3.0. The generated validation module retains the full
author license and source; it is not shaded into GAT’s plugin. A production
backend is packaged/licensed separately in `native-alignment/`, outside Fiji's
classpath. The released preview1 archive predates this alignment integration.

Run with Python 3, JDK 17+ and Maven:

```sh
python3 native-inference/validation/template-matching/check.py --platform macosx-arm64 --output target/template-matching-mac
```

Use `--platform linux-x86_64` on Linux. `--maven` selects a Maven executable.
The script fetches the original public 448×448, 142-frame, 16-bit calcium TIFF
and both checksum-pinned source files. It compiles only the modern port against
official Maven artifacts for the selected platform, runs two known-shift synthetic
controls (8/16 bit) and all public frames, using both first and non-first
reference slices (2,3,71), then requires exactly equal per-frame
shifts and aligned pixel SHA-256 against isolated old-runtime references.

The initial Linux/Mac comparison passed all 150 frames: synthetic shifts were corrected
by (-3,+2) and (+4,-5); all aligned pixels were identical between versions.
The public calcium movie has little measured drift, so synthetic controls are
important and this does not establish quality on arbitrary large motion.
The extended six-case control covers300 outputs and preserves every original
reference exactly. Its Linux production client/worker/CSV path also passed all
six cases; native Mac adapter execution is a separate CI gate.

To rebuild the old reference without changing it, add `--engine legacy` and use
`--platform linux-x86_64`. This fetches the original unchanged source and pins
JavaCV1.4.4, JavaCPP1.4.4, OpenCV4.0.1-1.4.4 and ImageJ1.54p. It requires exact
agreement with the checked-in references, records dependency hashes, and never
refreshes those references automatically. The probe also invokes the original
macro-option parser and verifies that GAT's exact option string selects the
same method, ROI, search, reference and non-subpixel settings.

For the actual GAT adapter, build the root classes/dependency classpath and the
matching-platform `native-alignment` bundle, then run:

```sh
python3 native-inference/validation/template-matching/check_adapter.py \
  --root-classpath target/workflow-classpath.txt \
  --worker-directory native-alignment/target --output target/alignment-adapter
```

The adapter check includes source metadata and verified per-frame motion CSV.
Unavailable SIFT transforms are not fabricated as zero shifts or read from an
unrelated global ResultsTable. Template Matching CSVs describe that stage only.

The original plugin’s edge behavior, including FloatProcessor-based peak
selection, is deliberately preserved. No threshold, interpolation or algorithm
change is made to force agreement. New templates, unusual LUTs, search-window
settings and subpixel registration are outside this fixed GAT-parameter test.

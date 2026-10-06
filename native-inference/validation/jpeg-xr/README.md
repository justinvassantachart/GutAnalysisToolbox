# JPEG-XR native repair experiment

Validation only. This directory does not modify production GAT, Fiji, Bio-Formats,
Maven artifacts, updater records, or installed libraries. Its generated native
JAR is an experimental resource overlay, **not an upstream release**.

## Status (2026-10-05)

- Official `ome:jxrlib-all:0.2.4` Linux x86-64 native: **PASS** all 13 fixtures with
  upstream golden decoded-pixel MD5s, plus recorded decoded-pixel SHA-256s
- Locally rebuilt Linux x86-64 native from the same source: **PASS**, byte-exact
  agreement for all 13 fixtures, using the **unchanged published Java classes**
- All **59 published JNI method declarations match** regenerated declarations;
  the legacy `ImageData` vector API is also exercised
- Actual Bio-Formats **8.5.0** `JPEGXRServiceImpl` and `JPEGXRCodec` decode paths:
  **PASS**, including BGR-to-RGB normalization, using the same unchanged Java JAR
- Negative controls: a wrong golden MD5 and a mismatched JVM platform both
  produce a nonzero failure, recorded in `results/negative-controls.json`
- macOS arm64 native build/decode: **pending a separate Mac CI run**. A Linux pass
  does not establish that a Mac binary builds, loads, or returns correct pixels

Final Linux execution reports and decode/compiler logs are checked in under
`results/`. Checked-in execution logs are path-redacted: `<VALIDATION_OUTPUT>`
replaces the local output-directory prefix and `<DEPENDENCY_CACHE>` replaces
the local dependency-cache prefix. Filenames, resource paths, source URLs,
hashes and observed results are preserved. Original local logs are unmodified. Native binary SHA-256: `04d4c1431ea6c45098e9722b5e3acac0f20586b31860cfd1aec84eb43ec7465a`.
This is the final recorded build, not a reproducible-build promise: upstream
assertions can embed absolute source paths. The source rebuild used GCC 14.2.0, SWIG 4.3.0 and Temurin 17.0.20.1.

The checked-in `linux-reference.tsv` records every input SHA-256, dimensions,
bytes per pixel, BGR flag, upstream golden MD5, decoded native SHA-256 and
Bio-Formats output SHA-256. `fixtures.json` records pixel format GUIDs as well.
The upstream golden suite has **13 entries**, even though the first-tiles
folder has 14 files. The unreferenced extra file is not silently counted as a
validated golden fixture.

## Reproduce

Requirements: Python 3, a native Java JDK 11+, make, compiler, and SWIG for the
native rebuild. No Maven build of GAT or TensorFlow is needed. JNI compilation
uses only two build processes; decoding uses a JVM limited to 256 MiB heap.
Use a fresh output directory each time. Downloads are pinned by SHA-256 and
cached; a corrupted cached artifact is an error, never silently trusted.

```sh
# Existing official binary reference: Linux x86-64 only
python3 native-inference/validation/jpeg-xr/check.py \
  --mode reference --expect-platform linux_64 --output target/jpeg-xr-reference

# Rebuild and validate on a native Apple Silicon Mac
command -v swig || brew install swig
python3 native-inference/validation/jpeg-xr/check.py \
  --mode native --expect-platform osx_arm64 --output target/jpeg-xr-mac

# Independent source-build validation on Linux x86-64
python3 native-inference/validation/jpeg-xr/check.py \
  --mode native --expect-platform linux_64 --output target/jpeg-xr-linux

python3 -m unittest discover -s native-inference/validation/jpeg-xr -p 'test_*.py' -v
```

The native runner builds the upstream **JNI target**, rather than `make all`:
the unrelated C++ CLI links OpenSSL, which is unnecessary for JPEG-XR decoding.
It supplies two missing C declarations in an isolated generated compatibility
header (`<wchar.h>` and the exact `unsigned int _byteswap_ulong(unsigned int)`
signature from `image/sys/strcodec.c`). It retains legacy incompatible-pointer
warnings using `-Wno-error=incompatible-pointer-types`; upstream itself already
suppresses warnings with `-w`. This is compiler compatibility, not a claim that
all historical source safety problems have been repaired.

C++98 preserves the legacy wrapper's pre-move semantics when using modern SWIG.
The official SWIG 3.0.10 Java `std_vector.i` is downloaded at a pinned commit and
hash, because modern SWIG changes vector JNI method names and signatures. The
runner verifies all generated JNI declarations against the published class and
exercises vector operations. **No jxrlib codec or wrapper source file is
edited.** No recompression, conversion, model change, altered pixel scale, or
replacement decoder is used.

On Mac, compilation explicitly targets `arm64` and deployment target `11.0`.
`lipo` must confirm an arm64-only library. `otool` dependency/load-command logs
capture its actual minimum macOS and dependencies. That build target is not a
claim of testing on macOS 11; the wider GAT TensorFlow worker currently requires
macOS 14. The Mac results must be inspected before choosing distribution claims.

## What is checked

The official tests cover seven 587×246, 8-bit BGR brightfield tiles and six
16-bit little-endian grayscale fluorescence tiles (690×690, 697×690 and
2040×2040), with lossy and lossless inputs. Channel count in a source filename
refers to the source acquisition: an extracted fluorescence tile is one channel.

For every fixture, the Java probe checks:

1. Input SHA-256, dimensions, decoded byte count and bytes per pixel
2. Direct `Decode.decodeFirstFrame` output against the upstream golden MD5
3. Full byte equality against the direct `ByteBuffer` API
4. Bio-Formats service output against the direct bytes with only the documented
   BGR-to-RGB channel swap; grayscale bytes remain unchanged
5. Bio-Formats codec output against service output with interleaved,
   little-endian codec options
6. Native and Bio-Formats decoded SHA-256 against the recorded Linux reference

The probe reports actual class code sources and native resource URL. A native
run fails unless it resolves the generated overlay resource. System-native
search paths are empty and `LD_LIBRARY_PATH`/`DYLD_LIBRARY_PATH` overrides are
removed for the test. This is a real JNI decode and package-loader test, not
merely `dlopen`, a platform-name check, or a synthetic replacement fixture.

## Loader and potential integration

The required Apple Silicon resource is:

```
META-INF/lib/osx_arm64/libjxrjava.dylib
```

SciJava `native-lib-loader:2.5.0` recognizes an `aarch64` JVM and that resource
layout. Current Fiji's updater metadata already lists 2.5.0; the standalone
Bio-Formats package also contains a loader, so this experiment places the
explicit 2.5.0 JAR first. It likewise places unchanged `jxrlib-all:0.2.4` Java
classes before the equivalent copies in the Bio-Formats package.

An overlay can be resource-only; replacing Java decoder classes or renaming an
arm64 library into `osx_64` is unnecessary and wrong. A production integration
still needs verification with Fiji's actual classloader, updater behavior,
multiple-JAR precedence, codesigning/quarantine requirements, all relevant
plugins, and a full real CZI/LIF dataset. This experiment tests standalone
JPEG-XR tiles and Bio-Formats codec/service integration, not every reader's
metadata/series/ROI handling. It does not cover all JPEG-XR formats, malformed
input robustness, encoding, or long-running concurrent decoding.

## Upstream and provenance

Upstream was checked on 2026-10-05:

- [Glencoe jxrlib repository](https://github.com/glencoesoftware/jxrlib): master
  `19cc1fa19ca6607449d210aea946b3187f808f2c` (2024-03-15); latest tag `v0.2.4`,
  commit `a8e7f81b8f13ef620049caddeb537b5ea5ecffda` (2020-05-11)
- [Open arm64 build issue #35](https://github.com/glencoesoftware/jxrlib/issues/35)
  links [PR #34](https://github.com/glencoesoftware/jxrlib/pull/34), which proposes
  a loader update; it does not contain a complete arm64 binary release
- [Open modernization issue #36](https://github.com/glencoesoftware/jxrlib/issues/36)
  (2026-05-15) still requests building modern x86/arm64 platforms
- [Upstream golden test parameters](https://github.com/glencoesoftware/jxrlib/blob/a8e7f81b8f13ef620049caddeb537b5ea5ecffda/java/src/test/resources/testng.xml)
  and [official fixtures](https://github.com/glencoesoftware/jxrlib/tree/a8e7f81b8f13ef620049caddeb537b5ea5ecffda/fixtures/first-tiles)
- [SciJava loader](https://github.com/scijava/native-lib-loader/tree/7492ab507ac12a3b41a4992d3e3c23968b698c01)
  and [SWIG 3.0.10 vector typemap](https://github.com/swig/swig/blob/d9875c6579efc8a56132313704c69e627c990dac/Lib/java/std_vector.i)

The exact URLs and SHA-256s of all downloaded artifacts are embedded in
`check.py` and copied to each `report.json`. Source-code changes between the
chosen jxrlib release and checked master were POM/build metadata only; this
experiment uses the release source that matches Bio-Formats' existing bindings.

**License/provenance boundary:** Microsoft's C codec contains BSD-style notices;
Glencoe's C++ and Java wrapper source headers explicitly say
**GPL-2.0-or-later**, while its POM advertises Simplified BSD. The mismatch is
tracked by [upstream issue #28](https://github.com/glencoesoftware/jxrlib/issues/28)
and should not be hidden by labeling a newly built wrapper binary BSD-only.
SWIG library-code terms must also be retained for the pinned typemap/generated
wrapper. No independent redistribution license is asserted here for the image
fixtures. This harness fetches official fixtures for validation rather than
vendoring or redistributing their pixels.

Keep this experiment out of the GAT production/preview package until its source
and license obligations have been reviewed and the Mac/Fiji integration has
passed. CI should preserve JSON, TSV and logs only; do not accidentally upload
the whole output directory (which includes source, fixtures, dependencies and
experimental binaries). No upstream PR, contact, account grant, or release is
part of this validation work.

## Suggested separate Mac CI job

See `mac-ci-job.yml.example`. The repository owner should integrate it into the
existing workflow; this validation directory does not edit shared workflows.

# Packaging the optional native JPEG XR overlay

`package-overlay.py` is a separate offline distribution step. It does not change
`check.py`, codec source/function bodies, installed Fiji, Java classes, the native
binary's install ID, or shared CI. It consumes the complete successful native
check directory, not a diagnostics-only download.

## Mac CI commands

After the existing successful checker command, in the **same native Mac job**
with its original source/cache and SWIG 4.5.0 still available:

```sh
python3 -m unittest discover -s native-inference/validation/jpeg-xr -p 'test_*.py' -v
python3 native-inference/validation/jpeg-xr/package-overlay.py \
  --check-output target/jpeg-xr-mac \
  --output target/jpeg-xr-overlay
```

If `check.py` used an external cache, add `--cache /exact/original/cache`. No
network request occurs in this packaging step. It rejects non-native-Mac hosts,
failed/incomplete checks, changed artifact/native/source/license hashes,
incorrect architectures/dependencies, unsafe paths and missing corresponding
source. A different SWIG generator version requires a reviewed notice/provenance
update, not suppression of the version check.

Upload only after the package command succeeds. Suggested owner-managed CI
artifact paths (the owner edits shared YAML):

```text
target/jpeg-xr-overlay/gat-jpeg-xr-0.2.4-macos-arm64-test-overlay.zip
target/jpeg-xr-overlay/gat-jpeg-xr-0.2.4-macos-arm64-test-overlay.zip.sha256
target/jpeg-xr-overlay/gat-jxrlib-0.2.4-corresponding-source.zip
target/jpeg-xr-overlay/gat-jxrlib-0.2.4-corresponding-source.zip.sha256
target/jpeg-xr-overlay/package-report.json
target/jpeg-xr-overlay/final-overlay-*.log
target/jpeg-xr-overlay/final-overlay-actual.tsv
target/jpeg-xr-overlay/source-regeneration.log
```

The install ZIP already includes its matching source ZIP, exact licenses and
checksums. Do not distribute only the loose JNI resource JAR without the complete
corresponding source and notice materials. Do not upload the entire checker
output/cache: it contains upstream fixture images and third-party dependencies.

## Packaging gates

- Successful native arm64 13-fixture exact-golden and 59-JNI-declaration report,
  matching the checker's pinned artifact provenance
- Native Mach-O SHA unchanged from that check; arm64-only dylib; runtime
  dependencies exactly macOS libc++ and libSystem; no custom rpaths or loader
  environment commands. Its own absolute LC_ID_DYLIB is recorded, not confused
  with a runtime dependency, and is never rewritten
- Original build inputs compare byte-for-byte with the pinned upstream archive
- Complete corresponding JNI/C/C++/Java source, Makefile, preferred SWIG interface,
  generated wrapper, compatibility header, pinned old vector typemap and offline
  rebuild recipe are packaged. Generated sources are independently regenerated
  with the recorded SWIG version and compared byte-for-byte
- Resource-only JAR has zero Java classes and retains exact license materials,
  including Glencoe GPL-2.0-or-later headers/full GPL2, Microsoft BSD-style notices,
  and both SWIG versions' library terms/copyright notices
- Final JAR is put last on the actual published Java/Bio-Formats classpath and
  decoded again in a fresh JVM with no native-path overrides; its resource URL
  must be the source of the loaded dylib and all 13 outputs must match

The generated ZIP timestamps/order are deterministic. Native Mach-O reproducibility
across different SDKs, compilers or build paths is not claimed. Full installed
Fiji classloader/updater behavior and full microscopy-container GUI checks remain
required. The overlay is optional and experimental; it must not silently become
an all-format compatibility claim in a release.

## Local packaging unit tests

The 14 packaging tests plus five existing checker tests cover dependency/install-ID
distinction, bad architecture/commands, unsafe paths/symlinks, deterministic
resource-only archives, license completeness/tampering, failed-check rejection,
complete source assembly, source changes and missing generated source. Unit
fixtures are not represented as successful native binaries. A real pinned Linux
source-tree assembly/regeneration check tests the packaging mechanism separately;
only a native Mac final-JAR rerun can produce a distributable overlay ZIP.

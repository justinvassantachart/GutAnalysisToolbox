# Rebuilding the corresponding JPEG XR JNI source

This source ZIP accompanies the exact resource-only JAR; it contains no install
hook and performs no network access. Verify `SHA256SUMS` after extraction.

Prerequisites, obtained separately from official sources with your approval:
native macOS ARM64, Apple clang/make command-line build tools, and a native JDK
with JNI headers. Set `JAVA_HOME` to that JDK's `Contents/Home` directory. Then:

```sh
sh rebuild.sh
```

The default uses the supplied generated JNI C++ source. SWIG need not be
installed for that build. To regenerate wrapper sources from `java/JXR.i`, use
SWIG **4.5.0**, with the included unchanged SWIG **3.0.10** `std_vector.i` override:

```sh
SWIG=/absolute/path/to/swig sh rebuild.sh --regenerate
```

The compatibility header supplies missing standard/source declarations only:
`#include <wchar.h>` and `extern unsigned int _byteswap_ulong(unsigned int);`.
The codec and wrapper function sources are unchanged from the pinned archive.
C++98 preserves the pre-move vector wrapper API; the validation requires all
59 published native JNI declarations to match and exercises the vector methods.
No OpenSSL-dependent command-line decoder is built. No source files or engine
metadata are patched during installation.

`BUILD_INFO.json` in the outer overlay records the successful compiler and SWIG
versions, exact native hash and source hash. Reproducing the build recipe does
not promise a byte-identical Mach-O with a different SDK, compiler, path or
linker: UUIDs/install IDs can differ. Test any rebuild against the pinned golden
fixtures and published Java API before installing it. The library's own
`LC_ID_DYLIB` can contain its build path; it is an identity, not an external
runtime dependency. The validated library requires only macOS's libc++ and
libSystem and no custom rpath. Do not normalize an ID and reuse old validation
hashes without decoding again.

The complete C/C++/Java build source, preferred SWIG interface, generated wrapper,
compatibility header and old vector typemap accompany the binary. Fixture image
pixels and prebuilt utilities are intentionally not redistributed. To rerun
13-fixture Bio-Formats validation, use the pinned GAT `validation/jpeg-xr/check.py`
and its fixture manifest; those official downloads require separate permission
under your execution environment's rules. See THIRD_PARTY_NOTICES.md and the
full license texts before redistribution.

# JPEG XR overlay source and license notices

This optional test overlay rebuilds the JNI target of Glencoe Software jxrlib
v0.2.4, commit `a8e7f81b8f13ef620049caddeb537b5ea5ecffda`. It does not replace
any Java class or change a codec function. It is not an upstream release or an
assertion that the upstream POM's BSD-only label covers the entire wrapper.

- The Microsoft C codec source carries BSD-style source/binary redistribution
  conditions. The complete header is in `LICENSES/MICROSOFT-CODEC-HEADER.txt`;
  every original source notice is retained in the corresponding-source ZIP.
- Glencoe's C++/Java wrapper headers expressly license that code under
  **GPL-2.0-or-later**. The full example header and full GPL version 2 text are
  included. The wrapper source and its generated JNI implementation accompany
  this binary; keep the source and license materials with any redistribution.
  No independent permissive relicensing is claimed. The upstream metadata
  inconsistency is documented at https://github.com/glencoesoftware/jxrlib/issues/28.
- The vector typemap comes unchanged from SWIG 3.0.10 commit
  `d9875c6579efc8a56132313704c69e627c990dac`. The remaining generated wrapper
  came from the exact generator recorded in `SWIG_VERSION` and
  `SOURCE_PROVENANCE.json` (reviewed releases: SWIG 4.5.0 and 4.5.1).
  The old typemap and both reviewed generator releases' license, university
  notices and copyright files are retained. The four corresponding official
  SWIG 4.5.0/4.5.1 notice files are byte-identical, verified at their immutable
  source commits; their version-specific source URLs remain explicit in
  `license-manifest.json`. Their LICENSE files
  separately permit copying/modifying/distributing the Lib/Examples library
  code; the SWIG executable's GPL-3.0 terms are not presented as a restriction
  on all generated output. A GPL-3.0 text is included for completeness of those
  notices. The SWIG executable itself is not redistributed here.
- Compatibility additions consist of `gat-compat.h`, the pinned old vector
  typemap, the supplied generated wrapper, explicit ARM64/macOS deployment/C++98
  build flags and packaging/validation instructions. Codec/wrapper function
  source from the pinned jxrlib archive is unchanged. Supplied build/packaging
  scripts follow GAT's BSD-3-Clause repository license, included separately as
  `LICENSES/GAT-BSD-3-Clause.txt`. This does not replace or weaken the native
  Glencoe wrapper's GPL-2.0-or-later terms.

`license-manifest.json` identifies exact source URLs, checksums and the one
readability-only character-set conversion for the displayed Microsoft header.
The corresponding-source ZIP includes all original C/C++/Java JNI build inputs,
Makefile, interface source, generated C++/Java wrapper, compatibility header,
old SWIG typemap and an offline rebuild recipe. System compilers, the JDK and
SWIG are external build tools, not bundled executables.

Upstream fixture images, prebuilt Windows utilities, the unnecessary Gradle wrapper binary and unrelated binary
specification documents are omitted: no independent permission to redistribute
those fixtures is asserted. They are unnecessary to rebuild this JNI library.
The existing validation checker downloads pinned official fixtures separately.
The source provenance manifest enumerates every excluded file and every
included original-source checksum.

There is no warranty or upstream endorsement. Retain the exact notices and
source; this provenance record does not purport to resolve the upstream license
metadata inconsistency or certify every deployment's redistribution compliance.

# Isolated native Template Matching worker (experimental)

Separate GPL-3.0 worker for the original Template Matching algorithm with
modern native OpenCV. This module must remain outside Fiji's jars/plugins.
It does not substitute SIFT and does not change the legacy matching method,
reference ROI, search, integer peak selection or ImageJ translation.

Build: `mvn -f native-alignment/pom.xml clean package` (macOS arm64 bundle).
Linux validation: append `-Dopencv.platform=linux-x86_64`.
The worker requires native Java11+. No runtime downloads are performed.

Input GATA protocol version 2 contains width, height, frame count, bit depth,
1-based reference slice, then each frame's display minimum/maximum (two
big-endian doubles), 256-entry base ARGB palette, and unsigned 8-bit or
big-endian 16-bit pixels. Palette and display range must be shared across the
stack, as in ImageJ's ordinary ImageStack. Both are preserved because the
original 8-bit matcher uses the rendered image. Stack limit is 67,108,864 pixels.
Version 1 is rejected: install the matching plugin and worker together.
Output GATS version 2 contains frame count and a pair of finite integer-valued
shift doubles for every frame, including zero for the reference. The caller
validates the complete output before changing its images. Standard GAT options
are fixed: method5, 70% reference ROI at floor(size/6), whole-image search,
subpixel=false, interpolation0. Unsupported data is rejected explicitly.

The original source and full license are included. See THIRD_PARTY_NOTICES.md.
Native Mac execution, process-boundary and GUI integration results are recorded
separately; do not infer a supported release merely from a successful build.

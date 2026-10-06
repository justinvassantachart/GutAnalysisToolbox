# Third-party source and licenses

This standalone worker is distributed under GPL-3.0; see LICENSE. It is separate
from GAT's Fiji plugin and communicates only through a local versioned protocol.

TemplateMatching/Align_slices.java and cvMatch_Template.java are from Qingzong
Tseng's imagej_plugins repository, commit e64b9816cb24403542d45457d915f9861f24fa12,
current/src/Template Matching. Copyright and attribution remain in the sources.
https://github.com/qztseng/imagej_plugins/tree/e64b9816cb24403542d45457d915f9861f24fa12

Align_slices is unchanged. cvMatch_Template changes only the OpenCV import
packages and getFloatBuffer → createBuffer API. Algorithm, peak selection,
normalization and translation remain unchanged. Original source hashes and
old/new comparisons are in native-inference/validation/template-matching.

JavaCV/JavaCPP, OpenCV, OpenBLAS and ImageJ are unmodified official Maven
artifacts. Their original JARs retain embedded notices/licenses. This worker
uses JavaCV/JavaCPP1.5.12, OpenCV4.11.0, OpenBLAS0.3.30 and ImageJ1.54p.

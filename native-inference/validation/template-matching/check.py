#!/usr/bin/env python3
"""Compile a minimal official-plugin API port; compare exact old/new alignment."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMMIT = "e64b9816cb24403542d45457d915f9861f24fa12"
AUTHOR_BASE = "https://raw.githubusercontent.com/qztseng/imagej_plugins/" + COMMIT + "/"
SOURCES = {
    "Align_slices.java": ("current/src/Template%20Matching/Align_slices.java", "cd715d900075f6d373dc180c92324bc10943b3492e87a41768c371dbeed48fcf"),
    "cvMatch_Template.java": ("current/src/Template%20Matching/cvMatch_Template.java", "6d7cc415f202908987beb412ac350f00236d179e4786a9d60660b2bdb9380e66"),
    "LICENSE": ("LICENSE", "8ceb4b9ee5adedde47b31e975c1d90c73ad27b6b165a1dcd80c7c545eb65b903"),
}
CALCIUM_URL = "https://raw.githubusercontent.com/pr4deepr/GutAnalysisToolbox/61d57c4e4bcfe82aa0369100c0a3b0739b70affa/Sample%20Images/2D_enteric_neuron_IF/calcium_imaging_mouse_distal_colon_25X.tif"
CALCIUM_SHA = "3ff6e4eb82a1ee4cd128c079a97c7d99be2be51168cbe4c9a0fe6e77e13f91af"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch(url, path, expected):
    if not path.exists():
        partial = path.with_suffix(path.suffix + ".download")
        subprocess.run(["curl", "--fail", "--location", "--silent", "--show-error", "--proto", "=https",
                        "--max-time", "180", url, "-o", str(partial)], check=True)
        if sha(partial) != expected:
            raise ValueError("Downloaded hash mismatch: " + path.name)
        partial.replace(path)
    if sha(path) != expected:
        raise ValueError("Cached hash mismatch: " + path.name)


def replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError("Expected exactly one API migration target: " + before)
    return text.replace(before, after)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=["macosx-arm64", "linux-x86_64"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--maven", default="mvn")
    parser.add_argument("--java", default="java")
    parser.add_argument("--input", type=Path, help="Optional already-downloaded public TIFF, still hash-verified")
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    original = out / "author-source"
    original.mkdir(exist_ok=True)
    source = out / "module/src/main/java/TemplateMatching"
    source.mkdir(parents=True, exist_ok=True)
    for name, (relative, digest) in SOURCES.items():
        fetch(AUTHOR_BASE + relative, original / name, digest)
    shutil.copyfile(original / "Align_slices.java", source / "Align_slices.java")
    text = (original / "cvMatch_Template.java").read_text()
    text = replace_once(text, "import static org.bytedeco.javacpp.opencv_core.*;",
                        "import org.bytedeco.opencv.opencv_core.*;\nimport org.bytedeco.opencv.global.opencv_core;\nimport static org.bytedeco.opencv.global.opencv_core.*;")
    text = replace_once(text, "import static org.bytedeco.javacpp.opencv_imgproc.*;", "import static org.bytedeco.opencv.global.opencv_imgproc.*;")
    text = replace_once(text, "res.getFloatBuffer()", "(FloatBuffer) res.createBuffer()")
    (source / "cvMatch_Template.java").write_text(text)
    shutil.copyfile(HERE / "TemplateMatchProbe.java", source / "TemplateMatchProbe.java")
    shutil.copyfile(original / "LICENSE", out / "module/LICENSE")
    dependencies = ""
    for group, artifact, version, classifier in [
        ("net.imagej", "ij", "1.54p", None),
        ("org.bytedeco", "javacv", "1.5.12", None),
        ("org.bytedeco", "javacpp", "1.5.12", None),
        ("org.bytedeco", "javacpp", "1.5.12", args.platform),
        ("org.bytedeco", "opencv", "4.11.0-1.5.12", None),
        ("org.bytedeco", "opencv", "4.11.0-1.5.12", args.platform),
        ("org.bytedeco", "openblas", "0.3.30-1.5.12", args.platform),
    ]:
        dependencies += ("<dependency><groupId>" + group + "</groupId><artifactId>" + artifact + "</artifactId><version>" + version + "</version>"
                         + ("<classifier>" + classifier + "</classifier>" if classifier else "")
                         + ("<exclusions><exclusion><groupId>*</groupId><artifactId>*</artifactId></exclusion></exclusions>" if artifact == "javacv" else "") + "</dependency>")
    (out / "module/pom.xml").write_text('<project xmlns="http://maven.apache.org/POM/4.0.0"><modelVersion>4.0.0</modelVersion><groupId>org.gatanalysis.validation</groupId><artifactId>template-modern</artifactId><version>0.1</version><properties><maven.compiler.release>11</maven.compiler.release><project.build.sourceEncoding>UTF-8</project.build.sourceEncoding></properties><dependencies>' + dependencies + '</dependencies><build><plugins><plugin><groupId>org.apache.maven.plugins</groupId><artifactId>maven-compiler-plugin</artifactId><version>3.14.1</version></plugin></plugins></build></project>')
    input_file = args.input.resolve() if args.input else out / "calcium-public.tif"
    if args.input:
        if sha(input_file) != CALCIUM_SHA: raise ValueError("Public input hash mismatch")
    else:
        fetch(CALCIUM_URL, input_file, CALCIUM_SHA)
    cp_file = out / "classpath.txt"
    subprocess.run([args.maven, "-B", "-ntp", "-f", str(out / "module/pom.xml"), "compile",
                    "dependency:build-classpath", "-Dmdep.outputFile=" + str(cp_file)], check=True, timeout=600)
    classpath = str(out / "module/target/classes") + os.pathsep + cp_file.read_text().strip()
    start = time.monotonic()
    subprocess.run([args.java, "-Djava.awt.headless=true", "-Xmx1g", "-cp", classpath,
                    "TemplateMatching.TemplateMatchProbe", str(out / "actual.json"), str(input_file)], check=True, timeout=300)
    elapsed = time.monotonic() - start
    actual = json.loads((out / "actual.json").read_text())
    expected = json.loads((HERE / "legacy-reference.json").read_text())
    if len(actual["cases"]) != len(expected["cases"]): raise AssertionError("Case count changed")
    checks = []
    for candidate, reference in zip(actual["cases"], expected["cases"]):
        errors = [key for key, value in reference.items() if candidate.get(key) != value]
        checks.append({"case": reference["case"], "status": "FAIL" if errors else "PASS",
                       "mismatched_fields": errors, "frames": reference["frames"],
                       "aligned_pixel_sha256": candidate["aligned_pixel_sha256"], "milliseconds": candidate["milliseconds"]})
    report = {"checks": checks, "requested_platform": args.platform, "java": actual["java"], "arch": actual["arch"],
              "cold_process_wall_seconds": elapsed, "author_commit": COMMIT,
              "input_sha256": CALCIUM_SHA, "legacy_reference_sha256": sha(HERE / "legacy-reference.json"),
              "port_source_sha256": sha(source / "cvMatch_Template.java"),
              "dependency_artifacts": [{"filename": Path(p).name, "sha256": sha(Path(p))}
                                       for p in cp_file.read_text().strip().split(os.pathsep)],
              "scope": "Original alignment algorithm and ImageJ translation with API-only OpenCV port; not GAT GUI/process integration"}
    (out / "comparison.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps(report, indent=2))
    if any(c["status"] != "PASS" for c in checks): raise AssertionError("Native alignment reference mismatch")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Assemble an installable M-series test package from already-built artifacts."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("dist"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    namespace = {"m": "http://maven.apache.org/POM/4.0.0"}
    version = ET.parse(root / "pom.xml").getroot().findtext("m:version", namespaces=namespace)
    plugin = root / "target" / f"GutAnalysisToolbox_-{version}.jar"
    worker = root / "native-inference/target/gat-native-inference-macosx-arm64.zip"
    if not plugin.is_file() or not worker.is_file():
        raise SystemExit("Build the root plugin and clean-build the macosx-arm64 worker first.")
    with zipfile.ZipFile(plugin) as archive:
        names = archive.namelist()
        assert "Features/Inference/NativeStarDist.class" in names, "Missing native backend adapter"
        assert not any(n.startswith("org/tensorflow/") for n in names), "TensorFlow must not enter Fiji's classpath"
    with zipfile.ZipFile(worker) as archive:
        names = archive.namelist()
        assert "gat-native-inference/gat-native-inference.jar" in names, "Wrong worker distribution layout"
        native = [n for n in names if "/lib/tensorflow-core-native-" in n and n.endswith("-macosx-arm64.jar")]
        assert len(native) == 1, "Missing/multiple Apple Silicon native runtime classifiers"
        assert not any("-linux-" in n or "-windows-" in n or "-macosx-x86_64" in n for n in names), "Mixed runtime platforms"
    args.output.mkdir(parents=True, exist_ok=True)
    destination = args.output / f"GAT-{version}-macos-arm64-preview.zip"
    source_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True).strip())
    metadata = {
        "version": version,
        "source_commit": source_commit,
        "source_worktree_modified": dirty,
        "target": "macos-arm64",
        "experimental": True,
        "plugin_sha256": hashlib.sha256(plugin.read_bytes()).hexdigest(),
        "worker_bundle_sha256": hashlib.sha256(worker.read_bytes()).hexdigest(),
        "validation_note": "See APPLE_SILICON.md for exact test coverage. Packaging is not a macOS runtime test.",
    }
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as output:
        output.write(plugin, "plugins/" + plugin.name)
        with zipfile.ZipFile(worker) as source:
            for entry in source.infolist():
                if entry.is_dir():
                    continue
                parts = Path(entry.filename).parts
                if Path(entry.filename).is_absolute() or ".." in parts:
                    raise ValueError("Unsafe worker archive entry: " + entry.filename)
                with source.open(entry) as src, output.open(entry.filename, "w") as dst:
                    shutil.copyfileobj(src, dst)
        output.write(root / "docs/apple-silicon.md", "APPLE_SILICON.md")
        matrix = root / "docs/apple-silicon-workflow-matrix.md"
        if matrix.is_file():
            output.write(matrix, "apple-silicon-workflow-matrix.md")
        output.write(root / "LICENSE", "GAT_LICENSE")
        output.writestr("BUILD_INFO.json", json.dumps(metadata, indent=2) + "\n")
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_suffix(destination.suffix + ".sha256").write_text(f"{digest}  {destination.name}\n")
    print(destination)
    print(digest)


if __name__ == "__main__":
    main()

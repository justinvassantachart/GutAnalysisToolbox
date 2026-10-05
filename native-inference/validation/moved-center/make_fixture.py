#!/usr/bin/env python3
"""Reproduce compact fixed references from original archived tensors, never candidates.

Writes only a new directory. Exact input/tensor and generated artifact hashes must
match fixture-manifest.json. CI never regenerates or blesses reference files.
"""
import argparse
import gzip
import io
import json
from pathlib import Path
import subprocess
import tempfile

import check


def compressed(data):
    output = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=output, mtime=0) as stream:
        stream.write(data)
    return output.getvalue()


def generate(input_path, tensors, output, cache, java, javac):
    manifest = json.loads((check.ROOT / "fixture-manifest.json").read_text())
    check.hu.verify(input_path, manifest["input_sha256"])
    for side, path in tensors.items():
        check.hu.verify(path, manifest["reference_tensors"][side]["sha256"])
    output.mkdir(parents=True, exist_ok=False)
    pixels = check.input_pixels(input_path, manifest["width"], manifest["height"])
    nms = check.prepare_nms(cache, java, javac)
    payloads = {"input.gati": input_path.read_bytes()}
    with tempfile.TemporaryDirectory(prefix="gat-moved-center-reference-") as temporary:
        for side, tensor in tensors.items():
            prefix = Path(temporary)/side
            subprocess.run(nms+[str(tensor), str(prefix), "0.5"], check=True, timeout=300)
            summary = json.loads(Path(str(prefix)+".nms.json").read_text())
            labels = check.hu.read_values(Path(str(prefix)+".labels.u16be"), "H", len(pixels))
            summary.update(check.measurements(labels, pixels, manifest["width"], manifest["height"]))
            payloads[side+".summary.json"] = (json.dumps(summary, indent=2)+"\n").encode()
            for suffix in (".labels.u16be", ".probability.f32be", ".polygons.gz"):
                payloads[side+suffix] = Path(str(prefix)+suffix).read_bytes()
    for name, data in payloads.items():
        destination = output / (name if name.endswith(".gz") else name+".gz")
        destination.write_bytes(data if name.endswith(".gz") else compressed(data))
    for name, record in manifest["files"].items():
        check.hu.verify(output/name, record["sha256"])
    if {p.name for p in output.iterdir()} != set(manifest["files"]):
        raise AssertionError("Reference artifact names differ")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--legacy", type=Path, required=True)
    parser.add_argument("--modern", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dependencies", type=Path, required=True)
    parser.add_argument("--java", default="java"); parser.add_argument("--javac", default="javac")
    args = parser.parse_args()
    generate(args.input.resolve(), {"legacy": args.legacy.resolve(), "modern": args.modern.resolve()},
             args.output.resolve(), args.dependencies.resolve(), args.java, args.javac)
    print("Compact references reproduced byte-for-byte; fixed references were not changed")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Reproduce compact references from the exact archived TF 1.15 GATO outputs.

Writes a NEW directory only. CI never invokes this tool. Models and the legacy
runner remain separate; this is not a way to accept candidate predictions.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

import check


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--legacy-neuron", type=Path, required=True)
    parser.add_argument("--legacy-subtype", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dependencies", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((check.ROOT / "fixture-manifest.json").read_text())
    source = check.ROOT / "fixtures" / "hu-input.gati"
    check.verify(source, manifest["files"][source.name])
    shutil.copyfile(source, output / source.name)
    pixels = check.input_pixels(source)
    nms = check.prepare_nms(args.dependencies.resolve())
    for case, prediction in zip(manifest["cases"], (args.legacy_neuron, args.legacy_subtype)):
        check.verify(prediction, case["legacy_gato_sha256"])
        prefix = output / case["name"]
        subprocess.run(nms + [str(prediction.resolve()), str(prefix), str(case["probability_threshold"])],
                       check=True, timeout=180)
        nms_path = Path(str(prefix) + ".nms.json")
        summary = json.loads(nms_path.read_text())
        summary.update(check.label_summary(check.read_values(Path(str(prefix) + ".labels.u16be"), "H", len(pixels)), pixels))
        Path(str(prefix) + ".summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        nms_path.unlink()
    for name, sha256 in manifest["files"].items():
        check.verify(output / name, sha256)
    print("Compact references reproduced byte-for-byte; original references were not modified")


if __name__ == "__main__":
    main()

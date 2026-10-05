#!/usr/bin/env python3
"""Exercise the production GAT adapter and isolated worker against fixed references."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root-classpath", type=Path, required=True)
    parser.add_argument("--worker-directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--java", default="java")
    parser.add_argument("--javac", default="javac")
    args = parser.parse_args()
    out = args.output.resolve();out.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location("template_port_check", HERE / "check.py")
    helper = importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    image = args.input.resolve() if args.input else out / "calcium-public.tif"
    if args.input:
        if helper.sha(image) != helper.CALCIUM_SHA: raise ValueError("Public fixture checksum mismatch")
    else:
        helper.fetch(helper.CALCIUM_URL, image, helper.CALCIUM_SHA)
    classes = out / "classes";classes.mkdir(exist_ok=True)
    cp = str(ROOT / "target/classes") + os.pathsep + args.root_classpath.resolve().read_text().strip()
    subprocess.run([args.javac, "--release", "11", "-cp", cp, "-d", str(classes), str(HERE / "AdapterProbe.java")], check=True, timeout=120)
    with (out / "adapter.log").open("w") as log:
        subprocess.run([args.java, "-Djava.awt.headless=true", "-cp", str(classes) + os.pathsep + cp,
                        "Features.Tools.AdapterProbe", str(out), str(args.worker_directory.resolve()), str(image)],
                       stdout=log, stderr=subprocess.STDOUT, check=True, timeout=600)
    actual = json.loads((out / "adapter.json").read_text())
    reference = json.loads((HERE / "legacy-reference.json").read_text())
    if len(actual["cases"]) != len(reference["cases"]): raise AssertionError("Adapter case count changed")
    checks = []
    for candidate, expected in zip(actual["cases"], reference["cases"]):
        differences = [key for key, value in expected.items() if candidate.get(key) != value]
        checks.append({"case": expected["case"], "status": "FAIL" if differences else "PASS",
                       "mismatched_fields": differences, "adapter_seconds": candidate["adapter_seconds"]})
    report = {"checks": checks, "scope": "Actual GAT alignTemplateMatching → isolated process → translated pixels and verified motion CSV; fixed public/synthetic controls",
              "reference_sha256": helper.sha(HERE / "legacy-reference.json"), "input_sha256": helper.CALCIUM_SHA}
    (out / "adapter-comparison.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps(report, indent=2))
    if any(row["status"] != "PASS" for row in checks): raise AssertionError("GAT adapter regression mismatch")


if __name__ == "__main__": main()

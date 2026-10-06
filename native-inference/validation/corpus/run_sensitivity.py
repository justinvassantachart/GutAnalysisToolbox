#!/usr/bin/env python3
"""Repeat one retained outlier and run explicitly diagnostic threading/optimization controls."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess

from run_corpus import verify_input


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scores(path, probes):
    result = {}
    with path.open("rb") as stream:
        magic, version, width, height, channels = struct.unpack(">5i", stream.read(20))
        if magic != 0x4741544F or version != 1: raise ValueError("Invalid GATO output")
        for x, y in probes:
            if not (0 <= x < width and 0 <= y < height): raise ValueError("Probe outside image")
            stream.seek(20 + 4 * ((y * width + x) * channels))
            result[f"{x},{y}"] = struct.unpack(">f", stream.read(4))[0]
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--models", type=Path, required=True)
    parser.add_argument("--java", default="java")
    parser.add_argument("--modern-classpath", required=True)
    parser.add_argument("--legacy-classpath", required=True)
    parser.add_argument("--comparator-classpath", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--probe", action="append", default=[], help="Zero-based probability-grid x,y")
    args = parser.parse_args()
    with args.manifest.open() as stream:
        matches = [r for r in csv.DictReader(stream, delimiter="\t") if r["case_id"] == args.case_id]
    if len(matches) != 1: raise ValueError("Case must occur exactly once in manifest")
    row = matches[0]
    verify_input(row)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    model = args.models / ("2D_enteric_neuron_v4_1.zip" if row["model"] == "neuron" else "2D_enteric_neuron_subtype_v4.zip")
    probes = [tuple(map(int, value.split(","))) for value in args.probe]
    packet = {"case_id": args.case_id, "input_sha256": row["input_sha256"], "model_sha256": sha256(model),
              "source_path": row["source_path"], "source_sha256": row["source_sha256"],
              "width": int(row["width"]), "height": int(row["height"]), "tiles": int(row["tiles"]),
              "probability_threshold": 0.4 if row["model"] == "subtype" else 0.5, "nms_threshold": 0.3,
              "interpretation": "Linux CPU sensitivity diagnostics only; not an Apple-hardware test or a production configuration change",
              "source_metadata": {key: value for key, value in row.items()
                                  if key not in ("input_path", "modern_path", "legacy_path")},
              "baseline_retained": {}, "runs": [], "comparisons": {}}
    original_paths = {name: Path(row[name + "_path"]) for name in ("modern", "legacy")}
    for name, path in original_paths.items():
        packet["baseline_retained"][name] = {"tensor_sha256": sha256(path), "probability_probes": scores(path, probes)}
    variants = [("baseline-repeat-1", "baseline"), ("baseline-repeat-2", "baseline"),
                ("single-thread", "single-thread"), ("single-thread-no-optimizations", "single-thread-no-optimizations")]
    paths = {}
    for label, mode in variants:
        for engine in ("modern", "legacy"):
            destination = output / (label + "-" + engine + ".bin")
            if destination.exists(): raise ValueError(f"Control output already exists: {destination.name}")
            verify_input(row)
            threads = "2" if mode == "baseline" else "1"
            environment = dict(os.environ, TF_NUM_INTRAOP_THREADS=threads, TF_NUM_INTEROP_THREADS="1", OMP_NUM_THREADS=threads, TF_ENABLE_ONEDNN_OPTS="1")
            if mode == "single-thread-no-optimizations": environment["TF_ENABLE_ONEDNN_OPTS"] = "0"
            with (output / (label + "-" + engine + ".log")).open("w") as log:
                subprocess.run([args.java, "-XX:-UsePerfData", "-Xms64m", "-Xmx3g", "-cp", getattr(args, engine + "_classpath"),
                                f"org.gatanalysis.inference.{engine.capitalize()}SensitivityMain", str(model), row["input_path"],
                                str(destination), row["tiles"], mode], stdout=log, stderr=subprocess.STDOUT, env=environment,
                               check=True, timeout=900)
            digest = sha256(destination)
            entry = {"variant": label, "engine": engine, "mode": mode, "tensor_sha256": digest,
                     "matches_retained_same_engine_hash": digest == packet["baseline_retained"][engine]["tensor_sha256"],
                     "probability_probes": scores(destination, probes),
                     "requested_threading": {"intra_op": int(threads), "inter_op": 1, "omp": int(threads)},
                     "thread_counts_explicit_in_session_config": mode != "baseline",
                     "meta_optimizer_disabled": mode == "single-thread-no-optimizations",
                     "oneDNN_disabled_environment": mode == "single-thread-no-optimizations",
                     "oneDNN_environment_value": environment["TF_ENABLE_ONEDNN_OPTS"]}
            packet["runs"].append(entry)
            paths[(label, engine)] = destination
            (output / "sensitivity.json").write_text(json.dumps(packet, indent=2))
            print(json.dumps(entry), flush=True)
    # Exact repeat hashes establish within-engine reproducibility without rerunning
    # identical NMS work. Controls are compared separately across engines and versus
    # the retained legacy baseline; thresholds and tie-breaking never change.
    comparisons = []
    for label in ("single-thread", "single-thread-no-optimizations"):
        comparisons.append((label + "-cross-engine", paths[(label, "modern")], paths[(label, "legacy")]))
        comparisons.append((label + "-modern-vs-retained-legacy", paths[(label, "modern")], original_paths["legacy"]))
    for label, modern, legacy in comparisons:
        run = subprocess.run([args.java, "-XX:-UsePerfData", "-Xmx3g", "-Djava.awt.headless=true", "-cp", args.comparator_classpath,
                              "CorpusNmsComparison", str(modern), str(legacy), str(packet["probability_threshold"]), "0.3",
                              str(output / "outlines" / label)], capture_output=True, text=True, check=True, timeout=900)
        lines = [line for line in run.stdout.splitlines() if line.startswith("{")]
        if len(lines) != 1: raise ValueError("Comparator did not produce one JSON record")
        packet["comparisons"][label] = json.loads(lines[0])
        (output / "sensitivity.json").write_text(json.dumps(packet, indent=2))
        print("COMPARED " + label, flush=True)
    packet["complete"] = True
    packet["baseline_repeats_identical_to_retained"] = all(r["matches_retained_same_engine_hash"] for r in packet["runs"] if r["mode"] == "baseline")
    packet["input_still_matches_manifest"] = sha256(Path(row["input_path"])) == row["input_sha256"]
    (output / "sensitivity.json").write_text(json.dumps(packet, indent=2))
    print("COMPLETE sensitivity diagnostics", flush=True)


if __name__ == "__main__":
    main()

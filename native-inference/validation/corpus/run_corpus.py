#!/usr/bin/env python3
"""Run every manifest case, one matched pair at a time, with durable review backpressure.

A reviewer must write outputs/<case>/.reviewed after metrics/hashes are durable.
The runner never removes predictions; retention is decided by the reviewer.
"""
import argparse
import csv
import hashlib
import itertools
import json
import os
from pathlib import Path
import selectors
import subprocess
import time


def reply(process, timeout=900):
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    try:
        if not selector.select(timeout):
            raise TimeoutError(f"Inference process produced no reply within {timeout} seconds")
        line = process.stdout.readline()
        if not line:
            raise RuntimeError(f"Inference process exited, status={process.poll()}")
        return line.rstrip("\n")
    finally:
        selector.close()


def verify_input(row):
    digest = hashlib.sha256()
    with Path(row["input_path"]).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != row["input_sha256"]:
        raise ValueError(f"Input checksum changed for {row['case_id']}")


class Engine:
    def __init__(self, java, classpath, name, model, root):
        self.log = (root / f"{name}-{model.stem}.log").open("a")
        self.name = name
        env = dict(os.environ, TF_NUM_INTRAOP_THREADS="2", TF_NUM_INTEROP_THREADS="1", OMP_NUM_THREADS="2")
        self.process = subprocess.Popen(
            [java, "-XX:-UsePerfData", "-Xms64m", "-Xmx3g", "-XX:MinHeapFreeRatio=10", "-XX:MaxHeapFreeRatio=20",
             "-cp", classpath, f"org.gatanalysis.inference.{name.capitalize()}BatchMain", str(model)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log, text=True, bufsize=1, env=env)
        line = reply(self.process)
        if line != "READY":
            raise RuntimeError(f"Unexpected {name} startup reply: {line}")

    def infer(self, row):
        verify_input(row)
        path = Path(row[self.name + "_path"])
        if path.exists():
            raise RuntimeError(f"Existing unreviewed output requires explicit reconciliation: {path}")
        request = "\t".join((row["case_id"], row["input_path"], str(path), row["tiles"]))
        self.process.stdin.write(request + "\n")
        self.process.stdin.flush()
        result = reply(self.process)
        if not result.startswith("DONE\t" + row["case_id"] + "\t"):
            raise RuntimeError(f"{self.name}: {result}")
        return int(result.split("\t")[2])

    def close(self):
        if self.process.poll() is None:
            try:
                self.process.stdin.write("STOP\n")
                self.process.stdin.flush()
                self.process.wait(timeout=20)
            except (BrokenPipeError, subprocess.TimeoutExpired):
                self.process.terminate()
                try: self.process.wait(timeout=10)
                except subprocess.TimeoutExpired: self.process.kill(); self.process.wait()
        self.log.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--models", type=Path, required=True)
    parser.add_argument("--java", default="java")
    parser.add_argument("--modern-classpath", required=True)
    parser.add_argument("--legacy-classpath", required=True)
    parser.add_argument("--split", choices=("test", "train", "all"), default="all")
    args = parser.parse_args()
    with args.manifest.open() as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    if args.split != "all": rows = [row for row in rows if row["split"] == args.split]
    root = args.manifest.parent
    models = {"neuron": args.models / "2D_enteric_neuron_v4_1.zip", "subtype": args.models / "2D_enteric_neuron_subtype_v4.zip"}
    progress = root / "prediction-progress.jsonl"
    for (split, model), group in itertools.groupby(rows, key=lambda row: (row["split"], row["model"])):
        group = [row for row in group if not (Path(row["modern_path"]).parent / ".reviewed").exists()]
        if not group: continue
        engines = []
        try:
            for name in ("modern", "legacy"):
                engines.append(Engine(args.java, getattr(args, name + "_classpath"), name, models[model], root))
            for row in group:
                directory = Path(row["modern_path"]).parent
                start = time.time()
                durations = {}
                for engine in engines:
                    durations[engine.name + "_milliseconds"] = engine.infer(row)
                event = dict(case_id=row["case_id"], model=model, split=split, width=int(row["width"]), height=int(row["height"]), **durations)
                with progress.open("a") as stream: stream.write(json.dumps(event) + "\n")
                (directory / ".ready").write_text(json.dumps(event))
                print(json.dumps(event), flush=True)
                # A pending review is active work; no arbitrary review timeout.
                while not (directory / ".reviewed").exists():
                    if (root / "STOP").exists(): raise InterruptedError("Requested corpus stop")
                    time.sleep(1)
                print(f"REVIEWED\t{row['case_id']}\t{time.time() - start:.2f}s", flush=True)
        finally:
            for engine in engines: engine.close()
    (root / "predictions-complete.json").write_text(json.dumps({"cases": len(rows), "split": args.split}))
    (root / ".producer-complete").write_text(json.dumps({"cases": len(rows), "split": args.split}))
    print(f"COMPLETE\t{len(rows)} cases", flush=True)


if __name__ == "__main__":
    main()

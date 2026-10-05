#!/usr/bin/env python3
"""Strict real-image regression against compact Linux TensorFlow 1.15 references.

Python standard library + JDK 17 only. Third-party NMS inputs are checksum-pinned.
This never regenerates references and never changes a failing comparison's limits.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import struct
import subprocess
import time
import urllib.request

ROOT = Path(__file__).resolve().parent
ATOL = RTOL = 1e-4


def timed_subprocess(command, timeout, env=None):
    """Wall time includes process startup and all child work, not just a kernel."""
    started = time.perf_counter()
    options = {"check": True, "timeout": timeout}
    if env is not None:
        options["env"] = env
    subprocess.run(command, **options)
    return time.perf_counter() - started


def runner_metadata(java):
    """Read-only, bounded probes; missing metadata never changes scientific gates."""
    metadata = {"system": platform.system(), "machine": platform.machine(),
                "os_release": platform.release(), "logical_cpu_count": os.cpu_count(),
                "reported_cpu_brand": platform.processor() or None,
                "gpu_comparison_performed": False,
                "worker_cuda_visible_devices": "-1"}
    if hasattr(os, "sched_getaffinity"):
        try:
            metadata["cpu_affinity_count"] = len(os.sched_getaffinity(0))
        except OSError:
            metadata["cpu_affinity_count"] = None
    if hasattr(os, "getloadavg"):
        try:
            metadata["system_load_average_1m_5m_15m"] = list(os.getloadavg())
        except OSError:
            pass
    if metadata["system"] == "Darwin":
        metadata["macos_version"] = platform.mac_ver()[0]
        for key, field in (("machdep.cpu.brand_string", "reported_cpu_brand"),
                           ("hw.physicalcpu", "reported_physical_cpu_count")):
            try:
                probe = subprocess.run(["/usr/sbin/sysctl", "-n", key],
                                       capture_output=True, text=True, timeout=2, check=False)
                if probe.returncode == 0:
                    value = probe.stdout.strip()[:200]
                    metadata[field] = int(value) if field.endswith("count") else value
            except (OSError, ValueError, subprocess.TimeoutExpired):
                metadata[field] = None
    elif metadata["system"] == "Linux":
        try:
            with Path("/proc/cpuinfo").open() as cpuinfo:
                text = cpuinfo.read(65536)
            for line in text.splitlines():
                key, separator, value = line.partition(":")
                if separator and key.strip() == "model name":
                    metadata["reported_cpu_brand"] = value.strip()[:200]
                    break
        except OSError:
            pass
    try:
        probe = subprocess.run([java, "-XshowSettings:properties", "-version"],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, timeout=10, check=False)
        # Do not retain usernames, home directories, classpaths or full environment.
        permitted = {"java.version", "java.vm.name", "java.vm.vendor", "os.arch"}
        metadata["java"] = {}
        for line in probe.stdout.splitlines():
            key, separator, value = line.partition("=")
            if separator and key.strip() in permitted:
                metadata["java"][key.strip()] = value.strip()[:200]
        if probe.returncode:
            metadata["java_probe_exit_code"] = probe.returncode
    except (OSError, subprocess.TimeoutExpired) as error:
        metadata["java_metadata_error"] = type(error).__name__
    metadata["numeric_thread_environment"] = {
        name: int(os.environ[name])
        for name in ("TF_NUM_INTRAOP_THREADS", "TF_NUM_INTEROP_THREADS", "OMP_NUM_THREADS")
        if os.environ.get(name, "").isdigit()
    }
    return metadata


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(path, sha256):
    if digest(path) != sha256:
        raise AssertionError(f"SHA-256 mismatch: {path.name}")


def read_values(path, code, pixels):
    raw = path.read_bytes()
    if len(raw) != struct.calcsize(code) * pixels:
        raise AssertionError(f"Wrong byte length: {path.name}")
    return struct.unpack(f">{pixels}{code}", raw)


def input_pixels(path):
    raw = path.read_bytes()
    if struct.unpack(">4i", raw[:16]) != (0x47415449, 1, 175, 175) or len(raw) != 16 + 175 * 175 * 4:
        raise AssertionError("Wrong GATI fixture shape or size")
    values = struct.unpack(f">{175 * 175}f", raw[16:])
    if not all(math.isfinite(x) for x in values):
        raise AssertionError("Non-finite input")
    return values


def label_summary(labels, source, width=175):
    """Uncalibrated per-label raster measurements; zero-based pixel-center coords."""
    objects = {}
    canonical = {}
    canonical_labels = []
    for p, label in enumerate(labels):
        if not label:
            canonical_labels.append(0)
            continue
        canonical.setdefault(label, len(canonical) + 1)
        canonical_labels.append(canonical[label])
        row = objects.setdefault(label, {"label": label, "area_pixels": 0,
                                       "sum_x": 0, "sum_y": 0, "integrated_intensity": 0.0})
        row["area_pixels"] += 1
        row["sum_x"] += p % width
        row["sum_y"] += p // width
        row["integrated_intensity"] += source[p]
    measurements = []
    for label in sorted(objects):
        row = objects[label]
        area = row["area_pixels"]
        row["centroid_x_pixels"] = row.pop("sum_x") / area + 0.5
        row["centroid_y_pixels"] = row.pop("sum_y") / area + 0.5
        row["mean_intensity"] = row["integrated_intensity"] / area
        measurements.append(row)
    return {"raster_object_count": len(objects), "measurements": measurements,
            "raw_label_sha256": hashlib.sha256(struct.pack(f">{len(labels)}H", *labels)).hexdigest(),
            "canonical_shape_sha256": hashlib.sha256(struct.pack(f">{len(labels)}H", *canonical_labels)).hexdigest()}


def compare(reference_prefix, actual_prefix, source):
    pixels = len(source)
    ref_prob = read_values(Path(str(reference_prefix) + ".probability.f32be"), "f", pixels)
    got_prob = read_values(Path(str(actual_prefix) + ".probability.f32be"), "f", pixels)
    failures = []
    differences = [abs(got - ref) for got, ref in zip(got_prob, ref_prob)]
    bad_probabilities = sum(not (math.isfinite(got) and math.isfinite(ref)
                                  and abs(got - ref) <= ATOL + RTOL * abs(ref))
                            for got, ref in zip(got_prob, ref_prob))
    if bad_probabilities:
        failures.append(f"{bad_probabilities} probability values outside atol=rtol=1e-4")
    ref_labels = read_values(Path(str(reference_prefix) + ".labels.u16be"), "H", pixels)
    got_labels = read_values(Path(str(actual_prefix) + ".labels.u16be"), "H", pixels)
    label_differences = sum(got != ref for got, ref in zip(got_labels, ref_labels))
    if label_differences:
        failures.append(f"{label_differences} raw label pixels differ")
    expected = json.loads(Path(str(reference_prefix) + ".summary.json").read_text())
    observed = json.loads(Path(str(actual_prefix) + ".nms.json").read_text())
    observed.update(label_summary(got_labels, source))
    # Includes exact NMS count, candidate count, winner centers, raw label IDs,
    # raster count, per-label area, centroid, integrated and mean input intensity.
    for key in expected:
        if observed.get(key) != expected[key]:
            failures.append(f"{key} differs")
    # Rejected nonfinite predictions must still produce standards-compliant JSON.
    finite_differences = all(math.isfinite(value) for value in differences)
    max_error = max(differences) if finite_differences else None
    mean_error = sum(differences) / pixels if finite_differences else None
    report = {"case": reference_prefix.name, "passed": not failures,
              "probability_max_abs_error": max_error,
              "probability_mean_abs_error": mean_error,
              "probability_failures": bad_probabilities,
              "raw_label_pixel_differences": label_differences,
              "expected_count": expected["count"], "actual_count": observed["count"],
              "expected_raw_label_sha256": expected["raw_label_sha256"],
              "actual_raw_label_sha256": observed["raw_label_sha256"],
              "expected_canonical_shape_sha256": expected["canonical_shape_sha256"],
              "actual_canonical_shape_sha256": observed["canonical_shape_sha256"],
              "failures": failures}
    return report


def prepare_nms(cache, java="java", javac="javac"):
    dependencies = json.loads((ROOT / "dependencies.json").read_text())
    files = []
    cache.mkdir(parents=True, exist_ok=True)
    for entry in dependencies:
        path = cache / entry["file"]
        if not path.exists():
            temporary = path.with_suffix(path.suffix + ".download")
            with urllib.request.urlopen(entry["url"], timeout=120) as response:
                temporary.write_bytes(response.read())
            verify(temporary, entry["sha256"])
            temporary.replace(path)
        verify(path, entry["sha256"])
        files.append(path)
    classpath = os.pathsep.join(str(path) for path in files if path.suffix == ".jar")
    classes = cache / "classes"
    classes.mkdir(exist_ok=True)
    subprocess.run([javac, "-encoding", "UTF-8", "-cp", classpath, "-d", str(classes)]
                   + [str(path) for path in files if path.suffix == ".java"]
                   + [str(ROOT / "FixtureNms.java")], check=True, timeout=180)
    return [java, "-Djava.awt.headless=true", "-cp", str(classes) + os.pathsep + classpath, "FixtureNms"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", type=Path, required=True)
    parser.add_argument("--models", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "target")
    parser.add_argument("--java", default="java")
    parser.add_argument("--javac", default="javac")
    args = parser.parse_args()
    validation_started = time.perf_counter()
    metadata_started = time.perf_counter()
    metadata = runner_metadata(args.java)
    metadata_seconds = time.perf_counter() - metadata_started
    manifest = json.loads((ROOT / "fixture-manifest.json").read_text())
    fixtures = ROOT / "fixtures"
    for name, sha256 in manifest["files"].items():
        verify(fixtures / name, sha256)
    source = input_pixels(fixtures / "hu-input.gati")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    dependency_files = json.loads((ROOT / "dependencies.json").read_text())
    cached_dependencies = sum((output / "dependencies" / item["file"]).is_file()
                              for item in dependency_files)
    setup_started = time.perf_counter()
    nms = prepare_nms(output / "dependencies", args.java, args.javac)
    setup_seconds = time.perf_counter() - setup_started
    worker = args.worker.resolve()
    classpath = str(worker) + os.pathsep + str(worker.parent / "lib" / "*")
    worker_command = [args.java, "-cp", classpath, "org.gatanalysis.inference.NativeInferenceMain"]
    worker_environment = os.environ.copy()
    # Match the Fiji adapter's explicit CPU baseline; do not accidentally time CUDA.
    worker_environment["CUDA_VISIBLE_DEVICES"] = "-1"
    reports = []
    for case in manifest["cases"]:
        model = args.models.resolve() / case["model"]
        verify(model, case["model_sha256"])
        prefix = output / case["name"]
        prediction = prefix.with_suffix(".gato")
        # A previous result must never be mistaken for the current worker output.
        if prediction.exists():
            prediction.unlink()
        worker_seconds = timed_subprocess(
            worker_command + [str(model), str(fixtures / "hu-input.gati"),
                              str(prediction), str(case["tiles"])],
            timeout=900, env=worker_environment)
        nms_seconds = timed_subprocess(
            nms + [str(prediction), str(prefix), str(case["probability_threshold"])],
            timeout=180)
        comparison_started = time.perf_counter()
        report = compare(fixtures / case["name"], prefix, source)
        report["timing_seconds"] = {
            "cold_worker_subprocess_end_to_end": worker_seconds,
            "nms_subprocess_end_to_end": nms_seconds,
            "reference_comparison": time.perf_counter() - comparison_started,
        }
        report["runner"] = metadata
        report["timing_sample_count"] = 1
        report["timing_warmup_runs"] = 0
        reports.append(report)
        print(json.dumps(report, sort_keys=True, allow_nan=False), flush=True)
    shared_timing = {
        "runner_metadata_collection": metadata_seconds,
        "nms_dependency_download_verification_and_compilation": setup_seconds,
        "fixture_validation_wall": time.perf_counter() - validation_started,
        "dependency_files_cached_at_start": cached_dependencies,
        "dependency_files_total": len(dependency_files),
    }
    for report in reports:
        report["shared_setup_and_run_timing"] = shared_timing
    (output / "comparison.json").write_text(json.dumps(reports, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"shared_setup_and_run_timing": shared_timing}, allow_nan=False), flush=True)
    if not all(report["passed"] for report in reports):
        raise AssertionError("Cross-platform regression failed; see comparison.json (thresholds are fixed)")
    print("PASS: both real-image probability/label/count/measurement regressions")
    print("The subtype-on-Hu case is technical smoke only, not representative subtype performance.")


if __name__ == "__main__":
    main()

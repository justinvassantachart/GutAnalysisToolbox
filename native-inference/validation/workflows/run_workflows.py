#!/usr/bin/env python3
"""Run bounded, isolated GAT workflow component/command checks; never edit a Fiji install."""
import argparse
import hashlib
import json
import os
import platform
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SUITES = {
    "helpers": ("WorkflowSmoke", "workflow-smoke.json", True, 120),
    "registration": ("RegistrationMorphologySmoke", "registration-morphology.json", False, 300),
    "calcium": ("CalciumWorkflowSmoke", "calcium-report.json", False, 180),
    "opencl": ("OpenClWorkflowSmoke", "opencl-report.json", True, 240),
    "ganglia-djl": ("GangliaDjlSmoke", "ganglia-djl-report.json", True, 300),
    "ganglia-jdll": ("GangliaJdllSmoke", "ganglia-jdll-report.json", True, 300),
}


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_command(command):
    try:
        p = subprocess.run(command, capture_output=True, text=True, timeout=20)
        return {"exit_code": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"error": str(exc)}


def tree_rss_kib(pid):
    """Sum this validation process and descendant RSS, on Linux/macOS only."""
    try:
        p = subprocess.run(["ps", "-axo", "pid=,ppid=,rss="], capture_output=True, text=True, timeout=5)
        rows = [tuple(map(int, line.split())) for line in p.stdout.splitlines() if len(line.split()) == 3]
        children = {pid}
        while True:
            expanded = children | {child for child, parent, _ in rows if parent in children}
            if expanded == children:
                break
            children = expanded
        return sum(rss for child, _, rss in rows if child in children)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def execute(command, log, timeout, env, rss_limit_kib=3145728):
    start = time.monotonic()
    max_rss = 0
    stop = None
    with log.open("w") as stream:
        process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT,
                                   env=env, start_new_session=True)
        while process.poll() is None:
            rss = tree_rss_kib(process.pid)
            if rss is not None:
                max_rss = max(max_rss, rss)
                if rss > rss_limit_kib:
                    stop = "process-tree RSS ceiling exceeded"
            if time.monotonic() - start > timeout:
                stop = "process deadline exceeded"
            if stop:
                os.killpg(process.pid, signal.SIGKILL)
                break
            time.sleep(0.25)
        code = process.wait()
    return {"exit_code": code, "cold_process_wall_seconds": time.monotonic() - start,
            "observed_peak_process_tree_rss_kib": max_rss or None,
            "rss_sampling_note": "sampled aggregate RSS; shared pages may be counted per process",
            "rss_ceiling_kib": rss_limit_kib, "timeout_seconds": timeout,
            "resource_stop_reason": stop, "log": log.name}


def fetch(artifact, cache):
    path = cache / artifact["filename"]
    if path.exists():
        if digest(path) != artifact["sha256"]:
            raise RuntimeError("Cached artifact checksum mismatch: " + path.name)
        return path
    temporary = path.with_suffix(path.suffix + ".download")
    subprocess.run(["curl", "--fail", "--location", "--silent", "--show-error", "--proto", "=https",
                    "--max-time", "180", artifact["url"], "--output", str(temporary)], check=True)
    if digest(temporary) != artifact["sha256"]:
        raise RuntimeError("Downloaded artifact checksum mismatch: " + artifact["filename"])
    temporary.replace(path)
    return path


def classify(exit_code, checks):
    counts = {}
    for check in checks:
        status = check.get("status", "UNKNOWN")
        counts[status] = counts.get(status, 0) + 1
    if exit_code or not checks or any(s.startswith("FAIL") or s == "UNKNOWN" for s in counts):
        return "FAIL", counts
    if any(s.startswith("BLOCKED") or s == "NOT_RUN" for s in counts):
        return "PARTIAL", counts
    if any(s != "PASS" for s in counts):
        return "FAIL", counts
    return "PASS", counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root-classpath", type=Path, required=True,
                        help="Text file made by root Maven dependency:build-classpath")
    parser.add_argument("--output", type=Path, required=True, help="New empty result directory")
    parser.add_argument("--cache", type=Path, default=ROOT / "target/workflow-dependencies")
    parser.add_argument("--java", default="java")
    parser.add_argument("--javac", default="javac")
    parser.add_argument("--only", nargs="+", choices=list(SUITES), default=list(SUITES))
    args = parser.parse_args()
    out, cache = args.output.resolve(), args.cache.resolve()
    if out.exists() and any(out.iterdir()):
        parser.error("Use a new empty --output directory; existing evidence is never overwritten")
    out.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    root_cp = args.root_classpath.resolve().read_text().strip()
    if not root_cp or not (ROOT / "target/classes/Features/Core/Params.class").exists():
        parser.error("Build the root plugin and its dependency classpath first; runner does not mutate root targets")
    platform_key = {("Darwin", "arm64"): "macosx-arm64", ("Linux", "x86_64"): "linux-x86_64"}.get((platform.system(), platform.machine()))
    environment = {"system": platform.system(), "machine": platform.machine(), "platform": platform.platform(),
                   "python_version": platform.python_version(), "logical_processors": os.cpu_count(),
                   "github_actions": os.getenv("GITHUB_ACTIONS") == "true", "java": read_command([args.java, "-version"]),
                   "source_revision": read_command(["git", "-C", str(ROOT), "rev-parse", "HEAD"]),
                   "performance_scope": "Hosted-runner/component timing only; not a benchmark of the user's M1"}
    if platform.system() == "Darwin":
        for key, command in {"macos": ["sw_vers"], "chip": ["sysctl", "-n", "machdep.cpu.brand_string"],
                             "model": ["sysctl", "-n", "hw.model"], "memory_bytes": ["sysctl", "-n", "hw.memsize"],
                             "physical_cores": ["sysctl", "-n", "hw.physicalcpu"], "logical_cores": ["sysctl", "-n", "hw.logicalcpu"]}.items():
            environment[key] = read_command(command)
    environment["root_classpath_artifacts"] = [{"path": str(Path(item).resolve()), "sha256": digest(Path(item))}
        for item in root_cp.split(os.pathsep) if Path(item).is_file()]
    class_hash = hashlib.sha256()
    for path in sorted((ROOT / "target/classes").rglob("*.class")):
        class_hash.update(str(path.relative_to(ROOT / "target/classes")).encode())
        class_hash.update(digest(path).encode())
    environment["root_classes_sha256_manifest_digest"] = class_hash.hexdigest()
    (out / "environment.json").write_text(json.dumps(environment, indent=2) + "\n")
    pinned = json.loads((HERE / "dependencies.json").read_text())["artifacts"]
    summary = {"schema_version": 1, "environment": environment, "suites": [], "artifacts": [],
               "scope": "Real helpers/commands as labeled. No full GAT GUI or scientific-validation blanket pass."}
    base_env = os.environ.copy()
    base_env.update(OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1",
                    ENGINE_CACHE_DIR=str(cache / "engine-cache"), DJL_CACHE_DIR=str(cache / "engine-cache"), PYTORCH_VERSION="2.0.0")
    bounds = "-Xmx768m -XX:ActiveProcessorCount=1 -Dai.djl.pytorch.num_threads=1 -Dai.djl.pytorch.num_interop_threads=1"
    base_env["JAVA_TOOL_OPTIONS"] = (base_env.get("JAVA_TOOL_OPTIONS", "") + " " + bounds).strip()
    if "opencl" in args.only and (HERE / "system-opencl.py").is_file():
        capability = execute([sys.executable, str(HERE / "system-opencl.py"), "--output", str(out / "system-opencl.json")],
                             out / "system-opencl.log", 60, base_env, 1048576)
        summary["system_opencl_probe"] = capability
    for name in args.only:
        class_name, report_name, headless, deadline = SUITES[name]
        suite_out = out / name
        suite_out.mkdir()
        row = {"suite": name, "status": "NOT_RUN", "scope": "component/command tests, see per-check report"}
        try:
            groups = set()
            if name == "registration":
                groups.add("registration")
            if name.startswith("ganglia"):
                if not platform_key:
                    row.update(status="BLOCKED", reason="No pinned PyTorch CPU native for this platform")
                    continue
                groups.update(("engine", "jdll-base", "model"))
            artifacts = [a for a in pinned if groups.intersection(a["groups"]) and (not a.get("platform") or a["platform"] == platform_key)]
            paths = {a["filename"]: fetch(a, cache) for a in artifacts}
            for a in artifacts:
                if a not in summary["artifacts"]:
                    summary["artifacts"].append(a)
            classes = suite_out / "classes"
            classes.mkdir()
            if name.startswith("ganglia"):
                group = "engine" if name == "ganglia-djl" else "jdll-base"
                cp_items = [str(paths[a["filename"]]) for a in artifacts if group in a["groups"]]
                if name == "ganglia-djl":
                    cp_items.append(str(paths["gson-2.11.0.jar"]))
            else:
                cp_items = [str(ROOT / "target/classes"), root_cp] + [str(p) for p in paths.values()]
            cp = os.pathsep.join(cp_items)
            compile_result = execute([args.javac, "-cp", cp, "-d", str(classes), str(HERE / "WorkflowReport.java"),
                                      str(HERE / (class_name + ".java"))], suite_out / "compile.log", 90, base_env)
            row["compile"] = compile_result
            if compile_result["exit_code"]:
                row.update(status="FAIL", reason="Validation harness compilation failed")
                continue
            command = [args.java, "-Djava.awt.headless=" + str(headless).lower(), "-cp", str(classes) + os.pathsep + cp,
                       class_name, str(suite_out)]
            if name.startswith("ganglia"):
                model_dir = suite_out / "model"
                model_dir.mkdir()
                for a in artifacts:
                    if "model" in a["groups"]:
                        shutil.copy2(paths[a["filename"]], model_dir / a["filename"])
                command.append(str(model_dir))
                if name == "ganglia-jdll":
                    engine_root = suite_out / "engines"
                    engine_dir = engine_root / ("pytorch-2.0.0-2.0.0-" + platform_key + "-cpu" + ("-gpu" if platform_key == "linux-x86_64" else ""))
                    engine_dir.mkdir(parents=True)
                    for a in artifacts:
                        if "engine" in a["groups"]:
                            shutil.copy2(paths[a["filename"]], engine_dir / a["filename"])
                    command.append(str(engine_root))
            result = execute(command, suite_out / "execution.log", deadline, base_env)
            row["execution"] = result
            report = suite_out / report_name
            if report.exists():
                detail = json.loads(report.read_text())
                row["report"] = str(report.relative_to(out))
                checks = detail.get("checks", [])
                row["status"], row["check_status_counts"] = classify(result["exit_code"], checks)
            else:
                row.update(status="FAIL", reason="No report produced; see execution log/exit code, including native abort or resource stop")
            # Keep portable output/evidence, not duplicated models and dependency jars.
            for bulky in (suite_out / "model", suite_out / "engines"):
                if bulky.exists():
                    shutil.rmtree(bulky)
        except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
            row.update(status="FAIL", reason=type(exc).__name__ + ": " + str(exc))
        finally:
            summary["suites"].append(row)
            (out / "run-summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
            print(name + ": " + row["status"], flush=True)
    failures = any(s["status"] == "FAIL" for s in summary["suites"]) or bool(summary.get("system_opencl_probe", {}).get("exit_code", 0))
    summary["status"] = "FAIL" if failures else "PARTIAL" if any(s["status"] != "PASS" for s in summary["suites"]) else "PASS"
    summary["unrun_requested_suites"] = [s for s in SUITES if s not in args.only]
    (out / "run-summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    return int(failures)


if __name__ == "__main__":
    sys.exit(main())

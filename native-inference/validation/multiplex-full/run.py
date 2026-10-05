#!/usr/bin/env python3
"""Isolated real GAT multiplex-service acceptance, with explicit display/setup blockers."""
import argparse
import hashlib
import importlib.util
import json
import os
import platform
import re
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WORKFLOWS = HERE.parent / "workflows"
CASES = ("controls", "full-sift", "full-mops", "no-files", "missing-marker", "missing-round")
FULL_REQUIRED = {
    "service_return", "saved_dimensions_and_labels", "every_round_and_channel_transform",
    "saved_calibration", "common_marker_qc", "landmark_zip_roundtrip", "source_files_preserved",
    "real_command_route", "final_dialog_cancel_preserves_results",
}
REQUIRED = {
    "controls": {"fixture_roundtrip", "alignment_detector_negative_controls", "existing_results_refused", "dialog_controller_contract"},
    "display-probe": {"awt_display"},
    "full-sift": FULL_REQUIRED, "full-mops": FULL_REQUIRED,
    "no-files": {"expected_input_failure"}, "missing-marker": {"expected_input_failure"},
    "missing-round": {"missing_round_failure"},
}
LIMITS = {
    "controls": {"complete_workflow"},
    "full-sift": {"computation_cancellation", "block_matching_fallback"},
    "full-mops": {"computation_cancellation", "block_matching_fallback"},
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def classify(case, execution, checks, phase="unknown", log=""):
    """Report tested-scope status separately from explicit unsupported/unrun coverage."""
    counts = {}
    for check in checks:
        state = check.get("status", "UNKNOWN")
        counts[state] = counts.get(state, 0) + 1
    if any(check.get("status") == "FAIL" for check in checks):
        return "FAIL_ASSERTION", counts
    if any(check.get("status") not in ("PASS", "FAIL", "BLOCKED", "NOT_RUN") for check in checks):
        return "FAIL_REPORT", counts
    if execution.get("resource_stop_reason"):
        if phase in ("initialization", "display_setup", "blocked_setup"):
            return "BLOCKED_SETUP", counts
        if "DIALOG_UNHANDLED" in log:
            return "BLOCKED_INTERACTION", counts
        return "INCONCLUSIVE_RESOURCE_LIMIT", counts
    if any(c.get("id") == "display_setup" and c.get("status") == "BLOCKED" for c in checks):
        return "BLOCKED_SETUP", counts
    if execution.get("exit_code"):
        return "FAIL_PROCESS", counts
    ids = [c.get("id") for c in checks]
    if not checks or len(ids) != len(set(ids)):
        return "FAIL_REPORT", counts
    lookup = {c.get("id"): c for c in checks}
    if not REQUIRED[case].issubset(lookup):
        return "FAIL_REPORT", counts
    if any(lookup[check].get("status") != "PASS" for check in REQUIRED[case]):
        return "PARTIAL", counts
    for check in checks:
        if check.get("status") == "PASS":
            continue
        if check.get("status") == "NOT_RUN" and check.get("id") in LIMITS.get(case, set()):
            continue
        return "FAIL_REPORT", counts
    return "PASS", counts


def verify_official_commands(jar, required):
    with zipfile.ZipFile(jar) as archive:
        config = archive.read("plugins.config").decode("utf-8")
    found = {}
    for line in config.splitlines():
        match = re.match(r'^[^#].*?,\s*"([^"]+)"\s*,\s*([^\s,]+)\s*$', line)
        if match:
            found[match[1]] = match[2]
    for command, implementation in required.items():
        if found.get(command) != implementation:
            raise ValueError(f"Official command mapping differs: {command}: {found.get(command)!r}")
    return {"required": required, "plugin_manifest_sha256": hashlib.sha256(config.encode()).hexdigest(),
            "block_matching_command_present": "Extract Block Matching Correspondences" in found}


def load_shared_runner():
    spec = importlib.util.spec_from_file_location("gat_workflow_runner", WORKFLOWS / "run_workflows.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root-classpath", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New empty evidence directory")
    parser.add_argument("--cache", type=Path, default=ROOT / "target/multiplex-full-dependencies")
    parser.add_argument("--java", default="java")
    parser.add_argument("--javac", default="javac")
    parser.add_argument("--only", nargs="+", choices=CASES, default=list(CASES))
    parser.add_argument("--expect-native-mac", action="store_true", help="Require actual Darwin arm64 host and JVM")
    parser.add_argument("--timeout", type=int, default=360, help="Per-service process deadline in seconds")
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists() and any(out.iterdir()):
        parser.error("Use a new empty output directory; prior evidence is never overwritten")
    out.mkdir(parents=True, exist_ok=True)
    shared = load_shared_runner()
    environment = {"system": platform.system(), "machine": platform.machine(), "platform": platform.platform(),
                   "java": shared.read_command([args.java, "-version"]),
                   "java_properties": shared.read_command([args.java, "-XshowSettings:properties", "-version"]),
                   "git_revision": shared.read_command(["git", "-C", str(ROOT), "rev-parse", "HEAD"]),
                   "git_dirty": shared.read_command(["git", "-C", str(ROOT), "status", "--porcelain"]),
                   "github_actions": os.environ.get("GITHUB_ACTIONS") == "true",
                   "github_run_url": f"https://github.com/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ['GITHUB_RUN_ID']}" if os.environ.get("GITHUB_REPOSITORY") and os.environ.get("GITHUB_RUN_ID") else None,
                   "hardware_scope": "Actual recorded runner, never inferred to be the user's physical M1"}
    if platform.system() == "Darwin":
        environment["chip"] = shared.read_command(["sysctl", "-n", "machdep.cpu.brand_string"])
        environment["model"] = shared.read_command(["sysctl", "-n", "hw.model"])
    summary = {"schema_version": 1, "suite": "multiplex-full", "environment": environment, "cases": [],
               "scope": "Existing full service on deterministic synthetic 3-round 3-marker TIFFs; no GUI-pane/biological/batch-cancellation blanket claim",
               "coverage_limits": ["No computation cancellation API in current service", "Block Matching command absent in pinned mpicbg manifest", "MOPS uses allowed steps=31 boundary, not a naturally occurring SIFT failure"],
               "requested_cases": args.only, "unrequested_cases": [case for case in CASES if case not in args.only]}

    def write():
        (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    try:
        if args.timeout < 30:
            raise ValueError("Service timeout must be at least 30 seconds")
        if args.expect_native_mac:
            properties = environment["java_properties"].get("stderr", "")
            if platform.system() != "Darwin" or platform.machine() != "arm64" or not re.search(r"os.arch\s*=\s*(aarch64|arm64)\b", properties):
                summary.update(status="BLOCKED_SETUP", reason="Requested native Apple Silicon validation requires Darwin/arm64 host and native arm64 JVM; this run cannot establish it")
                write(); return 2
        classes_root = ROOT / "target/classes"
        service_class = classes_root / "services/multiplex/core/MultiplexRegistrationService.class"
        if not service_class.is_file():
            raise ValueError("Build current root production classes first")
        cp_entries = args.root_classpath.resolve().read_text().strip().split(os.pathsep)
        if any(not Path(item).is_file() for item in cp_entries):
            raise ValueError("Root dependency classpath must contain only existing files, not stale production/test class directories")
        environment["root_classpath"] = [{"path": str(Path(item).resolve()), "sha256": digest(item)} for item in cp_entries]
        environment["production_classes"] = {str(path.relative_to(classes_root)): digest(path) for path in sorted((classes_root / "services/multiplex").rglob("*.class"))}
        environment["production_sources"] = {str(path.relative_to(ROOT)): digest(path) for path in sorted((ROOT / "src/main/java/services/multiplex").rglob("*.java"))}
        environment["harness_sources"] = {str(path.relative_to(ROOT)): digest(path) for path in sorted(HERE.glob("*")) if path.is_file() and (path.suffix in (".java", ".py") or path.name in ("dependencies.json", "provenance.json"))}
        provenance = json.loads((HERE / "provenance.json").read_text())
        artifacts = json.loads((HERE / "dependencies.json").read_text())["artifacts"]
        cache = args.cache.resolve(); cache.mkdir(parents=True, exist_ok=True)
        paths = {artifact["filename"]: shared.fetch(artifact, cache) for artifact in artifacts}
        summary["dependencies"] = artifacts
        summary["official_command_audit"] = verify_official_commands(paths["mpicbg_-1.6.6.jar"], provenance["official_commands"])
        # Pinned mpicbg/JAMA precede Maven transitive jars; production classes are always current root target.
        cp = os.pathsep.join([str(classes_root)] + [str(path) for path in paths.values()] + cp_entries)
        classes = out / "classes"; classes.mkdir()
        env = os.environ.copy()
        env["JAVA_TOOL_OPTIONS"] = (env.get("JAVA_TOOL_OPTIONS", "") + " -Xmx768m -XX:ActiveProcessorCount=1").strip()
        summary["compile"] = shared.execute([args.javac, "-cp", cp, "-d", str(classes), str(WORKFLOWS / "WorkflowReport.java"), str(HERE / "MultiplexFullProbe.java")], out / "compile.log", 90, env)
        if summary["compile"]["exit_code"]:
            summary.update(status="FAIL_HARNESS_COMPILE"); write(); return 1

        def execute_case(case, deadline):
            folder = out / case; folder.mkdir()
            headless = case == "controls" or (platform.system() == "Linux" and not os.environ.get("DISPLAY"))
            command = [args.java, "-Djava.awt.headless=" + str(headless).lower(), "-cp", str(classes) + os.pathsep + cp, "MultiplexFullProbe", str(folder), case]
            execution = shared.execute(command, folder / "execution.log", deadline, env, cwd=folder)
            checks = json.loads((folder / "report.json").read_text()).get("checks", []) if (folder / "report.json").is_file() else []
            phase = json.loads((folder / "phase.json").read_text()).get("phase", "unknown") if (folder / "phase.json").is_file() else "initialization"
            log = (folder / "execution.log").read_text(errors="replace")
            status, counts = classify(case, execution, checks, phase, log)
            row = {"case": case, "status": status, "check_counts": counts, "execution": execution, "phase": phase, "report": str((folder / "report.json").relative_to(out)) if checks else None}
            summary["cases"].append(row); write(); print(case + ": " + status, flush=True)
            return status

        if "controls" in args.only:
            execute_case("controls", 60)
        gui_cases = [case for case in args.only if case != "controls"]
        if gui_cases:
            display = execute_case("display-probe", 45)
            if display == "PASS":
                for case in gui_cases:
                    execute_case(case, args.timeout)
            else:
                summary["cases"].extend({"case": case, "status": "BLOCKED_SETUP", "reason": "Display/ImageJ preflight did not pass; full service was not invoked", "execution": None} for case in gui_cases)
        statuses = [row["status"] for row in summary["cases"]]
        summary["status"] = "FAIL" if any(state.startswith("FAIL") for state in statuses) else "PARTIAL" if any(state != "PASS" for state in statuses) else "PASS_REQUESTED_SCOPES"
        summary["full_service_acceptance_passed"] = all(any(row["case"] == case and row["status"] == "PASS" for row in summary["cases"]) for case in ("full-sift", "full-mops", "no-files", "missing-marker", "missing-round"))
        write()
        return 1 if summary["status"] == "FAIL" else 2 if summary["status"] == "PARTIAL" else 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, zipfile.BadZipFile) as exc:
        summary.update(status="BLOCKED_SETUP", reason=f"{type(exc).__name__}: {exc}")
        write(); print(summary["reason"], file=sys.stderr); return 2


if __name__ == "__main__":
    raise SystemExit(main())

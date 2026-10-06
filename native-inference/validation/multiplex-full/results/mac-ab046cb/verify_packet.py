#!/usr/bin/env python3
"""Read-only integrity and provenance verification; no network or writes."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile

ROOT = Path(__file__).resolve().parent
EXPECTED_REVISION = "ab046cb604dc04e75cf935b7a9f3c17b52843188"
EXPECTED_ARCHIVE_SHA256 = "fac1354084a4e06ff86359c92dfb23ec4979e70b28806905d3b03947b0da441c"


def require(condition, message):
    if not condition:
        raise SystemExit("FAIL: " + message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def safe_path(name):
    path = PurePosixPath(name)
    require(not path.is_absolute() and ".." not in path.parts, "Unsafe relative path: " + name)
    return ROOT / path


def main():
    expected_files = {}
    for line in (ROOT / "SHA256SUMS").read_text().splitlines():
        expected, name = line.split("  ", 1)
        require(name not in expected_files, "Duplicate checksum entry: " + name)
        path = safe_path(name)
        require(path.is_file() and not path.is_symlink(), "Missing or symlinked packet file: " + name)
        require(digest(path.read_bytes()) == expected, "Packet checksum mismatch: " + name)
        expected_files[name] = expected
    actual_files = {str(p.relative_to(ROOT)) for p in ROOT.rglob("*") if p.is_file()}
    require(actual_files == set(expected_files) | {"SHA256SUMS"}, "Packet file set differs from SHA256SUMS")

    manifest = load("original/artifact-manifest.json")
    archive_info = manifest["archive"]
    archive = ROOT / "original" / archive_info["path"]
    archive_bytes = archive.read_bytes()
    require(len(archive_bytes) == archive_info["size_bytes"] == 398562, "Archive size mismatch")
    require(digest(archive_bytes) == archive_info["sha256"] == EXPECTED_ARCHIVE_SHA256, "Archive digest mismatch")
    require(manifest["artifact_id"] == 11373712129, "Wrong artifact id")
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        require(len(names) == len(set(names)) == archive_info["member_count"] == 77, "Archive membership count mismatch")
        require(z.testzip() is None, "Archive CRC failure")
        rows = manifest["members"]
        require(len(rows) == 77 and {r["path"] for r in rows} == set(names), "Member manifest mismatch")
        for row in rows:
            safe_path(row["path"])
            b = z.read(row["path"])
            require(len(b) == row["size_bytes"] and digest(b) == row["sha256"], "Member mismatch: " + row["path"])
        portable = load("portable-copy-manifest.json")
        text_members = {n for n in names if n.endswith((".json", ".log"))}
        require(len(portable["files"]) == len(text_members) == 34, "Portable member count mismatch")
        require({r["path"] for r in portable["files"]} == text_members, "Portable member set mismatch")
        for row in portable["files"]:
            original = z.read(row["path"])
            require(len(original) == row["original_size_bytes"] and digest(original) == row["original_sha256"], "Original portable provenance mismatch")
            text = original.decode("utf-8")
            for replacement in portable["replacements"]:
                text = text.replace(replacement["original"], replacement["portable"])
            published = safe_path(row["path"]).read_bytes()
            require(published == text.encode("utf-8"), "Non-path-only portable change: " + row["path"])
            require(len(published) == row["portable_size_bytes"] and digest(published) == row["portable_sha256"], "Portable checksum mismatch")
            require(row["path_substitutions_applied"] == (original != published), "Portable substitution flag mismatch")
        summary = json.loads(z.read("summary.json"))
        require(summary["environment"]["git_revision"]["stdout"] == EXPECTED_REVISION, "Wrong native revision")
        require(summary["status"] == "PASS_REQUESTED_SCOPES" and summary["full_service_acceptance_passed"] is True, "Corrected acceptance status mismatch")
        statuses = {c["case"]: c["status"] for c in summary["cases"]}
        require(statuses == {"controls": "PASS", "display-probe": "PASS", "full-sift": "PASS", "full-mops": "PASS", "no-files": "PASS", "missing-marker": "PASS", "missing-round": "PASS"}, "Unexpected native case statuses")
        for case in ("full-sift", "full-mops"):
            report = json.loads(z.read(case + "/report.json"))
            require(sum(c["status"] == "PASS" for c in report["checks"]) == 9 and sum(c["status"] == "NOT_RUN" for c in report["checks"]) == 2 and len(report["checks"]) == 11, "Wrong corrected check counts")
            calibration = next(c for c in report["checks"] if c["id"] == "saved_calibration")["metrics"]
            require(calibration["input"] == calibration["aligned"] == calibration["common"], "Calibration metrics differ")
            preserved = next(c for c in report["checks"] if c["id"] == "source_files_preserved")["metrics"]["hashes"]
            for name, expected in preserved.items():
                require(digest(z.read(case + "/inputs/" + name)) == expected, "Input TIFF hash mismatch")
            outputs = next(c for c in report["checks"] if c["id"] == "final_dialog_cancel_preserves_results")["metrics"]["output_hashes_unchanged"]
            for name, expected in outputs.items():
                require(digest(z.read(case + "/output/Results/" + name)) == expected, "Output hash mismatch")

    snapshots = load("independent/source-snapshot/manifest.json")
    require(snapshots["revision"] == EXPECTED_REVISION, "Wrong source snapshot revision")
    for row in snapshots["files"]:
        b = safe_path(row["packet_path"]).read_bytes()
        require(len(b) == row["size_bytes"] and digest(b) == row["sha256"] == summary["environment"]["production_sources"][row["source_path"]], "Historical source mismatch")

    terminal = load("separate-run-metadata/terminal-ci-status.json")
    job = terminal["jobs"]["jobs"][0]
    require(terminal["run_id"] == job["run_id"] == 37380708003 and terminal["source_commit"] == EXPECTED_REVISION, "Terminal native identity mismatch")
    require(job["id"] == 112001650098 and job["status"] == "completed" and job["conclusion"] == "success", "Terminal native status mismatch")
    artifact_metadata = load("separate-run-metadata/artifact-ci-status.json")
    artifact = artifact_metadata["artifacts"]["artifacts"][0]
    require(artifact_metadata["run_id"] == artifact["workflow_run"]["id"] == 37380708003 and artifact["workflow_run"]["head_sha"] == EXPECTED_REVISION, "Connector artifact/run identity mismatch")
    require(artifact["id"] == 11373712129 and artifact["size_in_bytes"] == 398562 and artifact["digest"] == "sha256:" + EXPECTED_ARCHIVE_SHA256, "Connector artifact digest mismatch")
    audit = load("independent/provenance.json")
    require(audit["system"] == "Linux" and audit["machine"] == "x86_64", "Independent audit scope mismatch")
    native_ij = next(j for j in summary["environment"]["root_classpath"] if j["path"].endswith("/ij-1.54p.jar"))
    require(audit["imagej"]["sha256"] == native_ij["sha256"], "ImageJ audit/native dependency mismatch")
    require(len(audit["commands"]) == 4, "Wrong audit command count")
    for command in audit["commands"]:
        require(command["exit_code"] == 0 and digest(safe_path(command["log"]).read_bytes()) == command["sha256"], "Audit completion/log mismatch")
    for name in ("independent-output-review.log",):
        require((ROOT / "independent" / name).read_bytes() == (ROOT / "independent/original-review" / name).read_bytes(), "Repeated audit did not match original: " + name)

    comparison = load("comparison/paired-comparison.json")
    before_archive = ROOT / comparison["before"]["archive_path"]
    require(before_archive.is_file(), "Adjacent failed packet is required for paired verification")
    require(digest(before_archive.read_bytes()) == comparison["before"]["archive_sha256"] == "5fb5df261efbb1666b1427c53b62fc7fc4b8e534456273a3c0109e8ad3a63985", "Paired old archive mismatch")
    require(comparison["after"]["archive_sha256"] == EXPECTED_ARCHIVE_SHA256 and comparison["after"]["revision"] == EXPECTED_REVISION, "Paired corrected identity mismatch")
    with zipfile.ZipFile(before_archive) as before_zip, zipfile.ZipFile(archive) as after_zip:
        before_summary = json.loads(before_zip.read("summary.json"))
        require(before_summary["status"] == "FAIL" and before_summary["full_service_acceptance_passed"] is False, "Paired old failure status changed")
        require(before_summary["environment"]["harness_sources"] == summary["environment"]["harness_sources"], "Harness hashes changed")
        require(len(comparison["harness_sources"]) == 5, "Wrong harness comparison count")
        for row in comparison["harness_sources"]:
            require(row["before_sha256"] == row["after_sha256"] == summary["environment"]["harness_sources"][row["path"]] and row["git_blobs_byte_identical"] is True, "Harness comparison mismatch")
        require(before_summary["dependencies"] == summary["dependencies"] == comparison["unchanged_dependencies"], "Pinned dependencies changed")
        require(before_summary["official_command_audit"] == summary["official_command_audit"], "Command audit changed")
        jar_pairs = lambda s: sorted((Path(j["path"]).name, j["sha256"]) for j in s["environment"]["root_classpath"])
        require(jar_pairs(before_summary) == jar_pairs(summary) and len(jar_pairs(summary)) == comparison["root_classpath_jar_count"] == 97, "Runtime JAR identities changed")
        require(len(comparison["retained_inputs"]) == 18, "Wrong paired input count")
        expected_inputs = {name for name in after_zip.namelist() if name.startswith(("full-sift/inputs/", "full-mops/inputs/"))}
        require({row["path"] for row in comparison["retained_inputs"]} == expected_inputs, "Paired input set mismatch")
        for row in comparison["retained_inputs"]:
            a, b = before_zip.read(row["path"]), after_zip.read(row["path"])
            require(a == b and len(b) == row["size_bytes"] and digest(a) == row["before_sha256"] == row["after_sha256"] and row["byte_identical"] is True, "Paired retained TIFF differs")
        actual_changed = {name for name, value in summary["environment"]["production_sources"].items() if value != before_summary["environment"]["production_sources"][name]}
        require(len(actual_changed) == 3 and actual_changed == {row["path"] for row in comparison["production_source_changes"]}, "Wrong production change set")
        for row in comparison["production_source_changes"]:
            require(row["before_sha256"] == before_summary["environment"]["production_sources"][row["path"]] and row["after_sha256"] == summary["environment"]["production_sources"][row["path"]], "Production comparison hash mismatch")

    require(len(audit["native_metric_comparisons"]) == 12, "Wrong independent/native metric comparison count")
    for row in audit["native_metric_comparisons"]:
        report = load(row["case"] + "/report.json")
        if "channel" in row:
            channels = next(c for c in report["checks"] if c["id"] == "every_round_and_channel_transform")["metrics"]["channels"]
            native = next(c for c in channels if c["source_file"] == row["channel"])
            require(row["before_mse"] == native["before_mse"] and row["after_mse"] == native["after_mse"], "Independent/native MSE mismatch")
        else:
            native = next(c for c in report["checks"] if c["id"] == "landmark_zip_roundtrip")["metrics"]["pairs"][row["pair"] - 1]
            require(row["point_count"] == native["point_count"] and row["mean_error_px"] == native["mean_translation_error_px"], "Independent/native ROI mismatch")
        require(row["exact_native_metric_match"] is True, "Metric comparison flag mismatch")

    print("PASS: " + str(len(actual_files)) + " packet files; original ZIP 398562 bytes; all 77 members verified")
    print("PASS: 34 exact portable text copies, corrected source snapshots, terminal CI metadata, and independent audit logs verified")
    print("PASS: 18 byte-identical old/new input TIFFs, five identical harness sources, 97 identical runtime JAR identities")
    print("PASS: all eight later-channel MSE pairs and four ROI errors match independent/native reports exactly")
    print("Native acceptance is PASS_REQUESTED_SCOPES: both full routes retain nine PASS and two NOT_RUN checks")



if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Read-only integrity and provenance verification; no network or writes."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile

ROOT = Path(__file__).resolve().parent
EXPECTED_REVISION = "5a00f6d6a414f5bd59e0b5dc461eb469afda907c"
EXPECTED_ARCHIVE_SHA256 = "5fb5df261efbb1666b1427c53b62fc7fc4b8e534456273a3c0109e8ad3a63985"


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
    require(len(archive_bytes) == archive_info["size_bytes"] == 394926, "Archive size mismatch")
    require(digest(archive_bytes) == archive_info["sha256"] == EXPECTED_ARCHIVE_SHA256, "Archive digest mismatch")
    require(manifest["artifact_id"] == 11372532765, "Wrong artifact id")
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
        require(summary["status"] == "FAIL" and summary["full_service_acceptance_passed"] is False, "Failure status was changed")
        statuses = {c["case"]: c["status"] for c in summary["cases"]}
        require(statuses == {"controls": "PASS", "display-probe": "PASS", "full-sift": "FAIL_ASSERTION", "full-mops": "FAIL_ASSERTION", "no-files": "PASS", "missing-marker": "PASS", "missing-round": "PASS"}, "Unexpected native case statuses")
        for case in ("full-sift", "full-mops"):
            report = json.loads(z.read(case + "/report.json"))
            require({c["id"] for c in report["checks"] if c["status"] == "FAIL"} == {"every_round_and_channel_transform", "saved_calibration", "landmark_zip_roundtrip"}, "Wrong recorded assertions")
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
    require(terminal["run_id"] == job["run_id"] == 37375259755 and terminal["source_commit"] == EXPECTED_REVISION, "Terminal native identity mismatch")
    require(job["id"] == 111995832061 and job["status"] == "completed" and job["conclusion"] == "failure", "Terminal native status mismatch")
    artifact = terminal["artifacts"]["artifacts"][0]
    require(artifact["id"] == 11372532765 and artifact["size_in_bytes"] == 394926 and artifact["digest"] == "sha256:" + EXPECTED_ARCHIVE_SHA256, "Connector artifact identity mismatch")
    earlier = load("separate-run-metadata/preceding-cancelled-run-status.json")
    earlier_job = earlier["jobs"]["jobs"][0]
    require(earlier["run_id"] == 37374110712 and earlier_job["id"] == 111978206214, "Earlier run identity mismatch")
    require(earlier_job["status"] == "completed" and earlier_job["conclusion"] == "cancelled" and earlier["artifacts"]["artifacts"] == [], "Earlier cancellation evidence mismatch")
    require("BlobNotFound" in earlier["terminal_log_lookup"]["error"], "Earlier unavailable log evidence mismatch")

    audit = load("independent/provenance.json")
    require(audit["system"] == "Linux" and audit["machine"] == "x86_64", "Independent audit scope mismatch")
    native_ij = next(j for j in summary["environment"]["root_classpath"] if j["path"].endswith("/ij-1.54p.jar"))
    require(audit["imagej"]["sha256"] == native_ij["sha256"], "ImageJ audit/native dependency mismatch")
    require(len(audit["commands"]) == 4, "Wrong audit command count")
    for command in audit["commands"]:
        require(command["exit_code"] == 0 and digest(safe_path(command["log"]).read_bytes()) == command["sha256"], "Audit completion/log mismatch")
    for name in ("independent-output-review.log", "batch-selection-control.log"):
        require((ROOT / "independent" / name).read_bytes() == (ROOT / "independent/original-review" / name).read_bytes(), "Repeated audit did not match original: " + name)

    print("PASS: " + str(len(actual_files)) + " packet files; original ZIP 394926 bytes; all 77 members verified")
    print("PASS: 34 exact portable text copies, historical source snapshots, native/earlier CI metadata, and isolated audit logs verified")
    print("Native acceptance remains FAIL: full-sift and full-mops each retain three assertion failures")


if __name__ == "__main__":
    main()

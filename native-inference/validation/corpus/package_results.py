#!/usr/bin/env python3
"""Create compact, portable evidence with deterministic, browser-upload-sized outline ZIPs."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

from export_results import reconcile_manifest, summarize

MAX_ARCHIVE_BYTES = 20 * 1024 * 1024


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def partition(entries, maximum=MAX_ARCHIVE_BYTES):
    chunks = []
    current, size = [], 22
    for name, source in sorted(entries):
        # Account conservatively for local + central ZIP headers and both names.
        item_size = source.stat().st_size + 2 * len(name.encode("utf-8")) + 128
        if item_size + 22 > maximum:
            raise ValueError(f"Single outline payload exceeds archive budget: {name}")
        if current and size + item_size > maximum:
            chunks.append(current); current, size = [], 22
        current.append((name, source)); size += item_size
    if current: chunks.append(current)
    return chunks


def write_archive(path, entries):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, source in sorted(entries):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, source.read_bytes())
    if path.stat().st_size >= 25 * 1024 * 1024:
        raise ValueError(f"Archive exceeds browser upload limit: {path.name}")


def save(path, obj):
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--core", type=Path, required=True, help="Complete portable export of 180 core cases")
    parser.add_argument("--supplement", type=Path, required=True, help="Complete portable export of 191 supplement cases")
    parser.add_argument("--controls", type=Path, required=True, help="Completed sensitivity control output directory")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--production-commit", required=True)
    parser.add_argument("--outlier-overlap", type=Path, help="Independent compact moved-center object-overlap evidence")
    parser.add_argument("--mac-smoke", type=Path, help="Separate verified native-Mac smoke evidence, distinct from this Linux corpus")
    args = parser.parse_args()
    sources = {"core": args.core.resolve(), "supplement": args.supplement.resolve()}
    all_cases, summaries = [], {}
    for name, expected in (("core", 180), ("supplement", 191)):
        summary = json.loads((sources[name] / "summary.json").read_text())
        if (summary["expected_cases"] != expected or summary["compared_cases"] != expected
                or not summary["all_expected_cases_have_outline_check"]
                or summary["comparison_failed_cases"] != 0
                or summary["manifest_reconciliation"]["missing_case_ids"]):
            raise ValueError(f"{name} evidence is incomplete or inconsistent")
        cases = json.loads((sources[name] / "cases.json").read_text())
        with (sources[name] / "manifest.tsv").open() as stream:
            manifest_rows = list(csv.DictReader(stream, delimiter="\t"))
        reconciliation = reconcile_manifest(manifest_rows, cases, expected)
        if reconciliation["missing_case_ids"]:
            raise ValueError(f"{name} has missing case evidence")
        for field, value in summarize(cases, expected).items():
            if summary.get(field) != value:
                raise ValueError(f"{name} summary does not match its actual cases: {field}")
        summaries[name] = summary
        all_cases.extend(cases)
    controls = json.loads((args.controls / "sensitivity.json").read_text())
    if not controls.get("complete") or not controls.get("input_still_matches_manifest"):
        raise ValueError("Sensitivity controls are incomplete or input integrity failed")
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError("Output must be new or empty; avoid leaving stale evidence artifacts")
    output.mkdir(parents=True, exist_ok=True)
    entries = []
    for name, source in sources.items():
        destination = output / name
        destination.mkdir()
        for path in source.iterdir():
            if path.is_file() and path.suffix in (".json", ".csv", ".tsv"):
                shutil.copyfile(path, destination / path.name)
        entries.extend((name + "/outlines/" + path.name, path) for path in (source / "outlines").glob("*.gz"))
    (output / "controls").mkdir()
    save(output / "controls/sensitivity.json", controls)
    shutil.copyfile(Path(__file__).with_name("REGRESSION_REPORT.md"), output / "REPORT.md")
    if args.outlier_overlap:
        save(output / "controls/moved-center-object-overlap.json", json.loads(args.outlier_overlap.read_text()))
    if args.mac_smoke:
        save(output / "native-mac-smoke.json", json.loads(args.mac_smoke.read_text()))
    entries.extend(("controls/outlines/" + path.name, path) for path in (args.controls / "outlines").glob("*.gz"))
    archive_map, manifest, archives = {}, [], []
    for index, chunk in enumerate(partition(entries), 1):
        archive_name = f"outline-payloads-{index:03d}.zip"
        path = output / archive_name
        write_archive(path, chunk)
        archives.append({"path": archive_name, "sha256": digest(path), "bytes": path.stat().st_size})
        for name, source in chunk:
            archive_map[name] = archive_name
            manifest.append({"path_after_extraction": name, "archive": archive_name,
                             "sha256": digest(source), "bytes": source.stat().st_size})
    save(output / "outline-sha256.json", {"archives": archives, "payloads": manifest})
    for name in sources:
        path = output / name / "cases.json"
        cases = json.loads(path.read_text())
        for case in cases:
            for artifact in case.get("polygon_artifacts", []):
                entry = name + "/" + artifact["path"]
                artifact["archive"] = "../" + archive_map[entry]
                artifact["archive_entry"] = entry
                artifact["path_note"] = "Available after extracting the indicated archive at the results root"
        save(path, cases)
    input_hashes = {case["metadata"]["input_sha256"] for case in all_cases}
    source_hashes = {str(path.relative_to(Path(__file__).parent)): digest(path)
                     for path in Path(__file__).parent.rglob("*")
                     if path.is_file() and path.suffix in (".py", ".java", ".md") and "results" not in path.parts}
    combined = {"production_source_commit": args.production_commit, "case_count": len(all_cases),
                "distinct_pixel_inputs": len(input_hashes), "input_pixels": sum(s["input_pixels"] for s in summaries.values()),
                "count_difference_cases": sum(s["count_difference_cases"] for s in summaries.values()),
                "exact_label_raster_and_measurement_cases": sum(s["exact_label_raster_and_measurement_cases"] for s in summaries.values()),
                "label_id_order_only_cases": sum(s["label_id_order_only_cases"] for s in summaries.values()),
                "geometry_count_or_measurement_change_cases": sum(s["geometry_count_or_measurement_change_cases"] for s in summaries.values()),
                "all_cases_have_outline_checks": True, "groups": summaries,
                "sensitivity_controls_complete": True, "validation_source_sha256": source_hashes,
                "interpretation": "Technical runtime consistency on Linux CPU; training, source-labeled test, static crops and out-of-domain temporal frames are separate strata. Any native-Mac smoke is separate narrow evidence, not broad native-Mac corpus validation or biological accuracy"}
    save(output / "summary.json", combined)
    (output / "README.md").write_text("# GAT runtime regression evidence\n\n"
        "Production source commit: `" + args.production_commit + "`.\n\n"
        "Core: 180 archive files / 178 distinct inputs. Supplement: 49 static cases plus 142 calcium frames / 190 distinct inputs. "
        "Overall: 371 cases / 368 distinct pixel inputs. Refer to each summary for exact results and limitations. "
        "Counts refer to StarDist NMS, not the complete GAT workflow or unique biological cells.\n\n"
        "The core and supplement directories contain human-readable case JSON/CSV, reconciled manifests, summaries and provenance. "
        "The controls directory contains repeatability and configuration sensitivity evidence. Large raw prediction tensors and source images are deliberately excluded.\n\n"
        "## Outline payloads\n\n"
        "All paired gzip polygon payloads are stored in deterministic numbered ZIP archives, each below 25 MiB. "
        "Extract every `outline-payloads-*.zip` into this results directory; this creates `core/outlines/`, `supplement/outlines/` and `controls/outlines/`. "
        "`outline-sha256.json` records each archive and each extracted payload's SHA-256 and size. "
        "The gzip payload is the documented big-endian GATP version-1 format.\n\n"
        "Geometry delta maxima cover only matched winning centers. Consult unmatched-center counts and the complete per-object measurements for NMS candidate changes. "
        "Global IoU can hide a larger local change in one cell. These cross-runtime corpus tests ran on Linux CPU. "
        "If present, `native-mac-smoke.json` records separate, narrower native-Mac CI evidence and its exact job link; it does not establish broad Mac corpus parity.\n")
    checksums = []
    for path in sorted(output.rglob("*")):
        if path.is_file(): checksums.append(digest(path) + "  " + str(path.relative_to(output)))
    (output / "SHA256SUMS").write_text("\n".join(checksums) + "\n")
    print(json.dumps({"files": len(checksums) + 1, "archives": archives, "cases": len(all_cases)}, indent=2))


if __name__ == "__main__":
    main()

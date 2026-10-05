#!/usr/bin/env python3
"""Export portable, explicitly complete/partial public regression evidence."""
import argparse
import collections
import csv
import hashlib
import shutil
from datetime import datetime, timezone
import json
from pathlib import Path


def portable(value, corpus):
    if isinstance(value, dict):
        return {key: portable(item, corpus) for key, item in value.items() if key != "traceback"}
    if isinstance(value, list):
        return [portable(item, corpus) for item in value]
    if isinstance(value, str):
        if value.startswith(str(corpus) + "/"):
            return str(Path(value).relative_to(corpus))
        if value.startswith(("/workspace/", "/tmp/")):
            return Path(value).name
    return value


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def classify(row):
    if row.get("status") != "compared": return "comparison_failed"
    metric = row["metrics"]
    equivalent = (metric["modern_count"] == metric["legacy_count"]
                  and metric["different_canonical_label_pixels"] == 0
                  and metric["different_foreground_pixels"] == 0
                  and metric["pixel_measurements_equal"])
    if not equivalent: return "geometry_count_or_measurement_change"
    if not metric["winner_centers_equal"]: return "winner_center_only"
    if metric["different_label_pixels"] != 0: return "label_id_order_only"
    return "exact_labels_and_measurements"


def summarize(rows, expected):
    summary = {
        "expected_cases": expected,
        "terminal_cases": len(rows),
        "all_expected_cases_terminal": len(rows) == expected,
        "compared_cases": 0,
        "comparison_failed_cases": 0,
        "exact_label_raster_and_measurement_cases": 0,
        "nonidentical_label_raster_or_measurement_cases": 0,
        "outline_checked_cases": 0,
        "strict_quantized_outline_match_cases": 0,
        "quantized_outline_difference_cases": 0,
        "cases_with_unmatched_outline_centers": 0,
        "unmatched_modern_outline_centers": 0,
        "unmatched_legacy_outline_centers": 0,
        "outline_ray_count_mismatches": 0,
        "outline_delta_scope": "Vertex/perimeter/polygon-area delta maxima cover matched winning centers only; unmatched centers are explicitly counted and require separate object-level analysis",
        "outlines_with_changed_vertices": 0,
        "changed_outline_vertices": 0,
        "max_abs_vertex_coordinate_delta_px": 0,
        "max_euclidean_vertex_delta_px": 0,
        "max_abs_polygon_perimeter_delta_px": 0,
        "max_abs_polygon_area_delta_px2": 0,
        "equivalent_geometry_count_measurement_cases": 0,
        "label_id_order_only_cases": 0,
        "winner_center_only_cases": 0,
        "geometry_count_or_measurement_change_cases": 0,
        "numeric_flag_cases": 0,
        "input_pixels": 0,
        "modern_objects": 0,
        "legacy_objects": 0,
        "different_label_pixels": 0,
        "different_canonical_label_pixels": 0,
        "different_foreground_pixels": 0,
        "count_difference_cases": 0,
        "measurement_difference_cases": 0,
        "winner_center_difference_cases": 0,
        "probability_threshold_flips": 0,
        "values_outside_atol_1e_minus_4_rtol_1e_minus_4": 0,
        "max_abs_probability": 0,
        "max_abs_distance": 0,
    }
    for row in rows:
        if row.get("status") != "compared":
            summary["comparison_failed_cases"] += 1
            continue
        metric = row["metrics"]
        summary["compared_cases"] += 1
        category = classify(row)
        summary["exact_label_raster_and_measurement_cases" if category == "exact_labels_and_measurements"
                else "nonidentical_label_raster_or_measurement_cases"] += 1
        if "strict_quantized_outlines_equal" in metric:
            summary["outline_checked_cases"] += 1
            summary["strict_quantized_outline_match_cases" if metric["strict_quantized_outlines_equal"]
                    else "quantized_outline_difference_cases"] += 1
            summary["cases_with_unmatched_outline_centers"] += bool(
                metric["unmatched_modern_outline_centers"] or metric["unmatched_legacy_outline_centers"])
            for name in ("unmatched_modern_outline_centers", "unmatched_legacy_outline_centers", "outline_ray_count_mismatches"):
                summary[name] += metric[name]
            for name in ("outlines_with_changed_vertices", "changed_outline_vertices"):
                summary[name] += metric[name]
            for name in ("max_abs_vertex_coordinate_delta_px", "max_euclidean_vertex_delta_px",
                         "max_abs_polygon_perimeter_delta_px", "max_abs_polygon_area_delta_px2"):
                summary[name] = max(summary[name], metric[name])
        if category != "geometry_count_or_measurement_change":
            summary["equivalent_geometry_count_measurement_cases"] += 1
        if category in ("label_id_order_only", "winner_center_only", "geometry_count_or_measurement_change"):
            summary[category + "_cases"] += 1
        outside = metric.get("values_outside_atol_1e_minus_4_rtol_1e_minus_4", 0)
        summary["numeric_flag_cases"] += bool(outside or metric["probability_threshold_flips"])
        summary["values_outside_atol_1e_minus_4_rtol_1e_minus_4"] += outside
        summary["probability_threshold_flips"] += metric["probability_threshold_flips"]
        summary["input_pixels"] += metric["width"] * metric["height"]
        summary["modern_objects"] += metric["modern_count"]
        summary["legacy_objects"] += metric["legacy_count"]
        for name in ("different_label_pixels", "different_canonical_label_pixels", "different_foreground_pixels"):
            summary[name] += metric[name]
        summary["count_difference_cases"] += metric["modern_count"] != metric["legacy_count"]
        summary["measurement_difference_cases"] += not metric["pixel_measurements_equal"]
        summary["winner_center_difference_cases"] += not metric["winner_centers_equal"]
        for name in ("max_abs_probability", "max_abs_distance"):
            summary[name] = max(summary[name], metric[name])
    summary["all_expected_cases_have_outline_check"] = summary["outline_checked_cases"] == expected
    return summary


def reconcile_manifest(manifest, rows, expected):
    """Reject inconsistent evidence; missing results are an explicit partial export."""
    if expected != len(manifest):
        raise ValueError(f"--expected {expected} does not match manifest size {len(manifest)}")
    records = {}
    for entry in manifest:
        case_id = entry.get("case_id")
        if not case_id or case_id in records:
            raise ValueError(f"Missing or duplicate manifest case ID: {case_id}")
        for field in ("input_sha256", "model", "split", "width", "height", "tiles"):
            if field not in entry or entry[field] in (None, ""):
                raise ValueError(f"Manifest case {case_id} is missing {field}")
        records[case_id] = entry
    seen = set()
    for row in rows:
        case_id = row.get("case_id")
        if case_id in seen:
            raise ValueError(f"Duplicate result case ID: {case_id}")
        if case_id not in records:
            raise ValueError(f"Unknown result case ID: {case_id}")
        seen.add(case_id)
        metadata = row.get("metadata", {})
        if metadata.get("case_id") != case_id:
            raise ValueError(f"Result and metadata case IDs disagree: {case_id}")
        expected_row = records[case_id]
        for field in ("input_sha256", "model", "split"):
            if metadata.get(field) != expected_row[field]:
                raise ValueError(f"Result {case_id} has inconsistent {field}")
        for field in ("width", "height", "tiles"):
            if field not in metadata or int(metadata[field]) != int(expected_row[field]):
                raise ValueError(f"Result {case_id} has inconsistent {field}")
        if row.get("status") not in ("compared", "comparison_failed"):
            raise ValueError(f"Result {case_id} has an unsupported status")
        if row["status"] == "compared":
            for field in ("width", "height"):
                if int(row.get("metrics", {}).get(field, -1)) != int(expected_row[field]):
                    raise ValueError(f"Result {case_id} tensor {field} differs from manifest")
    return {"manifest_cases": len(records), "result_cases": len(seen),
            "missing_case_ids": sorted(set(records) - seen),
            "unknown_case_ids": [], "duplicate_case_ids": [],
            "metadata_consistent": True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected", type=int, required=True)
    args = parser.parse_args()
    corpus, output = args.corpus.resolve(), args.output.resolve()
    with (corpus / "manifest.tsv").open() as stream:
        manifest = list(csv.DictReader(stream, delimiter="\t"))
    source_rows = []
    paths = sorted((corpus / "review/results").glob("*.json"))
    for path in paths:
        row = json.loads(path.read_text())
        if path.stem != row.get("case_id"):
            raise ValueError(f"Result filename and case ID disagree: {path.name}")
        source_rows.append(row)
    reconciliation = reconcile_manifest(manifest, source_rows, args.expected)
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for path, source_row in zip(paths, source_rows):
        row = portable(source_row, corpus)
        metrics = row.get("metrics", {})
        artifacts = []
        for relative in row.get("polygon_artifacts", []):
            source = (corpus / relative).resolve()
            if not source.is_relative_to(corpus):
                raise ValueError("Polygon artifact must remain inside its corpus root")
            destination = output / "outlines" / source.name
            destination.parent.mkdir(exist_ok=True)
            shutil.copyfile(source, destination)
            artifacts.append({"path": "outlines/" + source.name,
                              "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
                              "format": "gzip-compressed GATP binary version 1"})
        if artifacts: row["polygon_artifacts"] = artifacts
        # The local comparator's abbreviated key denotes 10^-4, not 10^4.
        if "outside_atol_1e4_rtol_1e4" in metrics:
            metrics["values_outside_atol_1e_minus_4_rtol_1e_minus_4"] = metrics.pop("outside_atol_1e4_rtol_1e4")
        row["pixel_difference_category"] = classify(row)
        row["exact_label_raster_and_measurement_match"] = row["pixel_difference_category"] == "exact_labels_and_measurements"
        row["comparison_schema"] = 2 if "strict_quantized_outlines_equal" in metrics else 1
        prior_path = corpus / "review/results-v1" / path.name
        if prior_path.exists():
            prior = json.loads(prior_path.read_text())
            previous_metrics = prior.get("metrics", {})
            row["prior_raster_review"] = {
                "comparator_source_sha256": prior.get("comparator_source_sha256"),
                "modern_tensor_sha256": previous_metrics.get("modern_tensor_sha256"),
                "legacy_tensor_sha256": previous_metrics.get("legacy_tensor_sha256"),
                "outline_replay_pending": row["comparison_schema"] < 2,
                "replayed_tensor_hashes_identical": (None if row["comparison_schema"] < 2 else
                    metrics.get("modern_tensor_sha256") == previous_metrics.get("modern_tensor_sha256") and
                    metrics.get("legacy_tensor_sha256") == previous_metrics.get("legacy_tensor_sha256"))}

        row["outline_difference_category"] = ("not_checked" if row["comparison_schema"] == 1 else
            "exact_quantized_outlines" if metrics["strict_quantized_outlines_equal"] else "quantized_outline_difference")
        rows.append(row)
    summary = summarize(rows, args.expected)
    summary["manifest_reconciliation"] = reconciliation
    summary["all_expected_cases_terminal"] = not reconciliation["missing_case_ids"]
    summary["all_expected_cases_successfully_compared"] = (
        summary["all_expected_cases_terminal"] and summary["compared_cases"] == args.expected)
    summary["compared_unique_input_contents"] = len({row["metadata"]["input_sha256"]
        for row in rows if row.get("status") == "compared"})
    summary["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
    summary["interpretation"] = "Legacy-versus-modern technical consistency; not biological accuracy, full GAT workflow equivalence, or evidence of native Apple hardware execution"
    groups = collections.defaultdict(list)
    input_groups = collections.defaultdict(list)
    for row in manifest:
        input_groups[row["input_sha256"]].append({"case_id": row["case_id"], "model": row["model"], "split": row["split"]})
    summary["expected_unique_input_contents"] = len(input_groups)
    summary["duplicate_input_groups"] = [{"input_sha256": digest, "cases": cases}
        for digest, cases in input_groups.items() if len(cases) > 1]
    test_inputs = {row["input_sha256"] for row in manifest if row["split"] == "test"}
    train_inputs = {row["input_sha256"] for row in manifest if row["split"] == "train"}
    summary["source_labeled_test_files"] = sum(row["split"] == "test" for row in manifest)
    summary["distinct_source_test_inputs"] = len(test_inputs)
    summary["test_input_contents_also_in_train"] = len(test_inputs & train_inputs)
    summary["duplication_note"] = "Exact pixel-input hashes only; absence of an exact duplicate does not establish statistically independent samples"
    counts = collections.Counter(row["model"] + "/" + row["split"] for row in manifest)
    for row in rows:
        groups[row["metadata"]["model"] + "/" + row["metadata"]["split"]].append(row)
    summary["by_model_and_split"] = {key: summarize(groups[key], count) for key, count in sorted(counts.items())}
    with (output / "manifest.tsv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(manifest[0]) if manifest else [], delimiter="\t")
        writer.writeheader()
        writer.writerows(portable(entry, corpus) for entry in manifest)
    write_json(output / "summary.json", summary)
    write_json(output / "cases.json", rows)
    controls = {}
    for name in ("sanity-neuron.json", "negative-control.json"):
        path = corpus / "review" / name
        if path.exists(): controls[name] = portable(json.loads(path.read_text()), corpus)
    if controls: write_json(output / "comparator-controls.json", controls)
    provenance = corpus / "provenance.json"
    if provenance.exists(): write_json(output / "provenance.json", portable(json.loads(provenance.read_text()), corpus))
    fields = ["case_id", "model", "split", "source_path", "input_sha256", "width", "height", "tiles", "status", "pixel_difference_category", "exact_label_raster_and_measurement_match", "outline_difference_category",
              "probability_threshold", "nms_threshold", "modern_count", "legacy_count", "different_label_pixels", "different_canonical_label_pixels",
              "different_foreground_pixels", "pixel_measurements_equal", "winner_centers_equal", "max_abs_probability", "max_abs_distance",
              "probability_threshold_flips", "values_outside_atol_1e_minus_4_rtol_1e_minus_4",
              "strict_quantized_outlines_equal", "unmatched_modern_outline_centers", "unmatched_legacy_outline_centers", "outlines_with_changed_vertices", "changed_outline_vertices",
              "max_abs_vertex_coordinate_delta_px", "max_euclidean_vertex_delta_px",
              "max_abs_polygon_perimeter_delta_px", "max_abs_polygon_area_delta_px2"]
    with (output / "cases.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            flattened = {**row["metadata"], **row.get("metrics", {}), "case_id": row["case_id"], "status": row["status"],
                         "exact_label_raster_and_measurement_match": row["exact_label_raster_and_measurement_match"],
                         "pixel_difference_category": row["pixel_difference_category"], "outline_difference_category": row["outline_difference_category"]}
            writer.writerow({field: flattened.get(field, "") for field in fields})
    # Fail export if a known local absolute machine path was accidentally retained.
    for path in output.glob("*"):
        if path.suffix not in (".json", ".csv", ".tsv"): continue
        content = path.read_text()
        if "/workspace/" in content or "/tmp/" in content:
            raise ValueError(f"Machine-specific path remains in {path.name}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

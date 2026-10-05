#!/usr/bin/env python3
"""Diagnostic comparison to BOTH fixed outlier references; never tune acceptance limits.

A completed diagnostic can report differences from either or both references.
Its zero exit status means successful measurement, not segmentation equivalence.
"""
import argparse
import gzip
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import time

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("gat_hu_reference", ROOT.parent / "cross-platform/check.py")
hu = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hu)
ATOL = RTOL = 1e-4


def prepare_nms(cache, java="java", javac="javac"):
    command = hu.prepare_nms(cache, java, javac)
    classes, classpath = cache / "classes", command[-2]
    subprocess.run([javac, "-encoding", "UTF-8", "-cp", classpath, "-d", str(classes),
                    str(ROOT / "MovedCenterNms.java")], check=True, timeout=180)
    return [java, "-Xmx2g", "-XX:-UsePerfData"] + command[1:-1] + ["MovedCenterNms"]


def input_pixels(path, width, height):
    data = path.read_bytes()
    if len(data) != 16 + width * height * 4 or struct.unpack(">4i", data[:16]) != (0x47415449, 1, width, height):
        raise AssertionError("Wrong fixed GATI fixture shape or size")
    values = struct.unpack(f">{width * height}f", data[16:])
    if not all(math.isfinite(v) for v in values):
        raise AssertionError("Non-finite input")
    return values


def measurements(labels, pixels, width, height):
    result = hu.label_summary(labels, pixels, width)
    extra = {}
    for p, label in enumerate(labels):
        if not label:
            continue
        x, y = p % width, p // width
        row = extra.setdefault(label, {"bbox": [x, y, x, y], "perimeter_4_neighbor_pixels": 0})
        box = row["bbox"]
        box[0], box[1], box[2], box[3] = min(box[0], x), min(box[1], y), max(box[2], x), max(box[3], y)
        row["perimeter_4_neighbor_pixels"] += ((x == 0 or labels[p-1] != label)
            + (x == width-1 or labels[p+1] != label)
            + (y == 0 or labels[p-width] != label)
            + (y == height-1 or labels[p+width] != label))
    for row in result["measurements"]:
        row.update(extra[row["label"]])
    return result


def read_polygons(path, width, height):
    with gzip.open(path, "rb") as stream:
        raw = stream.read()
    if len(raw) < 20:
        raise AssertionError("Short polygon payload")
    magic, version, w, h, count = struct.unpack_from(">5i", raw)
    if (magic, version, w, h) != (0x47415450, 1, width, height) or count < 0 or count > width * height:
        raise AssertionError("Invalid polygon header")
    offset, polygons = 20, {}
    for _ in range(count):
        x, y, rays = struct.unpack_from(">ffi", raw, offset); offset += 12
        if rays != 96 or not math.isfinite(x) or not math.isfinite(y):
            raise AssertionError("Invalid polygon center/ray count")
        values = struct.unpack_from(f">{rays * 2}f", raw, offset); offset += rays * 8
        if not all(math.isfinite(v) for v in values) or (x, y) in polygons:
            raise AssertionError("Invalid or duplicate polygon")
        polygons[x, y] = list(zip(values[::2], values[1::2]))
    if offset != len(raw):
        raise AssertionError("Trailing polygon bytes")
    return polygons


def polygon_measurements(points):
    perimeter, area = 0.0, 0.0
    for (x, y), (nx, ny) in zip(points, points[1:] + points[:1]):
        perimeter += math.hypot(nx-x, ny-y); area += x*ny-nx*y
    return {"perimeter_px": perimeter, "area_px2": abs(area)/2}


def outline_comparison(reference, actual):
    common = sorted(reference.keys() & actual.keys())
    max_coordinate = max_euclidean = max_area = max_perimeter = 0.0
    changed_vertices = 0
    for center in common:
        first, second = reference[center], actual[center]
        if len(first) != len(second):
            raise AssertionError("Ray count differs")
        for (x, y), (nx, ny) in zip(first, second):
            dx, dy = abs(nx-x), abs(ny-y)
            changed_vertices += (dx != 0 or dy != 0)
            max_coordinate = max(max_coordinate, dx, dy)
            max_euclidean = max(max_euclidean, math.hypot(dx, dy))
        r, a = polygon_measurements(first), polygon_measurements(second)
        max_area = max(max_area, abs(a["area_px2"]-r["area_px2"]))
        max_perimeter = max(max_perimeter, abs(a["perimeter_px"]-r["perimeter_px"]))
    return {"scope": "Delta maxima cover matched winning centers only",
            "matched_centers": len(common), "unmatched_reference_centers": sorted(reference.keys()-actual.keys()),
            "unmatched_actual_centers": sorted(actual.keys()-reference.keys()),
            "changed_vertices_at_matched_centers": changed_vertices,
            "max_abs_coordinate_delta_px": max_coordinate, "max_euclidean_vertex_delta_px": max_euclidean,
            "max_abs_polygon_area_delta_px2": max_area, "max_abs_polygon_perimeter_delta_px": max_perimeter,
            "strict_quantized_outlines_equal": reference == actual}


def affected_overlap(reference_labels, actual_labels, reference_id, reference, actual):
    intersections = {}
    reference_area = sum(label == reference_id for label in reference_labels)
    for old, new in zip(reference_labels, actual_labels):
        if old == reference_id and new:
            intersections[new] = intersections.get(new, 0) + 1
    areas = {row["label"]: row["area_pixels"] for row in actual["measurements"]}
    if not intersections:
        return {"reference_label": reference_id, "matched_actual_label": None, "iou": 0.0, "dice": 0.0}
    best = max(intersections, key=lambda label: (intersections[label] / (reference_area + areas[label] - intersections[label]), -label))
    intersection, area = intersections[best], areas[best]
    ref_center, actual_center = reference["winner_centers"][reference_id-1], actual["winner_centers"][best-1]
    return {"matching_method": "maximum filled-mask IoU across all actual labels; ties prefer lower label ID",
            "reference_label": reference_id, "matched_actual_label": best,
            "reference_center": ref_center, "actual_center": actual_center,
            "reference_area_pixels": reference_area, "actual_area_pixels": area,
            "intersection_pixels": intersection, "union_pixels": reference_area+area-intersection,
            "iou": intersection/(reference_area+area-intersection), "dice": 2*intersection/(reference_area+area)}


def compare(reference_prefix, actual_prefix, pixels, width, height, affected_label=104):
    count = len(pixels)
    expected = json.loads(Path(str(reference_prefix)+".summary.json").read_text())
    observed = json.loads(Path(str(actual_prefix)+".nms.json").read_text())
    ref_labels = hu.read_values(Path(str(reference_prefix)+".labels.u16be"), "H", count)
    got_labels = hu.read_values(Path(str(actual_prefix)+".labels.u16be"), "H", count)
    ref_prob = hu.read_values(Path(str(reference_prefix)+".probability.f32be"), "f", count)
    got_prob = hu.read_values(Path(str(actual_prefix)+".probability.f32be"), "f", count)
    if not all(math.isfinite(p) and 0 <= p <= 1 for p in ref_prob + got_prob):
        raise AssertionError("Invalid probability values")
    observed.update(measurements(got_labels, pixels, width, height))
    calculated_ref = measurements(ref_labels, pixels, width, height)
    if any(expected.get(k) != v for k, v in calculated_ref.items()):
        raise AssertionError("Reference measurement summary does not match its fixed labels/input")
    differences = [abs(a-b) for a, b in zip(ref_prob, got_prob)]
    probability_failures = sum(error > ATOL + RTOL*abs(ref) for ref, error in zip(ref_prob, differences))
    foreground_union = sum(bool(a or b) for a, b in zip(ref_labels, got_labels))
    foreground_intersection = sum(bool(a and b) for a, b in zip(ref_labels, got_labels))
    expected_measurements = {row["label"]: row for row in expected["measurements"]}
    actual_measurements = {row["label"]: row for row in observed["measurements"]}
    changed_measurements = [{"label": label, "reference": expected_measurements.get(label), "actual": actual_measurements.get(label)}
                            for label in sorted(expected_measurements.keys() | actual_measurements.keys())
                            if expected_measurements.get(label) != actual_measurements.get(label)]
    polygons = outline_comparison(read_polygons(Path(str(reference_prefix)+".polygons.gz"), width, height),
                                 read_polygons(Path(str(actual_prefix)+".polygons.gz"), width, height))
    result = {"reference": reference_prefix.name,
              "expected_count": expected["count"], "actual_count": observed["count"],
              "counts_equal": expected["count"] == observed["count"],
              "expected_candidates": expected["candidates"], "actual_candidates": observed["candidates"],
              "candidates_equal": expected["candidates"] == observed["candidates"],
              "winner_centers_and_label_order_equal": expected["winner_centers"] == observed["winner_centers"],
              "raw_label_pixels_differing": sum(a != b for a, b in zip(ref_labels, got_labels)),
              "canonical_masks_equal": expected["canonical_shape_sha256"] == observed["canonical_shape_sha256"],
              "foreground_pixels_differing": sum(bool(a) != bool(b) for a, b in zip(ref_labels, got_labels)),
              "whole_image_foreground_iou": foreground_intersection/foreground_union if foreground_union else 1.0,
              "measurements_equal": not changed_measurements, "measurement_differences_by_label_id": changed_measurements,
              "probability_atol": ATOL, "probability_rtol": RTOL,
              "probability_values_outside_tolerance": probability_failures,
              "probability_max_abs_error": max(differences), "probability_mean_abs_error": sum(differences)/count,
              "probability_threshold_flips": sum((a>0.5) != (b>0.5) for a, b in zip(ref_prob, got_prob)),
              "probability_maps_exact": all(d == 0 for d in differences),
              "distance_maps_compared": False, "outline_comparison": polygons,
              "affected_cell": affected_overlap(ref_labels, got_labels, affected_label, expected, observed),
              "actual_summary": observed}
    result["exact_raster_centers_measurements_match"] = (result["counts_equal"] and result["candidates_equal"]
        and result["winner_centers_and_label_order_equal"] and result["raw_label_pixels_differing"] == 0
        and result["measurements_equal"])
    return result


def extract_fixtures(output, manifest):
    output.mkdir(parents=True, exist_ok=False)
    for name, record in manifest["files"].items():
        source = ROOT / "fixtures" / name
        hu.verify(source, record["sha256"])
        if record["encoding"] not in ("gzip", "identity"):
            raise AssertionError("Unknown fixture encoding")
        raw = gzip.decompress(source.read_bytes()) if record["encoding"] == "gzip" else source.read_bytes()
        if len(raw) != record["extracted_bytes"] or hashlib.sha256(raw).hexdigest() != record["extracted_sha256"]:
            raise AssertionError("Incorrect decompressed fixture: " + name)
        (output / record["extracted_name"]).write_bytes(raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", type=Path)
    parser.add_argument("--models", type=Path)
    parser.add_argument("--prediction", type=Path, help="Compare existing GATO without running inference")
    parser.add_argument("--output", type=Path, required=True, help="New output directory")
    parser.add_argument("--dependencies", type=Path, help="Optional shared pinned-NMS cache")
    parser.add_argument("--java", default="java"); parser.add_argument("--javac", default="javac")
    args = parser.parse_args()
    if not args.prediction and (not args.worker or not args.models):
        parser.error("--worker and --models are required unless --prediction is supplied")
    manifest = json.loads((ROOT / "fixture-manifest.json").read_text())
    if hu.digest(ROOT.parent / "cross-platform/dependencies.json") != manifest["nms_dependencies_manifest_sha256"]:
        raise AssertionError("Pinned NMS dependency manifest changed")
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=False)
    fixtures = output / "fixtures"; extract_fixtures(fixtures, manifest)
    width, height = manifest["width"], manifest["height"]
    pixels = input_pixels(fixtures / "input.gati", width, height)
    nms = prepare_nms((args.dependencies or output / "dependencies").resolve(), args.java, args.javac)
    started = time.perf_counter(); prediction = args.prediction.resolve() if args.prediction else output / "prediction.gato"
    if not args.prediction:
        model = args.models.resolve() / manifest["model"]; hu.verify(model, manifest["model_sha256"])
        worker = args.worker.resolve()
        environment = os.environ.copy(); environment["CUDA_VISIBLE_DEVICES"] = "-1"
        subprocess.run([args.java, "-Xmx3g", "-XX:-UsePerfData", "-cp", str(worker)+os.pathsep+str(worker.parent/"lib/*"),
                        "org.gatanalysis.inference.NativeInferenceMain", str(model), str(fixtures/"input.gati"), str(prediction), "4"],
                       check=True, timeout=1200, env=environment)
    prediction_seconds = time.perf_counter()-started
    actual_prefix = output / "actual"
    subprocess.run(nms+[str(prediction), str(actual_prefix), "0.5"], check=True, timeout=300)
    reports = [compare(fixtures / side, actual_prefix, pixels, width, height) for side in ("legacy", "modern")]
    result = {"diagnostic_complete": True, "scientific_equivalence_claimed": False,
              "production_source_commit": manifest["production_source_commit"], "case_id": manifest["case_id"],
              "input_sha256": manifest["input_sha256"], "expected_model_sha256": manifest["model_sha256"],
              "executed_model_sha256": manifest["model_sha256"] if not args.prediction else None,
              "prediction_origin": "verified model and fixed input executed by this checker" if not args.prediction
                  else "externally supplied tensor; originating input/model/runtime are not attested by this checker",
              "prediction_sha256": hu.digest(prediction), "prediction_seconds": prediction_seconds,
              "inference_executed_by_checker": not bool(args.prediction), "runner": hu.runner_metadata(args.java),
              "worker_jar_sha256": hu.digest(args.worker) if args.worker else None,
              "oneDNN_environment_value": os.environ.get("TF_ENABLE_ONEDNN_OPTS") if os.environ.get("TF_ENABLE_ONEDNN_OPTS") in ("0", "1") else "unset_or_unrecognized",
              "validation_source_sha256": {str(path.relative_to(ROOT.parent)): hu.digest(path)
                  for path in (ROOT/"check.py", ROOT/"MovedCenterNms.java", ROOT/"fixture-manifest.json",
                               ROOT.parent/"cross-platform/check.py", ROOT.parent/"cross-platform/dependencies.json")},
              "exact_raster_reference_sides": [r["reference"] for r in reports if r["exact_raster_centers_measurements_match"]],
              "interpretation": "Completed diagnostic, not an equivalence pass. Differences against both fixed Linux reference sides are reported without changing thresholds or tolerances. No complete distance maps are retained in this compact packet.",
              "comparisons": reports}
    probabilities = hu.read_values(Path(str(actual_prefix)+".probability.f32be"), "f", width*height)
    result["score_probes"] = [{"x": x, "y": y, "probability": probabilities[y*width+x]}
                              for x, y in manifest["score_probe_pixels"]]
    (output/"report.json").write_text(json.dumps(result, indent=2, allow_nan=False)+"\n")
    print(json.dumps({"diagnostic_complete": True, "exact_raster_reference_sides": result["exact_raster_reference_sides"],
                      "comparison_count": len(reports)}, indent=2))


if __name__ == "__main__":
    main()

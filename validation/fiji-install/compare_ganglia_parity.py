#!/usr/bin/env python3
"""Strict, fail-closed comparison of installed-Fiji ganglia evidence.

This reads actual probe output; it never performs or substitutes model inference.
The three public images are behavioral fixtures, not expert ground truth. Plots
are display-only previews; every numerical comparison uses the native pixels.

Dependencies: numpy==2.2.6 tifffile==2025.5.10 Pillow==11.2.1
Run: python3 compare_ganglia_parity.py --directory fresh-fiji-results
Exit 0 means the bounded parity gate passed. Missing/invalid/failed evidence,
absent positive control, or any original/corrected difference exits 2.
"""

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import textwrap

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import tifffile


VARIANTS = ("original", "control", "fork")
SAMPLES = ("model_public", "distal_hu_gfap", "proximal_hu_chat")
SAMPLE_CHANNELS = {
    "model_public": (2, 2, 1),
    "distal_hu_gfap": (3, 2, 3),
    "proximal_hu_chat": (4, 1, 4),
}
SAMPLE_GEOMETRY = {
    "model_public": (1024, 1024, 8),
    "distal_hu_gfap": (1024, 1024, 16),
    "proximal_hu_chat": (770, 770, 8),
}
HISTORICAL_ROI_SHA256 = "83ccffc774522829a3cd1372708359b1487d9109bd6dcea65d2e119b03f82b5f"
INPUT_CONTRACT = {"channels": 3, "axes": "cyx", "mapping": "R=cell,G=ganglia,B=cell", "encoding": "float32-big-endian"}
PARAMETER_FIELDS = ("rdf_threshold", "gat_threshold", "open_iterations", "minimum_area_um2", "minimum_area_px")
SUMMARY_FILE = "ganglia-parity-summary.json"
SCOPE = ("Behavioral parity on three real public samples; source images and fixed "
         "historical neuron ROIs are not expert ground truth. No biological accuracy, "
         "manual review, or all-workflow claim. Numerical comparisons use native "
         "pixels; previews may be resized for display.")
COMMON_FIELDS = (
    "width", "height", "source_channels", "source_bit_depth", "ganglia_channel",
    "cell_channel", "source_sha256", "pixel_width_um", "pixel_height_um",
    "calibration", "input_contract", "input_axes", "params", "rdf_threshold",
    "gat_threshold", "open_iterations", "minimum_area_um2", "minimum_area_px",
)


class EvidenceError(ValueError):
    """Evidence is missing, malformed, or internally inconsistent."""


def require(condition, message):
    if not condition:
        raise EvidenceError(message)


def integer(value, name, minimum=0):
    require(type(value) is int and value >= minimum, f"{name}: expected integer >= {minimum}")
    return value


def finite_number(value, name, minimum=None):
    require(type(value) in (int, float) and math.isfinite(value), f"{name}: expected finite number")
    require(minimum is None or value >= minimum, f"{name}: value below {minimum}")
    return value


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(value, name):
    require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value),
            f"{name}: expected lowercase SHA-256")
    return value


def evidence_path(directory, value, name):
    require(isinstance(value, str) and value, f"{name}: missing filename")
    candidate = Path(value)
    require(not candidate.is_absolute() and ".." not in candidate.parts,
            f"{name}: evidence must stay in its results directory")
    path = (directory / candidate).resolve()
    require(path.is_relative_to(directory.resolve()), f"{name}: evidence path escapes results directory")
    require(path.is_file(), f"{name}: missing evidence file {value}")
    return path


def reject_constant(value):
    raise EvidenceError(f"Non-finite JSON value: {value}")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def read_report(directory, variant):
    path = directory / f"{variant}_parity.json"
    require(path.is_file(), f"Missing report: {path.name}")
    try:
        report = json.loads(path.read_text(encoding="utf-8"),
                            parse_constant=reject_constant, object_pairs_hook=unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise EvidenceError(f"{path.name}: cannot read JSON: {error}") from error
    require(isinstance(report, dict), f"{path.name}: report must be an object")
    require(report.get("status") == "PASS", f"{path.name}: status must be PASS, got {report.get('status')!r}")
    require(report.get("mode") == "parity", f"{path.name}: expected parity probe mode")
    metrics = report.get("metrics")
    require(isinstance(metrics, dict), f"{path.name}: missing metrics")
    rows = metrics.get("samples")
    require(isinstance(rows, list), f"{path.name}: missing metrics.samples")
    require(all(isinstance(row, dict) and isinstance(row.get("id"), str) for row in rows),
            f"{path.name}: invalid sample rows")
    ids = [row["id"] for row in rows]
    require(len(ids) == len(SAMPLES) and len(set(ids)) == len(ids) and set(ids) == set(SAMPLES),
            f"{path.name}: require exactly one of each expected sample {SAMPLES}, got {ids}")
    return {row["id"]: row for row in rows}


def read_raster(directory, row, kind, dtype, shape, hash_key):
    path = evidence_path(directory, row.get(f"{kind}_file"), f"{kind}_file")
    try:
        array = tifffile.imread(path)
    except Exception as error:
        raise EvidenceError(f"{path.name}: cannot decode TIFF: {error}") from error
    require(array.shape == shape, f"{kind}: expected shape {shape}, got {array.shape}")
    require(array.dtype.kind == "u" and array.dtype.itemsize == np.dtype(dtype).itemsize,
            f"{kind}: expected {dtype} unsigned raster, got {array.dtype}")
    raw = array.astype(dtype, copy=False).tobytes(order="C")
    require(sha256(raw) == digest(row.get(hash_key), hash_key), f"{kind}: saved pixels do not match reported SHA-256")
    file_hash_key = f"{kind}_tiff_sha256"
    if file_hash_key in row:
        require(sha256(path.read_bytes()) == digest(row[file_hash_key], file_hash_key),
                f"{kind}: TIFF file SHA-256 mismatch")
    return array


def validate_assignments(row, count):
    keys = ("assignments", "neurons_per_ganglion", "assignment_neuron_source", "assignment_neuron_roi_sha256")
    if row["id"] != "distal_hu_gfap":
        require(not any(key in row for key in keys),
                f"{row['id']}: historical neuron ROIs/assignments belong only to distal_hu_gfap")
        return None
    source = row.get("assignment_neuron_source")
    require(isinstance(source, str) and source.strip(), "Missing historical neuron assignment provenance")
    require(digest(row.get("assignment_neuron_roi_sha256"), "assignment_neuron_roi_sha256") == HISTORICAL_ROI_SHA256,
            "Historical neuron ROI SHA-256 differs from the pinned 83-ROI set")
    assignments = row.get("assignments")
    require(isinstance(assignments, list) and len(assignments) == 83,
            "distal_hu_gfap: require the 83 fixed historical neuron assignments")
    by_neuron = {}
    for item in assignments:
        require(isinstance(item, dict) and set(item) == {"neuron_id", "ganglion_id"}, "Invalid assignment row")
        neuron = integer(item["neuron_id"], "neuron_id", 1)
        ganglion = integer(item["ganglion_id"], "ganglion_id")
        require(neuron not in by_neuron, "Duplicate neuron assignment")
        require(ganglion <= count, "Assignment references nonexistent ganglion")
        by_neuron[neuron] = ganglion
    require(set(by_neuron) == set(range(1, 84)), "Historical neuron IDs must be exactly 1..83")
    counts = row.get("neurons_per_ganglion")
    # GangliaOps returns empty arrays when there are no ganglia. Preserve that API.
    expected = [0] * (count + 1) if count else []
    for ganglion in by_neuron.values():
        if ganglion:
            expected[ganglion] += 1
    require(isinstance(counts, list), "Missing neurons_per_ganglion")
    for value in counts:
        integer(value, "neurons_per_ganglion entry")
    require(counts == expected, "neurons_per_ganglion differs from recorded assignments")
    return by_neuron


def validate_sample(directory, row):
    for field in COMMON_FIELDS:
        require(field in row, f"Missing sample contract field: {field}")
    width, height = integer(row["width"], "width", 1), integer(row["height"], "height", 1)
    shape = (height, width)
    for field in ("source_channels", "ganglia_channel", "cell_channel"):
        integer(row[field], field, 1)
    require(tuple(row[field] for field in ("source_channels", "ganglia_channel", "cell_channel")) == SAMPLE_CHANNELS[row["id"]],
            "Sample channel contract differs from the pinned public fixture")
    require(type(row["source_bit_depth"]) is int and row["source_bit_depth"] in (8, 16, 32), "Invalid source bit depth")
    require((width, height, row["source_bit_depth"]) == SAMPLE_GEOMETRY[row["id"]],
            "Sample geometry/bit depth differs from the pinned public fixture")
    digest(row["source_sha256"], "source_sha256")
    require(row.get("source_unchanged") is True, "Source pixels were not verified unchanged")
    require(row.get("calibration_preserved") is True, "Calibration was not verified preserved")
    pw = finite_number(row["pixel_width_um"], "pixel_width_um")
    ph = finite_number(row["pixel_height_um"], "pixel_height_um")
    require(pw > 0 and ph > 0, "Pixel calibration must be positive")
    require(row["calibration"] == {"pixel_width_um": pw, "pixel_height_um": ph},
            "Calibration contract does not match top-level pixel calibration")
    require(row["input_contract"] == INPUT_CONTRACT, "Input contract differs from the pinned GAT channel/encoding contract")
    require(row["input_axes"] == "cyx", "Prepared input axes must be cyx")
    for key, value in (("rdf_threshold", .6), ("gat_threshold", .6), ("open_iterations", 1), ("minimum_area_um2", 1.0)):
        finite_number(row[key], key)
        require(row[key] == value, f"Changed fixed parameter: {key}")
    require(integer(row["minimum_area_px"], "minimum_area_px", 1) == math.ceil(1.0 / (pw * pw)),
            "Minimum area pixels do not match GAT's unchanged calibration convention")
    require(row["params"] == {key: row[key] for key in PARAMETER_FIELDS},
            "Parameter contract does not match top-level parameters")
    # The Java probe hashes these decompressed bytes, not the gzip container.
    input_path = evidence_path(directory, row.get("input_float_file"), "input_float_file")
    expected_size = 3 * height * width * 4
    try:
        with gzip.open(input_path, "rb") as stream:
            raw_input = stream.read(expected_size + 1)
    except (OSError, EOFError) as error:
        raise EvidenceError(f"Prepared input cannot be decompressed: {error}") from error
    require(len(raw_input) == expected_size, "Prepared input has wrong decompressed byte length")
    require(sha256(raw_input) == digest(row.get("input_float_sha256"), "input_float_sha256"),
            "Prepared float pixels do not match reported SHA-256")
    prepared = np.frombuffer(raw_input, dtype=">f4").reshape((3, height, width))
    require(bool(np.isfinite(prepared).all()), "Prepared input contains non-finite floats")
    for key, value in (("input_min", float(prepared.min())), ("input_max", float(prepared.max()))):
        require(finite_number(row.get(key), key) == value, f"{key}: does not match saved prepared input")
    mask = read_raster(directory, row, "mask", "u1", shape, "mask_pixels_uint8_row_major_sha256")
    require(bool(np.isin(mask, (0, 255)).all()), "Mask contains nonbinary pixels")
    foreground = int(np.count_nonzero(mask))
    require(integer(row.get("foreground_pixels"), "foreground_pixels") == foreground, "Foreground count differs from saved mask")
    labels = read_raster(directory, row, "labels", ">u2", shape, "labels_pixels_uint16_be_sha256")
    require(np.array_equal(labels > 0, mask > 0), "Label support differs from mask foreground")
    ids = np.unique(labels[labels > 0])
    count = integer(row.get("ganglion_count"), "ganglion_count")
    require(count == len(ids), "Ganglion count differs from saved labels")
    require(np.array_equal(ids, np.arange(1, count + 1)), "Labels must have contiguous GAT ganglion IDs")
    areas = row.get("areas_um2")
    require(isinstance(areas, list) and len(areas) == count + 1, "areas_um2 must include background index 0")
    for value in areas:
        finite_number(value, "areas_um2 entry", 0)
    area_pixels = np.bincount(labels.ravel(), minlength=count + 1)
    expected_areas = [0.0] + [int(n) * (pw * pw) for n in area_pixels[1:]]
    require(areas == expected_areas, "Area values differ from labels and actual GAT pixelWidth-squared convention")
    assignments = validate_assignments(row, count)
    rgb_path = evidence_path(directory, row.get("rgb_file"), "rgb_file")
    try:
        with Image.open(rgb_path) as image:
            require(image.mode == "RGB" and image.size == (width, height), "RGB preview has wrong format or geometry")
            rgb = np.array(image)
    except (OSError, ValueError) as error:
        raise EvidenceError(f"Cannot read actual GAT RGB preview: {error}") from error
    require(np.array_equal(rgb[:, :, 0], rgb[:, :, 2]), "GAT RGB preview violates R=Hu, G=ganglia, B=Hu")
    return {"row": row, "mask": mask, "labels": labels, "rgb": rgb,
            "prepared": prepared, "prepared_bytes": raw_input, "assignments": assignments}


def pair_comparison(baseline, candidate):
    a, b = baseline["row"], candidate["row"]
    changed_input = baseline["prepared"] != candidate["prepared"]
    byte_equal = baseline["prepared_bytes"] == candidate["prepared_bytes"]
    changed_mask = int(np.count_nonzero(baseline["mask"] != candidate["mask"]))
    changed_labels = int(np.count_nonzero(baseline["labels"] != candidate["labels"]))
    assignments_a, assignments_b = baseline["assignments"], candidate["assignments"]
    changed_assignments = None if assignments_a is None else sum(assignments_a[n] != assignments_b[n] for n in assignments_a)
    foreground_a, foreground_b = baseline["mask"] > 0, candidate["mask"] > 0
    intersection = int(np.count_nonzero(foreground_a & foreground_b))
    union = int(np.count_nonzero(foreground_a | foreground_b))
    combined = int(np.count_nonzero(foreground_a)) + int(np.count_nonzero(foreground_b))
    return {
        "input_bytes_equal": byte_equal,
        "input_changed_values": int(np.count_nonzero(changed_input)),
        "input_max_abs_difference": float(np.max(np.abs(baseline["prepared"].astype(np.float64) - candidate["prepared"]))),
        "mask_pixels_equal": changed_mask == 0, "mask_changed_pixels": changed_mask,
        "mask_agreement_fraction": 1.0 - changed_mask / baseline["mask"].size,
        "mask_pairwise_iou": intersection / union if union else 1.0,
        "mask_pairwise_dice": 2 * intersection / combined if combined else 1.0,
        "labels_equal": changed_labels == 0, "labels_changed_pixels": changed_labels,
        "ganglion_count_equal": a["ganglion_count"] == b["ganglion_count"],
        "ganglion_counts": [a["ganglion_count"], b["ganglion_count"]],
        "areas_equal": a["areas_um2"] == b["areas_um2"],
        "areas_um2": [a["areas_um2"], b["areas_um2"]],
        "assignments_recorded": assignments_a is not None,
        "assignments_equal": assignments_a == assignments_b,
        "assignments_changed": changed_assignments,
        "neurons_per_ganglion_equal": a.get("neurons_per_ganglion") == b.get("neurons_per_ganglion"),
        "neurons_per_ganglion": [a.get("neurons_per_ganglion"), b.get("neurons_per_ganglion")],
        "rgb_pixels_equal": np.array_equal(baseline["rgb"], candidate["rgb"]),
    }


def boundary(mask):
    """Native-pixel inner boundary using an eight-neighbor erosion, no relabeling."""
    foreground = mask > 0
    padded = np.pad(foreground, 1, constant_values=False)
    interior = foreground.copy()
    height, width = mask.shape
    for dy in range(3):
        for dx in range(3):
            interior &= padded[dy:dy + height, dx:dx + width]
    return foreground & ~interior


def display_boundary(mask):
    """Thicken outlines to three native pixels on a display-only copy."""
    edge = boundary(mask)
    padded = np.pad(edge, 1, constant_values=False)
    result = np.zeros_like(edge)
    height, width = mask.shape
    for dy in range(3):
        for dx in range(3):
            result |= padded[dy:dy + height, dx:dx + width]
    return result


def font(size):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default(size=size)


def area_caption(row):
    areas = row["areas_um2"][1:]
    result = f"{row['ganglion_count']} ganglia | {row['foreground_pixels']:,} foreground px"
    result += f"\nArea total {sum(areas):,.4f} um^2"
    if areas:
        result += f" | range {min(areas):,.4f}-{max(areas):,.4f}"
    return result


def plot_sample(directory, sample_id, evidence, comparison):
    # All overlays use the SAME actual original GAT RGB, without normalizing it
    # again, annotating foreign ROIs, or using model output as ground truth.
    rgb = evidence["original"]["rgb"]
    panels = [("Actual original GAT RGB", rgb,
               "R=Hu, G=ganglia, B=Hu\nNative pixels are compared before display resizing.")]
    colors = {"original": (0, 220, 255), "control": (255, 180, 45), "fork": (255, 100, 200)}
    titles = {"original": "Original v2 boundary", "control": "Unnormalized control boundary", "fork": "Corrected fork boundary"}
    for variant in VARIANTS:
        overlay = rgb.copy()
        foreground = evidence[variant]["mask"] > 0
        overlay[foreground] = (.82 * overlay[foreground] + .18 * np.array(colors[variant])).astype(np.uint8)
        overlay[display_boundary(evidence[variant]["mask"])] = colors[variant]
        panels.append((titles[variant], overlay, area_caption(evidence[variant]["row"])))
    original_mask = evidence["original"]["mask"] > 0
    corrected_mask = evidence["fork"]["mask"] > 0
    diff = np.zeros_like(rgb)
    diff[original_mask & corrected_mask] = (70, 70, 70)
    diff[original_mask & ~corrected_mask] = (0, 220, 255)
    diff[~original_mask & corrected_mask] = (255, 100, 200)
    pair = comparison["original_vs_fork"]
    panels.append(("Original / corrected pixel difference", diff,
                   f"{pair['mask_changed_pixels']:,} different pixels at native resolution\n"
                   "Cyan: original only | pink: corrected only | gray: shared"))
    tile_width, image_height, tile_height = 600, 445, 575
    canvas = Image.new("RGB", (tile_width * 3, 140 + tile_height * 2 + 72), (18, 23, 31))
    draw = ImageDraw.Draw(canvas)
    synthetic = bool(evidence["original"]["row"].get("test_fixture_kind"))
    heading = "SYNTHETIC LAYOUT TEST (not inference)" if synthetic else "GAT ganglia behavioral parity"
    draw.text((22, 16), f"{heading}: {sample_id}", font=font(28), fill="white")
    plot_status = "FAIL" if comparison["errors"] else "PASS"
    draw.text((22, 57), f"Sample parity: {plot_status} | exact native-pixel gate | display-only previews", font=font(20), fill=(196, 207, 223))
    draw.text((22, 91), "Public source images are not expert ground truth. No biological accuracy claim.", font=font(19), fill=(245, 193, 118))
    for index, (title, pixels, caption) in enumerate(panels):
        x, y = (index % 3) * tile_width, 140 + (index // 3) * tile_height
        draw.text((x + 15, y), title, font=font(21), fill="white")
        preview = Image.fromarray(pixels)
        preview.thumbnail((tile_width - 30, image_height), resample=Image.Resampling.NEAREST)
        canvas.paste(preview, (x + (tile_width - preview.width) // 2, y + 36 + (image_height - preview.height) // 2))
        draw.multiline_text((x + 15, y + 492), caption, font=font(16), fill=(211, 220, 232), spacing=6)
    x, y = 2 * tile_width + 20, 140 + tile_height
    control = comparison["original_vs_control"]
    notes = ["Exact comparison", "", f"Corrected input bytes equal: {pair['input_bytes_equal']}",
             f"Corrected mask pixels equal: {pair['mask_pixels_equal']}",
             f"Corrected label IDs equal: {pair['labels_equal']}",
             f"Corrected counts / areas equal: {pair['ganglion_count_equal']} / {pair['areas_equal']}",
             "", f"Control input values changed: {control['input_changed_values']:,}",
             f"Control mask pixels changed: {control['mask_changed_pixels']:,}",
             f"Control ganglia: {control['ganglion_counts'][1]}", ""]
    if pair["assignments_recorded"]:
        notes += ["83 fixed historical neuron ROIs, matched", "only to this distal image. Not expert truth.",
                  f"Corrected assignment changes: {pair['assignments_changed']}",
                  f"Control assignment changes: {control['assignments_changed']}"]
    else:
        notes += ["No historical neuron ROIs or assignments", "are applied to this sample."]
    notes += ["", "Full per-label areas and counts are in", SUMMARY_FILE]
    draw.multiline_text((x, y), "\n".join(notes), font=font(19), fill=(215, 225, 237), spacing=7)
    footer = ("Display only: 3-native-pixel colored boundaries and 18% foreground tint on the original RGB preview. "
              "Exact comparisons use untouched rasters. Pairwise agreement is not segmentation accuracy.")
    draw.multiline_text((22, canvas.height - 63), "\n".join(textwrap.wrap(footer, 152)), font=font(18), fill=(180, 192, 208), spacing=5)
    output = directory / f"parity-{sample_id}.png"
    canvas.save(output)
    return output.name


def compare_directory(directory, make_plots=True):
    directory = Path(directory)
    summary = {"schema_version": 1, "status": "FAIL", "scope": SCOPE,
               "expected_samples": list(SAMPLES), "reports": {}, "samples": [], "errors": [],
               "positive_control": {"status": "FAIL", "samples_with_input_and_mask_divergence": []}, "plots": []}
    documents = {}
    for variant in VARIANTS:
        try:
            documents[variant] = read_report(directory, variant)
            summary["reports"][variant] = "PASS"
        except (EvidenceError, OSError) as error:
            summary["reports"][variant] = "FAIL"
            summary["errors"].append(str(error))
    if len(documents) != len(VARIANTS):
        return summary
    for sample_id in SAMPLES:
        result = {"id": sample_id, "status": "FAIL", "errors": []}
        summary["samples"].append(result)
        try:
            evidence = {variant: validate_sample(directory, documents[variant][sample_id]) for variant in VARIANTS}
            original = evidence["original"]["row"]
            for variant in ("control", "fork"):
                for field in COMMON_FIELDS:
                    if original[field] != evidence[variant]["row"][field]:
                        result["errors"].append(f"{variant}: changed sample contract/parameter {field}")
                for field in ("assignment_neuron_source", "assignment_neuron_roi_sha256"):
                    if original.get(field) != evidence[variant]["row"].get(field):
                        result["errors"].append(f"{variant}: changed historical neuron provenance {field}")
            # Verify original and corrected prepared floats actually represent
            # the historical once-normalized byte RGB contract, in addition to
            # checking exact bytes between those two independent executions.
            # FloatProcessor.multiply first casts the double factor to float;
            # float64 multiplication then casting would differ by one ULP.
            expected = (np.moveaxis(evidence["original"]["rgb"], -1, 0).astype(np.float32)
                        * np.float32(1.0 / 255.0)).astype(">f4")
            for variant in ("original", "fork"):
                if evidence[variant]["prepared_bytes"] != expected.tobytes(order="C"):
                    result["errors"].append(f"{variant}: prepared floats violate the original once-normalized RGB contract")
            result["original_vs_fork"] = pair_comparison(evidence["original"], evidence["fork"])
            result["original_vs_control"] = pair_comparison(evidence["original"], evidence["control"])
            result["source_and_calibration_unchanged"] = all(
                original[field] == evidence[variant]["row"][field]
                for variant in VARIANTS for field in ("source_sha256", "calibration"))
            result["contracts_and_parameters_equal"] = all(
                original[field] == evidence[variant]["row"][field]
                for variant in VARIANTS for field in COMMON_FIELDS)
            result["saved_pixel_hashes_verified"] = True
            pair = result["original_vs_fork"]
            for check in ("input_bytes_equal", "mask_pixels_equal", "labels_equal", "ganglion_count_equal",
                          "areas_equal", "assignments_equal", "neurons_per_ganglion_equal", "rgb_pixels_equal"):
                if not pair[check]:
                    result["errors"].append(f"Original/corrected strict equality failed: {check}")
            control = result["original_vs_control"]
            if not control["rgb_pixels_equal"]:
                result["errors"].append("Original/control RGB preview differs despite unchanged source/channel contract")
            if not control["input_bytes_equal"] and not control["mask_pixels_equal"]:
                summary["positive_control"]["samples_with_input_and_mask_divergence"].append(sample_id)
            if make_plots:
                summary["plots"].append(plot_sample(directory, sample_id, evidence, result))
            result["status"] = "FAIL" if result["errors"] else "PASS"
        except (EvidenceError, OSError, ValueError) as error:
            result["errors"].append(str(error))
        summary["errors"].extend(f"{sample_id}: {error}" for error in result["errors"])
    if summary["positive_control"]["samples_with_input_and_mask_divergence"]:
        summary["positive_control"]["status"] = "PASS"
    else:
        summary["errors"].append("Positive control requires at least one actual sample with both prepared-input and mask divergence")
    if not summary["errors"]:
        summary["status"] = "PASS"
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", required=True, type=Path, help="Directory containing original/control/fork_parity.json and their saved rasters")
    args = parser.parse_args(argv)
    if not args.directory.is_dir():
        parser.error("--directory must be an existing results directory")
    # A repeated/failed comparison must not leave stale plots presented as new.
    for sample_id in SAMPLES:
        (args.directory / f"parity-{sample_id}.png").unlink(missing_ok=True)
    summary = compare_directory(args.directory)
    output = args.directory / SUMMARY_FILE
    temporary = output.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(output)
    print(f"Ganglia strict behavioral parity: {summary['status']}")
    for sample in summary["samples"]:
        print(f"  {sample['id']}: {sample['status']}")
    for error in summary["errors"]:
        print(f"  FAIL: {error}")
    print(f"Evidence: {output}")
    return 0 if summary["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

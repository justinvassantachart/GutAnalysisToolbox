#!/usr/bin/env python3
"""Create model-appropriate static and full calcium-frame technical regression cases.

Source TIFFs must be the public repository main-branch samples. No rescaling.
Oversized static channels are covered by explicit nonoverlapping <=1024 square crops.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import struct

import numpy as np
from PIL import Image

# One-based channels. First sample and DYM mappings are confirmed by ImageJ's
# CompositeImage LUTs and color suffixes in the filenames; the other mappings
# follow explicit marker order in filenames, checked against the ImageJ channels.
STATIC = {
    "146_02_14_20DYM8_6_mouse_Mid_Chat-g CalB-r CalR-b_max.tif": [(1, "subtype", "ChAT"), (2, "subtype", "Calbindin"), (3, "subtype", "Calretinin")],
    "181107_ms_distal_colon_GFAP_Hu_40X.tif": [(2, "neuron", "Hu")],
    "181107_ms_distal_colon_nNOS_GFAP_Hu_40X.tif": [(1, "subtype", "nNOS"), (3, "neuron", "Hu")],
    "DYM_22_7_Pr_Chat_BYFP_DIN_GFP-g_nNOS-m_VIP-r_Hu-b.tif": [(1, "subtype", "ChAT-GFP"), (2, "subtype", "VIP-out-of-domain"), (3, "subtype", "nNOS"), (4, "neuron", "Hu")],
    "DYM_22_7_Pr_Hu_crop.tif": [(1, "neuron", "Hu")],
    "Tilescan_GAT_ms_distal_colon_MP_hu.tif": [(1, "neuron", "Hu")],
    "ms_28_wk_colon_DAPI_nNOS_Hu_10X.tif": [(2, "subtype", "nNOS"), (3, "neuron", "Hu")],
    "ms_28_wk_ileum_DAPI_nNOS_Hu_10X.tif": [(2, "subtype", "nNOS"), (3, "neuron", "Hu")],
    "ms_distal_colon_Hu_20X.tif": [(1, "neuron", "Hu")],
    "ms_distal_colon_Hu_40X_1.tif": [(1, "neuron", "Hu")],
}
CALCIUM = "calcium_imaging_mouse_distal_colon_25X.tif"


def make_row(root, file, array, model, marker, channel, frame, crop, original_size, source_sha256, split):
    width, height = array.shape[1], array.shape[0]
    suffix = f"_c{channel}_t{frame}_x{crop[0]}_y{crop[1]}"
    case_id = re.sub(r"[^a-zA-Z0-9_-]+", "_", "repo_" + file.stem + suffix)
    input_path = root / "inputs" / (case_id + ".bin")
    raw = struct.pack(">4i", 0x47415449, 1, width, height) + array.astype(">f4").tobytes()
    input_path.write_bytes(raw)
    out = root / "outputs" / case_id
    out.mkdir(parents=True, exist_ok=True)
    return dict(case_id=case_id, model=model, split=split, input_path=str(input_path), input_sha256=hashlib.sha256(raw).hexdigest(),
                width=width, height=height, tiles=4, modern_path=str(out / "modern.bin"), legacy_path=str(out / "legacy.bin"),
                source="https://github.com/pr4deepr/GutAnalysisToolbox", source_path="Sample Images/2D_enteric_neuron_IF/" + file.name,
                source_sha256=source_sha256, channel=channel, frame=frame, marker=marker, crop_x=crop[0], crop_y=crop[1],
                original_width=original_size[0], original_height=original_size[1], dtype=str(array.dtype),
                minimum=float(array.min()), maximum=float(array.max()), mean=float(array.mean()),
                preprocessing="unrescaled original pixels; explicit nonoverlapping crop if oversized; shared worker normalization",
                interpretation="out-of-domain technical consistency; not GAT calcium-workflow validation" if split == "calcium" else
                    "static technical consistency; crop-only evidence for oversize sources; do not sum crop counts as whole-image evidence")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.output.resolve()
    (root / "inputs").mkdir(parents=True, exist_ok=True)
    rows = []
    for name, mappings in STATIC.items():
        file = args.source / name
        source_hash = hashlib.sha256(file.read_bytes()).hexdigest()
        with Image.open(file) as image:
            width, height = image.size
            # This threshold leaves room for CSBDeep block padding under the preview
            # 268,435,456-float cap at 97 channels. Current supported full frames
            # are <=1.45MP, so no near-limit frame is silently included.
            oversized = width * height > 2_500_000
            step_x, step_y = (1024, 1024) if oversized else (width, height)
            for channel, model, marker in mappings:
                image.seek(channel - 1)
                array = np.asarray(image)
                if array.ndim != 2: raise ValueError(f"Unexpected RGB rather than separate-channel source: {name}")
                for y in range(0, height, step_y):
                    for x in range(0, width, step_x):
                        rows.append(make_row(root, file, array[y:y + step_y, x:x + step_x], model, marker, channel, 1,
                                             (x, y), (width, height), source_hash, "repository"))
    # Preserve temporal order for the complete time series; it is a separate
    # out-of-domain stress set, not part of the Hu/subtype held-out analysis.
    file = args.source / CALCIUM
    source_hash = hashlib.sha256(file.read_bytes()).hexdigest()
    with Image.open(file) as image:
        for frame in range(image.n_frames):
            image.seek(frame)
            rows.append(make_row(root, file, np.asarray(image), "neuron", "calcium-out-of-domain", 1, frame + 1,
                                 (0, 0), image.size, source_hash, "calcium"))
    rows.sort(key=lambda r: (r["split"] == "calcium", r["model"], r["source_path"], r["frame"], r["channel"], r["crop_y"], r["crop_x"]))
    with (root / "manifest.tsv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader(); writer.writerows(rows)
    (root / "inventory.json").write_text(json.dumps(rows, indent=2))
    summary = {}
    for row in rows:
        key = row["split"] + "/" + row["model"]
        item = summary.setdefault(key, {"cases": 0, "pixels": 0})
        item["cases"] += 1; item["pixels"] += row["width"] * row["height"]
    (root / "inventory-summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

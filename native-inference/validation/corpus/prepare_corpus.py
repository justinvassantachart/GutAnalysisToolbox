#!/usr/bin/env python3
"""Inventory all model-appropriate public train/test images, without resizing or normalizing."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import struct
import zipfile

import numpy as np
from PIL import Image

EXPECTED_MD5 = {"neuron": "9936b4632d93ead585f77be018aa0e58", "subtype": "2e6bfb6bc253816dedc918efd2270b1a"}
SOURCE = "https://zenodo.org/records/15314214"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--archives", type=Path, required=True, help="Directory containing neuron.zip and subtype.zip")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=True)
    inputs = root / "inputs"
    inputs.mkdir(exist_ok=True)
    rows = []
    for model, expected in EXPECTED_MD5.items():
        archive_path = args.archives / (model + ".zip")
        digest = hashlib.md5(archive_path.read_bytes()).hexdigest()
        if digest != expected:
            raise ValueError(f"Published archive MD5 mismatch: {model}: {digest}")
        with zipfile.ZipFile(archive_path) as archive:
            paths = sorted(n for n in archive.namelist() if "/images/" in n and n.lower().endswith((".tif", ".tiff", ".png")))
            for source_path in paths:
                source_bytes = archive.read(source_path)
                image = Image.open(io.BytesIO(source_bytes))
                array = np.asarray(image)
                if image.n_frames != 1 or array.ndim != 2:
                    raise ValueError(f"Unexpected non-2D single-channel image: {source_path}")
                width, height = image.size
                split = "test" if source_path.startswith("test/") else "train"
                case_id = re.sub(r"[^a-zA-Z0-9_-]+", "_", model + "_" + split + "_" + Path(source_path).stem)
                input_path = inputs / (case_id + ".bin")
                binary = struct.pack(">4i", 0x47415449, 1, width, height) + array.astype(">f4").tobytes()
                input_path.write_bytes(binary)
                output_dir = root / "outputs" / case_id
                output_dir.mkdir(parents=True, exist_ok=True)
                rows.append(dict(case_id=case_id, model=model, split=split,
                                 input_path=str(input_path), input_sha256=hashlib.sha256(binary).hexdigest(),
                                 width=width, height=height, tiles=4,
                                 modern_path=str(output_dir / "modern.bin"), legacy_path=str(output_dir / "legacy.bin"),
                                 source=SOURCE, source_archive=model + ".zip", source_path=source_path,
                                 source_sha256=hashlib.sha256(source_bytes).hexdigest(), dtype=str(array.dtype),
                                 minimum=float(array.min()), maximum=float(array.max()), mean=float(array.mean()),
                                 preprocessing="raw supplied pixels; no resize/contrast; worker CSBDeep 1/99.8 normalization"))
    # All held-out images precede training; model grouping amortizes startup inside each phase.
    rows.sort(key=lambda row: (row["split"] != "test", row["model"], row["width"] * row["height"], row["case_id"]))
    with (root / "manifest.tsv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    (root / "inventory.json").write_text(json.dumps(rows, indent=2))
    summary = {}
    for row in rows:
        key = row["model"] + "/" + row["split"]
        bucket = summary.setdefault(key, {"images": 0, "pixels": 0, "min_width": row["width"], "max_width": 0, "min_height": row["height"], "max_height": 0})
        bucket["images"] += 1
        bucket["pixels"] += row["width"] * row["height"]
        for dimension in ("width", "height"):
            bucket["min_" + dimension] = min(bucket["min_" + dimension], row[dimension])
            bucket["max_" + dimension] = max(bucket["max_" + dimension], row[dimension])
    (root / "inventory-summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

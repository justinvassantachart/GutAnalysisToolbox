#!/usr/bin/env python3
"""Local, dependency-free real-model smoke check. No downloads or image uploads."""
import argparse
import math
import os
from pathlib import Path
import struct
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", required=True, type=Path)
    parser.add_argument("--models", required=True, type=Path)
    parser.add_argument("--java", default="java")
    args = parser.parse_args()
    classpath = str(args.worker.resolve()) + os.pathsep + str(args.worker.resolve().parent / "lib" / "*")
    prefix = [args.java, "-cp", classpath, "org.gatanalysis.inference.NativeInferenceMain"]
    subprocess.run(prefix + ["--self-test"], check=True, timeout=120)
    width, height = 129, 97
    # Odd dimensions exercise the legacy normalization/padding/tiling boundary.
    pixels = [float(3 + 220 * math.exp(-((x - 42) ** 2 + (y - 35) ** 2) / 80)
                    + 170 * math.exp(-((x - 91) ** 2 + (y - 62) ** 2) / 100))
              for y in range(height) for x in range(width)]
    for name in ("2D_enteric_neuron_v4_1.zip", "2D_enteric_neuron_subtype_v4.zip"):
        model = args.models / name
        if not model.is_file():
            raise FileNotFoundError(model)
        with tempfile.TemporaryDirectory(prefix="gat-smoke-") as directory:
            source, destination = Path(directory) / "input.bin", Path(directory) / "output.bin"
            source.write_bytes(struct.pack(">4i", 0x47415449, 1, width, height)
                               + struct.pack(">%df" % len(pixels), *pixels))
            subprocess.run(prefix + [str(model.resolve()), str(source), str(destination), "4"],
                           check=True, timeout=900)
            data = destination.read_bytes()
            magic, version, w, h, channels = struct.unpack(">5i", data[:20])
            assert (magic, version, w, h) == (0x4741544F, 1, width, height), "Wrong output header"
            assert 4 <= channels <= 1024, "Wrong output channel count"
            assert len(data) == 20 + 4 * width * height * channels, "Wrong output length"
            values = struct.unpack(">%df" % (width * height * channels), data[20:])
            assert all(math.isfinite(v) for v in values), "Non-finite model predictions"
            probabilities = values[::channels]
            assert min(probabilities) >= -1e-6 and max(probabilities) <= 1 + 1e-6, "Probability out of range"
            print(f"PASS {name}: {width}x{height}x{channels}; "
                  f"probability range {min(probabilities):.6g}..{max(probabilities):.6g}")
    print("Real-model inference smoke checks passed. This is not Fiji GUI or scientific-equivalence validation.")


if __name__ == "__main__":
    main()

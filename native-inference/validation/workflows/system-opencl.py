#!/usr/bin/env python3
"""Read the actual runner's OpenCL capability without assuming a GPU exists."""
import argparse
import ctypes as c
import ctypes.util
import json
import platform
import subprocess
from pathlib import Path


def command(*args):
    run = subprocess.run(args, text=True, capture_output=True, timeout=30)
    return {"exit": run.returncode, "stdout": run.stdout.strip(), "stderr": run.stderr.strip()}


def inspect():
    report = {"system": platform.system(), "machine": platform.machine(),
              "platform": platform.platform(), "status": "NOT_RUN", "platforms": []}
    if platform.system() == "Darwin":
        report["hardware"] = command("sysctl", "-n", "machdep.cpu.brand_string")
        report["cores"] = command("sysctl", "-n", "hw.logicalcpu")
        report["memory_bytes"] = command("sysctl", "-n", "hw.memsize")
        report["model"] = command("sysctl", "-n", "hw.model")
        report["macos"] = command("sw_vers")
    library = c.util.find_library("OpenCL")
    report["library"] = library
    if not library:
        report.update(status="BLOCKED_ENVIRONMENT", detail="Operating system OpenCL library unavailable")
        return report
    try:
        cl = c.CDLL(library)
        u, p, z = c.c_uint, c.c_void_p, c.c_size_t
        cl.clGetPlatformIDs.argtypes = [u, c.POINTER(p), c.POINTER(u)]
        cl.clGetPlatformIDs.restype = c.c_int
        cl.clGetPlatformInfo.argtypes = [p, u, z, p, c.POINTER(z)]
        cl.clGetPlatformInfo.restype = c.c_int
        cl.clGetDeviceIDs.argtypes = [p, c.c_ulonglong, u, c.POINTER(p), c.POINTER(u)]
        cl.clGetDeviceIDs.restype = c.c_int
        cl.clGetDeviceInfo.argtypes = [p, u, z, p, c.POINTER(z)]
        cl.clGetDeviceInfo.restype = c.c_int

        def info(fn, obj, key):
            n = z()
            error = fn(obj, key, 0, None, c.byref(n))
            if error: return {"error": error}
            if n.value > 1024 * 1024: raise ValueError("Unexpected OpenCL information length")
            data = c.create_string_buffer(n.value)
            error = fn(obj, key, n.value, data, None)
            return {"error": error} if error else data.value.decode("utf-8", "replace")

        count = u()
        error = cl.clGetPlatformIDs(0, None, c.byref(count))
        report["platform_query_error"] = error
        if error == -1001 or not count.value:
            report.update(status="BLOCKED_ENVIRONMENT", detail="No OpenCL platform exposed by this runner")
            return report
        if error or count.value > 64: raise RuntimeError("OpenCL platform query failed: " + str(error))
        ids = (p * count.value)()
        error = cl.clGetPlatformIDs(count.value, ids, None)
        if error: raise RuntimeError("OpenCL platform enumeration failed: " + str(error))
        for pid in ids:
            entry = {"name": info(cl.clGetPlatformInfo, pid, 0x0902),
                     "version": info(cl.clGetPlatformInfo, pid, 0x0901), "devices": []}
            devices = u()
            error = cl.clGetDeviceIDs(pid, 0xFFFFFFFF, 0, None, c.byref(devices))
            entry["device_query_error"] = error
            entry["alternate_device_queries"] = {}
            for label, device_type in (("all", 0xFFFFFFFF), ("cpu", 2), ("gpu", 4), ("default", 1)):
                bounded = (p * 128)()
                bounded_count = u()
                bounded_error = cl.clGetDeviceIDs(pid, device_type, 128, bounded, c.byref(bounded_count))
                entry["alternate_device_queries"][label] = {
                    "error": bounded_error, "count": bounded_count.value,
                    "names": [info(cl.clGetDeviceInfo, did, 0x102B) for did in bounded[:min(128, bounded_count.value)]]
                    if not bounded_error else []}
            if not error and devices.value:
                if devices.value > 128: raise ValueError("Unexpected device count")
                dids = (p * devices.value)()
                error = cl.clGetDeviceIDs(pid, 0xFFFFFFFF, devices.value, dids, None)
                if error: raise RuntimeError("OpenCL device enumeration failed: " + str(error))
                for did in dids:
                    entry["devices"].append({"name": info(cl.clGetDeviceInfo, did, 0x102B),
                                             "version": info(cl.clGetDeviceInfo, did, 0x102F)})
            report["platforms"].append(entry)
        report["status"] = "PASS" if any(p["devices"] for p in report["platforms"]) else "BLOCKED_ENVIRONMENT"
        report["detail"] = "Enumeration only; Java bindings, transfers and kernels require separate tests. Preserve error codes: failed enumeration is not proof of a defect on a physical Mac."
    except Exception as exc:
        report.update(status="FAIL", detail=type(exc).__name__ + ": " + str(exc))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = inspect()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(result, indent=2))

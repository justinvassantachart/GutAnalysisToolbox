#!/usr/bin/env python3
"""Compile and run the real, bounded, no-model NMS/ROI pairing in a disposable JVM.

Needs an existing supported AWT environment. Never establishes a desktop bridge,
downloads dependencies, launches Fiji, or runs a model. All paths are explicit.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--java-home', type=Path, required=True)
    parser.add_argument('--classpath-file', type=Path, required=True)
    parser.add_argument('--production-classes', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--timeout', type=int, default=240)
    args = parser.parse_args()
    if not 1 <= args.timeout <= 600:
        parser.error('Deadline must be 1–600 seconds')
    args.output.mkdir(parents=True, exist_ok=False)
    classes = args.output / 'classes'
    classes.mkdir()
    cp = str(args.production_classes.resolve()) + os.pathsep + args.classpath_file.read_text().strip()
    sources = [ROOT / 'src/main/java/Features/Macros/LegacyMacroStarDist.java', HERE / 'LegacyMacroNmsProbe.java']
    # Argument files avoid OS command-line limits in full Fiji installations.
    javac_args = args.output / 'javac.args'
    javac_args.write_text('\n'.join('"' + str(x).replace('\\', '\\\\').replace('"', '\\"') + '"'
                                    for x in ['-cp', cp, '-d', classes, *sources]) + '\n')
    provenance = {'scope': 'original-nms-vs-adapter-postprocessing-only', 'model_execution': False,
                  'whole_macro_execution': False, 'heap_mib': 256, 'active_processors': 1,
                  'sources': {str(p.relative_to(ROOT)): digest(p) for p in sources},
                  'status': 'COMPILING'}
    record = args.output / 'launcher.json'
    record.write_text(json.dumps(provenance, indent=2) + '\n')
    env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
    try:
        with (args.output / 'compile.log').open('w') as log:
            process = subprocess.run([str(args.java_home / 'bin/javac'), '-J-Xmx256m', '-J-XX:ActiveProcessorCount=1',
                                      '@' + str(javac_args)], env=env, stdout=log, stderr=subprocess.STDOUT, timeout=120)
        if process.returncode:
            provenance['status'] = 'BLOCKED_COMPILE'
            return 2
        command = [str(args.java_home / 'bin/java'), '-Xmx256m', '-XX:ActiveProcessorCount=1',
                   '-Djava.awt.headless=false', '-Dgat.stardist.backend=native',
                   '-cp', str(classes) + os.pathsep + cp,
                   'Features.Macros.LegacyMacroNmsProbe', str(args.output / 'result')]
        provenance['forced_backend'] = 'native; adapter postprocessing hook only, no inference called'
        provenance['status'] = 'RUNNING'
        record.write_text(json.dumps(provenance, indent=2) + '\n')
        with (args.output / 'runtime.log').open('w') as log:
            process = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=args.timeout)
        report = json.loads((args.output / 'result/report.json').read_text())
        provenance['exit_code'] = process.returncode
        provenance['status'] = report['status']
        return 0 if process.returncode == 0 and report['status'] == 'PASS_POSTPROCESSING_SCOPE' else 1
    except subprocess.TimeoutExpired:
        provenance['status'] = 'TIMEOUT_INCOMPLETE'
        return 2
    except Exception as error:
        provenance['status'] = 'ERROR_INCOMPLETE'
        provenance['error'] = str(error)
        return 2
    finally:
        record.write_text(json.dumps(provenance, indent=2) + '\n')
        print(provenance['status'])


if __name__ == '__main__':
    sys.exit(main())

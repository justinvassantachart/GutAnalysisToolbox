#!/usr/bin/env python3
"""Bounded original/native 512x512x257 capacity experiment.

Use only after shared-runtime coordination. The original parent is isolated and
bounded; timeout/OOM is inconclusive, never a proof of an original size limit.
No native cap or production setting is modified by this experiment.
"""
import argparse
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform

from alignment_runtime import artifacts, sha, validate
from run_alignment_probe import HERE, ROOT, macro_source, production_hashes

WIDTH, HEIGHT, PLANES, REFERENCE = 512, 512, 257, 3
SHIFTS = ((0, 0), (3, -2), (-4, 5), (0, 0))
STATUS = 'PASS_ORIGINAL_CAPACITY_COUNTEREXAMPLE'
NATIVE_STATUS = 'PASS_NATIVE_CAPACITY_CONTROL'


def shifted(source, dx, dy):
    result = bytearray(WIDTH * HEIGHT)
    for y in range(HEIGHT):
        sy = y - dy
        if 0 <= sy < HEIGHT:
            start, stop = max(0, dx), min(WIDTH, WIDTH + dx)
            result[y * WIDTH + start:y * WIDTH + stop] = source[sy * WIDTH + start - dx:sy * WIDTH + stop - dx]
    return result


def expected_hashes():
    state = (8291 ^ 0x5DEECE66D) & ((1 << 48) - 1)
    base = bytearray(WIDTH * HEIGHT)
    for y in range(10, HEIGHT - 10):
        for x in range(10, WIDTH - 10):
            while True:
                state = (state * 0x5DEECE66D + 11) & ((1 << 48) - 1)
                bits = state >> 17; value = bits % 200
                if bits - value + 199 < 1 << 31:
                    base[y * WIDTH + x] = value + 1
                    break
    inputs = [shifted(base, dx, dy) for dx, dy in SHIFTS]
    rx, ry = SHIFTS[REFERENCE - 1]
    outputs = [shifted(frame, rx - dx, ry - dy) for frame, (dx, dy) in zip(inputs, SHIFTS)]
    raw, aligned = hashlib.sha256(), hashlib.sha256()
    for z in range(PLANES):
        raw.update(inputs[z % 4]); aligned.update(outputs[z % 4])
    return raw.hexdigest(), aligned.hexdigest()


def validate_result(output, expected_source, variant='original', expected_adapter_hash=None):
    report = json.loads((output / 'report.json').read_text())
    native = variant == 'native'
    expected_input, expected_output = expected_hashes()
    fields = {'status': NATIVE_STATUS if native else STATUS, 'variant': variant, 'scope': 'original-alignment-capacity-counterexample',
              'whole_calcium_macro_executed': False, 'native_executed': native,
              'dimensions': [WIDTH, HEIGHT, PLANES], 'total_pixels': WIDTH * HEIGHT * PLANES, 'raw_pixel_bytes': WIDTH * HEIGHT * PLANES,
              'previous_native_total_pixel_cap': 67108864, 'bit_depth': 8, 'seed': 8291, 'reference': REFERENCE,
              'macro_source': expected_source, 'incorrect_pixels': 0, 'csv_roundtrip': True,
              'input_u8_sha256': expected_input, 'output_u8_sha256': expected_output,
              'expected_output_u8_sha256': expected_output,
              'plugin_class_sha256': artifacts()[0]['classes_sha256']['TemplateMatching/Align_slices.class']}
    for key, value in fields.items():
        if report.get(key) != value:
            raise ValueError('Original capacity evidence mismatch: ' + key)
    if report.get('macro_return') == '[aborted]' or report.get('errors') or report.get('ij_error') or report.get('commands', []).count('Align slices in stack...') != (0 if native else 1):
        raise ValueError('Original capacity runtime error/missing actual command')
    processes = report.get('worker_processes', {})
    if len(processes) != (1 if native else 0) or any('TemplateMatching.NativeAlignmentMain' not in p for p in processes.values()):
        raise ValueError('Missing/wrong actual capacity worker execution evidence')
    if native and (not expected_adapter_hash or report.get('adapter_class_sha256') != expected_adapter_hash):
        raise ValueError('Wrong/missing actual production adapter')
    log = report.get('log', '')
    if 'GAT_CAPACITY_AFTER_ALIGNMENT' not in log or any(term in log.lower() for term in ('exception', '[error]', 'unsatisfiedlink')):
        raise ValueError('Original capacity continuation/log failure')
    macro = (output / 'invoked.ijm').read_text()
    line, _ = macro_source(variant)
    want = ('selectWindow("capacity512x512x257");\nsizeX=512;sizeY=512;\n'
            'x_size=floor(sizeX*0.7);\ny_size=floor(sizeY*0.7);\nx0=floor(sizeX/6);\ny0=floor(sizeY/6);\n'
            + line + '\nprint("GAT_CAPACITY_AFTER_ALIGNMENT");\n')
    if macro != want or sha(output / 'invoked.ijm') != report.get('invoked_macro_sha256'):
        raise ValueError('Original capacity macro/options changed')
    rx, ry = SHIFTS[REFERENCE - 1]
    rows = [[z, rx - SHIFTS[(z - 1) % 4][0], ry - SHIFTS[(z - 1) % 4][1]]
            for z in [*range(REFERENCE - 1, 0, -1), *range(REFERENCE + 1, PLANES + 1)]]
    if report.get('rows') != rows:
        raise ValueError('Original capacity motion values/order changed')
    csv_data = list(csv.reader((output / 'motion.csv').read_text(encoding='utf-8-sig').splitlines()))
    if csv_data[0] == ['Slice', 'dX', 'dY']:
        values = csv_data[1:]
    elif csv_data[0] in (['', 'Slice', 'dX', 'dY'], [' ', 'Slice', 'dX', 'dY']):
        if [r[0] for r in csv_data[1:]] != [str(i) for i in range(1, PLANES)]:
            raise ValueError('Original capacity CSV indices changed')
        values = [r[1:] for r in csv_data[1:]]
    else:
        raise ValueError('Original capacity CSV headings changed')
    if [[float(v) for v in row] for row in values] != rows:
        raise ValueError('Original capacity CSV changed')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runtime-classpath', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--java', default='java'); p.add_argument('--javac', default='javac')
    p.add_argument('--compile-only', action='store_true')
    p.add_argument('--variant', choices=('original','native'), default='original')
    p.add_argument('--production-classes', type=Path)
    p.add_argument('--native-worker', type=Path)
    args = p.parse_args()
    native = args.variant == 'native'
    if native != bool(args.production_classes) or native != bool(args.native_worker):
        p.error('Native requires classes/worker; original forbids both')
    if not native and not args.compile_only and (platform.system(), platform.machine()) != ('Linux', 'x86_64'):
        p.error('Original pinned JNI requires Linux x86_64')
    entries = [Path(s).resolve() for s in args.runtime_classpath.read_text().strip().split(os.pathsep)]
    validate(entries)
    original_entries = list(entries); hashes = {}
    if native:
        hashes = production_hashes(args.production_classes)
        entries.insert(0,args.production_classes.resolve())
        if not (args.native_worker/'gat-native-alignment.jar').is_file() or not (args.native_worker/'lib').is_dir():
            raise ValueError('Separate native worker required')
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    classes = out / 'classes'; classes.mkdir()
    baseline = ROOT / 'native-inference/validation/baseline'
    sources = [HERE / 'LegacyMacroAlignmentCapacityProbe.java', baseline / 'BaselineUrlClassLoader.java', baseline / 'BaselineBootstrap.java']
    cp = os.pathsep.join(map(str, entries)); argfile = out / 'javac.args'
    argfile.write_text('\n'.join('"' + str(v).replace('\\', '\\\\').replace('"', '\\"') + '"'
                                for v in ['-proc:none', '-encoding', 'UTF-8', '-cp', cp, '-d', classes, *sources]) + '\n')
    spec = importlib.util.spec_from_file_location('bounded_capacity', ROOT / 'native-inference/validation/workflows/run_workflows.py')
    bounded = importlib.util.module_from_spec(spec); spec.loader.exec_module(bounded)
    env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', JAVA_TOOL_OPTIONS='-XX:ActiveProcessorCount=1')
    line, source = macro_source(args.variant)
    report = {'schema_version': 1, 'scope': 'original-alignment-capacity-counterexample', 'status': 'COMPILING',
              'whole_calcium_macro_executed': False, 'native_executed': native, 'variant': args.variant, 'macro_source': source, 'production_classes': hashes,
              'sources': {str(s.relative_to(ROOT)): sha(s) for s in sources},
              'runtime_artifacts': [{'name': e.name, 'sha256': sha(e)} for e in original_entries]}
    if native:
        report['worker_files'] = {str(f.relative_to(args.native_worker)):sha(f) for f in sorted(args.native_worker.rglob('*')) if f.is_file()}
    def save():
        (out / 'launcher.json').write_text(json.dumps(report, indent=2) + '\n')
    config = out / 'config.json'
    config.write_text(json.dumps({'variant': args.variant, 'output': str(out / 'result'), 'macro_line': line, 'macro_source': source}, indent=2) + '\n')
    save()
    report['compilation'] = bounded.execute([args.javac, '-J-Xmx256m', '-J-XX:ActiveProcessorCount=1', '@' + str(argfile)],
                                            out / 'compile.log', 180, env, rss_limit_kib=1048576)
    if report['compilation']['exit_code'] or report['compilation']['resource_stop_reason']:
        report['status'] = 'INCONCLUSIVE_COMPILE'; save(); return 2
    if args.compile_only:
        report['status'] = 'COMPILED_NOT_RUN'; save(); return 0
    home = out / 'imagej-home'; home.mkdir(); plugins = out / 'empty-plugins'; plugins.mkdir()
    command = [args.java, '--add-opens=java.base/java.lang=ALL-UNNAMED', '-Xmx256m', '-XX:ActiveProcessorCount=1',
               '-Djava.awt.headless=false', '-Djava.system.class.loader=BaselineUrlClassLoader',
               '-Dimagej.updater.disableAutocheck=true', '-Dimagej.dir=' + str(home), '-Dfiji.dir=' + str(home),
               '-Dplugins.dir=' + str(plugins), '-Duser.home=' + str(home), '-Djava.util.prefs.userRoot=' + str(out / 'prefs'),
               '-cp', str(classes) + os.pathsep + cp]
    if native:
        command += ['-Dgat.alignment.backend=native', '-Dgat.alignment.directory='+str(args.native_worker.resolve()), '-Dgat.alignment.timeoutSeconds=120']
    command += ['BaselineBootstrap', 'LegacyMacroAlignmentCapacityProbe', str(config)]
    report['execution'] = bounded.execute(command, out / 'runtime.log', 180, env, rss_limit_kib=1048576)
    report['status'] = 'INCONCLUSIVE_OR_FAILED_CAPACITY'
    if not report['execution']['exit_code'] and not report['execution']['resource_stop_reason']:
        try:
            validate_result(out / 'result', source, args.variant, hashes.get('Features/Macros/LegacyTemplateMatching.class')); report['status'] = NATIVE_STATUS if native else STATUS
        except (ValueError, OSError, KeyError, IndexError, TypeError) as error:
            report['validation_error'] = str(error)
    save(); print(report['status']); return 0 if report['status'] in (STATUS,NATIVE_STATUS) else 1


if __name__ == '__main__':
    raise SystemExit(main())

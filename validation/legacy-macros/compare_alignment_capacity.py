#!/usr/bin/env python3
"""Strict same-source original/native actual above-old-cap comparison."""
import argparse
import json
from pathlib import Path
from alignment_runtime import artifacts
from run_alignment_capacity import validate_result, STATUS, NATIVE_STATUS
from run_alignment_probe import macro_source


def load(directory, variant):
    launcher = json.loads((directory/'launcher.json').read_text())
    expected = NATIVE_STATUS if variant=='native' else STATUS
    if launcher.get('status')!=expected or launcher.get('variant')!=variant:
        raise ValueError('Incomplete/wrong-variant capacity launcher')
    for stage in ('compilation','execution'):
        result=launcher.get(stage,{})
        if result.get('exit_code')!=0 or result.get('resource_stop_reason') or result.get('rss_ceiling_kib')!=1048576 or result.get('timeout_seconds')!=180:
            raise ValueError('Incomplete/unbounded capacity '+stage)
        if not 0 < result.get('observed_peak_process_tree_rss_kib',0) <=1048576:
            raise ValueError('Missing/excess capacity RSS observation')
    runtime={r['name']:r['sha256'] for r in launcher.get('runtime_artifacts',[])}
    for row in artifacts():
        if runtime.get(row['file'])!=row['sha256']:
            raise ValueError('Missing/wrong pinned capacity dependency')
    _,source=macro_source(variant)
    if launcher.get('macro_source')!=source or launcher.get('whole_calcium_macro_executed') is not False:
        raise ValueError('Wrong source/scope')
    adapter=launcher.get('production_classes',{}).get('Features/Macros/LegacyTemplateMatching.class')
    if variant=='native':
        if not adapter or not launcher.get('worker_files',{}).get('gat-native-alignment.jar') or launcher.get('native_executed') is not True:
            raise ValueError('Native production/worker evidence absent')
    elif launcher.get('production_classes') or launcher.get('worker_files') or launcher.get('native_executed') is not False:
        raise ValueError('Original contaminated with native route')
    validate_result(directory/'result',source,variant,adapter)
    return launcher,json.loads((directory/'result/report.json').read_text())


def compare(original,native):
    result={'schema_version':1,'scope':'above-old-cap-legacy-macro-alignment','status':'FAIL_OR_INCOMPLETE','errors':[]}
    try:
        al,a=load(original,'original');bl,b=load(native,'native')
        if not al.get('sources') or al.get('sources')!=bl.get('sources'):
            raise ValueError('Different/missing actual probe source versions')
        fields=('dimensions','total_pixels','raw_pixel_bytes','bit_depth','reference','seed','input_u8_sha256','output_u8_sha256','expected_output_u8_sha256','incorrect_pixels','rows','csv_roundtrip')
        changed=[key for key in fields if a.get(key)!=b.get(key)]
        if changed: raise ValueError('Paired capacity differences: '+','.join(changed))
        result.update(status='PASS_PAIRED_CAPACITY_CONTROL',total_pixels=a['total_pixels'],incorrect_pixels=0,
                      raw_pixel_bytes=a['raw_pixel_bytes'],motion_rows=len(a['rows']),original_execution=al['execution'],native_execution=bl['execution'])
    except (ValueError,KeyError,OSError,TypeError,IndexError) as error:
        result['errors'].append(str(error))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--original',type=Path,required=True);p.add_argument('--native',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    if args.output.exists():p.error('Never overwrite existing evidence')
    result=compare(args.original,args.native);args.output.write_text(json.dumps(result,indent=2)+'\n');print(result['status'])
    return 0 if result['status']=='PASS_PAIRED_CAPACITY_CONTROL' else 1


if __name__=='__main__':raise SystemExit(main())

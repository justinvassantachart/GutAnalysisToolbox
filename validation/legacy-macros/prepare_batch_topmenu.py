#!/usr/bin/env python3
"""Prepare one original/generated batch example with data-only public overrides."""
import argparse
import hashlib
import json
from pathlib import Path
import prepare_topmenu
import audit_sources

DATA_OVERRIDES = [
 ('path = "C:/GAT/Sample Images/2D_enteric_neuron_IF/181107_ms_distal_colon_GFAP_Hu_40X.tif";', None),
 ('cell_channel=2;', 'cell_channel=1;'),
 ('cell_counts_per_ganglia="true";', 'cell_counts_per_ganglia="false";'),
 ('ganglia_channel=1;', 'ganglia_channel="NA";'),
 ('ganglia_roi_path= "";', 'ganglia_roi_path= "NA";'),
 ('finetune_detection_parameters="false";', 'finetune_detection_parameters="true";'),
 ('probability=0.5;', 'probability=0.3;'),
 ('overlap=0.3;', 'overlap=0.7;'),
]

def configure(data, path):
    result=data; changes=[]
    for before, after in DATA_OVERRIDES:
        if after is None: after='path = "'+str(path).replace('\\','\\\\').replace('"','\\"')+'";'
        if result.count(before.encode())!=1:raise ValueError('Unexpected exact batch assignment: '+before)
        result=result.replace(before.encode(),after.encode())
        changes.append({'before':before,'after':after})
    return result,changes

def prepare(args):
    args.scenario='unchanged'
    prepare_topmenu.prepare(args)
    for variant in ('original','native'):
        root=args.output.resolve()/variant
        config=json.loads((root/'config.json').read_text())
        name='Batch_mode/batch_mode_example.ijm'
        source=root/'Fiji'/('scripts/GAT/'+name if variant=='original' else audit_sources.destination(name))
        data,changes=configure(source.read_bytes(),config['input'])
        case=root/'batch-case.ijm';case.write_bytes(data)
        config.update(probe_jar='LegacyMacroBatchMenuProbe.jar',batch_script=str(case),batch_source=str(source),
                      batch_data_overrides=changes,batch_script_sha256=hashlib.sha256(data).hexdigest())
        (root/'config.json').write_text(json.dumps(config,indent=2)+'\n')
        (root/'driver.ijm').write_text(prepare_topmenu.driver_macro(root/'config.json').replace('LegacyMacroTopMenuProbe.launch','LegacyMacroBatchMenuProbe.launch'))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for flag in ('runtime','output','overlay','candidate','native-worker'):p.add_argument('--'+flag,type=Path,required=True)
    prepare(p.parse_args())

if __name__=='__main__':main()

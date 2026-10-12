#!/usr/bin/env python3
"""Prepare a finite public Hu+marker or no-Hu top-menu pair; no JVM launch."""
import argparse
import json
from pathlib import Path
import prepare_topmenu
import audit_sources

SCRIPTS = {'hu-one-marker':'_Analyse Neuron (Multi-channel).ijm',
           'no-hu-one-marker':'_Analyse Neuron (Multi-channel - No Hu).ijm'}

def prepare(args):
    args.scenario='unchanged'
    prepare_topmenu.prepare(args)
    for variant in ('original','native'):
        root=args.output.resolve()/variant
        config=json.loads((root/'config.json').read_text())
        config['family']=args.family
        config['probe_jar']='LegacyMacroMarkerMenuProbe.jar'
        name=SCRIPTS[args.family]
        config['source_script']=str(root/'Fiji'/('scripts/GAT/'+name if variant=='original' else audit_sources.destination(name)))
        (root/'config.json').write_text(json.dumps(config,indent=2)+'\n')
        driver=prepare_topmenu.driver_macro(root/'config.json').replace('LegacyMacroTopMenuProbe.launch','LegacyMacroMarkerMenuProbe.launch')
        (root/'driver.ijm').write_text(driver)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for flag in ('runtime','output','overlay','candidate','native-worker'):p.add_argument('--'+flag,type=Path,required=True)
    p.add_argument('--family',choices=tuple(SCRIPTS),required=True)
    prepare(p.parse_args())

if __name__=='__main__':main()

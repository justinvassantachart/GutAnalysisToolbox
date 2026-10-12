"""Fabricated reports exercise only the capacity evidence gate, never runtime."""
import json
from pathlib import Path
import tempfile
import unittest
import copy
import compare_alignment_capacity as paired

import run_alignment_capacity as c


class CapacityEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        line, self.source = c.macro_source('original')
        macro = ('selectWindow("capacity512x512x257");\nsizeX=512;sizeY=512;\n'
                 'x_size=floor(sizeX*0.7);\ny_size=floor(sizeY*0.7);\nx0=floor(sizeX/6);\ny0=floor(sizeY/6);\n'
                 + line + '\nprint("GAT_CAPACITY_AFTER_ALIGNMENT");\n')
        (self.root / 'invoked.ijm').write_text(macro)
        inp, out = c.expected_hashes(); rx, ry = c.SHIFTS[2]
        rows = [[z, rx-c.SHIFTS[(z-1)%4][0], ry-c.SHIFTS[(z-1)%4][1]] for z in [2,1,*range(4,258)]]
        self.report = dict(schema_version=1, status=c.STATUS, scope='original-alignment-capacity-counterexample',variant='original',
                           whole_calcium_macro_executed=False, native_executed=False, dimensions=[512,512,257],
                           total_pixels=67371008,raw_pixel_bytes=67371008, previous_native_total_pixel_cap=67108864, bit_depth=8, seed=8291, reference=3,
                           macro_source=self.source, incorrect_pixels=0, csv_roundtrip=True, input_u8_sha256=inp,
                           output_u8_sha256=out, expected_output_u8_sha256=out,
                           plugin_class_sha256=c.artifacts()[0]['classes_sha256']['TemplateMatching/Align_slices.class'],
                           errors=[], ij_error=None, commands=['Align slices in stack...'], log='GAT_CAPACITY_AFTER_ALIGNMENT\n',
                           invoked_macro_sha256=c.sha(self.root/'invoked.ijm'), rows=rows)
        (self.root/'motion.csv').write_text('Slice,dX,dY\n'+''.join(','.join(map(str,r))+'\n' for r in rows))
        self.save()

    def save(self):
        (self.root/'report.json').write_text(json.dumps(self.report))

    def test_complete_fabricated_fixture_passes_only_gate(self):
        c.validate_result(self.root,self.source)

    def test_seeded_oracle_hashes_are_fixed_and_above_production_cap(self):
        self.assertGreater(c.WIDTH*c.HEIGHT*c.PLANES,67108864)
        self.assertEqual(('9b6c9ba9b6127b6a55ec74ccea75b5b0915305bbf54499714d97839be10946e7',
                          '6312e519a4a135d2bcc9227b6400eff5947b95c3e575ee99928f8b425c55cb37'),c.expected_hashes())

    def test_rejects_inconclusive_missing_or_wrong_pixel_result(self):
        for key,value in [('status','COMPILED_NOT_RUN'),('incorrect_pixels',1),('output_u8_sha256','0'*64),
                          ('plugin_class_sha256','0'*64),('total_pixels',67108864),('native_executed',True)]:
            old=self.report[key]; self.report[key]=value; self.save()
            with self.assertRaises(ValueError,msg=key): c.validate_result(self.root,self.source)
            self.report[key]=old
        self.save()

    def test_rejects_runtime_error_or_missing_continuation(self):
        for key,value in [('errors',['NullPointerException']),('commands',[]),('log',''),('log','GAT_CAPACITY_AFTER_ALIGNMENT\nLinkageError exception')]:
            old=self.report[key]; self.report[key]=value; self.save()
            with self.assertRaises(ValueError,msg=key): c.validate_result(self.root,self.source)
            self.report[key]=old
        self.save()

    def test_rejects_changed_actual_macro_with_consistent_hash(self):
        p=self.root/'invoked.ijm';p.write_text(p.read_text().replace('method=5','method=3'))
        self.report['invoked_macro_sha256']=c.sha(p); self.save()
        with self.assertRaises(ValueError): c.validate_result(self.root,self.source)

    def test_rejects_motion_csv_even_if_json_claims_pass(self):
        p=self.root/'motion.csv';p.write_text(p.read_text().replace('2,-7,7','2,0,0'))
        with self.assertRaises(ValueError): c.validate_result(self.root,self.source)

    def paired_fixture(self):
        temp=tempfile.TemporaryDirectory(dir=self.root);self.addCleanup(temp.cleanup)
        root=Path(temp.name);original=root/'original';native=root/'native'
        for directory,variant in [(original,'original'),(native,'native')]:
            result=directory/'result';result.mkdir(parents=True)
            report=copy.deepcopy(self.report);report['variant']=variant
            macro=(self.root/'invoked.ijm').read_text()
            if variant=='native':
                macro=macro.replace(c.macro_source('original')[0],c.macro_source('native')[0])
                report.update(status=c.NATIVE_STATUS,native_executed=True,commands=[],adapter_class_sha256='c'*64,
                              worker_processes={'9':'java TemplateMatching.NativeAlignmentMain input output'})
            (result/'invoked.ijm').write_text(macro);report['invoked_macro_sha256']=c.sha(result/'invoked.ijm')
            (result/'motion.csv').write_bytes((self.root/'motion.csv').read_bytes())
            (result/'report.json').write_text(json.dumps(report))
            stage={'exit_code':0,'resource_stop_reason':None,'rss_ceiling_kib':1048576,'timeout_seconds':180,
                   'observed_peak_process_tree_rss_kib':450000}
            launcher={'status':report['status'],'variant':variant,'macro_source':self.source,
                      'whole_calcium_macro_executed':False,'native_executed':variant=='native',
                      'production_classes':{'Features/Macros/LegacyTemplateMatching.class':'c'*64} if variant=='native' else {},
                      'worker_files':{'gat-native-alignment.jar':'d'*64} if variant=='native' else {},
                      'sources':{'fabricated_test_probe':'b'*64},'compilation':dict(stage),'execution':dict(stage),
                      'runtime_artifacts':[{'name':r['file'],'sha256':r['sha256']} for r in c.artifacts()]}
            (directory/'launcher.json').write_text(json.dumps(launcher))
        return original,native

    def test_complete_fabricated_pair_passes_only_gate(self):
        a,b=self.paired_fixture();self.assertEqual('PASS_PAIRED_CAPACITY_CONTROL',paired.compare(a,b)['status'])

    def test_pair_rejects_resource_stop_or_relaxed_limit(self):
        for change in [{'resource_stop_reason':'RSS'},{'rss_ceiling_kib':2097152},{'observed_peak_process_tree_rss_kib':1048577}]:
            a,b=self.paired_fixture();p=b/'launcher.json';r=json.loads(p.read_text());r['execution'].update(change);p.write_text(json.dumps(r))
            self.assertEqual('FAIL_OR_INCOMPLETE',paired.compare(a,b)['status'])

    def test_pair_rejects_missing_real_native_worker(self):
        a,b=self.paired_fixture();p=b/'result/report.json';r=json.loads(p.read_text());r['worker_processes']={};p.write_text(json.dumps(r))
        self.assertEqual('FAIL_OR_INCOMPLETE',paired.compare(a,b)['status'])

    def test_pair_rejects_source_or_original_contamination(self):
        for side,change in [('native',{'sources':{}}),('original',{'production_classes':{'unexpected':'x'}})]:
            a,b=self.paired_fixture();p=(a if side=='original' else b)/'launcher.json';r=json.loads(p.read_text());r.update(change);p.write_text(json.dumps(r))
            self.assertEqual('FAIL_OR_INCOMPLETE',paired.compare(a,b)['status'])


if __name__=='__main__': unittest.main()

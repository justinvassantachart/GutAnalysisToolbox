"""Synthetic validator/setup counterexamples only, never GUI/model evidence."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import prepare_batch_topmenu as batch
import compare_marker_topmenu as marker
import compare_batch_topmenu as batch_compare
import prepare_marker_topmenu

ROOT=Path(__file__).resolve().parents[2]


def unit_pair():
    roi=['Marker_1',0,0,0,0,0,[[3.,4.],[6.,4.],[6.,8.]]]
    return {'family':'no-hu-one-marker','scenario':'unchanged','parameters':{'marker_no_manual':'2'},
            'input':{'channels':2},'fixture_sha256':'unit-fixture',
            'reviews':{'Marker':{'before':[roi],'after':[roi]}},
            'exports':[{'path':'unit.zip','reopened_rois':[roi]},{'path':'unit.csv','reopened_csv':'Marker\n1\n'}]}


class BatchPreparationTest(unittest.TestCase):
    def test_only_eight_data_assignments_change(self):
        original=(ROOT/'Batch_mode/batch_mode_example.ijm').read_bytes()
        configured,changes=batch.configure(original,'/public data/a.tif')
        self.assertEqual(len(changes),8)
        self.assertIn(b'run(" Analyse Neurons",args);',configured)
        self.assertIn(b'probability=0.3;',configured)
        self.assertIn(b'overlap=0.7;',configured)
        for change in reversed(changes):configured=configured.replace(change['after'].encode(),change['before'].encode())
        self.assertEqual(configured,original)

    def test_missing_or_duplicate_assignment_rejected(self):
        original=(ROOT/'Batch_mode/batch_mode_example.ijm').read_bytes()
        for changed in [original.replace(b'probability=0.5;',b'probability=0.6;'),original+b'\nprobability=0.5;']:
            with self.assertRaises(ValueError):batch.configure(changed,'/a.tif')

    def test_distinct_marker_entry_scripts(self):
        self.assertEqual(set(prepare_marker_topmenu.SCRIPTS),{'hu-one-marker','no-hu-one-marker'})
        self.assertEqual(len(set(prepare_marker_topmenu.SCRIPTS.values())),2)

    def test_unexecuted_extended_suites_cannot_pass(self):
        with tempfile.TemporaryDirectory() as d:
            for checker in [marker,batch_compare]:self.assertEqual(checker.compare(Path(d))['status'],'FAIL_OR_INCOMPLETE')


class MarkerComparatorTest(unittest.TestCase):
    def compare(self,other,atol=0):
        with patch.object(marker,'load_side',side_effect=[unit_pair(),other]):
            return marker.compare(Path('/unit-evidence-only'),atol)

    def test_exact_unit_pair(self):
        self.assertEqual(self.compare(unit_pair())['status'],'PASS_PAIRED_TOP_MENU_WORKFLOW_SCOPE')

    def test_channel_parameter_change_rejected(self):
        other=unit_pair();other['parameters']['marker_no_manual']='1'
        self.assertEqual(self.compare(other)['status'],'FAIL_TOP_MENU_DIFFERENCES')

    def test_wrong_marker_order_rejected(self):
        other=unit_pair();other['reviews']['Wrong']=other['reviews'].pop('Marker')
        self.assertEqual(self.compare(other)['status'],'FAIL_OR_INCOMPLETE')

    def test_geometry_count_and_csv_not_hidden(self):
        other=copy.deepcopy(unit_pair());other['reviews']['Marker']['before'][0][6][0][0]+=.1
        self.assertEqual(self.compare(other)['status'],'FAIL_TOP_MENU_DIFFERENCES')
        other=unit_pair();other['exports'][1]['reopened_csv']='Marker\n2\n'
        self.assertEqual(self.compare(other,100)['status'],'FAIL_TOP_MENU_DIFFERENCES')
        other=unit_pair();other['reviews']['Marker']['before']=[]
        self.assertEqual(self.compare(other,100)['status'],'FAIL_OR_INCOMPLETE')


if __name__=='__main__':unittest.main()

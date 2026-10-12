import importlib.util
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('overlay', Path(__file__).resolve().parents[1] / 'build_overlay.py')
overlay = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(overlay)


class OverlayContractTest(unittest.TestCase):
    def test_all_native_call_sites_are_pinned(self):
        _, info = overlay.generated_files()
        self.assertEqual(8, info['native_stardist_call_sites'])
        self.assertEqual(3, info['native_alignment_call_sites'])
        self.assertEqual(8, sum(c['count'] for f in info['files'] for c in f['substitutions'] if c['kind'] == 'stardist-command'))
        self.assertEqual(3, sum(c['count'] for f in info['files'] for c in f['substitutions'] if c['kind'] == 'alignment-command'))

    def test_reverse_allowlisted_substitutions_restore_all_source_bytes(self):
        output, info = overlay.generated_files()
        for record in info['files']:
            data = output[record['destination']]
            for change in reversed(record['substitutions']):
                data = data.replace(change['after'].encode(), change['before'].encode())
            original = (overlay.ROOT / record['source']).read_bytes()
            self.assertEqual(original, data, record['source'])

    def test_each_generated_command_leaf_is_unique_and_namespaced(self):
        paths = overlay.source_paths()
        destination_names = [overlay.destination_path(p).name for p in paths if p.suffix in ('.ijm', '.py')]
        self.assertEqual(len(destination_names), len(set(destination_names)))
        self.assertTrue(all('[MacroFork]' in name for name in destination_names))
        self.assertTrue(set(destination_names).isdisjoint(p.name for p in paths))

    def test_batch_targets_the_fork_menu(self):
        output, _ = overlay.generated_files()
        data = output['scripts/GAT MacroFork/Batch_mode/batch_mode_example [MacroFork].ijm']
        self.assertIn(b'run(" Analyse Neurons [MacroFork]",args);', data)
        self.assertNotIn(b'run(" Analyse Neurons",args);', data)

    def test_settings_are_not_rewritten_or_reset(self):
        with tempfile.TemporaryDirectory() as folder:
            settings = Path(folder) / 'settings.ijm'
            data = b'Parameters\tValues\r\nprob_neuron\t0.719283456\r\n'
            settings.write_bytes(data)
            output, _ = overlay.generated_files(settings=settings)
            self.assertEqual(data, output['scripts/GAT MacroFork/Tools/commands/gat_settings [MacroFork].ijm'])
            self.assertEqual(data, settings.read_bytes(), 'Original custom settings must remain unchanged')

    def test_unrecognized_stardist_call_site_fails_closed(self):
        with self.assertRaises(ValueError):
            overlay.transform(Path('unknown.ijm'), b'run("Command From Macro", "command=[de.csbdresden.stardist.StarDist2D]");', [])

    def test_original_scientific_and_ui_statements_remain(self):
        output, info = overlay.generated_files()
        for record in info['files']:
            if not record['source'].endswith('.ijm'):
                continue
            original = (overlay.ROOT / record['source']).read_bytes()
            generated = output[record['destination']]
            for marker in (b'#@', b'Ext.CLIJ2_', b'run("RGB Color")', b'do=Open', b'roiManager(', b'getPixelSize('):
                self.assertEqual(original.count(marker), generated.count(marker), (record['source'], marker))


if __name__ == '__main__':
    unittest.main()

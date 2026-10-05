import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
import stat

SPEC = importlib.util.spec_from_file_location('fresh', Path(__file__).with_name('run_fresh_fiji.py'))
fresh = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fresh)


class ArchiveSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.path = self.root / 'archive.zip'
    def tearDown(self):
        self.temp.cleanup()
    def archive(self, names):
        with zipfile.ZipFile(self.path, 'w') as z:
            for name, content in names:
                z.writestr(name, content)
        return self.path
    def test_actual_gat_reference_uses_four_tiles(self):
        reference = fresh.MANIFEST['neuron_reference']
        self.assertEqual(reference['tiles'], 4)
        self.assertEqual(reference['corpus_case'], 'repo_DYM_22_7_Pr_Hu_crop_c1_t1_x0_y0')
        self.assertEqual(fresh.MANIFEST['expected_neuron_label_sha256'], 'ea1767df58491cc03927e121943d955708450d091f3416b2493e1c93e51cd443')
    def test_empty_engine_directory_is_never_initialized(self):
        directory=self.root/'engines';directory.mkdir()
        with self.assertRaises(ValueError):
            fresh.verify_engine_files(directory,[{'filename':'real.jar','sha256':'0'*64}])
    def test_engine_requires_exact_bytes_and_no_extra_jars(self):
        directory=self.root/'engines';directory.mkdir();jar=directory/'real.jar';jar.write_bytes(b'verified')
        artifact={'filename':'real.jar','sha256':fresh.sha256(jar)}
        self.assertEqual(1,len(fresh.verify_engine_files(directory,[artifact])))
        jar.write_bytes(b'changed')
        with self.assertRaises(ValueError):fresh.verify_engine_files(directory,[artifact])
        jar.write_bytes(b'verified');(directory/'unrequested.jar').write_bytes(b'extra')
        with self.assertRaises(ValueError):fresh.verify_engine_files(directory,[artifact])
    def test_native_binary_is_separately_required(self):
        directory=self.root/'engine';directory.mkdir();jar=directory/'engine.jar';jar.write_bytes(b'engine')
        native=directory/'native.jar';native.write_bytes(b'cpu');native_hash=fresh.sha256(native);native.unlink()
        artifacts=[{'filename':'engine.jar','sha256':fresh.sha256(jar)},
                   {'filename':'native.jar','sha256':native_hash,'platform':'macosx-arm64'}]
        fresh.verify_engine_files(directory,artifacts)
        with self.assertRaises(ValueError):fresh.verify_engine_files(directory,artifacts,include_native=True)
        native.write_bytes(b'cpu');self.assertEqual(2,len(fresh.verify_engine_files(directory,artifacts,True)))
    def test_model_conflict_is_reported_without_overwrite(self):
        model=self.root/'rdf.yaml';model.write_bytes(b'actual descriptor')
        with self.assertRaises(ValueError):fresh.verify_required_assets(self.root,[{'path':'rdf.yaml','sha256':'0'*64}])
        self.assertEqual(b'actual descriptor',model.read_bytes())
    def test_engine_manifest_matches_previously_validated_artifacts(self):
        dependencies=json.loads((Path(__file__).resolve().parents[2]/'native-inference/validation/workflows/dependencies.json').read_text())['artifacts']
        expected=[a for a in dependencies if 'engine' in a['groups'] and a.get('platform','macosx-arm64')=='macosx-arm64']
        self.assertEqual(expected,fresh.MANIFEST['ganglia_engine']['artifacts'])
        self.assertEqual(8,len(expected))
        self.assertEqual('2.0.0',fresh.MANIFEST['ganglia_engine']['catalog_resolved_version'])
    def test_normal_layout(self):
        self.archive([('Fiji/', ''),('Fiji/jars/ij.jar','data')])
        self.assertEqual(4, fresh.safe_archive(self.path, 'Fiji', True))
    def test_traversal_absolute_backslash_and_wrong_root(self):
        for name in ('../evil','/tmp/evil','Fiji/../evil','Fiji\\evil','Fiji.app/evil'):
            with self.subTest(name=name):
                self.archive([(name,'x')])
                with self.assertRaises(ValueError):
                    fresh.safe_archive(self.path, 'Fiji', True)
    def test_duplicate_member(self):
        self.archive([('Fiji/a','x'),('Fiji/a','y')])
        with self.assertRaises(ValueError):
            fresh.safe_archive(self.path, 'Fiji', True)
    def test_symlink_escape_and_write_through(self):
        for target, child in (('../../escape',None),('other','Fiji/link/child')):
            with zipfile.ZipFile(self.path,'w') as z:
                info=zipfile.ZipInfo('Fiji/link'); info.external_attr=(stat.S_IFLNK|0o777)<<16
                z.writestr(info,target)
                if child:z.writestr(child,'x')
            with self.assertRaises(ValueError):fresh.safe_archive(self.path,'Fiji',True)
    def test_safe_distribution_symlink_but_no_overlay_symlinks(self):
        with zipfile.ZipFile(self.path,'w') as z:
            info=zipfile.ZipInfo('Fiji/java/link');info.external_attr=(stat.S_IFLNK|0o777)<<16
            z.writestr(info,'../real')
        fresh.safe_archive(self.path,'Fiji',True)
        with self.assertRaises(ValueError):fresh.safe_archive(self.path)
    def test_overlay_rejects_worker_classes_in_plugin(self):
        self.archive([('UI/GatPluginUI.class','x'),('plugins.config','x'),('org/tensorflow/types/TFloat32.class','x')])
        with zipfile.ZipFile(self.path) as z:
            with self.assertRaises(ValueError):fresh.validate_gat_jar(z)
    def test_pin_conflict_is_reported_not_repaired(self):
        pin=fresh.MANIFEST['expected_plugin_artifacts'][0]
        records=[{'path':'plugins/'+pin['file'],'sha256':'0'*64,'bytes':42}]
        compared=fresh.compare_pins(records)
        self.assertEqual('CONFLICT',compared[0]['status'])
        self.assertEqual('0'*64,records[0]['sha256'])
    def test_overlay_rejects_wrong_source_before_mutating(self):
        fiji=self.root/'Fiji';(fiji/'plugins').mkdir(parents=True);(fiji/'jars').mkdir()
        self.archive([('BUILD_INFO.json',json.dumps({'source_commit':'0'*40,'source_worktree_modified':False}))])
        with self.assertRaises(ValueError):fresh.overlay(fiji,archive=self.path,source_commit='1'*40,evidence=self.root/'evidence')
        self.assertEqual([],list((fiji/'plugins').iterdir()))
    def test_existing_plugins_not_replaced_arbitrarily(self):
        fiji=self.root/'Fiji';(fiji/'plugins').mkdir(parents=True);(fiji/'jars').mkdir()
        with zipfile.ZipFile(fiji/'plugins'/'unrelated.jar','w') as z:z.writestr('Other.class','untouched')
        with zipfile.ZipFile(fiji/'plugins'/'old-GAT.jar','w') as z:z.writestr('UI/GatPluginUI.class','old')
        self.archive([('UI/GatPluginUI.class','new'),('plugins.config','entry')])
        result=fresh.overlay(fiji,plugin=self.path,source_commit='1'*40,evidence=self.root/'evidence')
        self.assertTrue((fiji/'plugins'/'unrelated.jar').exists())
        self.assertFalse((fiji/'plugins'/'old-GAT.jar').exists())
        self.assertEqual(1,len(result['displaced_GAT_only']))
        self.assertFalse(result['runtime_dependency_jars_changed'])
    def test_environment_ignores_java_injections(self):
        from unittest.mock import patch
        with patch.dict('os.environ', {'JAVA_TOOL_OPTIONS':'bad','JAVA_HOME':'bad','CLASSPATH':'bad'}):
            env=fresh.clean_env(self.root)
        self.assertNotIn('JAVA_TOOL_OPTIONS',env)
        self.assertNotIn('JAVA_HOME',env)
        self.assertNotIn('CLASSPATH',env)
        self.assertEqual(str(self.root),env['HOME'])


if __name__=='__main__':unittest.main()
